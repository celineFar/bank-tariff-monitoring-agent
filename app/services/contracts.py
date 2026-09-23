from typing import Protocol

from app.domain.monitoring import MonitoringRun


class TariffPipeline(Protocol):
    async def execute(self, run: MonitoringRun) -> MonitoringRun: ...
