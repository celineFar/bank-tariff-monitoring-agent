"""One OpenTelemetry trace per monitoring run, across every process it touches.

A run is triggered in one process and executed in another: HTTP, the scheduler,
and the CLI all `submit()` a row that the worker later claims, and a run paused
for human review resumes inside whichever process served the decision. Ambient
OTel context does not survive those handoffs, so the trace context travels the
same road as the run state -- persisted in PostgreSQL by `inject_trace_context`
and restored by `extract_trace_context`. Every segment then shares one trace ID,
and a backend that groups observations by trace ID shows them as one trace.

Exported content is decided here and nowhere else. ADK writes prompts and model
responses into vendor-specific span attributes and captures them by default, so
`TariffSpanExporter` rewrites every span before it leaves the process: dropping
content entirely under `TraceContentMode.NONE`, or bounding it and renaming it
to the attributes a trace backend reads under `MAPPED`. Because that rewrite has
to happen before the batch processor serializes anything, it lives in a wrapping
exporter rather than a second span processor -- a sibling processor receives the
same read-only span and cannot change what the exporter already queued.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from typing import Final

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.config.models import ObservabilitySettings, TraceContentMode

logger = logging.getLogger(__name__)

TRACER_NAME: Final = "app.tariff"
TRACEPARENT_HEADER: Final = "traceparent"

# ADK reads both of these once per invocation, from the environment.
# `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` defaults to ON, so leaving it unset
# would export full prompts and model responses.
_ADK_CAPTURE_IN_SPANS: Final = "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"
_GENAI_CAPTURE_CONTENT: Final = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"

# ADK's own attributes. `_experimental_semconv` may add the `gen_ai.*` message
# attributes alongside them; both are treated as content.
_ADK_PROMPT: Final = "gcp.vertex.agent.llm_request"
_ADK_COMPLETION: Final = "gcp.vertex.agent.llm_response"
_ADK_TOOL_ARGS: Final = "gcp.vertex.agent.tool_call_args"
_ADK_TOOL_RESPONSE: Final = "gcp.vertex.agent.tool_response"

# What a trace backend reads for its input/output panes. Langfuse maps these two
# names; if a backend expects its own instead, change them here only.
_EXPORT_INPUT: Final = "gen_ai.content.prompt"
_EXPORT_OUTPUT: Final = "gen_ai.content.completion"

_INPUT_SOURCES: Final = (_ADK_PROMPT, _ADK_TOOL_ARGS)
_OUTPUT_SOURCES: Final = (_ADK_COMPLETION, _ADK_TOOL_RESPONSE)

# Every attribute that can carry model or document content.
_CONTENT_ATTRIBUTES: Final = frozenset(
    {
        _ADK_PROMPT,
        _ADK_COMPLETION,
        _ADK_TOOL_ARGS,
        _ADK_TOOL_RESPONSE,
        "gen_ai.input.messages",
        "gen_ai.output.messages",
        "gen_ai.system_instructions",
        "gen_ai.prompt",
        "gen_ai.completion",
        _EXPORT_INPUT,
        _EXPORT_OUTPUT,
    }
)

# A transcribed PDF page is large enough to make a span useless and to push
# source text into a backend wholesale. Bound it.
MAX_CONTENT_CHARS: Final = 8_000
_TRUNCATION_MARKER: Final = "…[truncated]"


def _bounded(value: object) -> str:
    text = value if isinstance(value, str) else str(value)
    if len(text) <= MAX_CONTENT_CHARS:
        return text
    return text[:MAX_CONTENT_CHARS] + _TRUNCATION_MARKER


class TariffSpanExporter(SpanExporter):
    """Rewrite every span's content attributes, then delegate the export.

    This is the only place that decides what model content leaves the process,
    which keeps the policy auditable in one file instead of spread across the
    call sites that happen to produce spans.
    """

    def __init__(
        self, delegate: SpanExporter, *, content_mode: TraceContentMode
    ) -> None:
        self._delegate = delegate
        self._content_mode = content_mode

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self._delegate.export(tuple(self._rewrite(span) for span in spans))

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return self._delegate.force_flush(timeout_millis)

    def _rewrite(self, span: ReadableSpan) -> ReadableSpan:
        attributes = dict(span.attributes or {})
        if not _CONTENT_ATTRIBUTES.intersection(attributes):
            return span
        rewritten = {
            key: value
            for key, value in attributes.items()
            if key not in _CONTENT_ATTRIBUTES
        }
        if self._content_mode is TraceContentMode.MAPPED:
            for source in _INPUT_SOURCES:
                if attributes.get(source):
                    rewritten[_EXPORT_INPUT] = _bounded(attributes[source])
                    break
            for source in _OUTPUT_SOURCES:
                if attributes.get(source):
                    rewritten[_EXPORT_OUTPUT] = _bounded(attributes[source])
                    break
        return ReadableSpan(
            name=span.name,
            context=span.get_span_context(),
            parent=span.parent,
            resource=span.resource,
            attributes=rewritten,
            events=span.events,
            links=span.links,
            kind=span.kind,
            status=span.status,
            start_time=span.start_time,
            end_time=span.end_time,
            instrumentation_scope=span.instrumentation_scope,
        )


def _build_exporter(settings: ObservabilitySettings) -> SpanExporter:
    """Export over OTLP when an endpoint is configured, else to the console.

    The console fallback keeps the instrumentation verifiable without standing
    up a trace backend.
    """
    if settings.otel_traces_endpoint is None:
        return ConsoleSpanExporter()
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    return OTLPSpanExporter(
        endpoint=settings.otel_traces_endpoint,
        timeout=int(settings.otel_export_timeout_seconds),
    )


def configure_telemetry(
    settings: ObservabilitySettings, *, component: str
) -> bool:
    """Install the tracer provider for one process. Safe to call once per entry point.

    Returns whether tracing was installed, so a caller can log the decision.
    `component` distinguishes the API, worker, and CLI within one service name.
    """
    if not settings.otel_enabled:
        return False

    # Must be set before ADK builds its first per-invocation TelemetryConfig.
    if settings.otel_trace_content is TraceContentMode.NONE:
        os.environ[_ADK_CAPTURE_IN_SPANS] = "false"
        os.environ.setdefault(_GENAI_CAPTURE_CONTENT, "NO_CONTENT")

    # ADK adds its own unredacted OTLP exporter when these are set, which would
    # defeat the rewrite above by exporting the same spans a second time.
    conflicting = [
        name
        for name in (
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        )
        if os.getenv(name)
    ]
    if conflicting:
        logger.warning(
            "ignoring telemetry setup: %s would add an unredacted exporter; "
            "configure OTEL_TRACES_ENDPOINT instead",
            ", ".join(conflicting),
        )
        return False

    processor = BatchSpanProcessor(
        TariffSpanExporter(
            _build_exporter(settings),
            content_mode=settings.otel_trace_content,
        )
    )
    installed = trace.get_tracer_provider()
    if isinstance(installed, TracerProvider):
        # The API process reaches here after `get_fast_api_app` has already
        # installed a provider carrying ADK's in-memory exporters, which back
        # the web UI's trace view. Setting a second provider would be ignored
        # with a warning, so extend the existing one instead and keep both.
        installed.add_span_processor(processor)
    else:
        from google.adk.telemetry.setup import OTelHooks, maybe_set_otel_providers

        maybe_set_otel_providers(
            otel_hooks_to_setup=[OTelHooks(span_processors=[processor])],
            otel_resource=Resource.create(
                {
                    "service.name": settings.otel_service_name,
                    "service.namespace": "tariff-monitor",
                    "deployment.component": component,
                }
            ),
        )
    logger.info(
        "tracing enabled component=%s endpoint=%s content=%s",
        component,
        settings.otel_traces_endpoint or "console",
        settings.otel_trace_content.value,
    )
    return True


def get_tracer() -> trace.Tracer:
    """Return the application tracer; a no-op when no provider is installed."""
    return trace.get_tracer(TRACER_NAME)


def inject_trace_context() -> str | None:
    """Serialize the active span context for storage alongside a run or review.

    Returns None when nothing is recording, so a disabled telemetry setup writes
    no column value rather than a placeholder.
    """
    carrier: dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)
    return carrier.get(TRACEPARENT_HEADER)


def extract_trace_context(traceparent: str | None) -> Context | None:
    """Rebuild a stored span context so later spans join the original trace."""
    if not traceparent:
        return None
    return TraceContextTextMapPropagator().extract(
        {TRACEPARENT_HEADER: traceparent}
    )


def current_trace_id() -> str | None:
    """Return the active trace ID, for correlating log lines with the trace."""
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None
    return trace.format_trace_id(context.trace_id)


def set_attributes(attributes: Mapping[str, object]) -> None:
    """Stamp identifiers onto the active span, skipping absent values."""
    span = trace.get_current_span()
    if not span.is_recording():
        return
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value if isinstance(value, bool) else str(value))
