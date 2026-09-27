"""Regression tests for the indexing fix plan (fix-process/indexing/).

One test per plan item (IX*) whose target behaviour is visible without
PostgreSQL; the database-level items live in
tests/integration/test_indexing_fixes_postgres.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import load_seed_catalog
from app.config.models import RagSettings
from app.domain.acquisition import SourceLocator, SourceType
from app.domain.knowledge import KnowledgeChunk, KnowledgeDocument, document_version_id
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
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
from app.domain.semantic_extraction import ExtractionField
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
from app.services.review_decisions import ReviewDecisionService
from tests.unit.test_monitoring_pipeline import _indexing, _offering
from tests.unit.test_multi_review_approval import (
    OPEN_FIELDS,
    _decision,
    _extraction,
    _Reviews,
    _Snapshots,
    _task,
)

NOW = datetime(2026, 9, 26, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"


def _review_required(monkeypatch) -> None:
    original = monitoring_pipeline.build_snapshot_attempt

    def build(**kwargs):
        return original(**kwargs).model_copy(
            update={"status": SnapshotStatus.REVIEW_REQUIRED, "accepted_at": None}
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
async def test_ix5_review_required_run_embeds_nothing_and_publishes_text(
    monkeypatch,
) -> None:
    _review_required(monkeypatch)
    service, events, publications = _indexing()

    await service.refresh(_offering(), uuid4(), uuid4())

    assert [event for event in events if event[0] == "embed"] == []
    published = publications.values[-1]
    assert published.snapshot.status is SnapshotStatus.REVIEW_REQUIRED
    assert published.documents
    assert all(
        chunk.embedding is None
        for document in published.documents
        for chunk in document.chunks
    )


# IX6 -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ix6_final_decision_carries_a_summary_of_the_final_snapshot() -> None:
    from app.services.knowledge_projection import OfferingSummaryProjector

    extraction = _extraction()
    snapshot_id = uuid4()
    snapshot = SnapshotAttempt(
        id=snapshot_id,
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        status=SnapshotStatus.REVIEW_REQUIRED,
        normalized_tariff={},
        semantic_extraction=extraction.model_dump(mode="json"),
        validation={"accepted": False, "review_signals": []},
        canonical_sha256="a" * 64,
        created_at=NOW,
    )
    snapshots = _Snapshots(snapshot)
    tasks = [_task(snapshot_id, field) for field in OPEN_FIELDS]
    reviews = _Reviews(tasks, snapshots)
    service = ReviewDecisionService(
        reviews,
        snapshots,
        summaries=OfferingSummaryProjector(
            KnowledgeProjectionService(), load_seed_catalog()
        ),
    )
    name = "Overdrafts via Cards not secured with property"

    await service.apply(
        tasks[0].id,
        _decision(ExtractionField.PRODUCT_NAME, name),
        reviewer="reviewer-1",
    )
    assert reviews.updates[0].summary is None  # not ready: nothing to publish
    await service.apply(
        tasks[1].id,
        _decision(ExtractionField.COLLATERAL, "none"),
        reviewer="reviewer-1",
    )

    final = reviews.updates[-1]
    assert final.ready_for_activation is True
    assert final.summary is not None
    assert final.summary.document_key == "offering-summary:overdraft"
    assert name in final.summary.chunks[0].content
    assert all(chunk.embedding is None for chunk in final.summary.chunks)


class _Vectors:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.offerings: list[OfferingId | None] = []
        self.fail = fail

    async def embed_missing(self, *, offering_id=None, limit: int = 200) -> int:
        self.offerings.append(offering_id)
        if self.fail is not None:
            raise self.fail
        return 1


def _overdraft_review_batch():
    extraction = _extraction()
    snapshot_id = uuid4()
    snapshot = SnapshotAttempt(
        id=snapshot_id,
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        status=SnapshotStatus.REVIEW_REQUIRED,
        normalized_tariff={},
        semantic_extraction=extraction.model_dump(mode="json"),
        validation={"accepted": False, "review_signals": []},
        canonical_sha256="a" * 64,
        created_at=NOW,
    )
    snapshots = _Snapshots(snapshot)
    tasks = [_task(snapshot_id, field) for field in OPEN_FIELDS]
    return snapshots, tasks, _Reviews(tasks, snapshots)


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [None, RuntimeError("quota")])
async def test_ix5_approval_embeds_the_activated_documents_after_the_last_decision(
    fail,
) -> None:
    snapshots, tasks, reviews = _overdraft_review_batch()
    vectors = _Vectors(fail=fail)
    service = ReviewDecisionService(reviews, snapshots, vectors=vectors)

    await service.apply(
        tasks[0].id,
        _decision(ExtractionField.PRODUCT_NAME, "Overdraft"),
        reviewer="reviewer-1",
    )
    assert vectors.offerings == []  # nothing activated yet
    decided = await service.apply(
        tasks[1].id,
        _decision(ExtractionField.COLLATERAL, "none"),
        reviewer="reviewer-1",
    )

    # Best effort: a failure is left to the sweep and never fails the decision.
    assert decided.status.value == "approved"
    assert vectors.offerings == [OfferingId.OVERDRAFT]


# IX7 -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ix7_quota_refusal_publishes_the_corpus_as_text() -> None:
    service, _, publications = _indexing(out_of_quota=True)

    result = await service.refresh(_offering(), uuid4(), uuid4())

    published = publications.values[-1]
    assert {document.document_kind.value for document in published.documents} == {
        "source",
        "offering_summary",
    }
    assert all(
        chunk.embedding is None
        for document in published.documents
        for chunk in document.chunks
    )
    assert "indexing.embedding_deferred" in result.manifest.warning_codes
    assert result.manifest.document_count == 2


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


def test_ix11_summary_of_the_same_values_hashes_equal_at_different_times() -> None:
    def summary(created_at: datetime):
        snapshot = SnapshotAttempt(
            id=uuid4(),
            run_id=uuid4(),
            offering_execution_id=uuid4(),
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.CONSUMER_STANDARD,
            status=SnapshotStatus.ACCEPTED,
            normalized_tariff={"interest_rate": {"max": "13.5", "min": "13.5"}},
            canonical_sha256="c" * 64,
            created_at=created_at,
            accepted_at=created_at,
        )
        return KnowledgeProjectionService().project_summary(
            run_id=snapshot.run_id,
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.CONSUMER_STANDARD,
            display_name="Consumer loans",
            source_url=URL,
            value=snapshot,
            language="en",
        )

    first = summary(NOW)
    later = summary(NOW + timedelta(days=1))

    assert first.content_sha256 == later.content_sha256
    assert first.metadata["as_of"] != later.metadata["as_of"]


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
