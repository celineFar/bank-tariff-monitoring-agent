from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.monitoring import MonitoringRun, RunCommand, RunSubmissionResult
from app.repositories.contracts import RunRepository


class RunServicePort(Protocol):
    async def submit(
        self, command: RunCommand, *, idempotency_key: str | None = None
    ) -> RunSubmissionResult: ...

    async def get(self, run_id: UUID) -> MonitoringRun | None: ...


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
