from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    ClaimedRun,
    MonitoringRun,
    RunCommand,
    RunFailureCode,
    RunStatus,
    RunSubmissionResult,
    RunTrigger,
)
from app.domain.review import ReviewReason, ReviewStatus, ReviewTask
from app.worker import MonitoringWorker, run_scheduled_monitoring


def _run(command: RunCommand, *, status: RunStatus | None = None) -> MonitoringRun:
    now = datetime.now(UTC)
    status = status or RunStatus.QUEUED
    return MonitoringRun(
        id=uuid4(),
        command=command,
        status=status,
        queued_at=now,
        started_at=(
            now if status in {RunStatus.RUNNING, RunStatus.AWAITING_REVIEW} else None
        ),
    )


class _RunService:
    def __init__(self) -> None:
        self.commands: list[tuple[RunCommand, str | None]] = []
        self.runs: dict[object, MonitoringRun] = {}

    async def submit(
        self, command: RunCommand, *, idempotency_key: str | None = None
    ) -> RunSubmissionResult:
        self.commands.append((command, idempotency_key))
        run = _run(command)
        self.runs[run.id] = run
        return RunSubmissionResult(run=run, created=True)

    async def get(self, run_id):
        return self.runs.get(run_id)


class _ConflictingRunService:
    def __init__(self) -> None:
        self.run = _run(
            RunCommand(
                product=ProductType.CONSUMER_LOAN,
                offering_id=OfferingId.OVERDRAFT,
                trigger=RunTrigger.API,
            ),
            status=RunStatus.AWAITING_REVIEW,
        )

    async def submit(self, command, *, idempotency_key=None):
        return RunSubmissionResult(
            run=self.run,
            created=False,
            reused_reason=RunFailureCode.ACTIVE_RUN_EXISTS,
        )


class _FailingRunService:
    async def submit(self, command, *, idempotency_key=None):
        raise RuntimeError("database DSN and internal detail")

    async def get(self, run_id):
        raise RuntimeError("database DSN and internal detail")


class _ReviewRepository:
    def __init__(self, review: ReviewTask) -> None:
        self.review = review

    async def list(self, **kwargs):
        return (self.review,)

    async def get(self, review_id):
        return self.review if review_id == self.review.id else None


@pytest.mark.asyncio
async def test_http_submit_and_status_use_shared_run_service() -> None:
    service = _RunService()
    app = FastAPI()
    app.state.run_service = service
    app.include_router(router)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/runs",
            json={"product": "consumer_loan", "offering_id": "consumer_standard"},
            headers={"Idempotency-Key": "request-1"},
        )
        fetched = await client.get(f"/api/v1/runs/{response.json()['run']['id']}")

    assert response.status_code == 202
    assert response.json()["status_url"] == (
        f"/api/v1/runs/{response.json()['run']['id']}"
    )
    assert response.json()["reviews_url"] == (
        f"/api/v1/reviews?run_id={response.json()['run']['id']}"
    )
    assert fetched.status_code == 200
    command, key = service.commands[0]
    assert command.trigger is RunTrigger.API
    assert command.product is ProductType.CONSUMER_LOAN
    assert key == "request-1"


@pytest.mark.asyncio
async def test_review_routes_are_diagnostic_and_read_only() -> None:
    now = datetime.now(UTC)
    review = ReviewTask(
        id=uuid4(),
        idempotency_key="review:http:1",
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        reason=ReviewReason.LARGE_RATE_CHANGE,
        issue_scope="interest_rate",
        candidates=(),
        status=ReviewStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    app = FastAPI()
    app.state.review_repository = _ReviewRepository(review)
    app.include_router(router)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        listed = await client.get("/api/v1/reviews")
        fetched = await client.get(f"/api/v1/reviews/{review.id}")
        decision = await client.post(
            f"/api/v1/reviews/{review.id}/decision",
            json={"decision_type": "approve"},
        )
        handoff = await client.get(f"/api/v1/runs/{review.run_id}/review-handoff")

    assert listed.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["id"] == str(review.id)
    assert decision.status_code in {404, 405}
    # The ADK-Web handoff route is gone: reviews are taken in the chat CLI.
    assert handoff.status_code == 404


@pytest.mark.asyncio
async def test_different_offering_run_is_reported_as_blocked_not_started() -> None:
    service = _ConflictingRunService()
    app = FastAPI()
    app.state.run_service = service
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/runs",
            json={"product": "consumer_loan", "offering_id": "credit_line"},
        )
    assert response.status_code == 409
    assert response.json()["detail"]["blocking_run_id"] == str(service.run.id)
    assert response.json()["detail"]["blocking_offering_id"] == "overdraft"
    # The chat path reports the same conflict as `blocked`; see
    # tests/unit/test_monitoring_node.py::test_an_active_run_for_another_offering_blocks_without_starting.


@pytest.mark.asyncio
async def test_http_persistence_failures_use_stable_bounded_envelopes() -> None:
    app = FastAPI()
    app.state.run_service = _FailingRunService()
    app.include_router(router)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        submitted = await client.post(
            "/api/v1/runs",
            json={"product": "consumer_loan"},
        )
        fetched = await client.get(f"/api/v1/runs/{uuid4()}")

    assert submitted.status_code == 503
    assert submitted.json()["detail"] == {
        "code": "run.persistence_failed",
        "message": "The monitoring run could not be persisted.",
    }
    assert fetched.status_code == 503
    assert "database" not in fetched.text.lower()


@pytest.mark.asyncio
async def test_scheduler_submits_each_family_through_the_shared_service() -> None:
    service = _RunService()

    await run_scheduled_monitoring(service)

    assert [item[0].trigger for item in service.commands] == [
        RunTrigger.SCHEDULE,
        RunTrigger.SCHEDULE,
    ]
    assert {item[0].product for item in service.commands} == {
        ProductType.CONSUMER_LOAN,
        ProductType.MORTGAGE,
    }


class _WorkerRuns:
    def __init__(self, run: MonitoringRun) -> None:
        self.run = run
        self.claimed = False
        self.recovery_before = None

    async def claim_next(self, worker_id: str) -> ClaimedRun | None:
        if self.claimed:
            return None
        self.claimed = True
        return ClaimedRun(run=self.run, worker_id=worker_id)

    async def recover_abandoned(self, *, before: datetime) -> int:
        self.recovery_before = before
        return 1

    async def finish(self, *args, **kwargs):
        raise AssertionError("successful pipeline owns the terminal transition")


class _Pipeline:
    def __init__(self) -> None:
        self.runs: list[MonitoringRun] = []
        self.progress = []

    async def execute(self, run: MonitoringRun, *, progress=None) -> MonitoringRun:
        self.runs.append(run)
        self.progress.append(progress)
        return run.model_copy(
            update={"status": RunStatus.SUCCEEDED, "completed_at": run.started_at}
        )


class _Resolution:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_runs_without_pending_reviews(self, *, limit: int = 100):
        self.calls += 1
        return 0


@pytest.mark.asyncio
async def test_worker_claims_queue_and_invokes_shared_pipeline() -> None:
    run = _run(
        RunCommand(product=ProductType.MORTGAGE, trigger=RunTrigger.SCHEDULE),
        status=RunStatus.RUNNING,
    )
    runs = _WorkerRuns(run)
    pipeline = _Pipeline()
    resolution = _Resolution()
    worker = MonitoringWorker(
        runs=runs,
        pipeline=pipeline,
        resolution=resolution,
        worker_id="worker-1",
        abandoned_after=timedelta(minutes=15),
    )

    await worker.startup_checks()
    assert await worker.process_next() is True
    assert await worker.process_next() is False
    # The worker calls the pipeline directly: no ADK app, no ADK session.
    assert pipeline.runs == [run]
    assert type(pipeline.progress[0]).__name__ == "LogProgressSink"
    assert runs.recovery_before is not None
    assert resolution.calls == 1


def test_the_worker_imports_nothing_from_google_adk() -> None:
    import ast
    from pathlib import Path

    tree = ast.parse(Path("app/worker.py").read_text(encoding="utf-8"))
    imported = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name.startswith("google.adk") for name in imported)
