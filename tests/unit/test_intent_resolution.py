"""The resolver around the interpreter: request, validation, state, failure (V7).

What the live interpreter answers for real messages is covered by the recorded
interpretation case set (`test_interpretation_cases.py`); these tests check
the mechanics with scripted interpretations.
"""

from __future__ import annotations

import pytest

from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.domain.intent import (
    ConversationResolutionState,
    RequestIntent,
    RequestLanguage,
)
from app.domain.interpretation import OfferKind, PendingOffer, ReplyKind
from app.domain.models import OfferingId, ProductType
from app.domain.structured_tariffs import FieldPath, QueryOperation
from app.services.intent_resolution import (
    InterpretationUnavailable,
    RequestResolver,
    detect_request_language,
)
from tests.fixtures.interpretations import ScriptedInterpreter, interp

ANSWER = RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION
RATE = (FieldPath.NOMINAL_RATE_MINIMUM, FieldPath.NOMINAL_RATE_MAXIMUM)


def _resolver(script) -> tuple[RequestResolver, ScriptedInterpreter]:
    interpreter = ScriptedInterpreter(script)
    return (
        RequestResolver(
            load_seed_catalog(), IntentResolutionSettings(), interpreter=interpreter
        ),
        interpreter,
    )


@pytest.mark.asyncio
async def test_the_interpreter_sees_the_whole_catalog_and_the_allowed_values() -> None:
    resolver, interpreter = _resolver(
        {"overdraft": interp(ANSWER, offering_ids=(OfferingId.OVERDRAFT,))}
    )
    await resolver.resolve_turn("overdraft")
    request = interpreter.requests[0]

    ids = {entry["id"] for entry in request.catalog}
    assert ids == {"consumer_loan", "mortgage"} | {item.value for item in OfferingId}
    overdraft = next(entry for entry in request.catalog if entry["id"] == "overdraft")
    assert "card overdraft" in overdraft["also_called"]
    assert overdraft["names"]["hy"] == "Օվերդրաֆտ"
    assert "clarification_response" not in request.allowed["intents"]
    assert "current" not in request.allowed["operations"]
    assert request.allowed["fields"]["rate.nominal.minimum"]


@pytest.mark.asyncio
async def test_state_and_offer_reach_the_interpreter_as_context() -> None:
    resolver, interpreter = _resolver(
        {
            "What's the express mortgage rate?": interp(
                ANSWER,
                offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
                operation=QueryOperation.SINGLE,
                fields=RATE,
                standalone_question="What is the Express Mortgage interest rate?",
            ),
            "ok": interp(
                RequestIntent.START_MONITORING_RUN,
                replies_to=ReplyKind.MONITORING_OFFER,
                accepts=True,
            ),
        }
    )
    offer = PendingOffer(
        kind=OfferKind.MONITORING,
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_EXPRESS,
    )
    first = await resolver.resolve_turn("What's the express mortgage rate?")
    second = await resolver.resolve_turn("ok", first.state, pending_offer=offer)

    context = interpreter.requests[1].context
    assert context.last_question == "What is the Express Mortgage interest rate?"
    assert context.last_scope.offering_ids == (OfferingId.MORTGAGE_EXPRESS,)
    assert context.pending_offer == offer
    assert second.resolution.intent is RequestIntent.START_MONITORING_RUN
    assert second.resolution.offering_id is OfferingId.MORTGAGE_EXPRESS


@pytest.mark.asyncio
async def test_a_failing_interpreter_makes_the_turn_unavailable() -> None:
    def fail(_request):
        raise RuntimeError("model down")

    resolver, _ = _resolver({"overdraft rate": fail})
    with pytest.raises(InterpretationUnavailable):
        await resolver.resolve_turn("overdraft rate")


@pytest.mark.asyncio
async def test_an_invalid_interpretation_makes_the_turn_unavailable(
    monkeypatch,
) -> None:
    resolver, _ = _resolver(
        {"overdraft rate": interp(ANSWER, offering_ids=(OfferingId.OVERDRAFT,))}
    )
    monkeypatch.delitem(resolver.validator._offering_labels, OfferingId.OVERDRAFT)
    with pytest.raises(InterpretationUnavailable):
        await resolver.resolve_turn("overdraft rate")


@pytest.mark.asyncio
async def test_no_interpreter_means_unavailable_never_a_guess() -> None:
    resolver = RequestResolver(load_seed_catalog())
    with pytest.raises(InterpretationUnavailable):
        await resolver.resolve_turn("What is the overdraft rate?")


@pytest.mark.asyncio
async def test_an_emoji_is_a_message_but_blank_text_is_not() -> None:
    resolver, interpreter = _resolver(
        {"👍": interp(RequestIntent.UNSUPPORTED_OR_GENERAL)}
    )
    turn = await resolver.resolve_turn("👍")
    assert turn.resolution.normalized_query == "👍"
    assert interpreter.calls == 1
    with pytest.raises(ValueError):
        await resolver.resolve_turn("   ")


@pytest.mark.asyncio
async def test_clarification_state_resolves_a_reply_and_clears_pending() -> None:
    resolver, _ = _resolver(
        {
            "current mortgage rate": interp(
                ANSWER,
                product=ProductType.MORTGAGE,
                operation=QueryOperation.SINGLE,
                fields=RATE,
                standalone_question="What is the current mortgage rate?",
            ),
            "the express one": interp(
                ANSWER,
                replies_to=ReplyKind.CLARIFICATION,
                offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
                operation=QueryOperation.SINGLE,
                fields=RATE,
                standalone_question="What is the current Express Mortgage rate?",
            ),
        }
    )
    first = await resolver.resolve_turn("current mortgage rate")
    second = await resolver.resolve_turn("the express one", first.state)

    assert first.state.pending_clarification.original_query == (
        "What is the current mortgage rate?"
    )
    assert first.state.pending_clarification.expects_single_value is True
    assert second.resolution.intent is RequestIntent.CLARIFICATION_RESPONSE
    assert second.resolution.continuation_intent is ANSWER
    assert second.resolution.offering_id is OfferingId.MORTGAGE_EXPRESS
    assert second.state.pending_clarification is None
    assert second.state.latest_offering_id is OfferingId.MORTGAGE_EXPRESS
    assert second.state.last_question == "What is the current Express Mortgage rate?"


@pytest.mark.asyncio
async def test_a_new_request_replaces_the_pending_clarification() -> None:
    resolver, _ = _resolver(
        {
            "current mortgage rate": interp(
                ANSWER,
                product=ProductType.MORTGAGE,
                operation=QueryOperation.SINGLE,
                fields=RATE,
            ),
            "What changed for consumer loans?": interp(
                RequestIntent.GET_CHANGE_HISTORY,
                product=ProductType.CONSUMER_LOAN,
                family_wide=True,
                operation=QueryOperation.HISTORY,
            ),
        }
    )
    first = await resolver.resolve_turn("current mortgage rate")
    second = await resolver.resolve_turn(
        "What changed for consumer loans?", first.state
    )

    assert second.resolution.intent is RequestIntent.GET_CHANGE_HISTORY
    assert second.resolution.product is ProductType.CONSUMER_LOAN
    assert second.state.pending_clarification is None


@pytest.mark.asyncio
async def test_a_family_reply_to_a_single_value_question_is_not_family_wide() -> None:
    resolver, _ = _resolver(
        {
            "What is the interest?": interp(
                ANSWER,
                operation=QueryOperation.SINGLE,
                fields=RATE,
                clarify=("consumer_loan", "mortgage"),
            ),
            # What the live model answered: a family-wide overview.
            "mortgage": interp(
                ANSWER,
                replies_to=ReplyKind.CLARIFICATION,
                product=ProductType.MORTGAGE,
                family_wide=True,
                operation=QueryOperation.OVERVIEW,
                fields=RATE,
            ),
        }
    )
    first = await resolver.resolve_turn("What is the interest?")
    second = await resolver.resolve_turn("mortgage", first.state)

    assert second.resolution.needs_clarification is True
    assert {c.product for c in second.resolution.candidates} == {ProductType.MORTGAGE}


def test_language_detection_defaults_mixed_text_to_mixed_and_plain_to_english() -> None:
    assert detect_request_language("mortgage հիփոթեք") is RequestLanguage.MIXED
    assert detect_request_language("12345") is RequestLanguage.ENGLISH


def test_session_state_rejects_cross_family_latest_scope() -> None:
    with pytest.raises(ValueError, match="does not belong"):
        ConversationResolutionState(
            latest_product=ProductType.CONSUMER_LOAN,
            latest_offering_id=OfferingId.MORTGAGE_EXPRESS,
        )


def test_the_catalog_payload_is_complete_or_a_short_introduction() -> None:
    resolver, _ = _resolver({})
    full = resolver.catalog_payload(RequestLanguage.ENGLISH, complete=True)
    intro = resolver.catalog_payload(RequestLanguage.ARMENIAN, complete=False)

    assert sum(len(family["offerings"]) for family in full["families"]) == 13
    assert intro["offer_full_list"] is True
    assert all(len(family["offerings"]) <= 3 for family in intro["families"])
    assert intro["families"][1]["name"] == "Հիփոթեքային վարկեր"
