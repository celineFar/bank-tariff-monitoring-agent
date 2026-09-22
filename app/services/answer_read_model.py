"""Reversible application-level switch between the legacy and structured paths.

The structured read model is the default after cutover. Setting
``TARIFF_ANSWER_READ_MODEL=legacy`` restores the old RAG answer path for every
ordinary question without a code change, so the cutover can be rolled back
while production behaviour is still being observed. The model cannot change
this setting; only configuration can.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from app.config.models import AnswerReadModel
from app.domain.monitoring import (
    AnswerCitation,
    AnswerFailureCode,
    AnswerResult,
    AnswerStatus,
    QuestionCommand,
)
from app.domain.structured_tariffs import (
    QueryStatus,
    ResolutionPlan,
    TariffQueryResult,
)
from app.services.rag_answer import RagAnswerService
from app.services.structured_query_planning import issue_typed_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService

logger = logging.getLogger(__name__)


__all__ = [
    "AnswerReadModel",
    "TariffAnswerRouter",
    "structured_to_answer_result",
]

_MAX_EXCERPT_CHARS = 1500


def _document_name(evidence) -> str:
    section = evidence.locator.get("section") if evidence.locator else None
    if isinstance(section, str) and section.strip():
        return section.strip()[:1000]
    return evidence.source_item_id[:1000]


def _page(evidence) -> int | None:
    page = evidence.locator.get("page_start") if evidence.locator else None
    return page if isinstance(page, int) and page >= 1 else None


def structured_to_answer_result(
    result: TariffQueryResult, command: QuestionCommand
) -> AnswerResult:
    """Adapt a typed structured result for the legacy `AnswerResult` contract."""
    citations = tuple(
        AnswerCitation(
            chunk_id=f"fact:{fact.fact_id}",
            evidence_id=evidence.evidence_id,
            source_url=evidence.source_url,
            document_name=_document_name(evidence),
            excerpt=evidence.quote[:_MAX_EXCERPT_CHARS],
            page=_page(evidence),
            section=(
                evidence.locator.get("section")
                if isinstance(evidence.locator.get("section"), str)
                else None
            ),
        )
        for fact in result.facts
        if fact.fact_id
        for evidence in fact.evidence
    )
    offering_id = (
        result.offering_ids[0] if len(result.offering_ids) == 1 else command.offering_id
    )
    if (
        result.status is QueryStatus.ANSWERED
        and result.answer
        and citations
        and result.as_of is not None
    ):
        return AnswerResult(
            status=AnswerStatus.ANSWERED,
            answer=result.answer,
            product=result.product,
            offering_id=offering_id,
            citations=citations,
            as_of=result.as_of,
            audit_metadata={
                "read_model": AnswerReadModel.STRUCTURED.value,
                "operation": result.operation.value,
                "offering_ids": [item.value for item in result.offering_ids],
                "facts": len(result.facts),
            },
        )
    return AnswerResult(
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        product=result.product,
        offering_id=offering_id,
        failure_code=AnswerFailureCode.INSUFFICIENT_EVIDENCE,
        audit_metadata={
            "read_model": AnswerReadModel.STRUCTURED.value,
            "operation": result.operation.value,
            "query_status": result.status.value,
            "reason": result.reason,
        },
    )


class TariffAnswerRouter:
    """One place that decides which read model answers an ordinary question."""

    def __init__(
        self,
        structured: StructuredTariffQueryService,
        legacy: RagAnswerService,
        read_model: AnswerReadModel = AnswerReadModel.STRUCTURED,
    ) -> None:
        self._structured = structured
        self._legacy = legacy
        self._read_model = read_model

    @property
    def read_model(self) -> AnswerReadModel:
        return self._read_model

    @property
    def structured_service(self) -> StructuredTariffQueryService:
        return self._structured

    @property
    def legacy_service(self) -> RagAnswerService:
        return self._legacy

    async def answer_plan(
        self, plan: ResolutionPlan, question: str
    ) -> TariffQueryResult:
        """Answer a scope-authorized turn; the plan bounds both read models."""
        if self._read_model is AnswerReadModel.STRUCTURED:
            return await self._structured.answer(plan, question)
        legacy = await self._legacy.answer(
            QuestionCommand(
                query=question,
                product=plan.product,
                offering_id=(
                    plan.offering_ids[0] if len(plan.offering_ids) == 1 else None
                ),
            )
        )
        return _legacy_to_query_result(legacy, plan)

    async def answer_question(self, command: QuestionCommand) -> AnswerResult:
        """Answer a typed API request that carries its own validated scope."""
        if self._read_model is AnswerReadModel.LEGACY:
            return await self._legacy.answer(command)
        if command.product is None:
            return AnswerResult(
                status=AnswerStatus.AMBIGUOUS_PRODUCT,
                failure_code=AnswerFailureCode.AMBIGUOUS_PRODUCT,
                audit_metadata={"read_model": AnswerReadModel.STRUCTURED.value},
            )
        try:
            plan = issue_typed_resolution_plan(
                command.query,
                product=command.product,
                offering_ids=(
                    (command.offering_id,) if command.offering_id is not None else ()
                ),
                session_id=f"api-{uuid4()}",
                turn_id=str(uuid4()),
            )
        except ValueError as exc:
            logger.info(
                "answer.unresolved_typed_scope product=%s offering=%s reason=%s",
                command.product.value,
                command.offering_id.value if command.offering_id else None,
                exc,
            )
            return AnswerResult(
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                product=command.product,
                offering_id=command.offering_id,
                failure_code=AnswerFailureCode.INSUFFICIENT_EVIDENCE,
                audit_metadata={
                    "read_model": AnswerReadModel.STRUCTURED.value,
                    "reason": str(exc),
                },
            )
        return structured_to_answer_result(
            await self._structured.answer(plan, command.query), command
        )


def _legacy_to_query_result(
    legacy: AnswerResult, plan: ResolutionPlan
) -> TariffQueryResult:
    """Wrap a legacy answer so rollback keeps one typed tool contract."""
    answered = legacy.status is AnswerStatus.ANSWERED
    return TariffQueryResult(
        status=QueryStatus.ANSWERED if answered else QueryStatus.INSUFFICIENT_EVIDENCE,
        operation=plan.operation,
        product=plan.product,
        offering_ids=plan.offering_ids,
        answer=legacy.answer,
        reason=(
            None
            if answered
            else (
                legacy.failure_code.value
                if legacy.failure_code is not None
                else "legacy path returned no answer"
            )
        ),
        as_of=legacy.as_of,
        metadata={
            "read_model": AnswerReadModel.LEGACY.value,
            "citations": [item.model_dump(mode="json") for item in legacy.citations],
        },
    )
