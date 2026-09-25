from typing import Protocol

from app.domain.monitoring import MonitoringRun
from app.services.monitoring_progress import ProgressSink


class TariffPipeline(Protocol):
    async def execute(
        self, run: MonitoringRun, *, progress: ProgressSink | None = None
    ) -> MonitoringRun: ...
