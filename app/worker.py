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
        abandoned_after: timedelta = timedelta(minutes=30),
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
        self._poll_interval_seconds = poll_interval_seconds
        self._embeddings = embeddings
        self._embedding_sweep_batch = embedding_sweep_batch
        self._embedding_sweep_interval_seconds = embedding_sweep_interval_seconds

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
                span.set_attribute("tariff.product", claimed.run.command.product.value)
                span.set_attribute("tariff.worker_id", self._worker_id)
                result = await self._pipeline.execute(
                    claimed.run, progress=LogProgressSink(logger)
                )
                span.set_attribute("tariff.run_status", result.status.value)
            logger.info(
                "monitoring run completed run_id=%s status=%s review_count=%s",
                claimed.run.id,
                result.status.value,
                len(result.summary.get("review_ids", []) or []),
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

    async def run_forever(self, stop: asyncio.Event) -> None:
        await self.startup_checks()
        sweep = asyncio.create_task(self._sweep_forever(stop))
        try:
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
        finally:
            sweep.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sweep


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
