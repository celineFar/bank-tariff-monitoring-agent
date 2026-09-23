from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from app.domain.monitoring import (
    MonitoringRun,
    OfferingExecution,
    RunCommand,
    RunSubmissionResult,
)
from app.repositories.contracts import RunRepository


def run_covers_command(run: MonitoringRun, requested: RunCommand) -> bool:
    return run.command.product is requested.product and (
        run.command.offering_id is None
        or run.command.offering_id is requested.offering_id
    )


class RunServicePort(Protocol):
    async def submit(
        self, command: RunCommand, *, idempotency_key: str | None = None
    ) -> RunSubmissionResult: ...

    async def get(self, run_id: UUID) -> MonitoringRun | None: ...


@runtime_checkable
class RunProgressPort(Protocol):
    """What a caller needs to narrate a run while the worker executes it.

    Kept separate from `RunServicePort` so progress readers state the two methods
    they call, and so the trigger adapters keep their smaller surface.
    """

    async def get(self, run_id: UUID) -> MonitoringRun | None: ...

    async def list_offering_executions(
        self, run_id: UUID
    ) -> tuple[OfferingExecution, ...]: ...


class RunService:
    """Shared application boundary used by HTTP, scheduler, and ADK adapters."""

    def __init__(self, repository: RunRepository) -> None:
        self._repository = repository

    async def submit(
        self, command: RunCommand, *, idempotency_key: str | None = None
    ) -> RunSubmissionResult:
        return await self._repository.submit(
            command,
            idempotency_key=idempotency_key,
        )

    async def get(self, run_id: UUID) -> MonitoringRun | None:
        return await self._repository.get(run_id)

    async def list_offering_executions(
        self, run_id: UUID
    ) -> tuple[OfferingExecution, ...]:
        return await self._repository.list_offering_executions(run_id)
