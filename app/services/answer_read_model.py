"""The answer path every ordinary question takes: accepted, typed facts.

The ADK `answer_tariff_query` tool, the post-monitoring answer and
`POST /api/v1/questions` all route through `TariffAnswerRouter`, so each answers
inside the scope it was authorized for. The earlier RAG answer path, and the
switch that could restore it, were removed.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from app.domain.models import OfferingId
from app.domain.monitoring import (
    AnswerCitation,
    AnswerFailureCode,
    AnswerResult,
    AnswerStatus,
    QuestionCommand,
)
from app.domain.query_shape import QueryShape
from app.domain.structured_tariffs import (
    QueryStatus,
    ResolutionPlan,
    TariffQueryResult,
)
from app.services.structured_query_planning import issue_typed_plan
from app.services.structured_tariff_query import StructuredTariffQueryService

logger = logging.getLogger(__name__)


__all__ = [
    "TariffAnswerRouter",
    "structured_to_answer_result",
]

READ_MODEL = "structured"
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
    """Adapt a typed structured result for the `AnswerResult` contract of `/questions`."""
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
                "read_model": READ_MODEL,
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
            "read_model": READ_MODEL,
            "operation": result.operation.value,
            "query_status": result.status.value,
            "reason": result.reason,
        },
    )


ShapeSource = Callable[..., Awaitable[QueryShape]]


class TariffAnswerRouter:
    """One place every ordinary question is answered from, inside its scope."""

    def __init__(
        self,
        structured: StructuredTariffQueryService,
        *,
        shapes: ShapeSource | None = None,
    ) -> None:
        self._structured = structured
        # D9: `RequestResolver.shape_for` - the interpreter proposes the shape
        # of a typed-scope question; the scope stays the caller's.
        self._shapes = shapes

    @property
    def structured_service(self) -> StructuredTariffQueryService:
        return self._structured

    async def answer_plan(
        self, plan: ResolutionPlan, question: str
    ) -> TariffQueryResult:
        """Answer a scope-authorized turn from accepted facts."""
        return await self._structured.answer(plan, question)

    async def answer_question(self, command: QuestionCommand) -> AnswerResult:
        """Answer a typed API request that carries its own validated scope."""
        if command.product is None:
            return AnswerResult(
                status=AnswerStatus.AMBIGUOUS_PRODUCT,
                failure_code=AnswerFailureCode.AMBIGUOUS_PRODUCT,
                audit_metadata={"read_model": READ_MODEL},
            )
        offering_ids: tuple[OfferingId, ...] = (
            (command.offering_id,) if command.offering_id is not None else ()
        )
        try:
            if self._shapes is None:
                raise ValueError("no request interpreter for the question's shape")
            shape = await self._shapes(
                command.query, product=command.product, offering_ids=offering_ids
            )
            plan = issue_typed_plan(
                command.query,
                product=command.product,
                offering_ids=offering_ids,
                shape=shape,
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
                    "read_model": READ_MODEL,
                    "reason": str(exc),
                },
            )
        return structured_to_answer_result(
            await self._structured.answer(plan, plan.question), command
        )
