"""Deterministic quality metrics for the 25 structured target questions.

The harness resolves each question with the model-free deterministic resolver,
issues a real `ResolutionPlan`, and answers it from the synthetic evaluation
corpus. It makes no model call, so it can run in CI and be compared between
revisions. Retrieval recall against PostgreSQL full-text search and the model
call/token/cost figures are measured separately; see `tests/eval/RESULTS.md`.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import asdict, dataclass

from app.config import load_seed_catalog
from app.config.models import IntentResolutionSettings
from app.domain.structured_tariffs import (
    QueryOperation,
    QueryStatus,
    TariffQueryResult,
)
from app.services.intent_resolution import RequestResolver
from app.services.structured_query_planning import issue_resolution_plan
from app.services.structured_shadow_read import _change_evidence
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.fixtures.evaluation_corpus import EvaluationRepository
from tests.fixtures.target_questions import TARGET_QUESTIONS, TargetQuestion

ABSTENTIONS = frozenset(
    {QueryStatus.MISSING, QueryStatus.INCOMPARABLE, QueryStatus.INSUFFICIENT_EVIDENCE}
)
COMPARATIVE = frozenset({QueryOperation.COMPARE, QueryOperation.FAMILY_RANK})


@dataclass(frozen=True)
class QuestionOutcome:
    number: int
    case_id: str
    routed: bool
    route_error: str | None
    operation: str | None
    status: str | None
    expected_status: str
    winner: str | None
    expected_winner: str | None
    facts: int
    expected_facts: int
    cited_facts: int
    citations: int
    units: int
    out_of_scope_facts: int
    latency_ms: float

    @property
    def status_correct(self) -> bool:
        return self.status == self.expected_status

    @property
    def winner_correct(self) -> bool:
        return self.expected_winner is None or self.winner == self.expected_winner

    @property
    def exact(self) -> bool:
        return self.routed and self.status_correct and self.winner_correct

    @property
    def variants_complete(self) -> bool:
        return self.facts == self.expected_facts

    @property
    def unsupported(self) -> bool:
        return self.status == QueryStatus.ANSWERED.value and self.citations == 0


@dataclass(frozen=True)
class StructuredEvalMetrics:
    questions: int
    deterministic_route_rate: float
    exact_fact_accuracy: float
    conditional_coverage: float
    valid_citation_rate: float
    unsupported_answer_rate: float
    scope_leakage_rate: float
    comparison_correctness: float
    abstention_correctness: float
    supported_unit_rate: float
    median_latency_ms: float
    p95_latency_ms: float
    model_calls: int
    outcomes: tuple[QuestionOutcome, ...]

    def as_dict(self) -> dict[str, object]:
        data = {key: value for key, value in asdict(self).items() if key != "outcomes"}
        data["outcomes"] = [asdict(item) for item in self.outcomes]
        return data


def _rate(matched: int, total: int) -> float:
    return round(matched / total, 4) if total else 1.0


def _expected_fact_count(
    repository: EvaluationRepository, question: TargetQuestion, plan
) -> int:
    """Every disclosed variant in the authorized scope must survive the answer."""
    if plan.operation is QueryOperation.HISTORY:
        return 0
    wanted = set(plan.fields)
    authorized = set(plan.offering_ids)
    currency = plan.conditions.get("currency")
    return sum(
        1
        for fact in repository.active_facts
        if fact.offering_id in authorized
        and fact.field_path in wanted
        and fact.status.value == "found"
        and fact.evidence
        and (currency is None or fact.currency == currency)
    )


async def measure(
    repository: EvaluationRepository | None = None,
) -> StructuredEvalMetrics:
    store = repository or EvaluationRepository()
    resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings())
    service = StructuredTariffQueryService(store)
    outcomes: list[QuestionOutcome] = []
    for question in TARGET_QUESTIONS:
        started = time.perf_counter()
        route_error: str | None = None
        result: TariffQueryResult | None = None
        plan = None
        try:
            resolution = (await resolver.resolve_turn(question.question)).resolution
            plan = issue_resolution_plan(
                question.question,
                resolution,
                session_id=f"eval-{question.case_id}",
                turn_id=question.case_id,
            )
            result = await service.answer(plan, question.question)
        except ValueError as exc:
            route_error = str(exc)
        latency_ms = (time.perf_counter() - started) * 1000
        citations = (
            sum(len(fact.evidence) for fact in result.facts)
            + len(_change_evidence(result))
            if result
            else 0
        )
        cited_facts = (
            sum(
                1
                for fact in result.facts
                if any(item.quote and item.locator for item in fact.evidence)
            )
            if result
            else 0
        )
        authorized = set(plan.offering_ids) if plan is not None else set()
        outcomes.append(
            QuestionOutcome(
                number=question.number,
                case_id=question.case_id,
                routed=route_error is None,
                route_error=route_error,
                operation=result.operation.value if result else None,
                status=result.status.value if result else None,
                expected_status=question.expected_status.value,
                winner=(
                    str(result.metadata.get("winner"))
                    if result and result.metadata.get("winner")
                    else None
                ),
                expected_winner=(
                    question.expected_winner.value if question.expected_winner else None
                ),
                facts=len(result.facts) if result else 0,
                expected_facts=(
                    _expected_fact_count(store, question, plan)
                    if plan is not None
                    and result is not None
                    and result.status is QueryStatus.ANSWERED
                    else (len(result.facts) if result else 0)
                ),
                cited_facts=cited_facts,
                citations=citations,
                units=len(result.retrieval_units) if result else 0,
                out_of_scope_facts=(
                    sum(
                        1 for fact in result.facts if fact.offering_id not in authorized
                    )
                    if result
                    else 0
                ),
                latency_ms=round(latency_ms, 3),
            )
        )
    latencies = sorted(item.latency_ms for item in outcomes)
    comparative = [
        item
        for item in outcomes
        if item.operation in {operation.value for operation in COMPARATIVE}
    ]
    expected_abstentions = [
        item
        for item in outcomes
        if item.expected_status in {status.value for status in ABSTENTIONS}
    ]
    answered = [item for item in outcomes if item.status == QueryStatus.ANSWERED.value]
    single_answered = [
        item for item in answered if item.operation == QueryOperation.SINGLE.value
    ]
    return StructuredEvalMetrics(
        questions=len(outcomes),
        deterministic_route_rate=_rate(
            sum(1 for item in outcomes if item.routed), len(outcomes)
        ),
        exact_fact_accuracy=_rate(
            sum(1 for item in outcomes if item.exact), len(outcomes)
        ),
        conditional_coverage=_rate(
            sum(1 for item in answered if item.variants_complete), len(answered)
        ),
        valid_citation_rate=_rate(
            sum(item.cited_facts for item in answered),
            sum(item.facts for item in answered),
        ),
        unsupported_answer_rate=_rate(
            sum(1 for item in outcomes if item.unsupported), len(outcomes)
        ),
        scope_leakage_rate=_rate(
            sum(1 for item in outcomes if item.out_of_scope_facts), len(outcomes)
        ),
        comparison_correctness=_rate(
            sum(1 for item in comparative if item.exact), len(comparative)
        ),
        abstention_correctness=_rate(
            sum(1 for item in expected_abstentions if item.status_correct),
            len(expected_abstentions),
        ),
        supported_unit_rate=_rate(
            sum(1 for item in single_answered if item.units), len(single_answered)
        ),
        median_latency_ms=round(statistics.median(latencies), 3) if latencies else 0.0,
        p95_latency_ms=(
            round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3)
            if latencies
            else 0.0
        ),
        model_calls=0,
        outcomes=tuple(outcomes),
    )
