import json

from app.domain.review import ReviewDecisionType, ReviewReason
from app.services.review_resolution import build_review_view
from scripts.demonstrate_native_hitl import (
    build_demo_payload,
    large_change_review,
    source_conflict_review,
)


def test_large_change_demo_uses_reason_specific_review_contract() -> None:
    prompt = build_review_view(large_change_review())

    assert prompt.reason is ReviewReason.LARGE_RATE_CHANGE
    assert prompt.allowed_decisions == (
        ReviewDecisionType.APPROVE,
        ReviewDecisionType.REJECT_ALL,
        ReviewDecisionType.OVERRIDE,
    )
    assert prompt.candidates[0].conditions["change_points"] == "3.6"
    assert prompt.evidence[0].page == 4


def test_source_conflict_demo_keeps_pdf_and_web_candidates_distinct() -> None:
    prompt = build_review_view(source_conflict_review())

    assert prompt.reason is ReviewReason.OFFICIAL_SOURCE_CONFLICT
    assert prompt.allowed_decisions == (
        ReviewDecisionType.SELECT_CANDIDATE,
        ReviewDecisionType.REJECT_ALL,
        ReviewDecisionType.OVERRIDE,
    )
    assert len(prompt.candidates) == 2
    assert {item.source_type for item in prompt.evidence} == {"pdf", "webpage"}


def test_demo_payload_is_what_the_node_puts_on_a_request_input() -> None:
    payloads = json.loads(build_demo_payload("all"))

    assert [item["position"] for item in payloads] == [1, 2]
    assert {item["kind"] for item in payloads} == {"tariff_review"}
    assert payloads[0]["input_format"]["field"] == "nominal_interest_rate"
