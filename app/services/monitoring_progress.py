"""Progress port for the monitoring pipeline.

The pipeline already knows when each stage starts and ends; this module lets it
say so without depending on who is listening. The worker logs progress, the ADK
monitoring node streams it to the caller as partial events, and everything else
ignores it.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Generic, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import OfferingId, ProductType

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ProgressKind(StrEnum):
    RUN_STARTED = "run_started"
    OFFERING_STARTED = "offering_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    OFFERING_SUCCEEDED = "offering_succeeded"
    OFFERING_REVIEW = "offering_review"
    OFFERING_FAILED = "offering_failed"
    RUN_FINISHED = "run_finished"
    FOLLOWING = "following"  # the run is owned by another process


class PipelineProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ProgressKind
    run_id: UUID
    product: ProductType
    offering_id: OfferingId | None = None
    stage: str | None = Field(default=None, max_length=100)
    elapsed_ms: int = Field(default=0, ge=0)
    detail: str | None = Field(default=None, max_length=500)
    failure_code: str | None = Field(default=None, max_length=100)
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProgressSink(Protocol):
    async def report(self, progress: PipelineProgress) -> None: ...


class NullProgressSink:
    async def report(self, progress: PipelineProgress) -> None:
        return None


class LogProgressSink:
    """One INFO line per item, for the worker's unattended runs."""

    def __init__(self, log: logging.Logger | None = None) -> None:
        self._log = log or logger

    async def report(self, progress: PipelineProgress) -> None:
        self._log.info(
            "progress run_id=%s kind=%s offering_id=%s stage=%s elapsed_ms=%s"
            " failure_code=%s detail=%s",
            progress.run_id,
            progress.kind.value,
            progress.offering_id.value if progress.offering_id else None,
            progress.stage,
            progress.elapsed_ms,
            progress.failure_code,
            progress.detail,
        )


class QueueProgressSink:
    """Hands progress to the consumer of `stream_progress`."""

    def __init__(self, queue: asyncio.Queue[PipelineProgress | object]) -> None:
        self._queue = queue

    async def report(self, progress: PipelineProgress) -> None:
        await self._queue.put(progress)


async def report_safely(sink: ProgressSink | None, progress: PipelineProgress) -> None:
    """Progress is best effort: a failing listener must never fail a run."""
    if sink is None:
        return
    try:
        await sink.report(progress)
    except Exception:  # pragma: no cover - defensive, exercised by the unit test
        logger.warning("progress sink failed kind=%s", progress.kind, exc_info=True)


_DONE = object()


class ProgressStream(Generic[T]):
    """Run a coroutine as a task and iterate the progress it reports.

    Iteration ends when the coroutine finishes; its return value is then on
    `result`, and its exception (if any) is raised from the iterator. If the
    consumer is cancelled or stops iterating, the task is cancelled and awaited
    so that its own cancellation handling (marking the run cancelled) completes
    before the cancellation propagates.
    """

    def __init__(self, factory: Callable[[ProgressSink], Awaitable[T]]) -> None:
        self._factory = factory
        self._result: T | None = None
        self._finished = False

    @property
    def result(self) -> T:
        if not self._finished:
            raise RuntimeError("progress stream has not finished")
        return self._result  # type: ignore[return-value]

    def __aiter__(self) -> AsyncIterator[PipelineProgress]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[PipelineProgress]:
        queue: asyncio.Queue[PipelineProgress | object] = asyncio.Queue()
        sink = QueueProgressSink(queue)

        async def run() -> T:
            try:
                return await self._factory(sink)
            finally:
                queue.put_nowait(_DONE)

        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is _DONE:
                    break
                yield item  # type: ignore[misc]
            self._result = await task
            self._finished = True
        except BaseException:
            if not task.done():
                task.cancel()
                # Wait for the task's own cancellation handling; asyncio.wait
                # never raises the task's exception, only our own cancellation.
                await asyncio.wait({task})
            raise


def stream_progress(
    factory: Callable[[ProgressSink], Awaitable[T]],
) -> ProgressStream[T]:
    return ProgressStream(factory)


STAGE_LABELS: dict[str, str] = {
    "starting": "Starting",
    "acquisition": "Acquiring web content",
    "normalization": "Reading source documents",
    "source_discovery": "Finding tariff evidence",
    "semantic_extraction": "Extracting tariff fields",
    "previous_snapshot": "Checking previous snapshot",
    "embedding": "Indexing evidence",
    "publication": "Saving tariffs",
    "projection": "Preparing documents",
    "review_approved": "Review approved",
    "review_rejected": "Review rejected",
    "published": "Snapshot published",
    "internal": "Recovering from an internal error",
}


def stage_label(stage: str | None) -> str:
    if not stage:
        return "Working"
    return STAGE_LABELS.get(stage, stage.replace("_", " ").capitalize())


def progress_label(progress: PipelineProgress) -> str:
    """A one-line human label; renderers should prefer the structured fields."""
    offering = progress.offering_id.value if progress.offering_id else None
    if progress.kind is ProgressKind.RUN_STARTED:
        return f"Monitoring {progress.product.value}" + (
            f" ({progress.detail})" if progress.detail else ""
        )
    if progress.kind is ProgressKind.OFFERING_STARTED:
        return f"{offering}"
    if progress.kind is ProgressKind.STAGE_STARTED:
        return f"{stage_label(progress.stage)}…"
    if progress.kind is ProgressKind.STAGE_COMPLETED:
        return f"{stage_label(progress.stage)} · {progress.elapsed_ms / 1000:.0f}s"
    if progress.kind is ProgressKind.OFFERING_SUCCEEDED:
        return f"{offering} accepted"
    if progress.kind is ProgressKind.OFFERING_REVIEW:
        return f"{offering} needs review"
    if progress.kind is ProgressKind.OFFERING_FAILED:
        return f"{offering} failed at {stage_label(progress.stage)}"
    if progress.kind is ProgressKind.RUN_FINISHED:
        return f"Monitoring finished · {progress.detail or ''}".rstrip(" ·")
    return progress.detail or "Following a run started elsewhere"
