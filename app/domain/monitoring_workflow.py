from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.monitoring import RunStatus
from app.domain.review import ReviewDecision


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


class MonitoringWorkflowResult(WorkflowModel):
    run_id: UUID
    status: RunStatus
    review_ids: tuple[UUID, ...] = ()
    paused: bool = False
    summary: dict[str, object] = Field(default_factory=dict)
