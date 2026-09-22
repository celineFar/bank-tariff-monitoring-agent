"""A run must read as one trace even though it crosses processes.

Triggering and executing a run never share a process: HTTP, the scheduler, and
the CLI write a queued row that a worker later claims, and a run paused for
review resumes wherever the decision was served. These tests pin the contract
that makes the segments join -- a traceparent stored with the row and restored
by whoever picks it up.
"""

from __future__ import annotations

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import format_trace_id

from app.services.telemetry import extract_trace_context, inject_trace_context


@pytest.fixture
def tracing() -> tuple[object, InMemorySpanExporter]:
    sink = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(sink))
    return provider.get_tracer("test"), sink


def test_worker_execution_joins_the_trace_that_submitted_the_run(tracing) -> None:
    tracer, sink = tracing

    # Triggering process: a row is written carrying the active context.
    with tracer.start_as_current_span("POST /api/v1/runs"):
        stored = inject_trace_context()

    # Worker process: the claim restores it before executing.
    with tracer.start_as_current_span(
        "execute_run", context=extract_trace_context(stored)
    ):
        pass

    submit, execute = sink.get_finished_spans()
    assert execute.name == "execute_run"
    assert execute.get_span_context().trace_id == submit.get_span_context().trace_id
    assert execute.parent.span_id == submit.get_span_context().span_id


def test_review_resume_joins_the_trace_that_paused(tracing) -> None:
    tracer, sink = tracing

    with tracer.start_as_current_span("execute_run") as run_span:
        expected = run_span.get_span_context().trace_id
        with tracer.start_as_current_span("request_human_input"):
            paused = inject_trace_context()

    with tracer.start_as_current_span(
        "resume_run", context=extract_trace_context(paused)
    ) as resumed:
        assert resumed.get_span_context().trace_id == expected

    names = {span.name for span in sink.get_finished_spans()}
    assert {"execute_run", "request_human_input", "resume_run"} <= names
    trace_ids = {span.get_span_context().trace_id for span in sink.get_finished_spans()}
    assert len(trace_ids) == 1, "a paused and resumed run must stay one trace"


def test_absent_context_starts_a_fresh_trace_instead_of_failing(tracing) -> None:
    """Rows written while tracing was off must not break a later claim."""
    tracer, sink = tracing

    with tracer.start_as_current_span(
        "execute_run", context=extract_trace_context(None)
    ):
        pass

    span = sink.get_finished_spans()[0]
    assert span.parent is None
    assert span.get_span_context().is_valid


def test_inject_returns_nothing_when_no_span_is_recording() -> None:
    """A disabled setup writes NULL rather than a meaningless traceparent."""
    assert inject_trace_context() is None


def test_stored_context_fits_the_column(tracing) -> None:
    """migrations/014 sizes the column at the fixed W3C traceparent length."""
    tracer, _ = tracing
    with tracer.start_as_current_span("submit"):
        stored = inject_trace_context()
    assert stored is not None
    assert len(stored) == 55
    version, trace_id, parent_id, flags = stored.split("-")
    assert (len(version), len(trace_id), len(parent_id), len(flags)) == (2, 32, 16, 2)


def test_restored_trace_id_matches_the_originating_trace(tracing) -> None:
    """The id used to correlate logs and SQL must survive the handoff."""
    tracer, _ = tracing
    with tracer.start_as_current_span("submit") as span:
        origin = format_trace_id(span.get_span_context().trace_id)
        stored = inject_trace_context()

    with tracer.start_as_current_span(
        "execute_run", context=extract_trace_context(stored)
    ) as resumed:
        assert format_trace_id(resumed.get_span_context().trace_id) == origin
