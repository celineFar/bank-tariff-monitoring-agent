from __future__ import annotations

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import format_trace_id

from app.config.models import ObservabilitySettings, TraceContentMode
from app.services.telemetry import (
    MAX_CONTENT_CHARS,
    TariffSpanExporter,
    configure_telemetry,
    extract_trace_context,
    inject_trace_context,
)


def _recorder(content_mode: TraceContentMode):
    """Give a private tracer that exports through the rewriting exporter.

    The provider stays local so no test installs a global one; the OTel API
    permits only the first global provider, which would leak across tests.
    """
    sink = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(
        SimpleSpanProcessor(TariffSpanExporter(sink, content_mode=content_mode))
    )
    return provider.get_tracer("test"), sink


def _emit(tracer, attributes: dict[str, object], name: str = "call_llm") -> None:
    with tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


def test_none_mode_drops_every_content_attribute() -> None:
    tracer, sink = _recorder(TraceContentMode.NONE)
    _emit(
        tracer,
        {
            "gcp.vertex.agent.llm_request": "secret prompt",
            "gcp.vertex.agent.llm_response": "secret response",
            "gen_ai.input.messages": "secret messages",
            "gen_ai.request.model": "gemini-3.7-flash",
        },
    )
    exported = sink.get_finished_spans()[0].attributes
    assert "gcp.vertex.agent.llm_request" not in exported
    assert "gcp.vertex.agent.llm_response" not in exported
    assert "gen_ai.input.messages" not in exported
    assert "gen_ai.content.prompt" not in exported
    # Non-content telemetry must survive redaction.
    assert exported["gen_ai.request.model"] == "gemini-3.7-flash"


def test_mapped_mode_renames_adk_attributes_to_exported_names() -> None:
    tracer, sink = _recorder(TraceContentMode.MAPPED)
    _emit(
        tracer,
        {
            "gcp.vertex.agent.llm_request": "the prompt",
            "gcp.vertex.agent.llm_response": "the completion",
        },
    )
    exported = sink.get_finished_spans()[0].attributes
    assert exported["gen_ai.content.prompt"] == "the prompt"
    assert exported["gen_ai.content.completion"] == "the completion"
    # The vendor-specific originals must not be exported twice.
    assert "gcp.vertex.agent.llm_request" not in exported


def test_mapped_mode_maps_tool_arguments_and_response() -> None:
    tracer, sink = _recorder(TraceContentMode.MAPPED)
    _emit(
        tracer,
        {
            "gcp.vertex.agent.tool_call_args": '{"product": "mortgage"}',
            "gcp.vertex.agent.tool_response": '{"status": "ok"}',
        },
        name="execute_tool",
    )
    exported = sink.get_finished_spans()[0].attributes
    assert exported["gen_ai.content.prompt"] == '{"product": "mortgage"}'
    assert exported["gen_ai.content.completion"] == '{"status": "ok"}'


def test_mapped_mode_bounds_transcribed_document_text() -> None:
    tracer, sink = _recorder(TraceContentMode.MAPPED)
    # Armenian, because that is what the transcribed source documents contain.
    armenian = "ա" * (MAX_CONTENT_CHARS * 3)  # noqa: RUF001
    _emit(tracer, {"gcp.vertex.agent.llm_response": armenian})
    exported = sink.get_finished_spans()[0].attributes["gen_ai.content.completion"]
    assert len(exported) < MAX_CONTENT_CHARS * 2
    assert exported.endswith("[truncated]")


def test_spans_without_content_are_passed_through_unchanged() -> None:
    tracer, sink = _recorder(TraceContentMode.MAPPED)
    _emit(tracer, {"tariff.stage": "acquisition"}, name="stage acquisition")
    span = sink.get_finished_spans()[0]
    assert span.name == "stage acquisition"
    assert span.attributes["tariff.stage"] == "acquisition"


def test_rewriting_preserves_span_identity_and_parentage() -> None:
    tracer, sink = _recorder(TraceContentMode.NONE)
    with tracer.start_as_current_span("parent") as parent:
        expected_trace_id = parent.get_span_context().trace_id
        _emit(tracer, {"gcp.vertex.agent.llm_request": "dropped"})
    child = next(s for s in sink.get_finished_spans() if s.name == "call_llm")
    assert child.get_span_context().trace_id == expected_trace_id
    assert child.parent is not None


def test_trace_context_round_trips_through_storage() -> None:
    """A traceparent stored in PostgreSQL must rebuild the same trace."""
    tracer, _ = _recorder(TraceContentMode.NONE)
    with tracer.start_as_current_span("submit") as span:
        traceparent = inject_trace_context()
        origin = format_trace_id(span.get_span_context().trace_id)
    assert traceparent is not None
    restored = extract_trace_context(traceparent)
    assert restored is not None
    from opentelemetry.trace import get_current_span

    assert format_trace_id(get_current_span(restored).get_span_context().trace_id) == (
        origin
    )


def test_extract_tolerates_missing_or_empty_context() -> None:
    assert extract_trace_context(None) is None
    assert extract_trace_context("") is None


def test_disabled_telemetry_installs_nothing() -> None:
    assert configure_telemetry(ObservabilitySettings(), component="worker") is False


def test_setup_refuses_when_adk_would_add_a_second_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The standard OTLP variables make ADK export the same spans unredacted."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    settings = ObservabilitySettings(
        otel_enabled=True, otel_traces_endpoint="http://langfuse:3000/v1/traces"
    )
    assert configure_telemetry(settings, component="worker") is False


def test_endpoint_must_be_an_absolute_url() -> None:
    with pytest.raises(ValueError):
        ObservabilitySettings(otel_traces_endpoint="langfuse:3000")
