from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.acquisition import PageArtifact, SourceLocator, SourceType
from app.domain.catalog import SeedCatalog, SeedCatalogEntry
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
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
    ValidatedFieldResult,
)
from app.domain.source_discovery import (
    Authority,
    DiscoveryScope,
    ExtractionContext,
    ExtractionContextItem,
    InformationRole,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.services.knowledge_projection import KnowledgeProjectionService
from app.services.monitoring_pipeline import (
    IndexingPipeline,
    OfferingPipelineError,
    TariffPipeline,
)

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
    )


def _artifact() -> PageArtifact:
    return PageArtifact.model_construct(retrieved_at=NOW, language="en")


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
    return SourceDiscoveryResult.model_construct(
        product=ProductType.CONSUMER_LOAN,
        input_content_hash="b" * 64,
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

    async def extract(self, bundle, discovery, *, retrieved_at):
        self.events.append(("extract", retrieved_at))
        return _extraction()


class _Embedder:
    def __init__(self, events, *, fail=False):
        self.events = events
        self.fail = fail

    async def embed(self, document):
        self.events.append(("embed", document.document_kind.value))
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


def _indexing(*, fail_embedding=False):
    events = []
    publications = _Publications()
    service = IndexingPipeline(
        acquisition=_Acquisition(events),
        normalization=_Normalization(events),
        discovery=_Discovery(events),
        extraction=_Extraction(events),
        projection=KnowledgeProjectionService(),
        embedder=_Embedder(events, fail=fail_embedding),
        snapshots=_Snapshots(),
        publications=publications,
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


class _FamilyIndexing:
    async def refresh(self, offering, run_id, offering_execution_id):
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


@pytest.mark.asyncio
async def test_tariff_pipeline_isolates_offerings_and_reports_partial_success() -> None:
    catalog = SeedCatalog(
        offerings=(
            _offering(OfferingId.CONSUMER_STANDARD),
            _offering(OfferingId.OVERDRAFT),
        )
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
    }
    assert len(runs.failures) == 1
    failure_payload = runs.failures[0][1]
    assert failure_payload["failure_detail"] == "RuntimeError"
    assert "fixture failure" not in str(failure_payload)
