from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from google.adk.sessions import InMemorySessionService

from app.app_utils.services import ensure_session_service_ready
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import MonitoringRun, RunCommand, RunStatus, RunTrigger
from app.domain.monitoring_workflow import ReconciliationIssueCode
from app.domain.review import ReviewReason, ReviewStatus, ReviewTask
from app.services.workflow_reconciliation import WorkflowReconciliationService

NOW = datetime(2026, 9, 20, tzinfo=UTC)


@pytest.mark.asyncio
async def test_session_startup_gate_allows_memory_only_when_explicit() -> None:
    service = InMemorySessionService()

    assert (
        await ensure_session_service_ready(service, require_persistent=False) is service
    )
    with pytest.raises(RuntimeError, match="requires a PostgreSQL"):
        await ensure_session_service_ready(service)


def _run() -> MonitoringRun:
    return MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.MORTGAGE,
            offering_id=OfferingId.MORTGAGE_PRIMARY,
            trigger=RunTrigger.SCHEDULE,
        ),
        status=RunStatus.AWAITING_REVIEW,
        queued_at=NOW,
        started_at=NOW,
        summary={"succeeded": 0, "failed": 0},
    )


def _review(run_id, status=ReviewStatus.PENDING) -> ReviewTask:
    return ReviewTask.model_construct(
        id=uuid4(),
        idempotency_key=f"review:{uuid4()}",
        run_id=run_id,
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        reason=ReviewReason.LARGE_RATE_CHANGE,
        issue_scope="interest_rate",
        candidates=(),
        evidence={},
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


class _Runs:
    def __init__(self, run: MonitoringRun) -> None:
        self.run = run
        self.audits = []

    async def list_by_status(self, status, *, limit=100):
        return (self.run,) if self.run.status is status else ()

    async def finish_after_review(self, run_id, status, *, summary):
        self.run = self.run.model_copy(
            update={"status": status, "summary": summary, "completed_at": NOW}
        )
        return self.run

    async def record_audit(self, run_id, event_type, **kwargs):
        self.audits.append((run_id, event_type, kwargs))


class _Reviews:
    def __init__(self, tasks=()) -> None:
        self.tasks = tuple(tasks)

    async def list(self, **kwargs):
        return tuple(
            task
            for task in self.tasks
            if (kwargs.get("run_id") is None or task.run_id == kwargs["run_id"])
            and (kwargs.get("status") is None or task.status is kwargs["status"])
        )

    async def get(self, review_id):
        return next((task for task in self.tasks if task.id == review_id), None)


class _Workflow:
    def __init__(self) -> None:
        self.started = []

    async def start(self, run):
        self.started.append(run.id)


@pytest.mark.asyncio
async def test_reconciliation_fails_orphaned_awaiting_run_safely() -> None:
    run = _run()
    runs = _Runs(run)
    service = WorkflowReconciliationService(
        runs=runs,
        reviews=_Reviews(),
        sessions=InMemorySessionService(),
        workflow=_Workflow(),
    )

    report = await service.reconcile()

    assert report.items[0].issue is ReconciliationIssueCode.AWAITING_RUN_WITHOUT_REVIEW
    assert report.items[0].repaired is True
    assert runs.run.status is RunStatus.FAILED
    assert runs.audits[0][1] == "review.reconciled"


@pytest.mark.asyncio
async def test_reconciliation_finishes_run_after_terminal_reviews() -> None:
    run = _run()
    task = _review(run.id, ReviewStatus.APPROVED)
    runs = _Runs(run)
    service = WorkflowReconciliationService(
        runs=runs,
        reviews=_Reviews((task,)),
        sessions=InMemorySessionService(),
        workflow=_Workflow(),
    )

    report = await service.reconcile()

    assert (
        report.items[-1].issue
        is ReconciliationIssueCode.TERMINAL_REVIEWS_WITH_PAUSED_RUN
    )
    assert runs.run.status is RunStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_reconciliation_does_not_claim_repair_without_new_interrupt() -> None:
    run = _run()
    task = _review(run.id)
    runs = _Runs(run)
    workflow = _Workflow()
    service = WorkflowReconciliationService(
        runs=runs,
        reviews=_Reviews((task,)),
        sessions=InMemorySessionService(),
        workflow=workflow,
    )

    report = await service.reconcile()

    assert report.items[0].issue is ReconciliationIssueCode.PENDING_WITHOUT_INTERRUPT
    assert report.items[0].repaired is False
    assert workflow.started == [run.id]
    assert runs.run.status is RunStatus.AWAITING_REVIEW
