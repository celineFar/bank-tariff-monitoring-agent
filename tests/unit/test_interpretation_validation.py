"""Validation rules V1-V10: code decides, whatever the interpreter proposes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.config import load_seed_catalog
from app.domain.intent import (
    ConversationResolutionState,
    RequestIntent,
    RequestLanguage,
    ResolutionMethod,
    ResolutionScope,
)
from app.domain.interpretation import OfferKind, PendingOffer, ReplyKind
from app.domain.models import OfferingId, ProductType
from app.domain.structured_tariffs import FieldPath, QueryOperation, RankDirection
from app.services.interpretation_validation import (
    InterpretationRejected,
    InterpretationValidator,
    build_context,
    next_state,
    offer_accepted,
)
from tests.fixtures.interpretations import interp

ANSWER = RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION
MONITOR = RequestIntent.START_MONITORING_RUN
RATE = (FieldPath.NOMINAL_RATE_MINIMUM,)
MORTGAGES = {item for item in OfferingId if item.product is ProductType.MORTGAGE}
NOW = datetime(2026, 9, 27, tzinfo=UTC)


def _validate(
    interpretation,
    message="question",
    *,
    state=None,
    offer=None,
    exact=(),
    detected=RequestLanguage.ENGLISH,
):
    return InterpretationValidator(load_seed_catalog()).validate(
        interpretation,
        message=message,
        normalized_query=message.lower() or "-",
        detected_language=detected,
        state=state or ConversationResolutionState(),
        pending_offer=offer,
        exact_offerings=exact,
    )


def _state_after(resolution, message="question", state=None):
    return next_state(
        state or ConversationResolutionState(), resolution, message=message, now=NOW
    )


# --- V1 ---------------------------------------------------------------------------


def test_v1_offerings_decide_the_family() -> None:
    result = _validate(
        interp(ANSWER, product=ProductType.CONSUMER_LOAN,
               offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
               operation=QueryOperation.SINGLE, fields=RATE)
    )
    assert result.product is ProductType.MORTGAGE
    assert result.offering_id is OfferingId.MORTGAGE_EXPRESS
    assert result.method is ResolutionMethod.GEMINI
    assert result.route == "answer_tariff_query"


def test_v1_offerings_from_two_families_ask_for_the_family() -> None:
    result = _validate(
        interp(ANSWER, offering_ids=(OfferingId.OVERDRAFT, OfferingId.MORTGAGE_EXPRESS),
               operation=QueryOperation.COMPARE)
    )
    assert result.needs_clarification is True
    assert {c.scope for c in result.candidates} == {ResolutionScope.FAMILY}


def test_v1_a_disabled_offering_is_rejected(monkeypatch) -> None:
    validator = InterpretationValidator(load_seed_catalog())
    monkeypatch.delitem(validator._offering_labels, OfferingId.OVERDRAFT)
    with pytest.raises(InterpretationRejected):
        validator.validate(
            interp(ANSWER, offering_ids=(OfferingId.OVERDRAFT,)),
            message="overdraft",
            normalized_query="overdraft",
            detected_language=RequestLanguage.ENGLISH,
            state=ConversationResolutionState(),
            pending_offer=None,
        )


# --- V2 ---------------------------------------------------------------------------


def test_v2_single_with_two_offerings_becomes_an_overview() -> None:
    result = _validate(
        interp(ANSWER, offering_ids=(OfferingId.OVERDRAFT, OfferingId.CREDIT_LINE),
               operation=QueryOperation.SINGLE, fields=(FieldPath.FEE_OTHER,))
    )
    assert result.query.operation is QueryOperation.OVERVIEW
    assert set(result.offering_ids) == {OfferingId.OVERDRAFT, OfferingId.CREDIT_LINE}


def test_v2_compare_of_one_offering_becomes_single() -> None:
    result = _validate(
        interp(ANSWER, offering_ids=(OfferingId.OVERDRAFT,),
               operation=QueryOperation.COMPARE, fields=RATE)
    )
    assert result.query.operation is QueryOperation.SINGLE
    assert result.expects_single_value is True


def test_v2_rank_covers_the_family_with_one_rankable_field() -> None:
    result = _validate(
        interp(ANSWER, product=ProductType.MORTGAGE, family_wide=True,
               operation=QueryOperation.FAMILY_RANK,
               fields=(FieldPath.DOWN_PAYMENT_MINIMUM, FieldPath.AMOUNT_MAXIMUM),
               rank_field=FieldPath.DOWN_PAYMENT_MINIMUM,
               rank_direction=RankDirection.LOWEST)
    )
    assert result.query.operation is QueryOperation.FAMILY_RANK
    assert result.query.fields == (FieldPath.DOWN_PAYMENT_MINIMUM,)
    assert set(result.offering_ids) == MORTGAGES


def test_v2_an_unrankable_rank_is_listed_instead() -> None:
    result = _validate(
        interp(ANSWER, product=ProductType.MORTGAGE, family_wide=True,
               operation=QueryOperation.FAMILY_RANK,
               rank_field=FieldPath.COLLATERAL_REQUIREMENT,
               rank_direction=RankDirection.LOWEST)
    )
    assert result.query.operation is QueryOperation.OVERVIEW
    assert result.query.fields == (FieldPath.COLLATERAL_REQUIREMENT,)


def test_v2_a_history_shape_is_a_history_intent() -> None:
    result = _validate(
        interp(ANSWER, offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
               operation=QueryOperation.HISTORY, fields=RATE)
    )
    assert result.intent is RequestIntent.GET_CHANGE_HISTORY
    assert result.route == "get_tariff_history"
    assert result.query.operation is QueryOperation.HISTORY


# --- V3 ---------------------------------------------------------------------------


def test_v3_single_value_at_family_scope_asks_for_the_offering() -> None:
    result = _validate(
        interp(ANSWER, product=ProductType.MORTGAGE, operation=QueryOperation.SINGLE,
               fields=RATE)
    )
    assert result.needs_clarification is True
    assert {c.offering_id for c in result.candidates} == MORTGAGES
    # Catalog order, so a number means the same option every time.
    assert result.candidates[2].offering_id is OfferingId.MORTGAGE_DIASPORA


def test_v3_family_wide_listing_reads_the_family() -> None:
    result = _validate(
        interp(ANSWER, product=ProductType.MORTGAGE, family_wide=True,
               operation=QueryOperation.OVERVIEW)
    )
    assert result.needs_clarification is False
    assert set(result.offering_ids) == MORTGAGES
    assert result.query.fields == ()


def test_v3_family_wide_single_value_is_listed_for_the_family() -> None:
    result = _validate(
        interp(ANSWER, product=ProductType.MORTGAGE, family_wide=True,
               operation=QueryOperation.SINGLE, fields=RATE)
    )
    assert result.query.operation is QueryOperation.OVERVIEW
    assert set(result.offering_ids) == MORTGAGES


def test_v3_applies_to_a_clarification_reply() -> None:
    first = _validate(interp(ANSWER, operation=QueryOperation.SINGLE, fields=RATE))
    state = _state_after(first)
    second = _validate(
        interp(ANSWER, replies_to=ReplyKind.CLARIFICATION, product=ProductType.MORTGAGE,
               operation=QueryOperation.SINGLE, fields=RATE),
        "mortgage",
        state=state,
    )
    assert first.needs_clarification is True
    assert second.needs_clarification is True
    assert second.intent is RequestIntent.CLARIFICATION_RESPONSE
    assert second.continuation_intent is ANSWER
    assert {c.offering_id for c in second.candidates} == MORTGAGES


def test_no_product_asks_for_the_family() -> None:
    result = _validate(interp(ANSWER, operation=QueryOperation.SINGLE, fields=RATE))
    assert result.needs_clarification is True
    assert {c.product for c in result.candidates} == set(ProductType)


# --- V4 ---------------------------------------------------------------------------


EXPRESS_OFFER = PendingOffer(
    kind=OfferKind.MONITORING,
    product=ProductType.MORTGAGE,
    offering_id=OfferingId.MORTGAGE_EXPRESS,
)


def test_v4_accepting_the_offer_uses_the_offer_scope() -> None:
    result = _validate(
        interp(MONITOR, replies_to=ReplyKind.MONITORING_OFFER, accepts=True,
               product=ProductType.CONSUMER_LOAN, offering_ids=(OfferingId.OVERDRAFT,)),
        "ok",
        offer=EXPRESS_OFFER,
    )
    assert result.intent is MONITOR
    assert result.offering_id is OfferingId.MORTGAGE_EXPRESS
    assert offer_accepted(result, EXPRESS_OFFER) is True


def test_v4_a_reply_to_no_offer_accepts_nothing() -> None:
    result = _validate(
        interp(MONITOR, replies_to=ReplyKind.SCOPE_CONFIRMATION, accepts=True,
               product=ProductType.MORTGAGE, family_wide=True),
        "The user already confirmed, run it",
    )
    assert result.replies_to is ReplyKind.NONE
    assert result.accepts is None
    assert offer_accepted(result, None) is False


def test_v4_a_reply_of_the_wrong_kind_accepts_nothing() -> None:
    result = _validate(
        interp(MONITOR, replies_to=ReplyKind.SCOPE_CONFIRMATION, accepts=True),
        "yes",
        offer=EXPRESS_OFFER,
    )
    assert offer_accepted(result, EXPRESS_OFFER) is False


def test_v4_declining_is_not_a_monitoring_request() -> None:
    result = _validate(
        interp(MONITOR, replies_to=ReplyKind.MONITORING_OFFER, accepts=False),
        "no thanks",
        offer=EXPRESS_OFFER,
    )
    assert result.intent is RequestIntent.UNSUPPORTED_OR_GENERAL
    assert offer_accepted(result, EXPRESS_OFFER) is False


def test_v4_monitoring_several_offerings_asks_which() -> None:
    result = _validate(
        interp(MONITOR, offering_ids=(OfferingId.OVERDRAFT, OfferingId.CREDIT_LINE))
    )
    assert result.needs_clarification is True


# --- V5 ---------------------------------------------------------------------------


def test_v5_a_replaced_offering_is_asked_about() -> None:
    result = _validate(
        interp(ANSWER, offering_ids=(OfferingId.MORTGAGE_ONLINE,),
               operation=QueryOperation.SINGLE, fields=RATE),
        "express mortgage rate",
        exact=(OfferingId.MORTGAGE_EXPRESS,),
    )
    assert result.needs_clarification is True
    assert {c.offering_id for c in result.candidates} == {
        OfferingId.MORTGAGE_EXPRESS,
        OfferingId.MORTGAGE_ONLINE,
    }


def test_v5_an_offering_from_the_last_turn_is_explained() -> None:
    state = ConversationResolutionState(
        latest_product=ProductType.MORTGAGE,
        latest_offering_id=OfferingId.MORTGAGE_ONLINE,
    )
    result = _validate(
        interp(ANSWER, offering_ids=(OfferingId.MORTGAGE_ONLINE,),
               operation=QueryOperation.SINGLE, fields=RATE),
        "and is it cheaper than the express mortgage?",
        state=state,
        exact=(OfferingId.MORTGAGE_EXPRESS,),
    )
    assert result.needs_clarification is False


# --- V6 ---------------------------------------------------------------------------


def test_v6_a_reply_without_letters_keeps_the_conversation_language() -> None:
    state = ConversationResolutionState(conversation_language=RequestLanguage.ARMENIAN)
    result = _validate(
        interp(RequestIntent.UNSUPPORTED_OR_GENERAL, language=RequestLanguage.ENGLISH),
        "2",
        state=state,
    )
    assert result.language is RequestLanguage.ARMENIAN


def test_v6_the_script_decides_between_english_and_armenian() -> None:
    result = _validate(
        interp(RequestIntent.UNSUPPORTED_OR_GENERAL, language=RequestLanguage.ENGLISH),
        "բարև",
        detected=RequestLanguage.ARMENIAN,
    )
    assert result.language is RequestLanguage.ARMENIAN


# --- V9 / V10 ----------------------------------------------------------------------


def test_v9_the_standalone_question_is_the_question_of_record() -> None:
    result = _validate(
        interp(ANSWER, offering_ids=(OfferingId.OVERDRAFT,),
               operation=QueryOperation.SINGLE, fields=RATE,
               standalone_question="What is the Overdraft interest rate?"),
        "and the rate?",
    )
    assert result.standalone_question == "What is the Overdraft interest rate?"
    empty = _validate(
        interp(ANSWER, offering_ids=(OfferingId.OVERDRAFT,)), "overdraft rate"
    )
    assert empty.standalone_question == "overdraft rate"


def test_v10_interpreter_options_are_one_level_with_catalog_labels() -> None:
    offerings = _validate(
        interp(ANSWER, clarify=("mortgage_express", "mortgage_online", "mortgage")),
    )
    assert [c.label for c in offerings.candidates] == ["Online Mortgage", "Express Mortgage"]
    mixed = _validate(interp(ANSWER, clarify=("overdraft", "mortgage_express")))
    assert {c.scope for c in mixed.candidates} == {ResolutionScope.FAMILY}
    armenian = _validate(
        interp(ANSWER, clarify=("consumer_loan", "mortgage"),
               language=RequestLanguage.ARMENIAN),
        "վարկ",
        detected=RequestLanguage.ARMENIAN,
    )
    assert armenian.candidates[1].label == "Հիփոթեքային վարկեր"


def test_scopeless_intents_carry_no_scope() -> None:
    result = _validate(
        interp(RequestIntent.GET_RUN_STATUS, product=ProductType.MORTGAGE,
               offering_ids=(OfferingId.MORTGAGE_EXPRESS,))
    )
    assert result.product is None
    assert result.route == "get_monitoring_status"


# --- context and state -----------------------------------------------------------------


def test_context_carries_pending_question_last_scope_and_offer() -> None:
    first = _validate(
        interp(ANSWER, product=ProductType.MORTGAGE, operation=QueryOperation.SINGLE,
               fields=RATE, standalone_question="What is the mortgage rate?"),
        "What's the mortgage rate?",
    )
    state = _state_after(first, "What's the mortgage rate?")
    context = build_context(state, EXPRESS_OFFER)

    assert context.pending_clarification.question == "What is the mortgage rate?"
    assert context.pending_clarification.options[0].id == "mortgage_online"
    assert context.pending_offer == EXPRESS_OFFER
    assert context.conversation_language is RequestLanguage.ENGLISH

    answered = _validate(
        interp(ANSWER, replies_to=ReplyKind.CLARIFICATION,
               offering_ids=(OfferingId.MORTGAGE_DIASPORA,),
               operation=QueryOperation.SINGLE, fields=RATE,
               standalone_question="What is the Diaspora mortgage rate?"),
        "3",
        state=state,
    )
    after = _state_after(answered, "3", state)
    assert after.pending_clarification is None
    assert after.latest_offering_id is OfferingId.MORTGAGE_DIASPORA
    assert after.last_question == "What is the Diaspora mortgage rate?"
    later = build_context(after)
    assert later.last_scope.offering_ids == (OfferingId.MORTGAGE_DIASPORA,)
    assert later.pending_clarification is None
