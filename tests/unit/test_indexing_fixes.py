"""Regression tests for the indexing fix plan (fix-process/indexing/).

One test per plan item (IX*) whose target behaviour is visible without
PostgreSQL; the database-level items live in
tests/integration/test_indexing_fixes_postgres.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.config.models import RagSettings
from app.domain.acquisition import SourceLocator, SourceType
from app.domain.knowledge import KnowledgeChunk, KnowledgeDocument, document_version_id
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotStatus
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    NormalizedTable,
    NormalizedTableCell,
    NormalizedTableRow,
    SourceReference,
)
from app.domain.source_discovery import (
    Authority,
    DecisionSource,
    DiscoveryScope,
    InformationRole,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    TemporalStatus,
)
from app.services import monitoring_pipeline
from app.services.knowledge_projection import KnowledgeProjectionService
from tests.unit.test_monitoring_pipeline import _indexing, _offering

NOW = datetime(2026, 9, 26, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"


def _review_required(monkeypatch) -> None:
    original = monitoring_pipeline.build_snapshot_attempt

    def build(**kwargs):
        snapshot = original(**kwargs)
        # A candidate always carries the question a reviewer answers.
        signal = {
            "reason": "large_rate_change",
            "issue_scope": "interest_rate",
            "field": "interest_rate",
        }
        return snapshot.model_copy(
            update={
                "status": SnapshotStatus.REVIEW_REQUIRED,
                "accepted_at": None,
                "validation": {**snapshot.validation, "review_signals": [signal]},
            }
        )

    monkeypatch.setattr(monitoring_pipeline, "build_snapshot_attempt", build)


# IX2 -------------------------------------------------------------------------


def _knowledge_document(contents: tuple[str, ...]) -> KnowledgeDocument:
    return KnowledgeDocument(
        run_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        document_key="page:0123456789abcdef",
        document_name="Consumer loans",
        source_url=URL,
        final_url=URL,
        mime_type="text/html",
        content_sha256="a" * 64,
        retrieved_at=NOW,
        extraction_method="browser",
        chunks=tuple(
            KnowledgeChunk(
                ordinal=index,
                content=content,
                language="en",
                extraction_method="browser",
            )
            for index, content in enumerate(contents)
        ),
    )


def test_ix2_same_source_bytes_with_other_chunks_is_another_version() -> None:
    live = _knowledge_document(("Rate 13.5%", "Term 60 months"))
    candidate = _knowledge_document(("Rate 14.0%",))

    assert live.content_sha256 == candidate.content_sha256
    assert live.projection_sha256 != candidate.projection_sha256
    assert document_version_id(live) != document_version_id(candidate)


# IX5 -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ix5_review_required_run_publishes_its_documents_as_text(
    monkeypatch,
) -> None:
    _review_required(monkeypatch)
    service, _, publications = _indexing()

    await service.refresh(_offering(), uuid4(), uuid4())

    published = publications.values[-1]
    assert published.snapshot.status is SnapshotStatus.REVIEW_REQUIRED
    assert published.documents


# IX7 -------------------------------------------------------------------------


# IX10 / IX13 -----------------------------------------------------------------


def _ref(item_id: str) -> SourceReference:
    return SourceReference(
        source_item_id=item_id,
        locator=SourceLocator(
            source_url=URL, source_type=SourceType.PAGE, block_id=item_id
        ),
    )


def _big_table_bundle() -> NormalizedSourceBundle:
    rows = tuple(
        NormalizedTableRow(
            id=f"fees.r{index}",
            cells=(
                NormalizedTableCell(
                    raw_text=f"Fee {index}",
                    text=f"Fee {index} " + "x" * 80,
                    source_refs=(_ref(f"fees.r{index}.c0"),),
                ),
                NormalizedTableCell(
                    raw_text=f"{index} AMD",
                    text=f"{index} AMD",
                    source_refs=(_ref(f"fees.r{index}.c1"),),
                ),
            ),
        )
        for index in range(40)
    )
    table = NormalizedTable(
        id="fees",
        title="Service fees",
        headers=("Fee", "Amount"),
        rows=rows,
        source_refs=(_ref("fees"),),
    )
    document = NormalizedDocument(
        id="page:0123456789abcdef",
        name="Consumer loans",
        source_url=URL,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256="a" * 64,
        extraction_method="browser",
        tables=(table,),
    )
    return NormalizedSourceBundle(
        canonical_url=URL,
        acquisition_content_hash="b" * 64,
        documents=(document,),
    )


def _label() -> SourceAssessment:
    return SourceAssessment(
        source_id="fees",
        document_id="page:0123456789abcdef",
        scope=DiscoveryScope.TABLE,
        product_association=ProductAssociation.CURRENT_PRODUCT,
        role=InformationRole.FEES,
        relevance=Relevance.RELEVANT,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        reason="test",
        decision_source=DecisionSource.RULE,
        input_fingerprint="c" * 64,
        structural_fingerprint="d" * 64,
        source_refs=(_ref("fees"),),
    )


def _project_big_table(labels=None):
    (document,) = KnowledgeProjectionService(max_chunk_chars=600).project_sources(
        run_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        bundle=_big_table_bundle(),
        retrieved_at=NOW,
        language="en",
        labels=labels,
    )
    return document


def test_ix10_every_piece_of_a_split_table_starts_with_title_and_header() -> None:
    document = _project_big_table()

    assert len(document.chunks) > 1
    for chunk in document.chunks:
        lines = chunk.content.splitlines()
        assert lines[:3] == ["### Service fees", "| Fee | Amount |", "| --- | --- |"]
        assert len(chunk.content) <= 600


def test_ix13_pieces_of_an_oversized_labelled_unit_keep_the_label() -> None:
    document = _project_big_table(labels={"fees": _label()})

    assert len(document.chunks) > 1
    assert all(
        chunk.metadata.get("product_associations") == ["current_product"]
        for chunk in document.chunks
    )


def test_ix10_a_chunk_starting_mid_section_opens_with_its_heading_path() -> None:
    blocks = tuple(
        NormalizedBlock(
            id=f"b{index}",
            type=NormalizedBlockType.PARAGRAPH,
            raw_text="y" * 400,
            text="y" * 400,
            heading_path=("Loan terms", "Repayment"),
            source_refs=(_ref(f"b{index}"),),
        )
        for index in range(4)
    )
    document = NormalizedDocument(
        id="page:0123456789abcdef",
        name="Consumer loans",
        source_url=URL,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256="a" * 64,
        extraction_method="browser",
        blocks=blocks,
    )
    (projected,) = KnowledgeProjectionService(max_chunk_chars=900).project_sources(
        run_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        bundle=NormalizedSourceBundle(
            canonical_url=URL,
            acquisition_content_hash="b" * 64,
            documents=(document,),
        ),
        retrieved_at=NOW,
        language="en",
    )

    assert len(projected.chunks) == 2
    for chunk in projected.chunks:
        assert chunk.content.startswith("## Loan terms / Repayment\n")
        assert len(chunk.content) <= 900


# IX11 ------------------------------------------------------------------------


# IX14 ------------------------------------------------------------------------


@pytest.mark.parametrize("size", [300, 2500])
def test_ix14_chunk_size_outside_the_embedding_window_is_rejected(size) -> None:
    with pytest.raises(ValueError):
        RagSettings(chunk_size_chars=size)
    assert "chunk_overlap_chars" not in RagSettings.model_fields


# IX7: the worker's embedding sweep -------------------------------------------


class _Sweep:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.limits: list[int] = []
        self.fail = fail

    async def embed_missing(self, *, limit: int = 200) -> int:
        self.limits.append(limit)
        if self.fail is not None:
            raise self.fail
        return 3


def _worker(sweep, *, batch: int = 50):
    from app.worker import MonitoringWorker

    return MonitoringWorker(
        runs=object(),
        pipeline=object(),
        worker_id="worker-1",
        embeddings=sweep,
        embedding_sweep_batch=batch,
    )


@pytest.mark.asyncio
async def test_ix7_worker_sweep_fills_vectors_in_bounded_batches() -> None:
    sweep = _Sweep()

    assert await _worker(sweep).sweep_embeddings() == 3
    assert sweep.limits == [50]


@pytest.mark.asyncio
async def test_ix7_worker_sweep_failure_never_stops_the_worker() -> None:
    sweep = _Sweep(fail=RuntimeError("provider down"))

    assert await _worker(sweep).sweep_embeddings() == 0


@pytest.mark.asyncio
async def test_ix7_worker_sweep_can_be_turned_off() -> None:
    sweep = _Sweep()

    assert await _worker(sweep, batch=0).sweep_embeddings() == 0
    assert sweep.limits == []
