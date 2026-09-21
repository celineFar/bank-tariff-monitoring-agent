from __future__ import annotations

from dataclasses import dataclass

import pytest
from google.adk.sessions.state import State

from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.domain.intent import (
    ConversationResolutionState,
    RequestIntent,
    RequestLanguage,
    ResolutionMethod,
)
from app.domain.models import OfferingId, ProductType
from app.services.intent_resolution import (
    GeminiResolutionDecision,
    RequestResolver,
    detect_request_language,
)
from app.tools import configure_services, resolve_request


@dataclass
class _FakeClassifier:
    decision: GeminiResolutionDecision | None = None
    error: Exception | None = None
    calls: int = 0
    candidate_ids: tuple[str, ...] = ()
    allowed_intents: tuple[RequestIntent, ...] = ()

    async def classify(self, **kwargs) -> GeminiResolutionDecision:
        self.calls += 1
        self.candidate_ids = tuple(
            candidate.candidate_id for candidate in kwargs["candidates"]
        )
        self.allowed_intents = kwargs["allowed_intents"]
        if self.error is not None:
            raise self.error
        assert self.decision is not None
        return self.decision


@dataclass
class _ToolContext:
    state: dict[str, object]


def _resolver(
    classifier: _FakeClassifier | None = None,
    **settings: object,
) -> RequestResolver:
    return RequestResolver(
        load_seed_catalog(),
        IntentResolutionSettings(**settings),
        classifier=classifier,
    )


@pytest.mark.asyncio
async def test_exact_english_offering_resolution_does_not_call_gemini() -> None:
    classifier = _FakeClassifier(error=AssertionError("must not be called"))

    turn = await _resolver(classifier).resolve_turn(
        "What is the current Express Mortgage rate?"
    )

    assert turn.resolution.intent is RequestIntent.GET_CURRENT_TARIFFS
    assert turn.resolution.offering_id is OfferingId.MORTGAGE_EXPRESS
    assert turn.resolution.method is ResolutionMethod.EXACT
    assert classifier.calls == 0


@pytest.mark.asyncio
async def test_armenian_and_transliterated_aliases_resolve_deterministically() -> None:
    resolver = _resolver()

    armenian = await resolver.resolve_turn("ներկայիս տոկոս Վարկային գիծ")
    transliterated = await resolver.resolve_turn("varkayin gic rate")

    assert armenian.resolution.language is RequestLanguage.ARMENIAN
    assert armenian.resolution.offering_id is OfferingId.CREDIT_LINE
    assert transliterated.resolution.offering_id is OfferingId.CREDIT_LINE


@pytest.mark.asyncio
async def test_conservative_fuzzy_match_resolves_clear_typo() -> None:
    turn = await _resolver(fuzzy_min_score=0.72).resolve_turn(
        "current expres mortgag rate"
    )

    assert turn.resolution.offering_id is OfferingId.MORTGAGE_EXPRESS
    assert turn.resolution.method is ResolutionMethod.FUZZY


@pytest.mark.asyncio
async def test_fuzzy_family_typo_does_not_collapse_to_an_offering() -> None:
    turn = await _resolver(fuzzy_min_score=0.72).resolve_turn(
        "current mortgag tariffs overview"
    )

    assert turn.resolution.product is ProductType.MORTGAGE
    assert turn.resolution.offering_id is None
    assert turn.resolution.method is ResolutionMethod.FUZZY
    assert turn.resolution.needs_clarification is False


@pytest.mark.asyncio
async def test_gemini_fallback_can_only_select_a_supplied_candidate() -> None:
    classifier = _FakeClassifier(
        decision=GeminiResolutionDecision(
            intent=RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
            candidate_id="mortgage_secondary_market",
        )
    )

    turn = await _resolver(classifier).resolve_turn("market home interest")

    assert classifier.calls == 1
    assert "mortgage_secondary_market" in classifier.candidate_ids
    assert classifier.allowed_intents == (RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,)
    assert turn.resolution.offering_id is OfferingId.MORTGAGE_SECONDARY_MARKET
    assert turn.resolution.method is ResolutionMethod.GEMINI


@pytest.mark.asyncio
async def test_invalid_or_failed_gemini_result_asks_instead_of_guessing() -> None:
    invalid = _FakeClassifier(
        decision=GeminiResolutionDecision(
            intent=RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
            candidate_id="not_in_catalog",
        )
    )
    failed = _FakeClassifier(error=RuntimeError("model unavailable"))

    invalid_turn = await _resolver(invalid).resolve_turn("market home interest")
    failed_turn = await _resolver(failed).resolve_turn("market home interest")

    assert invalid_turn.resolution.needs_clarification is True
    assert failed_turn.resolution.needs_clarification is True
    assert invalid_turn.resolution.product is None
    assert failed_turn.resolution.offering_id is None


@pytest.mark.asyncio
async def test_family_behavior_distinguishes_monitoring_overview_and_single_value() -> (
    None
):
    resolver = _resolver()

    monitoring = await resolver.resolve_turn("refresh all mortgage loans")
    overview = await resolver.resolve_turn("current mortgage tariffs overview")
    single = await resolver.resolve_turn("current mortgage rate")

    assert monitoring.resolution.intent is RequestIntent.START_MONITORING_RUN
    assert monitoring.resolution.product is ProductType.MORTGAGE
    assert monitoring.resolution.needs_clarification is False
    assert overview.resolution.intent is RequestIntent.GET_CURRENT_TARIFFS
    assert overview.resolution.product is ProductType.MORTGAGE
    assert overview.resolution.needs_clarification is False
    assert single.resolution.needs_clarification is True
    assert {candidate.offering_id for candidate in single.resolution.candidates} == set(
        OfferingId
    ) - {
        OfferingId.CONSUMER_STANDARD,
        OfferingId.OVERDRAFT,
        OfferingId.CREDIT_LINE,
        OfferingId.ONLINE_CONSUMER_FINANCE,
    }


@pytest.mark.asyncio
async def test_broad_overview_without_scope_remains_catalog_wide() -> None:
    turn = await _resolver().resolve_turn("current tariffs overview")

    assert turn.resolution.intent is RequestIntent.GET_CURRENT_TARIFFS
    assert turn.resolution.product is None
    assert turn.resolution.needs_clarification is False


@pytest.mark.asyncio
async def test_clarification_state_resolves_natural_follow_up_and_clears_pending() -> (
    None
):
    first = await _resolver().resolve_turn("current mortgage rate")

    second = await _resolver().resolve_turn("the express one", first.state)

    assert first.state.pending_clarification is not None
    assert second.resolution.intent is RequestIntent.CLARIFICATION_RESPONSE
    assert second.resolution.continuation_intent is RequestIntent.GET_CURRENT_TARIFFS
    assert second.resolution.offering_id is OfferingId.MORTGAGE_EXPRESS
    assert second.state.pending_clarification is None
    assert second.state.latest_offering_id is OfferingId.MORTGAGE_EXPRESS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("What products are supported?", RequestIntent.LIST_SUPPORTED_PRODUCTS),
        (
            "What is the Express Mortgage fee?",
            RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        ),
        (
            "What fees apply to the card credit line?",
            RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        ),
        ("Current tariffs overview", RequestIntent.GET_CURRENT_TARIFFS),
        (
            "Give me a current overview of all mortgage offerings",
            RequestIntent.GET_CURRENT_TARIFFS,
        ),
        ("Refresh consumer loans", RequestIntent.START_MONITORING_RUN),
        ("What is the run status?", RequestIntent.GET_RUN_STATUS),
        ("What is the status of run 99999999?", RequestIntent.GET_RUN_STATUS),
        ("What changed for mortgages?", RequestIntent.GET_CHANGE_HISTORY),
        ("Write me a poem", RequestIntent.UNSUPPORTED_OR_GENERAL),
    ],
)
async def test_deterministic_intent_taxonomy(
    query: str, expected: RequestIntent
) -> None:
    turn = await _resolver().resolve_turn(query)
    assert turn.resolution.intent is expected


@pytest.mark.asyncio
async def test_unsupported_request_never_invokes_classifier_or_business_scope() -> None:
    classifier = _FakeClassifier(error=AssertionError("must not be called"))

    turn = await _resolver(classifier).resolve_turn("Why is the sky blue?")

    assert turn.resolution.intent is RequestIntent.UNSUPPORTED_OR_GENERAL
    assert turn.resolution.product is None
    assert turn.resolution.offering_id is None
    assert classifier.calls == 0


def test_language_detection_defaults_mixed_text_to_mixed_and_plain_to_english() -> None:
    assert detect_request_language("mortgage հիփոթեք") is RequestLanguage.MIXED
    assert detect_request_language("12345") is RequestLanguage.ENGLISH


def test_session_state_rejects_cross_family_latest_scope() -> None:
    with pytest.raises(ValueError, match="does not belong"):
        ConversationResolutionState(
            latest_product=ProductType.CONSUMER_LOAN,
            latest_offering_id=OfferingId.MORTGAGE_EXPRESS,
        )


@pytest.mark.asyncio
async def test_resolve_request_tool_persists_only_session_clarification_state() -> None:
    context = _ToolContext(state={})
    configure_services(None, None, _resolver())
    try:
        first = await resolve_request("current mortgage rate", context)
        second = await resolve_request("the express one", context)
    finally:
        configure_services(None, None, None)

    assert first["needs_clarification"] is True
    assert first["catalog_intro"]["complete"] is False
    assert second["intent"] == RequestIntent.CLARIFICATION_RESPONSE.value
    assert second["offering_id"] == OfferingId.MORTGAGE_EXPRESS.value
    assert "catalog_intro" not in second
    assert context.state["intent_resolution"]
    assert context.state["temp:monitoring_authorization"] is None


@pytest.mark.asyncio
async def test_resolve_request_grants_and_revokes_scope_bound_monitoring_authorization() -> (
    None
):
    context = _ToolContext(state={})
    configure_services(None, None, _resolver())
    try:
        monitoring = await resolve_request("refresh Express Mortgage", context)
        authorization = context.state["temp:monitoring_authorization"]
        question = await resolve_request("What is the Express Mortgage fee?", context)
    finally:
        configure_services(None, None, None)

    assert monitoring["intent"] == RequestIntent.START_MONITORING_RUN.value
    assert authorization == {
        "product": ProductType.MORTGAGE.value,
        "offering_id": OfferingId.MORTGAGE_EXPRESS.value,
    }
    assert question["intent"] == RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION.value
    assert context.state["temp:monitoring_authorization"] is None


@pytest.mark.asyncio
async def test_resolve_request_supports_native_adk_state_contract() -> None:
    context = _ToolContext(state=State({}, {}))
    configure_services(None, None, _resolver())
    try:
        resolution = await resolve_request("What is the Express Mortgage fee?", context)
    finally:
        configure_services(None, None, None)

    assert resolution["intent"] == RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION.value
    assert context.state.get("temp:monitoring_authorization") is None


@pytest.mark.asyncio
async def test_catalog_list_is_complete_and_intro_is_not_repeated() -> None:
    context = _ToolContext(state={})
    configure_services(None, None, _resolver())
    try:
        first = await resolve_request("What products are supported?", context)
        second = await resolve_request("What products are supported?", context)
    finally:
        configure_services(None, None, None)

    assert first["catalog_intro"]["offer_full_list"] is True
    catalog = first["supported_catalog"]
    assert catalog["complete"] is True
    assert sum(len(family["offerings"]) for family in catalog["families"]) == 13
    assert "catalog_intro" not in second


@pytest.mark.asyncio
async def test_explicit_new_request_replaces_pending_clarification() -> None:
    resolver = _resolver()
    first = await resolver.resolve_turn("current mortgage rate")

    second = await resolver.resolve_turn(
        "What changed for consumer loans?", first.state
    )

    assert second.resolution.intent is RequestIntent.GET_CHANGE_HISTORY
    assert second.resolution.product is ProductType.CONSUMER_LOAN
    assert second.state.pending_clarification is None


@pytest.mark.asyncio
async def test_affirmative_refresh_uses_last_resolved_scope() -> None:
    context = _ToolContext(state={})
    configure_services(None, None, _resolver())
    try:
        await resolve_request("current Express Mortgage rate", context)
        confirmation = await resolve_request("yes", context)
    finally:
        configure_services(None, None, None)

    assert confirmation["intent"] == RequestIntent.START_MONITORING_RUN.value
    assert confirmation["refresh_confirmation"] is True
    assert context.state["temp:monitoring_authorization"] == {
        "product": ProductType.MORTGAGE.value,
        "offering_id": OfferingId.MORTGAGE_EXPRESS.value,
    }
