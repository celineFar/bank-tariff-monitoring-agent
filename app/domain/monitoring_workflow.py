from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.monitoring import RunStatus
from app.domain.review import (
    ReviewCandidateView,
    ReviewDecision,
    ReviewEvidenceView,
    ReviewPromptView,
)

# The review view models moved to `app.domain.review`; re-exported here until
# this module is deleted with the workflow (plan Phase 7).
__all__ = [
    "MonitoringReviewRequest",
    "MonitoringReviewResponse",
    "MonitoringWorkflowInput",
    "MonitoringWorkflowResult",
    "MonitoringWorkflowState",
    "ReconciliationIssueCode",
    "ReconciliationItem",
    "ReconciliationReport",
    "ReviewCandidateView",
    "ReviewEvidenceView",
    "ReviewPromptView",
    "ReviewResponseItem",
]


class WorkflowModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class MonitoringWorkflowInput(WorkflowModel):
    run_id: UUID


class MonitoringWorkflowState(WorkflowModel):
    run_id: UUID | None = None
    pipeline_executed: bool = False
    review_ids: tuple[UUID, ...] = ()


class ReviewResponseItem(WorkflowModel):
    review_id: UUID
    decision: ReviewDecision


class MonitoringReviewResponse(WorkflowModel):
    decisions: tuple[ReviewResponseItem, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_reviews(self) -> MonitoringReviewResponse:
        review_ids = [item.review_id for item in self.decisions]
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("review decisions must reference unique reviews")
        return self


class MonitoringReviewRequest(WorkflowModel):
    run_id: UUID
    reviews: tuple[ReviewPromptView, ...] = Field(min_length=1, max_length=20)


class MonitoringWorkflowResult(WorkflowModel):
    run_id: UUID
    status: RunStatus
    review_ids: tuple[UUID, ...] = ()
    paused: bool = False
    summary: dict[str, object] = Field(default_factory=dict)


class ReconciliationIssueCode(StrEnum):
    PENDING_WITHOUT_INTERRUPT = "pending_without_interrupt"
    INTERRUPT_WITHOUT_PENDING_REVIEW = "interrupt_without_pending_review"
    TERMINAL_REVIEWS_WITH_PAUSED_RUN = "terminal_reviews_with_paused_run"
    AWAITING_RUN_WITHOUT_REVIEW = "awaiting_run_without_review"


class ReconciliationItem(WorkflowModel):
    run_id: UUID
    issue: ReconciliationIssueCode
    repaired: bool
    review_ids: tuple[UUID, ...] = ()
    detail: str | None = Field(default=None, max_length=500)


class ReconciliationReport(WorkflowModel):
    scanned_runs: int = Field(ge=0)
    items: tuple[ReconciliationItem, ...] = ()
