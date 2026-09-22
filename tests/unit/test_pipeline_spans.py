"""The pipeline's own stages must appear in the trace, not just ADK's spans.

ADK instruments the agent and workflow layers. Everything between acquisition
and publication is ordinary Python, so without these spans a monitoring run
collapses into one opaque node and the trace answers nothing about the run.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.services import monitoring_pipeline
from app.services.monitoring_pipeline import OfferingPipelineError
from tests.unit.test_monitoring_pipeline import _indexing, _offering


@pytest.fixture
def spans(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    """Swap the module tracer for a private one.

    OTel permits only the first global tracer provider per process, so a global
    one would leak into every other test in the session.
    """
    sink = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(sink))
    monkeypatch.setattr(monitoring_pipeline, "tracer", provider.get_tracer("test"))
    return sink


def _names(sink: InMemorySpanExporter) -> list[str]:
    return [span.name for span in sink.get_finished_spans()]


@pytest.mark.asyncio
async def test_every_pipeline_stage_emits_its_own_span(
    spans: InMemorySpanExporter,
) -> None:
    service, _, _ = _indexing()

    await service.refresh(_offering(), uuid4(), uuid4())

    assert set(_names(spans)) >= {
        "stage acquisition",
        "stage normalization",
        "stage source_discovery",
        "stage semantic_extraction",
        "stage embedding",
        "stage publication",
    }


@pytest.mark.asyncio
async def test_stage_spans_carry_run_and_offering_identifiers(
    spans: InMemorySpanExporter,
) -> None:
    """The same identifiers key the SQL metrics, so traces and reports join."""
    service, _, _ = _indexing()
    run_id = uuid4()

    await service.refresh(_offering(), run_id, uuid4())

    acquisition = next(
        span for span in spans.get_finished_spans() if span.name == "stage acquisition"
    )
    assert acquisition.attributes["tariff.run_id"] == str(run_id)
    assert acquisition.attributes["tariff.offering_id"] == "consumer_standard"
    assert acquisition.attributes["tariff.stage"] == "acquisition"


@pytest.mark.asyncio
async def test_failing_stage_records_its_failure_code_on_the_span(
    spans: InMemorySpanExporter,
) -> None:
    service, _, _ = _indexing(fail_embedding=True)

    with pytest.raises(OfferingPipelineError):
        await service.refresh(_offering(), uuid4(), uuid4())

    embedding = next(
        span for span in spans.get_finished_spans() if span.name == "stage embedding"
    )
    assert embedding.attributes["tariff.failure_code"]
    assert embedding.status.is_ok is False


@pytest.mark.asyncio
async def test_stages_nest_under_one_parent_so_a_run_reads_as_a_tree(
    spans: InMemorySpanExporter,
) -> None:
    service, _, _ = _indexing()
    tracer = monitoring_pipeline.tracer

    with tracer.start_as_current_span("offering consumer_standard") as parent:
        expected = parent.get_span_context().span_id
        await service.refresh(_offering(), uuid4(), uuid4())

    stages = [s for s in spans.get_finished_spans() if s.name.startswith("stage ")]
    assert stages
    assert all(span.parent is not None for span in stages)
    assert {span.parent.span_id for span in stages} == {expected}
