"""The lease a process holds while it executes a run, and stop requests.

Both executors (the worker and the chat's monitoring node) run the pipeline
through `execute_with_lease`: the pipeline runs as a task while this loop
renews the run's heartbeat. The heartbeat is also how the owner hears that
another process asked it to stop (a chat following the run pressed Ctrl-C)
or that the run was closed as abandoned; either way the pipeline task is
cancelled, and the pipeline's own cancellation handling closes the run.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol, TypeVar
from uuid import UUID

from app.domain.monitoring import LeaseState, RunCancelOutcome

logger = logging.getLogger(__name__)
T = TypeVar("T")


class RunLeasePort(Protocol):
    async def heartbeat(self, run_id: UUID, owner: str) -> LeaseState: ...

    async def cancel_run(
        self,
        run_id: UUID,
        *,
        requested_by: str,
        stale_before: datetime | None = None,
    ) -> RunCancelOutcome: ...

    async def recover_abandoned(self, *, before: datetime) -> int: ...


class RunStopped(Exception):
    """The run was stopped from outside while this process executed it."""

    def __init__(self, run_id: UUID, state: LeaseState) -> None:
        super().__init__(f"run {run_id} stopped: {state.value}")
        self.run_id = run_id
        self.state = state


async def execute_with_lease(
    runs: RunLeasePort,
    run_id: UUID,
    owner: str,
    work: Callable[[], Awaitable[T]],
    *,
    heartbeat_seconds: float,
) -> T:
    """Run `work` while renewing the lease; raise `RunStopped` if told to stop.

    Cancelling the caller cancels `work` and waits for its cleanup, so the run
    is closed before the cancellation propagates.
    """
    task = asyncio.ensure_future(work())
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=heartbeat_seconds)
            if done:
                return task.result()
            try:
                state = await runs.heartbeat(run_id, owner)
            except Exception:
                # A missed beat is harmless until the lease expires; the
                # database being briefly unreachable must not stop the run.
                logger.warning("run heartbeat failed run_id=%s", run_id, exc_info=True)
                continue
            if state in {LeaseState.HELD, LeaseState.RELEASED}:
                continue
            logger.info("stopping run run_id=%s lease=%s", run_id, state.value)
            task.cancel()
            await asyncio.wait({task})
            if not task.cancelled():
                return task.result()  # it finished before the cancel landed
            raise RunStopped(run_id, state)
    except BaseException:
        if not task.done():
            task.cancel()
            await asyncio.wait({task})
        raise


async def recover_stale_runs(runs: RunLeasePort, lease_seconds: float) -> int:
    """Close `running` runs whose owner stopped renewing the lease."""
    try:
        recovered = await runs.recover_abandoned(before=lease_cutoff(lease_seconds))
    except Exception:
        logger.warning("stale run recovery failed", exc_info=True)
        return 0
    if recovered:
        logger.warning("closed %s abandoned run(s)", recovered)
    return recovered


def lease_cutoff(lease_seconds: float) -> datetime:
    return datetime.now(UTC) - timedelta(seconds=lease_seconds)


async def stop_run(
    runs: RunLeasePort,
    run_id: UUID,
    *,
    requested_by: str,
    lease_seconds: float,
) -> RunCancelOutcome | None:
    """Best-effort stop from a cancelled caller; never raises."""
    try:
        outcome = await runs.cancel_run(
            run_id,
            requested_by=requested_by,
            stale_before=lease_cutoff(lease_seconds),
        )
    except Exception:
        logger.warning("could not stop run %s", run_id, exc_info=True)
        return None
    logger.info("stop requested run_id=%s outcome=%s", run_id, outcome.value)
    return outcome
