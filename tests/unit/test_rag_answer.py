from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.config.models import AnswerReadModel
from app.domain.models import KnowledgeDocumentKind, OfferingId, ProductType
from app.domain.monitoring import AnswerFailureCode, AnswerStatus, QuestionCommand
from app.domain.retrieval import (
    RankExplanation,
    RetrievalHit,
    RetrievalResult,
    RetrievalStatus,
)
from app.services.answer_read_model import TariffAnswerRouter
from app.services.rag_answer import (
    AnswerDraft,
    AnswerDraftCitation,
    RagAnswerService,
)
from app.tools import configure_services

NOW = datetime(2026, 9, 19, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"


def _hit(kind: KnowledgeDocumentKind, content: str, suffix: str) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=f"chunk-{suffix}",
        content=content,
        lexical_score=0.9,
        vector_score=0.9,
        final_score=0.9,
        rank_explanation=RankExplanation(
            lexical_rank=1,
            vector_rank=1,
            lexical_weight=0.45,
            vector_weight=0.55,
            rrf_k=60,
            rrf_score=0.9,
            relevance_score=0.9,
            formula="test",
        ),
        document_id=uuid4(),
        document_checksum="a" * 64,
        document_name="Consumer loans",
        source_url=URL,
        final_url=URL,
        page_start=1,
        page_end=1,
        section="Rates",
        language="en",
        retrieved_at=NOW,
        extraction_method="browser",
        quality_score=1,
        offering_id=OfferingId.CONSUMER_STANDARD,
        document_kind=kind,
    )


class _Retriever:
    def __init__(self, result: RetrievalResult) -> None:
        self.result = result
        self.requests = []

    async def retrieve(self, request):
        self.requests.append(request)
        return self.result


class _Generator:
    def __init__(self, draft: AnswerDraft) -> None:
        self.draft = draft
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> AnswerDraft:
        self.prompts.append(prompt)
        return self.draft


class _SequenceGenerator:
    def __init__(self, drafts: tuple[AnswerDraft, ...]) -> None:
        self.drafts = iter(drafts)
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> AnswerDraft:
        self.prompts.append(prompt)
        return next(self.drafts)


class _FailingGenerator:
    async def generate(self, prompt: str) -> AnswerDraft:
        raise RuntimeError("credential or provider detail must not escape")


@pytest.mark.asyncio
async def test_answer_uses_summary_for_precision_and_source_for_citation() -> None:
    summary = _hit(
        KnowledgeDocumentKind.OFFERING_SUMMARY,
        "Nominal interest rate: 13.5%",
        "summary",
    )
    source = _hit(
        KnowledgeDocumentKind.SOURCE,
        "The nominal interest rate is 13.5% for this consumer loan.",
        "source",
    )
    retriever = _Retriever(
        RetrievalResult(
            status=RetrievalStatus.FOUND,
            hits=(summary, source),
            candidates_considered=2,
        )
    )
    generator = _Generator(
        AnswerDraft(
            answer="The nominal rate is 13.5%.",
            citations=(
                AnswerDraftCitation(
                    chunk_id=source.chunk_id,
                    excerpt="nominal interest rate is 13.5%",
                ),
            ),
        )
    )

    result = await RagAnswerService(retriever, generator).answer(
        QuestionCommand(
            query="What is the rate?",
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.CONSUMER_STANDARD,
        )
    )

    assert result.status is AnswerStatus.ANSWERED
    assert result.citations[0].source_url == source.source_url
    assert len(generator.prompts) == 1
    assert "kind=offering_summary" in generator.prompts[0]
    assert "kind=source" in generator.prompts[0]
    assert retriever.requests[0].offering_id is OfferingId.CONSUMER_STANDARD


@pytest.mark.asyncio
async def test_answer_abstains_for_ambiguous_or_invalid_evidence() -> None:
    source = _hit(KnowledgeDocumentKind.SOURCE, "Rate is 13.5%.", "source")
    retriever = _Retriever(
        RetrievalResult(
            status=RetrievalStatus.FOUND,
            hits=(source,),
            candidates_considered=1,
        )
    )
    generator = _Generator(
        AnswerDraft(
            answer="Rate is 12%.",
            citations=(
                AnswerDraftCitation(chunk_id=source.chunk_id, excerpt="Rate is 12%."),
            ),
        )
    )
    service = RagAnswerService(retriever, generator)

    ambiguous = await service.answer(QuestionCommand(query="What is the rate?"))
    invalid = await service.answer(
        QuestionCommand(query="Rate?", product=ProductType.CONSUMER_LOAN)
    )

    assert ambiguous.status is AnswerStatus.AMBIGUOUS_PRODUCT
    assert invalid.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert invalid.failure_code is AnswerFailureCode.INVALID_CITATION
    assert len(generator.prompts) == 2
    assert "CITATION REPAIR" in generator.prompts[1]
    assert invalid.audit_metadata["citation_error"] == "excerpt_not_in_chunk"


@pytest.mark.asyncio
async def test_answer_contains_generator_failure_without_model_prose() -> None:
    source = _hit(KnowledgeDocumentKind.SOURCE, "Rate is 13.5%.", "source")
    service = RagAnswerService(
        _Retriever(
            RetrievalResult(
                status=RetrievalStatus.FOUND,
                hits=(source,),
                candidates_considered=1,
            )
        ),
        _FailingGenerator(),
    )

    result = await service.answer(
        QuestionCommand(query="Rate?", product=ProductType.CONSUMER_LOAN)
    )

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert result.answer is None
    assert result.citations == ()
    assert result.failure_code is AnswerFailureCode.GENERATION_FAILED
    assert result.audit_metadata["reason"] == "RuntimeError"


class _UnusedStructuredService:
    async def answer(self, plan, question):  # pragma: no cover - legacy mode
        raise AssertionError("legacy read model must not call the structured path")


@pytest.mark.asyncio
async def test_http_and_adk_question_adapters_share_answer_service() -> None:
    source = _hit(KnowledgeDocumentKind.SOURCE, "Rate is 13.5%.", "source")
    service = RagAnswerService(
        _Retriever(
            RetrievalResult(
                status=RetrievalStatus.FOUND,
                hits=(source,),
                candidates_considered=1,
            )
        ),
        _Generator(
            AnswerDraft(
                answer="The rate is 13.5%.",
                citations=(
                    AnswerDraftCitation(
                        chunk_id=source.chunk_id,
                        excerpt="Rate is 13.5%.",
                    ),
                ),
            )
        ),
    )
    app = FastAPI()
    app.state.answer_service = service
    app.state.answer_router = TariffAnswerRouter(
        _UnusedStructuredService(), service, AnswerReadModel.LEGACY
    )
    app.include_router(router)
    configure_services(None, service)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/questions",
                json={"query": "Rate?", "product": "consumer_loan"},
            )
    finally:
        configure_services(None, None)

    assert response.status_code == 200
    assert response.json()["status"] == "answered"


@pytest.mark.asyncio
async def test_answer_repairs_invalid_citation_once(caplog) -> None:
    source = _hit(KnowledgeDocumentKind.SOURCE, "Rate is 13.5%.", "source")
    generator = _SequenceGenerator(
        (
            AnswerDraft(
                answer="The rate is 13.5%.",
                citations=(
                    AnswerDraftCitation(
                        chunk_id=source.chunk_id, excerpt="Rate is 13.5 percent"
                    ),
                ),
            ),
            AnswerDraft(
                answer="The rate is 13.5%.",
                citations=(
                    AnswerDraftCitation(
                        chunk_id=source.chunk_id, excerpt="Rate is 13.5%."
                    ),
                ),
            ),
        )
    )
    service = RagAnswerService(
        _Retriever(
            RetrievalResult(
                status=RetrievalStatus.FOUND,
                hits=(source,),
                candidates_considered=1,
            )
        ),
        generator,
    )

    result = await service.answer(
        QuestionCommand(query="Rate?", product=ProductType.CONSUMER_LOAN)
    )

    assert result.status is AnswerStatus.ANSWERED
    assert len(generator.prompts) == 2
    assert "CITATION REPAIR" in generator.prompts[1]
    assert "reason=excerpt_not_in_chunk" in caplog.text
    assert "Rate is 13.5 percent" not in caplog.text
