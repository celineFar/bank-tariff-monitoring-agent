import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.acquisition import PageArtifact, SourceLocator, SourceType
from app.domain.catalog import (
    CatalogLanguage,
    LocalizedCatalogTerms,
    ProductFamilyCatalogEntry,
    SeedCatalog,
    SeedCatalogEntry,
)
from app.domain.knowledge import (
    EMBEDDING_DIMENSIONS,
    EmbeddedKnowledgeChunk,
    EmbeddedKnowledgeDocument,
)
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    MonitoringRun,
    OfferingExecution,
    OfferingRunStatus,
    PublicationResult,
    RunCommand,
    RunStatus,
    RunTrigger,
)
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    SourceReference,
)
from app.domain.semantic_extraction import (
    EvidenceCitation,
    EvidenceItem,
    ExtractedValue,
    ExtractionField,
    ExtractionStatus,
    LoanCategory,
    LoanProduct,
    SemanticExtractionPlan,
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
    ValidatedFieldResult,
)
from app.domain.source_discovery import (
    Authority,
    DecisionSource,
    DiscoveryScope,
    ExtractionContext,
    ExtractionContextItem,
    InformationRole,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.services.knowledge_index import EmbeddingQuotaExhausted
from app.services.knowledge_projection import KnowledgeProjectionService
from app.services.monitoring_pipeline import (
    IndexingPipeline,
    OfferingPipelineError,
    TariffPipeline,
)
from app.services.pipeline_audit_archive import FileSystemPipelineAuditArchive

NOW = datetime(2026, 9, 19, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
EVIDENCE_ID = "ev_0123456789abcdef01234567"


def _offering(offering_id=OfferingId.CONSUMER_STANDARD) -> SeedCatalogEntry:
    return SeedCatalogEntry(
        product=offering_id.product,
        offering_id=offering_id,
        display_name=offering_id.value,
        seed_url=f"{URL}/{offering_id.value}",
        language="en",
        localized_names={
            CatalogLanguage.ENGLISH: LocalizedCatalogTerms(name=offering_id.value),
            CatalogLanguage.ARMENIAN: LocalizedCatalogTerms(
                name=f"hy-{offering_id.value}"
            ),
        },
    )


def _families() -> tuple[ProductFamilyCatalogEntry, ...]:
    return tuple(
        ProductFamilyCatalogEntry(
            product=product,
            localized_names={
                CatalogLanguage.ENGLISH: LocalizedCatalogTerms(
                    name=f"{product.value}-family"
                ),
                CatalogLanguage.ARMENIAN: LocalizedCatalogTerms(
                    name=f"hy-{product.value}-family"
                ),
            },
        )
        for product in (ProductType.CONSUMER_LOAN, ProductType.MORTGAGE)
    )


def _artifact() -> PageArtifact:
    return PageArtifact.model_construct(
        retrieved_at=NOW,
        language="en",
        title="Consumer loan",
        canonical_url=URL,
        markdown="# Consumer loan\n\nConsumer loan rate 13.5%\n",
    )


def _bundle() -> NormalizedSourceBundle:
    reference = SourceReference(
        source_item_id="rate",
        locator=SourceLocator(
            source_url=URL,
            source_type=SourceType.PAGE,
            block_id="rate",
        ),
    )
    document = NormalizedDocument(
        id="page",
        name="Consumer loan",
        source_url=URL,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256="a" * 64,
        extraction_method="browser",
        blocks=(
            NormalizedBlock(
                id="rate",
                type=NormalizedBlockType.PARAGRAPH,
                raw_text="Consumer loan rate 13.5%",
                text="Consumer loan rate 13.5%",
                heading_path=("Rates",),
                source_refs=(reference,),
            ),
        ),
    )
    return NormalizedSourceBundle(
        canonical_url=URL,
        acquisition_content_hash="b" * 64,
        documents=(document,),
    )


def _discovery() -> SourceDiscoveryResult:
    reference = SourceReference(
        source_item_id="rate",
        locator=SourceLocator(
            source_url=URL,
            source_type=SourceType.PAGE,
            block_id="rate",
        ),
    )
    item = ExtractionContextItem(
        source_id="rate",
        document_id="page",
        scope=DiscoveryScope.BLOCK,
        role=InformationRole.PRICING,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        precedence=1,
        text="Consumer loan rate 13.5%",
        source_refs=(reference,),
    )
    assessment = SourceAssessment(
        source_id="rate",
        document_id="page",
        scope=DiscoveryScope.BLOCK,
        product_association=ProductAssociation.CURRENT_PRODUCT,
        role=InformationRole.PRICING,
        relevance=Relevance.RELEVANT,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        reason="states the consumer loan rate",
        decision_source=DecisionSource.LLM,
        input_fingerprint="c" * 64,
        structural_fingerprint="d" * 64,
        source_refs=(reference,),
    )
    return SourceDiscoveryResult.model_construct(
        product=ProductType.CONSUMER_LOAN,
        input_content_hash="b" * 64,
        assessments=(assessment,),
        extraction_context=ExtractionContext(
            product=ProductType.CONSUMER_LOAN,
            items=(item,),
        ),
    )


def _extraction() -> SemanticExtractionResult:
    locator = SourceLocator(
        source_url=URL,
        source_type=SourceType.PAGE,
        block_id="rate",
    )
    citation = EvidenceCitation(
        evidence_id=EVIDENCE_ID,
        source_item_id="rate",
        source_url=URL,
        source_type=SourceType.PAGE,
        quote="Consumer loan rate 13.5%",
        locator=locator,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
    )
    extracted = ExtractedValue[str](
        value="Consumer loan",
        evidence=(citation,),
        status=ExtractionStatus.FOUND,
    )
    product = LoanProduct.model_construct(
        product_name=extracted,
        category=LoanCategory.CONSUMER_LOAN,
        canonical_url=URL,
        retrieved_at=NOW,
    )
    evidence = EvidenceItem(
        evidence_id=EVIDENCE_ID,
        document_id="page",
        source_item_id="rate",
        content="Consumer loan rate 13.5%",
        role=InformationRole.PRICING,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        precedence=1,
        locator=locator,
    )
    validated = ValidatedFieldResult(
        field=ExtractionField.PRODUCT_NAME,
        status=ExtractionStatus.FOUND,
        value="Consumer loan",
        evidence=(citation,),
        batch_id="identity",
    )
    return SemanticExtractionResult(
        product=ProductType.CONSUMER_LOAN,
        model_name="test",
        status=SemanticExtractionRunStatus.COMPLETED,
        loan_product=product,
        evidence_catalog=(evidence,),
        batch_results=(),
        validated_fields=(validated,),
        reused_batch_count=0,
    )


class _Acquisition:
    def __init__(self, events):
        self.events = events

    async def acquire(self, url):
        self.events.append(("acquire", url))
        return _artifact()


class _Normalization:
    def __init__(self, events):
        self.events = events

    async def normalize(self, artifact):
        self.events.append(("normalize", artifact))
        return _bundle()


class _Discovery:
    def __init__(self, events):
        self.events = events

    async def discover(self, bundle, product):
        self.events.append(("discover", product))
        return _discovery()


class _Extraction:
    def __init__(self, events):
        self.events = events

    async def plan(self, bundle, discovery):
        self.events.append(("plan", discovery.product))
        return SemanticExtractionPlan.model_construct(
            product=discovery.product,
            canonical_url=URL,
            input_content_hash=bundle.acquisition_content_hash,
            schema_version="1",
            prompt_version="1",
            model_name="test",
            evidence_catalog=(),
            batches=(),
            cached_batches=(),
            cache_hits=(),
        )

    async def extract(self, bundle, discovery, *, retrieved_at):
        self.events.append(("extract", retrieved_at))
        return _extraction()


class _Embedder:
    def __init__(self, events, *, fail=False, out_of_quota=False):
        self.events = events
        self.fail = fail
        self.out_of_quota = out_of_quota

    async def embed(self, document):
        self.events.append(("embed", document.document_kind.value))
        if self.out_of_quota:
            raise EmbeddingQuotaExhausted("embedding provider error 429")
        if self.fail:
            raise RuntimeError("embedding unavailable")
        return EmbeddedKnowledgeDocument(
            **document.model_dump(exclude={"chunks"}),
            chunks=tuple(
                EmbeddedKnowledgeChunk(
                    **chunk.model_dump(),
                    embedding=tuple(0.01 for _ in range(EMBEDDING_DIMENSIONS)),
                )
                for chunk in document.chunks
            ),
        )


class _Snapshots:
    async def get_latest_accepted(self, **kwargs):
        return None


class _Publications:
    def __init__(self):
        self.values = []

    async def publish(self, publication):
        self.values.append(publication)
        return PublicationResult(
            snapshot_id=publication.snapshot.id,
            document_results=(),
            offering_status=OfferingRunStatus.SUCCEEDED,
        )


def _indexing(*, fail_embedding=False, out_of_quota=False, audit_archive=None):
    events = []
    publications = _Publications()
    service = IndexingPipeline(
        acquisition=_Acquisition(events),
        normalization=_Normalization(events),
        discovery=_Discovery(events),
        extraction=_Extraction(events),
        projection=KnowledgeProjectionService(),
        embedder=_Embedder(events, fail=fail_embedding, out_of_quota=out_of_quota),
        snapshots=_Snapshots(),
        publications=publications,
        audit_archive=audit_archive,
    )
    return service, events, publications


@pytest.mark.asyncio
async def test_indexing_refresh_wires_existing_stages_and_publishes_once() -> None:
    service, events, publications = _indexing()

    result = await service.refresh(_offering(), uuid4(), uuid4())

    assert [event[0] for event in events[:4]] == [
        "acquire",
        "normalize",
        "discover",
        "extract",
    ]
    assert [event for event in events if event[0] == "embed"] == [
        ("embed", "source"),
        ("embed", "offering_summary"),
    ]
    assert len(publications.values) == 1
    assert result.manifest.source_count == 1
    assert result.manifest.selected_count == 1
    assert result.manifest.document_count == 2
    assert result.manifest.items[0].document_id is not None
    assert {timing.stage for timing in result.manifest.timings} >= {
        "acquisition",
        "normalization",
        "source_discovery",
        "semantic_extraction",
        "embedding",
        "publication",
    }
    audit = publications.values[0].audit_metadata
    assert "Consumer loan rate 13.5%" not in str(audit)


@pytest.mark.asyncio
async def test_indexing_failure_before_publication_leaves_state_untouched() -> None:
    service, _, publications = _indexing(fail_embedding=True)

    with pytest.raises(OfferingPipelineError) as captured:
        await service.refresh(_offering(), uuid4(), uuid4())

    assert captured.value.stage == "embedding"
    assert captured.value.failure_code == "indexing.embedding_failed"
    assert publications.values == []


@pytest.mark.asyncio
async def test_a_quota_refusal_publishes_the_snapshot_without_the_corpus() -> None:
    """A validated, reviewed run must survive a provider quota window.

    The snapshot, its facts and its retrieval units are projected from the
    snapshot itself, and the answer path falls back to lexical recall, so
    publishing without the source corpus degrades retrieval instead of
    discarding the tariff data.
    """
    service, _, publications = _indexing(out_of_quota=True)

    result = await service.refresh(_offering(), uuid4(), uuid4())

    published = publications.values[-1]
    assert published.snapshot is result.snapshot
    # No corpus was written, so nothing supersedes the last good one.
    assert published.documents == ()
    # And the deferral is auditable rather than silent.
    assert "indexing.embedding_deferred" in result.manifest.warning_codes
    assert result.manifest.document_count == 0


@pytest.mark.asyncio
async def test_only_a_quota_refusal_is_deferred() -> None:
    """A malformed response is a defect, not a window to wait out."""
    service, _, publications = _indexing(fail_embedding=True)

    with pytest.raises(OfferingPipelineError):
        await service.refresh(_offering(), uuid4(), uuid4())

    assert publications.values == []


class _FamilyIndexing:
    async def refresh(self, offering, run_id, offering_execution_id, *, progress=None):
        if offering.offering_id is OfferingId.OVERDRAFT:
            raise RuntimeError("fixture failure")
        return SimpleNamespace(
            publication=SimpleNamespace(offering_status=OfferingRunStatus.SUCCEEDED)
        )


class _Runs:
    def __init__(self):
        self.failures = []
        self.finished = None

    async def create_offering_execution(self, run_id, product, offering_id):
        return OfferingExecution(
            id=uuid4(),
            run_id=run_id,
            product=product,
            offering_id=offering_id,
            status=OfferingRunStatus.PENDING,
        )

    async def start_offering_execution(self, execution_id, *, stage="starting"):
        offering_id = (
            OfferingId.CONSUMER_STANDARD if not self.failures else OfferingId.OVERDRAFT
        )
        return OfferingExecution(
            id=execution_id,
            run_id=uuid4(),
            product=ProductType.CONSUMER_LOAN,
            offering_id=offering_id,
            status=OfferingRunStatus.RUNNING,
            current_stage=stage,
            started_at=NOW,
        )

    async def fail_offering_execution(self, execution_id, **kwargs):
        self.failures.append((execution_id, kwargs))
        return SimpleNamespace(status=OfferingRunStatus.FAILED)

    async def finish(self, run_id, status, **kwargs):
        self.finished = (status, kwargs)
        return MonitoringRun(
            id=run_id,
            command=RunCommand(
                product=ProductType.CONSUMER_LOAN,
                trigger=RunTrigger.API,
            ),
            status=status,
            queued_at=NOW,
            started_at=NOW,
            completed_at=NOW,
            failure_code=kwargs.get("failure_code"),
            summary=kwargs.get("summary", {}),
        )

    async def pause_for_review(self, run_id, *, summary):
        self.finished = (RunStatus.AWAITING_REVIEW, {"summary": summary})
        return MonitoringRun(
            id=run_id,
            command=RunCommand(
                product=ProductType.CONSUMER_LOAN,
                trigger=RunTrigger.API,
            ),
            status=RunStatus.AWAITING_REVIEW,
            queued_at=NOW,
            started_at=NOW,
            summary=summary,
        )


class _CandidateIndexing:
    async def refresh(self, offering, run_id, offering_execution_id, *, progress=None):
        snapshot = SimpleNamespace(
            id=uuid4(),
            run_id=run_id,
            offering_execution_id=offering_execution_id,
            product=offering.product,
            offering_id=offering.offering_id,
            validation={
                "review_signals": [
                    {
                        "reason": "large_rate_change",
                        "issue_scope": "interest_rate",
                        "field": "interest_rate",
                    }
                ]
            },
            evidence=(),
            created_at=NOW,
        )
        return SimpleNamespace(
            snapshot=snapshot,
            publication=SimpleNamespace(
                offering_status=OfferingRunStatus.CANDIDATE_REVIEW
            ),
        )


class _Reviews:
    def __init__(self):
        self.values = []

    async def create(self, review):
        self.values.append(review)
        return review


@pytest.mark.asyncio
async def test_tariff_pipeline_isolates_offerings_and_reports_partial_success() -> None:
    catalog = SeedCatalog(
        families=_families(),
        offerings=(
            _offering(OfferingId.CONSUMER_STANDARD),
            _offering(OfferingId.OVERDRAFT),
        ),
    )
    runs = _Runs()
    pipeline = TariffPipeline(
        catalog=catalog,
        indexing=_FamilyIndexing(),
        runs=runs,
    )
    running = MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            trigger=RunTrigger.API,
        ),
        status=RunStatus.RUNNING,
        queued_at=NOW,
        started_at=NOW,
    )

    completed = await pipeline.execute(running)

    assert completed.status is RunStatus.PARTIAL_SUCCESS
    assert completed.summary == {
        "offering_count": 2,
        "succeeded": 1,
        "review_required": 0,
        "failed": 1,
        "review_ids": [],
    }
    assert len(runs.failures) == 1
    failure_payload = runs.failures[0][1]
    assert failure_payload["failure_detail"] == "RuntimeError"
    assert "fixture failure" not in str(failure_payload)


@pytest.mark.asyncio
async def test_candidate_snapshot_creates_review_and_pauses_run() -> None:
    catalog = SeedCatalog(
        families=_families(),
        offerings=(_offering(OfferingId.CONSUMER_STANDARD),),
    )
    runs = _Runs()
    reviews = _Reviews()
    pipeline = TariffPipeline(
        catalog=catalog,
        indexing=_CandidateIndexing(),
        runs=runs,
        reviews=reviews,
    )
    running = MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            trigger=RunTrigger.API,
        ),
        status=RunStatus.RUNNING,
        queued_at=NOW,
        started_at=NOW,
    )

    paused = await pipeline.execute(running)

    assert paused.status is RunStatus.AWAITING_REVIEW
    assert paused.summary["review_required"] == 1
    assert paused.summary["review_ids"] == [str(reviews.values[0].id)]
    assert reviews.values[0].run_id == running.id


@pytest.mark.asyncio
async def test_single_offering_failure_reports_source_code_and_reason() -> None:
    from app.services.acquisition import AcquisitionError, AcquisitionFailure
    from app.services.monitoring_pipeline import OfferingPipelineError

    class FailingIndexing:
        async def refresh(
            self, offering, run_id, offering_execution_id, *, progress=None
        ):
            raise OfferingPipelineError(
                "acquisition",
                "source.parsing_failed",
                AcquisitionError(
                    AcquisitionFailure.INSUFFICIENT_CONTENT,
                    "source content is insufficient",
                ),
            )

    catalog = SeedCatalog(
        families=_families(),
        offerings=(_offering(OfferingId.OVERDRAFT),),
    )
    runs = _Runs()
    pipeline = TariffPipeline(catalog=catalog, indexing=FailingIndexing(), runs=runs)
    running = MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.OVERDRAFT,
            trigger=RunTrigger.API,
        ),
        status=RunStatus.RUNNING,
        queued_at=NOW,
        started_at=NOW,
    )

    completed = await pipeline.execute(running)

    assert completed.status is RunStatus.FAILED
    assert completed.failure_code == "source.parsing_failed"
    assert runs.failures[0][1]["failure_detail"] == (
        "AcquisitionError:INSUFFICIENT_CONTENT"
    )
    assert runs.failures[0][1]["audit_payload"]["reason"] == ("INSUFFICIENT_CONTENT")


@pytest.mark.asyncio
async def test_indexing_refresh_persists_progress_before_each_stage() -> None:
    service, _, _ = _indexing()

    class _StageRuns:
        def __init__(self) -> None:
            self.stages = []

        async def start_offering_execution(self, execution_id, *, stage):
            self.stages.append(stage)

    runs = _StageRuns()
    service._runs = runs

    await service.refresh(_offering(), uuid4(), uuid4())

    assert runs.stages == [
        "acquisition",
        "normalization",
        "source_discovery",
        "semantic_extraction",
        "previous_snapshot",
        "embedding",
        "publication",
    ]


@pytest.mark.asyncio
async def test_indexing_refresh_collects_stage_numbered_audit_markdown(
    tmp_path,
) -> None:
    archive = FileSystemPipelineAuditArchive(tmp_path)
    service, _, _ = _indexing(audit_archive=archive)
    run_id = uuid4()

    await service.refresh(_offering(), run_id, uuid4())

    directory = tmp_path / f"run_{run_id}" / OfferingId.CONSUMER_STANDARD.value
    assert sorted(path.name for path in directory.glob("*.md")) == [
        "0_run_context.md",
        "2_normalization_diff.md",
        "2_normalized_webpage.md",
        "3_selected_sources.md",
        "3_source_selection_decisions.md",
        "3_source_selection_diff.md",
        "4_extraction_evidence.md",
        "4_pre_validation.md",
        "4_review_queue.md",
    ]
    assert "Consumer loan rate 13.5%" in (
        directory / "3_source_selection_decisions.md"
    ).read_text(encoding="utf-8")
    assert "Semantic extraction audit" in (
        directory / "4_extraction_evidence.md"
    ).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_indexing_audit_records_the_failing_stage_and_never_masks_it(
    tmp_path,
) -> None:
    archive = FileSystemPipelineAuditArchive(tmp_path)
    service, _, _ = _indexing(audit_archive=archive)
    service._discovery = _FailingDiscovery()
    run_id = uuid4()

    with pytest.raises(OfferingPipelineError) as captured:
        await service.refresh(_offering(), run_id, uuid4())

    assert captured.value.stage == "source_discovery"
    directory = tmp_path / f"run_{run_id}" / OfferingId.CONSUMER_STANDARD.value
    report = (directory / "3_source_selection_decisions.md").read_text(encoding="utf-8")
    assert "classifier unavailable" in report
    assert not (directory / "4_extraction_evidence.md").exists()


@pytest.mark.asyncio
async def test_indexing_audit_failure_does_not_fail_the_run(tmp_path) -> None:
    unwritable = tmp_path / "blocked"
    unwritable.write_text("not a directory", encoding="utf-8")
    service, _, publications = _indexing(
        audit_archive=FileSystemPipelineAuditArchive(unwritable)
    )

    await service.refresh(_offering(), uuid4(), uuid4())

    assert len(publications.values) == 1


class _FailingDiscovery:
    async def discover(self, bundle, product):
        raise RuntimeError("classifier unavailable")


class _ListSink:
    def __init__(self) -> None:
        self.items = []

    async def report(self, progress):
        self.items.append(progress)


def _running(offering_id=None) -> MonitoringRun:
    return MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            offering_id=offering_id,
            trigger=RunTrigger.ADK,
        ),
        status=RunStatus.RUNNING,
        queued_at=NOW,
        started_at=NOW,
    )


@pytest.mark.asyncio
async def test_indexing_refresh_reports_start_and_completion_of_every_stage() -> None:
    service, _, _ = _indexing()
    sink = _ListSink()

    await service.refresh(_offering(), uuid4(), uuid4(), progress=sink)

    stages = [
        "acquisition",
        "normalization",
        "source_discovery",
        "semantic_extraction",
        "previous_snapshot",
        "embedding",
        "publication",
    ]
    assert [(item.kind.value, item.stage) for item in sink.items] == [
        pair
        for stage in stages
        for pair in (("stage_started", stage), ("stage_completed", stage))
    ]
    assert all(item.offering_id is OfferingId.CONSUMER_STANDARD for item in sink.items)
    assert all(
        item.elapsed_ms >= 0
        for item in sink.items
        if item.kind.value == "stage_completed"
    )


@pytest.mark.asyncio
async def test_tariff_pipeline_reports_run_and_offering_outcomes() -> None:
    catalog = SeedCatalog(
        families=_families(),
        offerings=(
            _offering(OfferingId.CONSUMER_STANDARD),
            _offering(OfferingId.OVERDRAFT),
        ),
    )
    sink = _ListSink()
    pipeline = TariffPipeline(catalog=catalog, indexing=_FamilyIndexing(), runs=_Runs())

    await pipeline.execute(_running(), progress=sink)

    assert [
        (item.kind.value, item.offering_id.value if item.offering_id else None)
        for item in sink.items
    ] == [
        ("run_started", None),
        ("offering_started", "consumer_standard"),
        ("offering_succeeded", "consumer_standard"),
        ("offering_started", "overdraft"),
        ("offering_failed", "overdraft"),
        ("run_finished", None),
    ]
    failed = sink.items[4]
    assert failed.failure_code == "run.internal_error"
    assert sink.items[-1].detail == "partial_success"


@pytest.mark.asyncio
async def test_candidate_offering_reports_review_and_run_awaiting_review() -> None:
    catalog = SeedCatalog(
        families=_families(),
        offerings=(_offering(OfferingId.CONSUMER_STANDARD),),
    )
    sink = _ListSink()
    pipeline = TariffPipeline(
        catalog=catalog,
        indexing=_CandidateIndexing(),
        runs=_Runs(),
        reviews=_Reviews(),
    )

    await pipeline.execute(_running(), progress=sink)

    kinds = [item.kind.value for item in sink.items]
    assert kinds == [
        "run_started",
        "offering_started",
        "offering_review",
        "run_finished",
    ]
    assert sink.items[2].detail == "1 review"
    assert sink.items[-1].detail == "awaiting_review"


class _AuditedRuns(_Runs):
    def __init__(self):
        super().__init__()
        self.audits = []

    async def record_audit(self, run_id, event_type, **kwargs):
        self.audits.append((event_type, kwargs))


class _BlockingIndexing:
    """Reports the first stage, then waits until the run is cancelled."""

    def __init__(self) -> None:
        self.in_stage = asyncio.Event()

    async def refresh(self, offering, run_id, offering_execution_id, *, progress=None):
        from app.services.monitoring_progress import PipelineProgress, ProgressKind

        await progress.report(
            PipelineProgress(
                kind=ProgressKind.STAGE_STARTED,
                run_id=run_id,
                product=offering.product,
                offering_id=offering.offering_id,
                stage="semantic_extraction",
            )
        )
        self.in_stage.set()
        await asyncio.Event().wait()


@pytest.mark.asyncio
async def test_cancellation_marks_run_and_in_flight_offering_cancelled() -> None:
    catalog = SeedCatalog(
        families=_families(),
        offerings=(_offering(OfferingId.CONSUMER_STANDARD),),
    )
    runs = _AuditedRuns()
    indexing = _BlockingIndexing()
    pipeline = TariffPipeline(catalog=catalog, indexing=indexing, runs=runs)

    task = asyncio.create_task(pipeline.execute(_running()))
    await indexing.in_stage.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert runs.finished is not None
    status, finished = runs.finished
    assert status is RunStatus.FAILED
    assert finished["failure_code"] == "run.cancelled"
    assert len(runs.failures) == 1
    assert runs.failures[0][1]["failure_code"] == "run.cancelled"
    assert runs.failures[0][1]["stage"] == "semantic_extraction"
    assert runs.audits == [
        (
            "run.cancelled",
            {
                "reason_code": "run.cancelled",
                "payload": {"stage": "semantic_extraction"},
            },
        )
    ]


@pytest.mark.asyncio
async def test_cancellation_cleanup_failure_never_replaces_the_cancellation() -> None:
    catalog = SeedCatalog(
        families=_families(),
        offerings=(_offering(OfferingId.CONSUMER_STANDARD),),
    )

    class BrokenRuns(_Runs):
        async def finish(self, run_id, status, **kwargs):
            raise RuntimeError("database gone")

    indexing = _BlockingIndexing()
    pipeline = TariffPipeline(catalog=catalog, indexing=indexing, runs=BrokenRuns())

    task = asyncio.create_task(pipeline.execute(_running()))
    await indexing.in_stage.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
