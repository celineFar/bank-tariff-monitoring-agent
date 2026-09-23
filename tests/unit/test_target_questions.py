"""Every one of the 25 target questions must reach its expected typed outcome."""

from __future__ import annotations

import pytest

from app.config import load_seed_catalog
from app.config.models import IntentResolutionSettings
from app.domain.structured_tariffs import QueryOperation, QueryStatus
from app.repositories.structured_tariff_query import lexical_search_terms
from app.services.intent_resolution import RequestResolver
from app.services.structured_query_planning import issue_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.eval.structured_metrics import measure
from tests.fixtures.evaluation_corpus import EvaluationRepository
from tests.fixtures.target_questions import TARGET_QUESTIONS, TargetQuestion


def _resolver() -> RequestResolver:
    return RequestResolver(load_seed_catalog(), IntentResolutionSettings())


@pytest.mark.parametrize(
    "question", TARGET_QUESTIONS, ids=[item.case_id for item in TARGET_QUESTIONS]
)
@pytest.mark.asyncio
async def test_target_question_routes_and_answers_as_specified(
    question: TargetQuestion,
) -> None:
    resolution = (await _resolver().resolve_turn(question.question)).resolution
    plan = issue_resolution_plan(
        question.question,
        resolution,
        session_id=f"case-{question.case_id}",
        turn_id=question.case_id,
    )

    assert plan.product is question.product
    assert plan.operation is question.operation
    assert set(plan.offering_ids) == set(question.offering_ids)
    assert plan.rank_direction == question.rank_direction
    assert set(question.required_fields) <= set(plan.fields)

    result = await StructuredTariffQueryService(EvaluationRepository()).answer(
        plan, question.question
    )

    assert result.status is question.expected_status, result.reason
    if question.expected_winner is not None:
        assert result.metadata["winner"] == question.expected_winner.value
    if result.status is QueryStatus.ANSWERED:
        assert all(fact.offering_id in plan.offering_ids for fact in result.facts)
        assert all(
            fact.evidence and all(item.quote and item.locator for item in fact.evidence)
            for fact in result.facts
        )
    else:
        assert result.answer is None
        assert result.reason


@pytest.mark.asyncio
async def test_fee_inventory_lists_scopes_without_inventing_a_highest_fee() -> None:
    question = next(item for item in TARGET_QUESTIONS if item.number == 13)
    resolution = (await _resolver().resolve_turn(question.question)).resolution
    plan = issue_resolution_plan(
        question.question, resolution, session_id="fees", turn_id="fees"
    )

    result = await StructuredTariffQueryService(EvaluationRepository()).answer(
        plan, question.question
    )

    units = {(fact.field_path.value, fact.unit) for fact in result.facts}
    assert {"fee.application", "fee.service"} <= {path for path, _ in units}
    assert {"money", "percent"} <= {unit for _, unit in units}
    # Nothing ranks a fixed fee against a percentage fee into one winner.
    assert "winner" not in result.metadata
    assert result.operation is QueryOperation.SINGLE


@pytest.mark.asyncio
async def test_currency_condition_narrows_the_answer_to_one_variant() -> None:
    question = next(item for item in TARGET_QUESTIONS if item.number == 5)
    resolution = (await _resolver().resolve_turn(question.question)).resolution
    plan = issue_resolution_plan(
        question.question, resolution, session_id="usd", turn_id="usd"
    )

    result = await StructuredTariffQueryService(EvaluationRepository()).answer(
        plan, question.question
    )

    assert plan.conditions == {"currency": "USD"}
    assert result.facts
    assert {fact.currency for fact in result.facts} == {"USD"}


def test_lexical_terms_drop_bilingual_function_words() -> None:
    assert (
        lexical_search_terms("What is the nominal interest rate of the Overdraft?")
        == '"nominal" or "interest" or "rate" or "overdraft"'
    )
    assert lexical_search_terms("Օվերդրաֆտի տոկոսադրույքը որքա՞ն է։") == (  # noqa: RUF001
        '"օվերդրաֆտի" or "տոկոսադրույքը"'
    )
    assert lexical_search_terms("what is the?") is None
    assert (
        len(lexical_search_terms(" ".join(str(n) * 3 for n in range(30))).split(" or "))
        == 12
    )


@pytest.mark.asyncio
async def test_structured_eval_metrics_meet_the_acceptance_bar() -> None:
    metrics = await measure()

    assert metrics.questions == 25
    assert metrics.deterministic_route_rate == 1.0
    assert metrics.exact_fact_accuracy == 1.0
    assert metrics.conditional_coverage == 1.0
    assert metrics.valid_citation_rate == 1.0
    assert metrics.unsupported_answer_rate == 0.0
    assert metrics.scope_leakage_rate == 0.0
    assert metrics.comparison_correctness == 1.0
    assert metrics.abstention_correctness == 1.0
    assert metrics.supported_unit_rate >= 0.8
    assert metrics.model_calls == 0
