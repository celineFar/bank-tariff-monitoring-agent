"""Stopping runs: the execution lease, worker shutdown, stale-run recovery.

Found by the stop experiments in fix-process/adk-behavior: a SIGTERM let the
worker finish the whole run (model calls included), a chat following a
worker's run could not stop it, and a killed process left its run `running`
until a worker restarted 30 minutes later.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    ClaimedRun,
    LeaseState,
    MonitoringRun,
    RunCancelOutcome,
    RunCommand,
    RunFailureCode,
    RunStatus,
    RunTrigger,
)
from app.services.run_lease import RunStopped, execute_with_lease
from app.worker import MonitoringWorker

NOW = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)


class _Lease:
    def __init__(self, *states: LeaseState) -> None:
        self.states = list(states)
        self.beats = 0

    async def heartbeat(self, run_id: UUID, owner: str) -> LeaseState:
        self.beats += 1
        state = self.states.pop(0) if self.states else LeaseState.HELD
        if isinstance(state, Exception):
            raise state
        return state


class _Work:
    def __init__(self, result: object = "done", *, forever: bool = False) -> None:
        self.result = result
        self.forever = forever
        self.cancelled = False
        self.cleaned_up = False

    async def __call__(self):
        try:
            if self.forever:
                await asyncio.Event().wait()
            await asyncio.sleep(0.05)
            return self.result
        except asyncio.CancelledError:
            self.cancelled = True
            await asyncio.sleep(0)  # cleanup that awaits, like the pipeline's
            self.cleaned_up = True
            raise


@pytest.mark.asyncio
async def test_lease_returns_the_work_result_and_beats_meanwhile() -> None:
    lease = _Lease()
    work = _Work("finished")

    result = await execute_with_lease(
        lease, uuid4(), "worker-1", work, heartbeat_seconds=0.01
    )

    assert result == "finished"
    assert lease.beats >= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [LeaseState.CANCEL_REQUESTED, LeaseState.LOST])
async def test_a_stop_signal_in_the_lease_cancels_the_work(state) -> None:
    work = _Work(forever=True)

    with pytest.raises(RunStopped) as stopped:
        await execute_with_lease(
            _Lease(LeaseState.HELD, state),
            uuid4(),
            "worker-1",
            work,
            heartbeat_seconds=0.01,
        )

    assert stopped.value.state is state
    assert work.cancelled and work.cleaned_up


@pytest.mark.asyncio
async def test_a_released_lease_or_a_failed_beat_does_not_stop_the_work() -> None:
    # Released: the pipeline itself just finished or paused the run.
    lease = _Lease(LeaseState.RELEASED, RuntimeError("database away"))
    work = _Work("kept")

    result = await execute_with_lease(
        lease, uuid4(), "worker-1", work, heartbeat_seconds=0.01
    )

    assert result == "kept"
    assert not work.cancelled


@pytest.mark.asyncio
async def test_cancelling_the_caller_cancels_the_work_and_waits_for_cleanup() -> None:
    work = _Work(forever=True)
    caller = asyncio.create_task(
        execute_with_lease(_Lease(), uuid4(), "worker-1", work, heartbeat_seconds=1)
    )
    await asyncio.sleep(0.02)

    caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await caller

    assert work.cleaned_up  # finished before the cancellation reached us


# --- the worker ---------------------------------------------------------------------


def _running_run() -> MonitoringRun:
    return MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.OVERDRAFT,
            trigger=RunTrigger.API,
        ),
        status=RunStatus.RUNNING,
        queued_at=NOW,
        started_at=NOW,
    )


class _WorkerRuns:
    """Just enough RunRepository for the worker, with PostgreSQL's rules."""

    def __init__(self, run: MonitoringRun) -> None:
        self.run = run
        self.owner: str | None = None
        self.cancel_requested = False
        self.cancels: list[str] = []
        self.recoveries = 0

    async def claim_next(self, worker_id: str) -> ClaimedRun | None:
        if self.owner is not None:
            return None
        self.owner = worker_id
        return ClaimedRun(run=self.run, worker_id=worker_id)

    async def heartbeat(self, run_id: UUID, owner: str) -> LeaseState:
        if self.run.status is not RunStatus.RUNNING:
            return LeaseState.RELEASED
        return LeaseState.CANCEL_REQUESTED if self.cancel_requested else LeaseState.HELD

    async def cancel_run(self, run_id, *, requested_by, stale_before=None):
        self.cancels.append(requested_by)
        if self.run.status is not RunStatus.RUNNING:
            return RunCancelOutcome.NOT_ACTIVE
        self.close(RunFailureCode.CANCELLED)
        return RunCancelOutcome.CANCELLED

    async def recover_abandoned(self, *, before: datetime) -> int:
        self.recoveries += 1
        return 0

    async def finish(self, run_id, status, **kwargs):
        raise AssertionError("the pipeline owns the terminal transition")

    def close(self, code: RunFailureCode) -> MonitoringRun:
        self.run = self.run.model_copy(
            update={"status": RunStatus.FAILED, "failure_code": code.value}
        )
        return self.run


class _BlockingPipeline:
    """Runs until cancelled, then closes the run the way TariffPipeline does."""

    def __init__(self, runs: _WorkerRuns) -> None:
        self.runs = runs
        self.started = asyncio.Event()
        self.cancelled = False

    async def execute(self, run, *, progress=None):
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            self.runs.close(RunFailureCode.CANCELLED)
            raise


def _worker(runs, pipeline, **options) -> MonitoringWorker:
    return MonitoringWorker(
        runs=runs,
        pipeline=pipeline,
        worker_id="worker-1",
        heartbeat_seconds=0.01,
        poll_interval_seconds=0.01,
        **options,
    )


@pytest.mark.asyncio
async def test_a_stop_signal_cancels_the_run_in_progress() -> None:
    runs = _WorkerRuns(_running_run())
    pipeline = _BlockingPipeline(runs)
    stop = asyncio.Event()
    worker = asyncio.create_task(_worker(runs, pipeline).run_forever(stop))
    await asyncio.wait_for(pipeline.started.wait(), 5)

    stop.set()  # what SIGTERM does
    await asyncio.wait_for(worker, 5)  # it exits instead of finishing the run

    assert pipeline.cancelled
    assert runs.run.failure_code == "run.cancelled"
    # Then the worker's own close finds nothing left to close.
    assert runs.cancels == ["worker-1"]


@pytest.mark.asyncio
async def test_a_stop_requested_by_a_following_chat_ends_the_workers_run() -> None:
    runs = _WorkerRuns(_running_run())
    pipeline = _BlockingPipeline(runs)
    worker = _worker(runs, pipeline)
    processing = asyncio.create_task(worker.process_next())
    await asyncio.wait_for(pipeline.started.wait(), 5)

    runs.cancel_requested = True

    assert await asyncio.wait_for(processing, 5) is True
    assert pipeline.cancelled
    assert runs.run.failure_code == "run.cancelled"


@pytest.mark.asyncio
async def test_the_worker_recovers_stale_runs_while_it_runs_not_only_at_start() -> None:
    runs = _WorkerRuns(_running_run())
    runs.owner = "someone-else"  # nothing to claim
    stop = asyncio.Event()
    worker = asyncio.create_task(
        _worker(
            runs,
            _BlockingPipeline(runs),
            recovery_interval_seconds=0.01,
            abandoned_after=timedelta(seconds=120),
        ).run_forever(stop)
    )
    await asyncio.sleep(0.1)
    stop.set()
    await asyncio.wait_for(worker, 5)

    assert runs.recoveries >= 3  # startup, then periodically
