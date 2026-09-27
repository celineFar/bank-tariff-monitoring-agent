from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import socket
from datetime import UTC, datetime, timedelta
from typing import Protocol

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.domain.models import ProductType
from app.domain.monitoring import (
    RunCommand,
    RunFailureCode,
    RunStatus,
    RunTrigger,
)
from app.repositories.contracts import RunRepository
from app.runtime import build_application_container
from app.services.contracts import TariffPipeline
from app.services.logging_setup import configure_application_logging
from app.services.monitoring_progress import LogProgressSink
from app.services.run_lease import RunStopped, execute_with_lease, stop_run
from app.services.run_service import RunServicePort
from app.services.telemetry import (
    configure_telemetry,
    extract_trace_context,
    get_tracer,
)

logger = logging.getLogger(__name__)
tracer = get_tracer()
PRODUCTS = (ProductType.CONSUMER_LOAN, ProductType.MORTGAGE)


class ReviewCompletionPort(Protocol):
    async def complete_runs_without_pending_reviews(
        self, *, limit: int = 100
    ) -> int: ...


class EmbeddingSweepPort(Protocol):
    async def embed_missing(self, *, limit: int = 200) -> int: ...


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
    """Queue consumer for unattended runs (scheduler and API).

    Executes the same `TariffPipeline` the chat node does, with progress going
    to the log. It owns no ADK app or session: a run that pauses for review is
    reviewed later from the CLI (`review_pending_candidates`).
    """

    def __init__(
        self,
        *,
        runs: RunRepository,
        pipeline: TariffPipeline,
        resolution: ReviewCompletionPort | None = None,
        worker_id: str,
        # A run whose heartbeat is older than this is closed as abandoned.
        abandoned_after: timedelta = timedelta(seconds=120),
        heartbeat_seconds: float = 5.0,
        recovery_interval_seconds: float = 60.0,
        poll_interval_seconds: float = 2.0,
        embeddings: EmbeddingSweepPort | None = None,
        embedding_sweep_batch: int = 200,
        embedding_sweep_interval_seconds: float = 300.0,
    ) -> None:
        self._runs = runs
        self._pipeline = pipeline
        self._resolution = resolution
        self._worker_id = worker_id
        self._abandoned_after = abandoned_after
        self._heartbeat_seconds = heartbeat_seconds
        self._recovery_interval_seconds = recovery_interval_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._embeddings = embeddings
        self._embedding_sweep_batch = embedding_sweep_batch
        self._embedding_sweep_interval_seconds = embedding_sweep_interval_seconds

    async def recover_abandoned(self) -> int:
        try:
            recovered = await self._runs.recover_abandoned(
                before=datetime.now(UTC) - self._abandoned_after
            )
        except Exception:
            logger.warning("abandoned run recovery failed", exc_info=True)
            return 0
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
                span.set_attribute("tariff.product", claimed.run.command.product.value)
                span.set_attribute("tariff.worker_id", self._worker_id)
                # Under the lease: a chat following this run can ask it to
                # stop, and the heartbeat keeps it from being recovered.
                result = await execute_with_lease(
                    self._runs,
                    claimed.run.id,
                    self._worker_id,
                    lambda: self._pipeline.execute(
                        claimed.run, progress=LogProgressSink(logger)
                    ),
                    heartbeat_seconds=self._heartbeat_seconds,
                )
                span.set_attribute("tariff.run_status", result.status.value)
            logger.info(
                "monitoring run completed run_id=%s status=%s review_count=%s",
                claimed.run.id,
                result.status.value,
                len(result.summary.get("review_ids", []) or []),
            )
        except RunStopped as stopped:
            logger.info("monitoring run stopped on request: %s", stopped)
        except asyncio.CancelledError:
            # The worker is shutting down. The pipeline closes the run it was
            # executing; this also closes one cancelled before it started.
            await stop_run(
                self._runs,
                claimed.run.id,
                requested_by=self._worker_id,
                lease_seconds=self._abandoned_after.total_seconds(),
            )
            raise
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

    async def startup_checks(self) -> None:
        """Close what a previous process left open; nothing needs correlating."""
        await self.recover_abandoned()
        if self._resolution is not None:
            completed = await self._resolution.complete_runs_without_pending_reviews()
            if completed:
                logger.warning(
                    "completed %s reviewed run(s) left awaiting review", completed
                )

    async def sweep_embeddings(self) -> int:
        """Embed active chunks stored text-only; never raises (IX7).

        An approval activates its documents before their vectors exist, and a
        quota refusal publishes a run as text; lexical search serves both until
        this fills the vectors.
        """
        if self._embeddings is None or self._embedding_sweep_batch <= 0:
            return 0
        try:
            filled = await self._embeddings.embed_missing(
                limit=self._embedding_sweep_batch
            )
        except Exception:
            logger.warning("embedding sweep failed", exc_info=True)
            return 0
        if filled:
            logger.info("embedding sweep filled %s chunk vector(s)", filled)
        return filled

    async def _sweep_forever(self, stop: asyncio.Event) -> None:
        # Its own loop: a quota refusal can keep the provider retrying for
        # minutes, and that must never hold up claiming runs.
        while not stop.is_set():
            await self.sweep_embeddings()
            try:
                await asyncio.wait_for(
                    stop.wait(), timeout=self._embedding_sweep_interval_seconds
                )
            except TimeoutError:
                pass

    async def _recover_forever(self, stop: asyncio.Event) -> None:
        # Not only at startup: a process killed mid-run must not block its
        # offering until the next worker restart.
        while not stop.is_set():
            try:
                await asyncio.wait_for(
                    stop.wait(), timeout=self._recovery_interval_seconds
                )
            except TimeoutError:
                await self.recover_abandoned()

    async def run_forever(self, stop: asyncio.Event) -> None:
        await self.startup_checks()
        background = (
            asyncio.create_task(self._sweep_forever(stop)),
            asyncio.create_task(self._recover_forever(stop)),
        )
        try:
            while not stop.is_set():
                if await self._until_stopped(self.process_next(), stop):
                    continue
                try:
                    await asyncio.wait_for(
                        stop.wait(),
                        timeout=self._poll_interval_seconds,
                    )
                except TimeoutError:
                    pass
        finally:
            for task in background:
                task.cancel()
            for task in background:
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    @staticmethod
    async def _until_stopped(work, stop: asyncio.Event) -> bool:
        """Run one unit of work; on a stop signal cancel it and wait for cleanup.

        Without this a SIGTERM waited for the whole run, model calls included
        and `docker stop` then killed the worker mid-run.
        """
        task = asyncio.ensure_future(work)
        stopping = asyncio.ensure_future(stop.wait())
        try:
            await asyncio.wait({task, stopping}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            stopping.cancel()
        if not task.done():
            logger.info("stop requested; cancelling the run in progress")
            task.cancel()
            await asyncio.wait({task})
            return False
        return task.result()


async def main() -> None:
    settings = get_settings()
    configure_application_logging(settings.observability)
    configure_telemetry(settings.observability, component="worker")
    container = build_application_container(settings)
    worker = MonitoringWorker(
        runs=container.runs,
        pipeline=container.tariff_pipeline,
        resolution=container.review_resolution,
        worker_id=f"{socket.gethostname()}:{id(container)}",
        embeddings=container.knowledge_indexer,
        embedding_sweep_batch=settings.rag.embedding_sweep_batch,
        embedding_sweep_interval_seconds=settings.rag.embedding_sweep_interval_seconds,
        abandoned_after=timedelta(seconds=settings.scheduler.run_lease_seconds),
        heartbeat_seconds=settings.scheduler.run_heartbeat_seconds,
        recovery_interval_seconds=settings.scheduler.run_recovery_interval_seconds,
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
