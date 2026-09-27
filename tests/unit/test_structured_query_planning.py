"""The read grant bounds a validated shape; it reads no words (RR20-RR22)."""

from __future__ import annotations

import pytest

from app.config import load_seed_catalog
from app.domain.intent import (
    ConversationResolutionState,
    RequestIntent,
    RequestLanguage,
)
from app.domain.models import OfferingId, ProductType
from app.domain.query_shape import QueryShape
from app.domain.structured_tariffs import FieldPath, QueryOperation, RankDirection
from app.services.intent_resolution import RequestResolver
from app.services.interpretation_validation import InterpretationValidator
from app.services.structured_query_planning import (
    issue_read_grant,
    issue_typed_plan,
)
from tests.fixtures.interpretations import interp
from tests.fixtures.recorded_interpretations import RecordedInterpreter

MORTGAGES = tuple(item for item in OfferingId if item.product is ProductType.MORTGAGE)


def _resolution(interpretation, message="question"):
    return InterpretationValidator(load_seed_catalog()).validate(
        interpretation,
        message=message,
        normalized_query=message,
        detected_language=RequestLanguage.ENGLISH,
        state=ConversationResolutionState(),
        pending_offer=None,
    )


def test_the_grant_is_the_validated_shape_and_the_question_of_record() -> None:
    resolution = _resolution(
        interp(
            RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
            offering_ids=(OfferingId.OVERDRAFT,),
            operation=QueryOperation.SINGLE,
            fields=(FieldPath.AMOUNT_MINIMUM,),
            currency="AMD",
            standalone_question="What is the AMD minimum amount of the Overdraft?",
        ),
        "and the minimum amount in drams?",
    )
    plan = issue_read_grant(resolution, session_id="s", turn_id="t")

    assert plan.operation is QueryOperation.SINGLE
    assert plan.offering_ids == (OfferingId.OVERDRAFT,)
    assert plan.fields == (FieldPath.AMOUNT_MINIMUM,)
    assert plan.conditions == {"currency": "AMD"}
    assert plan.question == "What is the AMD minimum amount of the Overdraft?"


def test_a_rank_grant_covers_the_family_with_one_field() -> None:
    resolution = _resolution(
        interp(
            RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
            product=ProductType.MORTGAGE,
            family_wide=True,
            operation=QueryOperation.FAMILY_RANK,
            fields=(FieldPath.DOWN_PAYMENT_MINIMUM,),
            rank_field=FieldPath.DOWN_PAYMENT_MINIMUM,
            rank_direction=RankDirection.LOWEST,
            standalone_question="Which mortgage has the lowest down payment?",
        )
    )
    plan = issue_read_grant(resolution, session_id="s", turn_id="t")

    assert plan.operation is QueryOperation.FAMILY_RANK
    assert plan.fields == (FieldPath.DOWN_PAYMENT_MINIMUM,)
    assert plan.rank_direction is RankDirection.LOWEST
    assert set(plan.offering_ids) == set(MORTGAGES)


def test_current_and_history_grants_are_scope_only_and_may_span_families() -> None:
    current = _resolution(
        interp(
            RequestIntent.GET_CURRENT_TARIFFS, standalone_question="Are you up to date?"
        )
    )
    history = _resolution(
        interp(
            RequestIntent.GET_CHANGE_HISTORY,
            operation=QueryOperation.HISTORY,
            fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
            standalone_question="What rates changed?",
        )
    )
    current_plan = issue_read_grant(current, session_id="s", turn_id="t")
    history_plan = issue_read_grant(history, session_id="s", turn_id="t")

    assert current_plan.operation is QueryOperation.CURRENT
    assert current_plan.product is None and current_plan.fields == ()
    assert history_plan.operation is QueryOperation.HISTORY
    assert history_plan.fields == (FieldPath.NOMINAL_RATE_MINIMUM,)


def test_no_grant_for_a_clarification_or_a_non_read_intent() -> None:
    clarify = _resolution(
        interp(
            RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
            product=ProductType.MORTGAGE,
            operation=QueryOperation.SINGLE,
            fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
        )
    )
    status = _resolution(interp(RequestIntent.GET_RUN_STATUS))
    with pytest.raises(ValueError):
        issue_read_grant(clarify, session_id="s", turn_id="t")
    with pytest.raises(ValueError):
        issue_read_grant(status, session_id="s", turn_id="t")


def test_a_typed_plan_is_bounded_like_a_chat_grant() -> None:
    single = issue_typed_plan(
        "q",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.OVERDRAFT, OfferingId.CREDIT_LINE),
        shape=QueryShape(operation=QueryOperation.SINGLE),
        session_id="s",
        turn_id="t",
    )
    assert single.operation is QueryOperation.OVERVIEW
    assert single.fields == ()  # the answer path finds the fields
    with pytest.raises(ValueError):
        issue_typed_plan(
            "q",
            product=ProductType.MORTGAGE,
            shape=QueryShape(
                operation=QueryOperation.FAMILY_RANK,
                rank_field=FieldPath.COLLATERAL_REQUIREMENT,
                rank_direction=RankDirection.LOWEST,
            ),
            session_id="s",
            turn_id="t",
        )
    with pytest.raises(ValueError):
        issue_typed_plan(
            "q",
            product=ProductType.MORTGAGE,
            offering_ids=(OfferingId.OVERDRAFT,),
            shape=QueryShape(operation=QueryOperation.SINGLE),
            session_id="s",
            turn_id="t",
        )


@pytest.mark.asyncio
async def test_recorded_bilingual_comparison_keeps_both_offerings() -> None:
    resolver = RequestResolver(load_seed_catalog(), interpreter=RecordedInterpreter())
    for question in (
        "How does Overdraft differ from the standard Consumer Loan in amount and fees?",
        "Համեմատիր Օվերդրաֆտ և Սպառողական վարկ տոկոսադրույքը",
    ):
        resolution = (await resolver.resolve_turn(question)).resolution
        plan = issue_read_grant(resolution, session_id="s", turn_id="t")
        assert plan.operation is QueryOperation.COMPARE
        assert set(plan.offering_ids) == {
            OfferingId.OVERDRAFT,
            OfferingId.CONSUMER_STANDARD,
        }
        assert 0 < len(plan.fields) <= 20
