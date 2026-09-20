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
from app.services.review_decisions import ReviewDecisionService

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


def _review_task() -> ReviewTask:
    return ReviewTask(
        id=uuid4(),
        idempotency_key="review-service-1",
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_EXPRESS,
        reason=ReviewReason.OFFICIAL_SOURCE_CONFLICT,
        issue_scope="nominal_rate:default",
        candidates=(
            ReviewCandidate(
                candidate_id="web-rate",
                field="nominal_rate",
                value="12.5%",
                evidence_references=("evidence:web:rates:4",),
            ),
        ),
        evidence={"items": [{"evidence_id": "evidence:web:rates:4"}]},
        status=ReviewStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )


class _ReviewRepository:
    def __init__(self, task: ReviewTask) -> None:
        self.task = task
        self.approved = None
        self.rejected = None

    async def get(self, review_id):
        return self.task if review_id == self.task.id else None

    async def approve(self, review_id, decision, *, reviewer, comment=None):
        self.approved = (review_id, decision, reviewer)
        return self.task.model_copy(
            update={
                "status": ReviewStatus.APPROVED,
                "reviewer": reviewer,
                "decision": decision,
                "decided_at": self.task.updated_at,
            }
        )

    async def reject(self, review_id, *, reviewer, comment=None):
        self.rejected = (review_id, reviewer)
        decision = ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL)
        return self.task.model_copy(
            update={
                "status": ReviewStatus.REJECTED,
                "reviewer": reviewer,
                "decision": decision,
                "decided_at": self.task.updated_at,
            }
        )


@pytest.mark.asyncio
async def test_decision_service_rejects_candidate_outside_review_scope() -> None:
    task = _review_task()
    repository = _ReviewRepository(task)
    service = ReviewDecisionService(repository, object())

    with pytest.raises(ValueError, match="outside the review scope"):
        await service.apply(
            task.id,
            ReviewDecision(
                decision_type=ReviewDecisionType.SELECT_CANDIDATE,
                candidate_id="unknown",
            ),
            reviewer="reviewer-1",
        )

    assert repository.approved is None


@pytest.mark.asyncio
async def test_decision_service_routes_reject_all_without_value() -> None:
    task = _review_task()
    repository = _ReviewRepository(task)
    service = ReviewDecisionService(repository, object())

    result = await service.apply(
        task.id,
        ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL),
        reviewer="reviewer-1",
    )

    assert result.status is ReviewStatus.REJECTED
    assert repository.rejected == (task.id, "reviewer-1")
