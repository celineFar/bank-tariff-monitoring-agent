from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.models import OfferingId, ProductType
from app.domain.review import (
    ReviewCandidate,
    ReviewDecision,
    ReviewDecisionType,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)

NOW = datetime(2026, 9, 20, tzinfo=UTC)


def test_override_requires_value_reason_and_existing_evidence_reference() -> None:
    decision = ReviewDecision(
        decision_type=ReviewDecisionType.OVERRIDE,
        override_value="12.25%",
        reason="The table footnote applies to this offering.",
        evidence_reference="evidence:web:rates:4",
    )
    assert decision.override_value == "12.25%"

    with pytest.raises(ValidationError, match="override requires"):
        ReviewDecision(
            decision_type=ReviewDecisionType.OVERRIDE,
            override_value="12.25%",
        )


def test_candidate_selection_requires_exact_candidate_id() -> None:
    with pytest.raises(ValidationError, match="requires candidate_id"):
        ReviewDecision(decision_type=ReviewDecisionType.SELECT_CANDIDATE)


def test_decided_review_requires_reviewer_decision_and_time() -> None:
    candidate = ReviewCandidate(
        candidate_id="web-rate",
        field="nominal_rate",
        value="12.5%",
        evidence_references=("evidence:web:rates:4",),
    )
    with pytest.raises(ValidationError, match="decided review requires"):
        ReviewTask(
            id=uuid4(),
            idempotency_key="review-1",
            run_id=uuid4(),
            offering_execution_id=uuid4(),
            snapshot_id=uuid4(),
            product=ProductType.MORTGAGE,
            offering_id=OfferingId.MORTGAGE_EXPRESS,
            reason=ReviewReason.OFFICIAL_SOURCE_CONFLICT,
            issue_scope="nominal_rate:default",
            candidates=(candidate,),
            status=ReviewStatus.APPROVED,
            created_at=NOW,
            updated_at=NOW,
        )
