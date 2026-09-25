from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr

from app.api.routes import router
from app.config.models import HitlSettings
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    MonitoringRun,
    RunCommand,
    RunStatus,
    RunTrigger,
)
from app.domain.monitoring_workflow import MonitoringWorkflowResult
from app.domain.review import (
    ReviewCandidate,
    ReviewCorrelation,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.services.chat_reviews import ChatReviewService

NOW = datetime(2026, 9, 21, tzinfo=UTC)


def _run(status: RunStatus = RunStatus.AWAITING_REVIEW) -> MonitoringRun:
    return MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.OVERDRAFT,
            trigger=RunTrigger.ADK,
        ),
        status=status,
        queued_at=NOW,
        started_at=NOW,
        completed_at=NOW if status.is_terminal else None,
    )


def _review(run: MonitoringRun, scope: str = "interest_rate") -> ReviewTask:
    review_id = uuid4()
    return ReviewTask(
        id=review_id,
        idempotency_key=f"review:{review_id}",
        run_id=run.id,
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        reason=ReviewReason.OFFICIAL_SOURCE_CONFLICT,
        issue_scope=scope,
        candidates=(
            ReviewCandidate(
                candidate_id="candidate-1",
                field=scope,
                value="12.5%",
                evidence_references=("evidence-1",),
            ),
        ),
        evidence={
            "items": [
                {
                    "evidence_id": "evidence-1",
                    "content": "Official rate is 12.5%",
                    "locator": {
                        "source_url": "https://ameriabank.am/rates.pdf",
                        "pdf_page": 2,
                    },
                }
            ]
        },
        correlation=ReviewCorrelation(
            app_name="tariff_monitoring_workflow",
            user_id="monitoring-adk",
            session_id=f"monitoring-run-{run.id}",
            invocation_id="invocation-1",
            interrupt_id=f"monitoring-review:{run.id}",
        ),
        created_at=NOW,
        updated_at=NOW,
    )


class _Runs:
    def __init__(self, run: MonitoringRun) -> None:
        self.run = run
        self.audits: list[str] = []

    async def get(self, run_id: UUID):
        return self.run if run_id == self.run.id else None

    async def record_audit(self, run_id, event_type, **kwargs):
        self.audits.append(event_type)


class _Reviews:
    def __init__(self, tasks: tuple[ReviewTask, ...]) -> None:
        self.tasks = tasks

    async def list(self, *, status=None, run_id=None, limit=100, offset=0, **kwargs):
        return tuple(
            task
            for task in self.tasks
            if (status is None or task.status is status)
            and (run_id is None or task.run_id == run_id)
        )[offset : offset + limit]


class _Workflow:
    def __init__(
        self, reviews: _Reviews | None = None, status: RunStatus = RunStatus.FAILED
    ) -> None:
        self.calls = []
        self.reviews = reviews
        self.status = status

    async def resume(self, **kwargs):
        self.calls.append(kwargs)
        if self.reviews is not None:
            self.reviews.tasks = tuple(
                task.model_copy(update={"status": ReviewStatus.REJECTED})
                for task in self.reviews.tasks
            )
        return MonitoringWorkflowResult(run_id=kwargs["run_id"], status=self.status)




















@pytest.mark.asyncio
async def test_abort_all_rejects_each_pending_run_through_workflow() -> None:
    run = _run()
    tasks = (_review(run), _review(run, "fees"))
    reviews = _Reviews(tasks)
    workflow = _Workflow(reviews)
    service = ChatReviewService(runs=_Runs(run), reviews=reviews, workflow=workflow)
    result = await service.abort_all()
    assert result["aborted_review_count"] == 2
    assert result["aborted_runs"][0]["run_id"] == str(run.id)
    assert result["failed_runs"] == []
    assert len(workflow.calls) == 1


@pytest.mark.asyncio
async def test_abort_reports_unprepared_review_as_failed_and_keeps_it_pending() -> None:
    run = _run()
    task = _review(run).model_copy(update={"correlation": None})
    reviews = _Reviews((task,))
    service = ChatReviewService(
        runs=_Runs(run), reviews=reviews, workflow=_Workflow(reviews)
    )
    result = await service.abort_all()
    assert result["aborted_review_count"] == 0
    assert result["failed_runs"] == [
        {"run_id": str(run.id), "reason": "ReviewNotReadyError"}
    ]
    assert reviews.tasks[0].status is ReviewStatus.PENDING


@pytest.mark.asyncio
async def test_abort_api_requires_configured_admin_token() -> None:
    class _AbortService:
        def __init__(self) -> None:
            self.reviewers = []

        async def reject_all_pending(self, *, reviewer):
            self.reviewers.append(reviewer)
            return {"aborted_runs": [], "failed_runs": [], "aborted_review_count": 0}

    app = FastAPI()
    app.state.review_resolution = _AbortService()
    app.state.settings = SimpleNamespace(
        hitl=HitlSettings(review_admin_token=SecretStr("secret-token"))
    )
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        missing = await client.post("/api/v1/reviews/abort-pending")
        wrong = await client.post(
            "/api/v1/reviews/abort-pending", headers={"X-Review-Admin-Token": "wrong"}
        )
        allowed = await client.post(
            "/api/v1/reviews/abort-pending",
            headers={"X-Review-Admin-Token": "secret-token"},
        )
    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["aborted_review_count"] == 0
    assert app.state.review_resolution.reviewers == ["api-admin"]
    app.state.settings = SimpleNamespace(hitl=HitlSettings())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        unconfigured = await client.post(
            "/api/v1/reviews/abort-pending",
            headers={"X-Review-Admin-Token": "secret-token"},
        )
    assert unconfigured.status_code == 503








@pytest.mark.asyncio
async def test_invalid_term_candidate_is_rejected_before_workflow_resume() -> None:
    from app.domain.monitoring_workflow import (
        MonitoringReviewResponse,
        ReviewResponseItem,
    )
    from app.domain.review import ReviewDecision, ReviewDecisionType

    run = _run()
    task = _review(run, "term")
    task = task.model_copy(
        update={
            "candidates": (
                ReviewCandidate(
                    candidate_id="unknown-term",
                    field="term",
                    value="Some indefinite term",
                    evidence_references=("evidence-1",),
                ),
            )
        }
    )
    runs = _Runs(run)
    workflow = _Workflow()
    service = ChatReviewService(runs=runs, reviews=_Reviews((task,)), workflow=workflow)
    response = MonitoringReviewResponse(
        decisions=(
            ReviewResponseItem(
                review_id=task.id,
                decision=ReviewDecision(
                    decision_type=ReviewDecisionType.SELECT_CANDIDATE,
                    candidate_id="unknown-term",
                ),
            ),
        )
    )

    with pytest.raises(ValueError, match="does not match the field schema"):
        await service.resume(
            run.id,
            response,
            actor_user_id="reviewer-1",
            actor_session_id="original-chat-1",
        )

    assert workflow.calls == []
    assert runs.audits == []




















