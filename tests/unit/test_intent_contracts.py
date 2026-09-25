from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.intent import (
    ClarificationOption,
    FreshnessPolicy,
    HistoryPolicy,
    HistoryQuery,
    HistoryRequestKind,
    IntentResolution,
    PendingClarification,
    RequestIntent,
    RequestLanguage,
    ResolutionCandidate,
    ResolutionMethod,
    ResolutionScope,
)
from app.domain.models import OfferingId, ProductType


def _candidate(offering_id: OfferingId, score: float) -> ResolutionCandidate:
    return ResolutionCandidate(
        candidate_id=offering_id.value,
        label=offering_id.value,
        scope=ResolutionScope.OFFERING,
        product=offering_id.product,
        offering_id=offering_id,
        score=score,
    )


def test_intent_taxonomy_contains_the_nine_approved_intents() -> None:
    # The ninth, review_pending_candidates, was added by the ADK-native runtime
    # redesign so pending reviews from headless runs are reachable from chat.
    assert {intent.value for intent in RequestIntent} == {
        "list_supported_products",
        "answer_indexed_tariff_question",
        "get_current_tariffs",
        "start_monitoring_run",
        "get_run_status",
        "get_change_history",
        "unsupported_or_general",
        "clarification_response",
        "review_pending_candidates",
    }


def test_resolved_offering_requires_matching_family() -> None:
    resolution = IntentResolution(
        intent=RequestIntent.GET_CURRENT_TARIFFS,
        language=RequestLanguage.ENGLISH,
        normalized_query="express mortgage",
        method=ResolutionMethod.EXACT,
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_EXPRESS,
    )

    assert resolution.offering_id is OfferingId.MORTGAGE_EXPRESS

    with pytest.raises(ValidationError, match="does not belong"):
        IntentResolution(
            intent=RequestIntent.GET_CURRENT_TARIFFS,
            language=RequestLanguage.ENGLISH,
            normalized_query="bad scope",
            method=ResolutionMethod.EXACT,
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.MORTGAGE_EXPRESS,
        )


def test_ambiguous_resolution_requires_multiple_candidates_and_no_selection() -> None:
    candidates = (
        _candidate(OfferingId.MORTGAGE_PRIMARY, 0.82),
        _candidate(OfferingId.MORTGAGE_SECONDARY_MARKET, 0.80),
    )

    resolution = IntentResolution(
        intent=RequestIntent.GET_CURRENT_TARIFFS,
        language=RequestLanguage.MIXED,
        normalized_query="market mortgage",
        method=ResolutionMethod.CLARIFICATION,
        candidates=candidates,
        needs_clarification=True,
    )

    assert resolution.candidates == candidates

    with pytest.raises(ValidationError, match="at least two"):
        IntentResolution(
            intent=RequestIntent.GET_CURRENT_TARIFFS,
            language=RequestLanguage.ENGLISH,
            normalized_query="mortgage",
            method=ResolutionMethod.CLARIFICATION,
            candidates=(candidates[0],),
            needs_clarification=True,
        )


def test_pending_clarification_requires_timezone_and_unique_options() -> None:
    option = ClarificationOption(
        option_id="mortgage_primary",
        label="Primary Market Mortgage",
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
    )
    second = ClarificationOption(
        option_id="mortgage_secondary_market",
        label="Secondary Market Mortgage",
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_SECONDARY_MARKET,
    )

    pending = PendingClarification(
        original_query="Which market mortgage?",
        intent=RequestIntent.GET_CURRENT_TARIFFS,
        language=RequestLanguage.ENGLISH,
        options=(option, second),
        created_at=datetime.now(UTC),
    )
    assert len(pending.options) == 2

    with pytest.raises(ValidationError, match="timezone-aware"):
        PendingClarification(
            original_query="Which one?",
            intent=RequestIntent.GET_CURRENT_TARIFFS,
            language=RequestLanguage.ENGLISH,
            options=(option, second),
            created_at=datetime.now(),
        )


def test_freshness_and_history_defaults_match_approved_policy() -> None:
    assert FreshnessPolicy().max_age_days == 7
    assert HistoryPolicy().recent_change_days == 60
    assert HistoryPolicy().default_history_days == 30


def test_history_query_validates_scope_and_time_range() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    query = HistoryQuery(
        kind=HistoryRequestKind.SHOW_HISTORY,
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_EXPRESS,
        start_at=start,
        end_at=end,
    )
    assert query.limit == 20

    with pytest.raises(ValidationError, match="must not precede"):
        HistoryQuery(
            kind=HistoryRequestKind.WHAT_CHANGED,
            start_at=end,
            end_at=start,
        )
