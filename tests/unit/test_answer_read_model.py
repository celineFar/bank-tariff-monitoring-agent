from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.config import load_settings
from app.config.models import AnswerReadModel
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    AnswerCitation,
    AnswerResult,
    AnswerStatus,
    QuestionCommand,
)
from app.domain.structured_tariffs import (
    FieldPath,
    QueryOperation,
    QueryStatus,
    ResolutionPlan,
)
from app.services.answer_read_model import TariffAnswerRouter
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.fixtures.evaluation_corpus import EvaluationRepository

NOW = datetime(2026, 9, 22, tzinfo=UTC)
QUESTION = "What is the nominal interest rate of the Overdraft?"
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"


class _Legacy:
    def __init__(self, result: AnswerResult) -> None:
        self.result = result
        self.calls: list[QuestionCommand] = []

    async def answer(self, command: QuestionCommand) -> AnswerResult:
        self.calls.append(command)
        return self.result


class _Structured:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def answer(self, plan, question):
        self.calls.append(question)
        raise AssertionError("legacy mode must not reach the structured read model")


def _legacy_answer() -> AnswerResult:
    return AnswerResult(
        status=AnswerStatus.ANSWERED,
        answer="Legacy answer.",
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        citations=(
            AnswerCitation(
                chunk_id="chunk-1",
                source_url=URL,
                document_name="Overdraft terms",
                excerpt="Nominal rate schedule",
            ),
        ),
        as_of=NOW,
    )


def _plan() -> ResolutionPlan:
    issued = datetime.now(UTC)
    return ResolutionPlan(
        session_id="session-1",
        turn_id="turn-1",
        question_sha256=hashlib.sha256(QUESTION.encode()).hexdigest(),
        issued_at=issued,
        expires_at=issued + timedelta(minutes=5),
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.OVERDRAFT,),
        operation=QueryOperation.SINGLE,
        fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
    )


def _router(read_model: AnswerReadModel, legacy: _Legacy) -> TariffAnswerRouter:
    structured = (
        StructuredTariffQueryService(EvaluationRepository())
        if read_model is AnswerReadModel.STRUCTURED
        else _Structured()
    )
    return TariffAnswerRouter(structured, legacy, read_model)


def test_default_settings_select_the_structured_read_model() -> None:
    settings = load_settings(_env_file=None)

    assert settings.tariff_queries.answer_read_model is AnswerReadModel.STRUCTURED


def test_configuration_can_roll_the_cutover_back_to_the_legacy_path() -> None:
    settings = load_settings(_env_file=None, tariff_answer_read_model="legacy")

    assert settings.tariff_queries.answer_read_model is AnswerReadModel.LEGACY


@pytest.mark.asyncio
async def test_structured_mode_answers_a_plan_from_typed_accepted_facts() -> None:
    legacy = _Legacy(_legacy_answer())
    router = _router(AnswerReadModel.STRUCTURED, legacy)

    result = await router.answer_plan(_plan(), QUESTION)

    assert result.status is QueryStatus.ANSWERED
    assert result.facts and all(fact.evidence for fact in result.facts)
    assert not legacy.calls


@pytest.mark.asyncio
async def test_legacy_mode_answers_the_same_plan_within_its_authorized_scope() -> None:
    legacy = _Legacy(_legacy_answer())
    router = _router(AnswerReadModel.LEGACY, legacy)

    result = await router.answer_plan(_plan(), QUESTION)

    assert result.status is QueryStatus.ANSWERED
    assert result.metadata["read_model"] == "legacy"
    assert result.offering_ids == (OfferingId.OVERDRAFT,)
    assert legacy.calls[0].offering_id is OfferingId.OVERDRAFT
    assert legacy.calls[0].product is ProductType.CONSUMER_LOAN


@pytest.mark.asyncio
async def test_legacy_abstention_maps_to_a_typed_insufficient_evidence_result() -> None:
    legacy = _Legacy(
        AnswerResult(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            product=ProductType.CONSUMER_LOAN,
        )
    )
    router = _router(AnswerReadModel.LEGACY, legacy)

    result = await router.answer_plan(_plan(), QUESTION)

    assert result.status is QueryStatus.INSUFFICIENT_EVIDENCE
    assert result.answer is None


@pytest.mark.asyncio
async def test_typed_api_question_keeps_citations_after_cutover() -> None:
    legacy = _Legacy(_legacy_answer())
    router = _router(AnswerReadModel.STRUCTURED, legacy)

    result = await router.answer_question(
        QuestionCommand(
            query=QUESTION,
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.OVERDRAFT,
        )
    )

    assert result.status is AnswerStatus.ANSWERED
    assert result.citations
    assert all(item.evidence_id for item in result.citations)
    assert all(item.excerpt for item in result.citations)
    assert result.audit_metadata["read_model"] == "structured"
    assert not legacy.calls


@pytest.mark.asyncio
async def test_typed_api_question_without_product_stays_ambiguous() -> None:
    router = _router(AnswerReadModel.STRUCTURED, _Legacy(_legacy_answer()))

    result = await router.answer_question(QuestionCommand(query=QUESTION))

    assert result.status is AnswerStatus.AMBIGUOUS_PRODUCT


@pytest.mark.asyncio
async def test_unresolvable_family_scope_abstains_instead_of_widening() -> None:
    router = _router(AnswerReadModel.STRUCTURED, _Legacy(_legacy_answer()))

    result = await router.answer_question(
        QuestionCommand(
            query="What is the nominal interest rate?",
            product=ProductType.CONSUMER_LOAN,
        )
    )

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert "comparison or rank" in str(result.audit_metadata["reason"])


@pytest.mark.asyncio
async def test_structured_abstention_does_not_leak_an_uncited_answer() -> None:
    router = _router(AnswerReadModel.STRUCTURED, _Legacy(_legacy_answer()))

    result = await router.answer_question(
        QuestionCommand(
            query="What application fee applies to the Express Mortgage?",
            product=ProductType.MORTGAGE,
            offering_id=OfferingId.MORTGAGE_EXPRESS,
        )
    )

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert result.answer is None
    assert result.citations == ()
    assert result.audit_metadata["query_status"] == "missing"


def test_retention_report_is_not_ready_without_any_active_fact() -> None:
    from app.services.evidence_retention_audit import EvidenceRetentionReport

    empty = EvidenceRetentionReport(
        active_found_facts=0,
        active_evidence_rows=0,
        facts_without_evidence=0,
        evidence_without_locator=0,
        evidence_without_document=0,
        evidence_with_checksum_drift=0,
        legacy_source_chunks=1010,
        legacy_summary_chunks=0,
        legacy_embedded_chunks=1010,
        gaps=(),
    )

    assert not empty.ready_to_deprecate_legacy_embeddings
