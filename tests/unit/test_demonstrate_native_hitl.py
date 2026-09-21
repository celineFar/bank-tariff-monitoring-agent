from app.domain.review import ReviewDecisionType, ReviewReason
from app.services.monitoring_workflow import build_review_request
from scripts.demonstrate_native_hitl import (
    RUN_ID,
    large_change_review,
    source_conflict_review,
)


def test_large_change_demo_uses_reason_specific_review_contract() -> None:
    prompt = build_review_request(RUN_ID, (large_change_review(),)).reviews[0]

    assert prompt.reason is ReviewReason.LARGE_RATE_CHANGE
    assert prompt.allowed_decisions == (
        ReviewDecisionType.APPROVE,
        ReviewDecisionType.REJECT_ALL,
        ReviewDecisionType.OVERRIDE,
    )
    assert prompt.candidates[0].conditions["change_points"] == "3.6"
    assert prompt.evidence[0].page == 4


def test_source_conflict_demo_keeps_pdf_and_web_candidates_distinct() -> None:
    prompt = build_review_request(RUN_ID, (source_conflict_review(),)).reviews[0]

    assert prompt.reason is ReviewReason.OFFICIAL_SOURCE_CONFLICT
    assert prompt.allowed_decisions == (
        ReviewDecisionType.SELECT_CANDIDATE,
        ReviewDecisionType.REJECT_ALL,
        ReviewDecisionType.OVERRIDE,
    )
    assert len(prompt.candidates) == 2
    assert {item.source_type for item in prompt.evidence} == {"pdf", "webpage"}
