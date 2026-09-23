from __future__ import annotations

import asyncio
import logging
import signal
import socket
from datetime import UTC, datetime, timedelta
from typing import Protocol

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.app_utils import services as adk_services
from app.config import get_settings
from app.domain.models import ProductType
from app.domain.monitoring import (
    MonitoringRun,
    RunCommand,
    RunFailureCode,
    RunStatus,
    RunTrigger,
)
from app.domain.monitoring_workflow import MonitoringWorkflowResult
from app.repositories.contracts import RunRepository
from app.runtime import build_application_container
from app.services.logging_setup import configure_application_logging
from app.services.run_service import RunServicePort
from app.services.telemetry import (
    configure_telemetry,
    extract_trace_context,
    get_tracer,
)

logger = logging.getLogger(__name__)
tracer = get_tracer()
PRODUCTS = (ProductType.CONSUMER_LOAN, ProductType.MORTGAGE)


class MonitoringWorkflowPort(Protocol):
    async def start(self, run: MonitoringRun) -> MonitoringWorkflowResult: ...


class ReconciliationPort(Protocol):
    async def reconcile(self): ...


async def run_scheduled_monitoring(service: RunServicePort) -> None:
    for product in PRODUCTS:
        result = await service.submit(
            RunCommand(product=product, trigger=RunTrigger.SCHEDULE)
        )
        logger.info(
            "scheduled tariff run submitted",
            extra={
                "product": product.value,
                "run_id": str(result.run.id),
                "created": result.created,
            },
        )


class MonitoringWorker:
    def __init__(
        self,
        *,
        runs: RunRepository,
        workflow: MonitoringWorkflowPort,
        reconciliation: ReconciliationPort | None = None,
        worker_id: str,
        abandoned_after: timedelta = timedelta(minutes=30),
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self._runs = runs
        self._workflow = workflow
        self._reconciliation = reconciliation
        self._worker_id = worker_id
        self._abandoned_after = abandoned_after
        self._poll_interval_seconds = poll_interval_seconds

    async def recover_abandoned(self) -> int:
        recovered = await self._runs.recover_abandoned(
            before=datetime.now(UTC) - self._abandoned_after
        )
        if recovered:
            logger.warning("marked %s abandoned run(s) failed", recovered)
        return recovered

    async def process_next(self) -> bool:
        claimed = await self._runs.claim_next(self._worker_id)
        if claimed is None:
            return False
        logger.info(
            "monitoring run started run_id=%s product=%s offering_id=%s",
            claimed.run.id,
            claimed.run.command.product.value,
            claimed.run.command.offering_id,
        )
        try:
            # Continue the trace started where the run was submitted, so the
            # HTTP request, scheduler tick, or CLI turn and this execution read
            # as one trace instead of two unrelated ones.
            with tracer.start_as_current_span(
                "execute_run",
                context=extract_trace_context(claimed.trace_parent),
            ) as span:
                span.set_attribute("tariff.run_id", str(claimed.run.id))
                span.set_attribute(
                    "tariff.product", claimed.run.command.product.value
                )
                span.set_attribute("tariff.worker_id", self._worker_id)
                result = await self._workflow.start(claimed.run)
                span.set_attribute("tariff.run_status", result.status.value)
            logger.info(
                "monitoring run completed run_id=%s status=%s review_count=%s",
                claimed.run.id,
                result.status.value,
                len(result.review_ids),
            )
        except Exception as exc:
            logger.exception(
                "monitoring run failed unexpectedly run_id=%s", claimed.run.id
            )
            await self._runs.finish(
                claimed.run.id,
                RunStatus.FAILED,
                failure_code=RunFailureCode.INTERNAL_ERROR.value,
                failure_detail=type(exc).__name__,
            )
        return True

    async def run_forever(self, stop: asyncio.Event) -> None:
        if self._reconciliation is not None:
            report = await self._reconciliation.reconcile()
            if report.items:
                logger.warning(
                    "reconciled %s monitoring workflow linkage issue(s)",
                    len(report.items),
                )
        await self.recover_abandoned()
        while not stop.is_set():
            if await self.process_next():
                continue
            try:
                await asyncio.wait_for(
                    stop.wait(),
                    timeout=self._poll_interval_seconds,
                )
            except TimeoutError:
                pass


async def main() -> None:
    settings = get_settings()
    configure_application_logging(settings.observability)
    configure_telemetry(settings.observability, component="worker")
    container = build_application_container(settings)
    await adk_services.ensure_session_service_ready()
    worker = MonitoringWorker(
        runs=container.runs,
        workflow=container.monitoring_workflow_runner,
        reconciliation=container.workflow_reconciliation,
        worker_id=f"{socket.gethostname()}:{id(container)}",
    )
    scheduler = AsyncIOScheduler(timezone=settings.scheduler.timezone)
    scheduler.add_job(
        run_scheduled_monitoring,
        trigger="cron",
        hour=settings.scheduler.hour,
        minute=settings.scheduler.minute,
        id="daily-ameria-tariff-monitoring",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
        args=(container.run_service,),
    )
    scheduler.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    try:
        await worker.run_forever(stop)
    finally:
        scheduler.shutdown(wait=False)
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
