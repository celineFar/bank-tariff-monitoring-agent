from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import MonitoringRun, RunCommand, RunStatus, RunTrigger
from app.domain.monitoring_workflow import (
    MonitoringReviewResponse,
    ReviewResponseItem,
)
from app.domain.review import (
    ReviewCorrelation,
    ReviewDecision,
    ReviewDecisionType,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.services.monitoring_workflow import (
    MonitoringWorkflowRunner,
    build_monitoring_app,
    build_monitoring_workflow,
    workflow_identity,
)

NOW = datetime(2026, 9, 20, tzinfo=UTC)


class _Runs:
    def __init__(self, run: MonitoringRun) -> None:
        self.run = run

    async def get(self, run_id: UUID) -> MonitoringRun | None:
        return self.run if self.run.id == run_id else None

    async def finish_after_review(
        self,
        run_id: UUID,
        status: RunStatus,
        *,
        summary: dict[str, object],
    ) -> MonitoringRun:
        assert run_id == self.run.id
        self.run = self.run.model_copy(
            update={"status": status, "summary": summary, "completed_at": NOW}
        )
        return self.run


class _Pipeline:
    def __init__(self, runs: _Runs) -> None:
        self.runs = runs
        self.calls = 0

    async def execute(self, run: MonitoringRun) -> MonitoringRun:
        self.calls += 1
        self.runs.run = run.model_copy(
            update={
                "status": RunStatus.AWAITING_REVIEW,
                "summary": {
                    "succeeded": 0,
                    "failed": 0,
                    "review_ids": [str(REVIEW_ID)],
                },
            }
        )
        return self.runs.run


class _Reviews:
    def __init__(self, task: ReviewTask) -> None:
        self.task = task

    async def get(self, review_id: UUID) -> ReviewTask | None:
        return self.task if review_id == self.task.id else None

    async def list(self, **kwargs) -> tuple[ReviewTask, ...]:
        if (
            kwargs.get("run_id") == self.task.run_id
            and kwargs.get("status") is self.task.status
        ):
            return (self.task,)
        return ()

    async def attach_workflow(
        self, review_id: UUID, correlation: ReviewCorrelation
    ) -> ReviewTask:
        assert review_id == self.task.id
        self.task = self.task.model_copy(update={"correlation": correlation})
        return self.task


class _Decisions:
    def __init__(self, reviews: _Reviews) -> None:
        self.reviews = reviews
        self.calls = 0

    async def apply(
        self,
        review_id: UUID,
        decision: ReviewDecision,
        *,
        reviewer: str,
    ) -> ReviewTask:
        self.calls += 1
        assert review_id == self.reviews.task.id
        self.reviews.task = self.reviews.task.model_copy(
            update={
                "status": ReviewStatus.APPROVED,
                "reviewer": reviewer,
                "decision": decision,
                "decided_at": NOW,
                "updated_at": NOW,
            }
        )
        return self.reviews.task


RUN_ID = uuid4()
REVIEW_ID = uuid4()


def _running_run() -> MonitoringRun:
    return MonitoringRun(
        id=RUN_ID,
        command=RunCommand(
            product=ProductType.MORTGAGE,
            offering_id=OfferingId.MORTGAGE_PRIMARY,
            trigger=RunTrigger.API,
        ),
        status=RunStatus.RUNNING,
        queued_at=NOW,
        started_at=NOW,
    )


def _review() -> ReviewTask:
    return ReviewTask(
        id=REVIEW_ID,
        idempotency_key=f"review:{REVIEW_ID}",
        run_id=RUN_ID,
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        reason=ReviewReason.LARGE_RATE_CHANGE,
        issue_scope="interest_rate",
        candidates=(),
        status=ReviewStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_native_request_input_resume_does_not_rerun_pipeline() -> None:
    runs = _Runs(_running_run())
    pipeline = _Pipeline(runs)
    reviews = _Reviews(_review())
    decisions = _Decisions(reviews)
    workflow = build_monitoring_workflow(
        runs=runs,
        pipeline=pipeline,
        reviews=reviews,
        decisions=decisions,
    )
    runner = MonitoringWorkflowRunner(
        app=build_monitoring_app(workflow),
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )

    paused = await runner.start(runs.run)

    assert paused.status is RunStatus.AWAITING_REVIEW
    assert paused.paused is True
    assert pipeline.calls == 1
    assert reviews.task.correlation is not None
    user_id, session_id = workflow_identity(runs.run)
    assert reviews.task.correlation.user_id == user_id
    assert reviews.task.correlation.session_id == session_id

    completed = await runner.resume(
        user_id=user_id,
        session_id=session_id,
        interrupt_id=reviews.task.correlation.interrupt_id,
        response=MonitoringReviewResponse(
            decisions=(
                ReviewResponseItem(
                    review_id=REVIEW_ID,
                    decision=ReviewDecision(
                        decision_type=ReviewDecisionType.APPROVE
                    ),
                ),
            )
        ),
        run_id=RUN_ID,
    )

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.paused is False
    assert pipeline.calls == 1
    assert decisions.calls == 1
    assert runs.run.summary["reviews_approved"] == 1
