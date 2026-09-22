"""Read-only comparison of the legacy answer path and the structured read model.

The reader never mutates state and never logs question text, source text,
excerpts, or generated answers. It records identifiers, counts, statuses, and
latencies so a cutover decision can be reviewed without handling payloads.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import AnswerResult, AnswerStatus, QuestionCommand
from app.domain.structured_tariffs import QueryStatus, ResolutionPlan, TariffQueryResult
from app.services.structured_query_planning import issue_resolution_plan

logger = logging.getLogger(__name__)

ANSWERED_STRUCTURED = frozenset({QueryStatus.ANSWERED})
ABSTAINED_STRUCTURED = frozenset(
    {QueryStatus.INSUFFICIENT_EVIDENCE, QueryStatus.INCOMPARABLE, QueryStatus.MISSING}
)


class Resolver(Protocol):
    async def resolve_turn(self, query: str, state=None): ...


class StructuredAnswerer(Protocol):
    async def answer(
        self, plan: ResolutionPlan, question: str
    ) -> TariffQueryResult: ...


class LegacyAnswerer(Protocol):
    async def answer(self, command: QuestionCommand) -> AnswerResult: ...


@dataclass(frozen=True)
class ShadowCase:
    case_id: str
    question: str
    product: ProductType
    offering_id: OfferingId | None = None

    @property
    def question_sha256(self) -> str:
        return hashlib.sha256(self.question.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ShadowObservation:
    """Per-question diagnostics with no source text or generated wording."""

    case_id: str
    question_sha256: str
    product: str
    agreement: str
    structured_status: str | None = None
    structured_operation: str | None = None
    structured_offerings: int = 0
    structured_facts: int = 0
    structured_citations: int = 0
    structured_units: int = 0
    structured_latency_ms: int = 0
    structured_error: str | None = None
    legacy_status: str | None = None
    legacy_failure_code: str | None = None
    legacy_citations: int = 0
    legacy_latency_ms: int = 0
    legacy_error: str | None = None
    shared_evidence_sources: int = 0
    legacy_only_evidence_sources: int = 0
    structured_only_evidence_sources: int = 0
    mismatch_reason: str | None = None

    @property
    def is_mismatch(self) -> bool:
        return self.mismatch_reason is not None


@dataclass(frozen=True)
class ShadowReport:
    generated_at: datetime
    legacy_enabled: bool
    observations: tuple[ShadowObservation, ...]
    agreement_counts: dict[str, int] = field(default_factory=dict)
    structured_status_counts: dict[str, int] = field(default_factory=dict)
    legacy_status_counts: dict[str, int] = field(default_factory=dict)

    @property
    def mismatches(self) -> tuple[ShadowObservation, ...]:
        return tuple(item for item in self.observations if item.is_mismatch)

    @property
    def structured_answer_rate(self) -> float:
        if not self.observations:
            return 0.0
        answered = sum(
            1
            for item in self.observations
            if item.structured_status == QueryStatus.ANSWERED.value
        )
        return answered / len(self.observations)

    @property
    def gate_reason(self) -> str | None:
        """Why the cutover gate is still closed, or None when it is open."""
        if not self.observations:
            return "no representative query was shadow-read"
        if not self.legacy_enabled:
            return "the legacy path was not run, so no comparison exists"
        if self.structured_answer_rate == 0:
            return "the structured read model answered no representative query"
        if self.mismatches:
            return f"{len(self.mismatches)} diverging cases are still unaudited"
        return None

    @property
    def gate_passed(self) -> bool:
        """Both paths must have run and every divergence must be audited."""
        return self.gate_reason is None


def _change_evidence(result: TariffQueryResult) -> tuple[dict, ...]:
    """History answers carry their verified citations on the change set."""
    changes = result.metadata.get("changes")
    if not isinstance(changes, list):
        return ()
    return tuple(
        evidence
        for change in changes
        if isinstance(change, dict)
        for item in (change.get("changes") or [])
        if isinstance(item, dict)
        for key in ("previous_evidence", "current_evidence")
        for evidence in (item.get(key) or [])
        if isinstance(evidence, dict)
    )


def _structured_citations(result: TariffQueryResult) -> int:
    return sum(len(fact.evidence) for fact in result.facts) + len(
        _change_evidence(result)
    )


def _structured_sources(result: TariffQueryResult) -> set[str]:
    sources = {
        str(evidence.source_url) for fact in result.facts for evidence in fact.evidence
    }
    sources.update(
        str(evidence["source_url"])
        for evidence in _change_evidence(result)
        if evidence.get("source_url")
    )
    return sources


def _legacy_sources(result: AnswerResult) -> set[str]:
    return {str(citation.source_url) for citation in result.citations}


class StructuredShadowReader:
    def __init__(
        self,
        resolver: Resolver,
        structured: StructuredAnswerer,
        legacy: LegacyAnswerer | None = None,
    ) -> None:
        self._resolver = resolver
        self._structured = structured
        self._legacy = legacy

    @property
    def legacy_enabled(self) -> bool:
        return self._legacy is not None

    async def observe(self, case: ShadowCase) -> ShadowObservation:
        session_id = f"shadow-{uuid4()}"
        structured: TariffQueryResult | None = None
        structured_error: str | None = None
        started = time.perf_counter()
        try:
            resolution = (await self._resolver.resolve_turn(case.question)).resolution
            plan = issue_resolution_plan(
                case.question,
                resolution,
                session_id=session_id,
                turn_id=str(uuid4()),
            )
            structured = await self._structured.answer(plan, case.question)
        except Exception as exc:  # diagnostics only; the reader never raises
            structured_error = type(exc).__name__
        structured_latency_ms = int((time.perf_counter() - started) * 1000)

        legacy: AnswerResult | None = None
        legacy_error: str | None = None
        legacy_latency_ms = 0
        if self._legacy is not None:
            started = time.perf_counter()
            try:
                legacy = await self._legacy.answer(
                    QuestionCommand(
                        query=case.question,
                        product=case.product,
                        offering_id=case.offering_id,
                    )
                )
            except Exception as exc:
                legacy_error = type(exc).__name__
            legacy_latency_ms = int((time.perf_counter() - started) * 1000)

        structured_sources = _structured_sources(structured) if structured else set()
        legacy_sources = _legacy_sources(legacy) if legacy else set()
        observation = ShadowObservation(
            case_id=case.case_id,
            question_sha256=case.question_sha256,
            product=case.product.value,
            agreement=_agreement(structured, structured_error, legacy, legacy_error),
            structured_status=structured.status.value if structured else None,
            structured_operation=structured.operation.value if structured else None,
            structured_offerings=len(structured.offering_ids) if structured else 0,
            structured_facts=len(structured.facts) if structured else 0,
            structured_citations=(
                _structured_citations(structured) if structured else 0
            ),
            structured_units=len(structured.retrieval_units) if structured else 0,
            structured_latency_ms=structured_latency_ms,
            structured_error=structured_error,
            legacy_status=legacy.status.value if legacy else None,
            legacy_failure_code=(
                legacy.failure_code.value
                if legacy is not None and legacy.failure_code is not None
                else None
            ),
            legacy_citations=len(legacy.citations) if legacy else 0,
            legacy_latency_ms=legacy_latency_ms,
            legacy_error=legacy_error,
            shared_evidence_sources=len(structured_sources & legacy_sources),
            legacy_only_evidence_sources=len(legacy_sources - structured_sources),
            structured_only_evidence_sources=len(structured_sources - legacy_sources),
            mismatch_reason=None,
        )
        reason = _mismatch_reason(observation)
        if reason is not None:
            observation = replace(observation, mismatch_reason=reason)
        logger.info(
            "shadow.observation case=%s question_hash=%s agreement=%s "
            "structured_status=%s legacy_status=%s structured_facts=%s "
            "structured_citations=%s legacy_citations=%s mismatch=%s",
            observation.case_id,
            observation.question_sha256[:12],
            observation.agreement,
            observation.structured_status,
            observation.legacy_status,
            observation.structured_facts,
            observation.structured_citations,
            observation.legacy_citations,
            observation.mismatch_reason,
        )
        return observation

    async def run(self, cases: Sequence[ShadowCase]) -> ShadowReport:
        observations = tuple([await self.observe(case) for case in cases])
        return ShadowReport(
            generated_at=datetime.now(UTC),
            legacy_enabled=self.legacy_enabled,
            observations=observations,
            agreement_counts=dict(Counter(item.agreement for item in observations)),
            structured_status_counts=dict(
                Counter(item.structured_status or "error" for item in observations)
            ),
            legacy_status_counts=dict(
                Counter(item.legacy_status or "not_run" for item in observations)
            ),
        )


def _agreement(
    structured: TariffQueryResult | None,
    structured_error: str | None,
    legacy: AnswerResult | None,
    legacy_error: str | None,
) -> str:
    if structured_error is not None:
        return "structured_error"
    if legacy_error is not None:
        return "legacy_error"
    assert structured is not None
    structured_answered = structured.status in ANSWERED_STRUCTURED
    if legacy is None:
        return "structured_only_run"
    legacy_answered = legacy.status is AnswerStatus.ANSWERED
    if structured_answered and legacy_answered:
        return "both_answered"
    if structured_answered:
        return "structured_only"
    if legacy_answered:
        return "legacy_only"
    return "both_abstained"


def _mismatch_reason(observation: ShadowObservation) -> str | None:
    """Flag every divergence a human must audit before the new path answers."""
    if observation.structured_error is not None:
        return "structured path raised " + observation.structured_error
    if observation.legacy_error is not None:
        return "legacy path raised " + observation.legacy_error
    if observation.agreement == "legacy_only":
        return "legacy answered where the structured read model abstains"
    if (
        observation.agreement == "both_answered"
        and observation.legacy_only_evidence_sources
    ):
        return "legacy cited a source the structured evidence does not cover"
    if (
        observation.structured_status == QueryStatus.ANSWERED.value
        and observation.structured_citations == 0
    ):
        return "structured answer carries no verified citation"
    return None


# A compact, checked-in shadow set covering every deterministic branch: single
# offering, explicit comparison, family extrema, accepted history, an offering
# with no accepted projection, and one Armenian question.
DEFAULT_SHADOW_CASES: tuple[ShadowCase, ...] = (
    ShadowCase(
        case_id="single_overdraft_rate",
        question="What is the nominal interest rate of the Overdraft?",
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
    ),
    ShadowCase(
        case_id="single_overdraft_rate_armenian",
        question="Օվերդրաֆտի տոկոսադրույքը որքա՞ն է։",  # noqa: RUF001
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
    ),
    ShadowCase(
        case_id="single_mortgage_down_payment",
        question=(
            "What down payment and collateral does the Primary Market Mortgage require?"
        ),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
    ),
    ShadowCase(
        case_id="compare_overdraft_credit_line",
        question="Compare the Overdraft and the Credit Line interest rate.",
        product=ProductType.CONSUMER_LOAN,
    ),
    ShadowCase(
        case_id="rank_consumer_lowest_rate",
        question="Which consumer loan has the lowest nominal interest rate in AMD?",
        product=ProductType.CONSUMER_LOAN,
    ),
    ShadowCase(
        case_id="rank_mortgage_longest_term",
        question="Which mortgage loans have the longest repayment term?",
        product=ProductType.MORTGAGE,
    ),
    ShadowCase(
        case_id="history_mortgage_primary",
        question="What changed in the Primary Market Mortgage tariff?",
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
    ),
    ShadowCase(
        case_id="missing_express_mortgage_fee",
        question="What application fee applies to the Express Mortgage?",
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_EXPRESS,
    ),
)
