import asyncio
import logging
from uuid import uuid4

import pytest

from app.domain.models import OfferingId, ProductType
from app.services.monitoring_progress import (
    LogProgressSink,
    PipelineProgress,
    ProgressKind,
    progress_label,
    report_safely,
    stage_label,
    stream_progress,
)

RUN_ID = uuid4()


def _item(kind: ProgressKind, stage: str | None = None) -> PipelineProgress:
    return PipelineProgress(
        kind=kind,
        run_id=RUN_ID,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        stage=stage,
    )


@pytest.mark.asyncio
async def test_stream_yields_progress_in_order_and_exposes_the_result() -> None:
    async def work(sink):
        await sink.report(_item(ProgressKind.STAGE_STARTED, "acquisition"))
        await asyncio.sleep(0)
        await sink.report(_item(ProgressKind.STAGE_COMPLETED, "acquisition"))
        return "done"

    stream = stream_progress(work)
    seen = [(item.kind, item.stage) async for item in stream]

    assert seen == [
        (ProgressKind.STAGE_STARTED, "acquisition"),
        (ProgressKind.STAGE_COMPLETED, "acquisition"),
    ]
    assert stream.result == "done"


@pytest.mark.asyncio
async def test_stream_surfaces_the_task_exception_after_draining() -> None:
    async def work(sink):
        await sink.report(_item(ProgressKind.STAGE_STARTED, "acquisition"))
        raise RuntimeError("boom")

    seen = []
    with pytest.raises(RuntimeError, match="boom"):
        async for item in stream_progress(work):
            seen.append(item.kind)

    assert seen == [ProgressKind.STAGE_STARTED]


@pytest.mark.asyncio
async def test_consumer_cancellation_cancels_the_task_and_waits_for_its_cleanup() -> (
    None
):
    started = asyncio.Event()
    cleaned_up = asyncio.Event()

    async def work(sink):
        await sink.report(_item(ProgressKind.STAGE_STARTED, "acquisition"))
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await asyncio.sleep(0)  # cleanup that itself awaits
            cleaned_up.set()
            raise

    async def consume():
        async for _ in stream_progress(work):
            pass

    consumer = asyncio.create_task(consume())
    await started.wait()
    consumer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumer

    assert cleaned_up.is_set()


@pytest.mark.asyncio
async def test_stopping_iteration_early_cancels_the_task() -> None:
    cancelled = asyncio.Event()

    async def work(sink):
        await sink.report(_item(ProgressKind.STAGE_STARTED, "acquisition"))
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    iterator = aiter(stream_progress(work))
    await anext(iterator)
    await iterator.aclose()

    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_result_is_unavailable_before_the_stream_finishes() -> None:
    async def work(sink):
        return 1

    with pytest.raises(RuntimeError):
        _ = stream_progress(work).result


@pytest.mark.asyncio
async def test_a_failing_sink_never_fails_the_reporter() -> None:
    class Broken:
        async def report(self, progress):
            raise OSError("listener gone")

    await report_safely(Broken(), _item(ProgressKind.RUN_STARTED))
    await report_safely(None, _item(ProgressKind.RUN_STARTED))


@pytest.mark.asyncio
async def test_log_sink_writes_one_line_per_item(caplog) -> None:
    log = logging.getLogger("test.progress")
    with caplog.at_level(logging.INFO, logger="test.progress"):
        await LogProgressSink(log).report(
            _item(ProgressKind.STAGE_COMPLETED, "embedding")
        )

    assert len(caplog.records) == 1
    assert "stage=embedding" in caplog.records[0].getMessage()
    assert "consumer_standard" in caplog.records[0].getMessage()


def test_labels_are_human_readable() -> None:
    assert stage_label("source_discovery") == "Finding tariff evidence"
    assert stage_label("some_new_stage") == "Some new stage"
    assert progress_label(_item(ProgressKind.STAGE_STARTED, "acquisition")) == (
        "Acquiring web content…"
    )
