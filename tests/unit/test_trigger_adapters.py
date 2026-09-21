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
    RunStatus,
    RunSubmissionResult,
    RunTrigger,
)
from app.domain.review import ReviewReason, ReviewStatus, ReviewTask
from app.tools import configure_run_service, start_tariff_monitoring
from app.worker import MonitoringWorker, run_scheduled_monitoring


def _run(command: RunCommand, *, status: RunStatus | None = None) -> MonitoringRun:
    now = datetime.now(UTC)
    status = status or RunStatus.QUEUED
    return MonitoringRun(
        id=uuid4(),
        command=command,
        status=status,
        queued_at=now,
        started_at=now if status is RunStatus.RUNNING else None,
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


class _FailingRunService:
    async def submit(self, command, *, idempotency_key=None):
        raise RuntimeError("database DSN and internal detail")

    async def get(self, run_id):
        raise RuntimeError("database DSN and internal detail")


class _ToolContext:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state


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

    assert listed.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["id"] == str(review.id)
    assert decision.status_code in {404, 405}


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
async def test_scheduler_and_adk_tool_submit_through_same_service() -> None:
    service = _RunService()
    configure_run_service(service)
    try:
        await run_scheduled_monitoring(service)
        result = await start_tariff_monitoring(
            "consumer_loan",
            None,
            _ToolContext(
                state={
                    "temp:monitoring_authorization": {
                        "product": "consumer_loan",
                        "offering_id": None,
                    }
                }
            ),
        )
    finally:
        configure_run_service(None)

    assert [item[0].trigger for item in service.commands] == [
        RunTrigger.SCHEDULE,
        RunTrigger.SCHEDULE,
        RunTrigger.ADK,
    ]
    assert result["status"] == "queued"


@pytest.mark.asyncio
async def test_adk_monitoring_tool_rejects_missing_or_non_monitoring_intent() -> None:
    service = _RunService()
    configure_run_service(service)
    try:
        result = await start_tariff_monitoring(
            "mortgage",
            "mortgage_express",
            _ToolContext(state={}),
        )
    finally:
        configure_run_service(None)

    assert result["status"] == "rejected"
    assert result["reason_code"] == "run.intent_not_authorized"
    assert service.commands == []


@pytest.mark.asyncio
async def test_adk_monitoring_tool_rejects_invalid_cross_family_scope() -> None:
    service = _RunService()
    configure_run_service(service)
    try:
        result = await start_tariff_monitoring(
            "consumer_loan",
            "mortgage_express",
            _ToolContext(
                state={
                    "temp:monitoring_authorization": {
                        "product": "consumer_loan",
                        "offering_id": "mortgage_express",
                    }
                }
            ),
        )
    finally:
        configure_run_service(None)

    assert result["status"] == "rejected"
    assert result["reason_code"] == "run.invalid_scope"
    assert service.commands == []


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


class _Workflow:
    def __init__(self) -> None:
        self.runs: list[MonitoringRun] = []

    async def start(self, run: MonitoringRun):
        self.runs.append(run)
        return {
            "run_id": str(run.id),
            "status": run.status.value,
            "paused": False,
        }


@pytest.mark.asyncio
async def test_worker_claims_queue_and_invokes_shared_pipeline() -> None:
    run = _run(
        RunCommand(product=ProductType.MORTGAGE, trigger=RunTrigger.SCHEDULE),
        status=RunStatus.RUNNING,
    )
    runs = _WorkerRuns(run)
    workflow = _Workflow()
    worker = MonitoringWorker(
        runs=runs,
        workflow=workflow,
        worker_id="worker-1",
        abandoned_after=timedelta(minutes=15),
    )

    assert await worker.recover_abandoned() == 1
    assert await worker.process_next() is True
    assert await worker.process_next() is False
    assert workflow.runs == [run]
    assert runs.recovery_before is not None
