from __future__ import annotations

from collections.abc import Awaitable, Sequence
from time import perf_counter
from typing import Protocol, TypeVar
from uuid import UUID, uuid4

from app.domain.acquisition import PageArtifact
from app.domain.catalog import SeedCatalog, SeedCatalogEntry
from app.domain.knowledge import (
    EmbeddedKnowledgeDocument,
    KnowledgeDocument,
    document_version_id,
)
from app.domain.monitoring import (
    ManifestItemStatus,
    MonitoringRun,
    OfferingFailureCode,
    OfferingPublication,
    OfferingRunStatus,
    RunFailureCode,
    RunStatus,
    SnapshotStatus,
    SourceManifestItem,
)
from app.domain.normalization import NormalizedSourceBundle
from app.domain.pipeline import IndexingRefreshResult, SourceManifest, StageTiming
from app.domain.semantic_extraction import SemanticExtractionResult
from app.domain.source_discovery import SourceDiscoveryResult
from app.repositories.contracts import (
    MonitoringSnapshotRepository,
    OfferingPublicationRepository,
    RunRepository,
)
from app.services.knowledge_projection import KnowledgeProjectionService
from app.services.snapshot_lifecycle import (
    build_snapshot_attempt,
    compare_accepted_snapshots,
    evidence_changed,
)

T = TypeVar("T")


class AcquisitionPort(Protocol):
    async def acquire(self, url: str) -> PageArtifact: ...


class NormalizationPort(Protocol):
    async def normalize(self, artifact: PageArtifact) -> NormalizedSourceBundle: ...


class SourceDiscoveryPort(Protocol):
    async def discover(
        self, bundle: NormalizedSourceBundle, product
    ) -> SourceDiscoveryResult: ...


class SemanticExtractionPort(Protocol):
    async def extract(
        self,
        bundle: NormalizedSourceBundle,
        discovery: SourceDiscoveryResult,
        *,
        retrieved_at,
    ) -> SemanticExtractionResult: ...


class KnowledgeEmbeddingPort(Protocol):
    async def embed(self, document: KnowledgeDocument) -> EmbeddedKnowledgeDocument: ...


class OfferingPipelineError(RuntimeError):
    def __init__(self, stage: str, failure_code: str, cause: Exception) -> None:
        super().__init__(f"{stage} failed: {type(cause).__name__}")
        self.stage = stage
        self.failure_code = failure_code
        self.cause_type = type(cause).__name__


class IndexingPipeline:
    def __init__(
        self,
        *,
        acquisition: AcquisitionPort,
        normalization: NormalizationPort,
        discovery: SourceDiscoveryPort,
        extraction: SemanticExtractionPort,
        projection: KnowledgeProjectionService,
        embedder: KnowledgeEmbeddingPort,
        snapshots: MonitoringSnapshotRepository,
        publications: OfferingPublicationRepository,
    ) -> None:
        self._acquisition = acquisition
        self._normalization = normalization
        self._discovery = discovery
        self._extraction = extraction
        self._projection = projection
        self._embedder = embedder
        self._snapshots = snapshots
        self._publications = publications

    async def refresh(
        self,
        offering: SeedCatalogEntry,
        run_id: UUID,
        offering_execution_id: UUID,
    ) -> IndexingRefreshResult:
        timings: list[StageTiming] = []
        artifact = await self._stage(
            "acquisition",
            OfferingFailureCode.ACQUISITION_FAILED,
            self._acquisition.acquire(str(offering.seed_url)),
            timings,
        )
        bundle = await self._stage(
            "normalization",
            OfferingFailureCode.NORMALIZATION_FAILED,
            self._normalization.normalize(artifact),
            timings,
        )
        discovery = await self._stage(
            "source_discovery",
            OfferingFailureCode.SOURCE_DISCOVERY_FAILED,
            self._discovery.discover(bundle, offering.product),
            timings,
        )
        extraction = await self._stage(
            "semantic_extraction",
            OfferingFailureCode.SEMANTIC_EXTRACTION_FAILED,
            self._extraction.extract(
                bundle,
                discovery,
                retrieved_at=artifact.retrieved_at,
            ),
            timings,
        )
        previous = await self._stage(
            "previous_snapshot",
            RunFailureCode.PERSISTENCE_FAILED,
            self._snapshots.get_latest_accepted(
                bank="ameria",
                product=offering.product,
                offering_id=offering.offering_id,
                before_run_id=run_id,
            ),
            timings,
        )
        snapshot = build_snapshot_attempt(
            run_id=run_id,
            offering_execution_id=offering_execution_id,
            product=offering.product,
            offering_id=offering.offering_id,
            result=extraction,
            previous_accepted_snapshot_id=previous.id if previous else None,
        )
        selected_document_ids = frozenset(
            item.document_id for item in discovery.extraction_context.items
        )
        source_documents = self._projection.project_sources(
            run_id=run_id,
            product=offering.product,
            offering_id=offering.offering_id,
            bundle=bundle,
            retrieved_at=artifact.retrieved_at,
            language=offering.language or artifact.language or "en",
            selected_document_ids=selected_document_ids,
        )
        if not source_documents:
            raise OfferingPipelineError(
                "projection",
                OfferingFailureCode.SOURCE_DISCOVERY_FAILED.value,
                ValueError("source discovery selected no projectable documents"),
            )
        documents: tuple[KnowledgeDocument, ...] = source_documents
        if snapshot.status is SnapshotStatus.ACCEPTED:
            documents = (
                *documents,
                self._projection.project_summary(
                    run_id=run_id,
                    product=offering.product,
                    offering_id=offering.offering_id,
                    display_name=offering.display_name,
                    source_url=offering.seed_url,
                    value=snapshot,
                    language=offering.language or artifact.language or "en",
                ),
            )
        embedded = await self._stage(
            "embedding",
            "indexing.embedding_failed",
            self._embed_all(documents),
            timings,
        )
        selected = {document.document_key: document for document in embedded}
        manifest_items = tuple(
            _manifest_item(
                run_id=run_id,
                offering_execution_id=offering_execution_id,
                offering=offering,
                document=document,
                embedded_by_key=selected,
            )
            for document in bundle.documents
        )
        change_set = compare_accepted_snapshots(previous, snapshot)
        manifest = SourceManifest(
            items=manifest_items,
            source_count=len(manifest_items),
            selected_count=sum(item.selected for item in manifest_items),
            document_count=len(embedded),
            chunk_count=sum(len(document.chunks) for document in embedded),
            warning_codes=tuple(warning.code.value for warning in bundle.warnings),
            timings=tuple(timings),
        )
        provenance_changed = evidence_changed(previous, snapshot)
        publication = await self._stage(
            "publication",
            "indexing.publication_failed",
            self._publications.publish(
                OfferingPublication(
                    offering_execution_id=offering_execution_id,
                    documents=embedded,
                    snapshot=snapshot,
                    changes=(change_set if change_set and change_set.changes else None),
                    manifests=manifest.items,
                    audit_metadata={
                        "provenance_changed": provenance_changed,
                        "timings": [
                            timing.model_dump(mode="json") for timing in timings
                        ],
                        "warning_codes": list(manifest.warning_codes),
                    },
                )
            ),
            timings,
        )
        return IndexingRefreshResult(
            manifest=manifest.model_copy(update={"timings": tuple(timings)}),
            snapshot=snapshot,
            publication=publication,
            provenance_changed=provenance_changed,
        )

    async def _embed_all(
        self, documents: Sequence[KnowledgeDocument]
    ) -> tuple[EmbeddedKnowledgeDocument, ...]:
        embedded: list[EmbeddedKnowledgeDocument] = []
        for document in documents:
            embedded.append(await self._embedder.embed(document))
        return tuple(embedded)

    @staticmethod
    async def _stage(
        stage: str,
        failure_code,
        operation: Awaitable[T],
        timings: list[StageTiming],
    ) -> T:
        started = perf_counter()
        try:
            return await operation
        except OfferingPipelineError:
            raise
        except Exception as exc:
            code = (
                failure_code.value if hasattr(failure_code, "value") else failure_code
            )
            raise OfferingPipelineError(stage, str(code), exc) from exc
        finally:
            timings.append(
                StageTiming(
                    stage=stage,
                    duration_ms=max(0, round((perf_counter() - started) * 1000)),
                )
            )


class TariffPipeline:
    def __init__(
        self,
        *,
        catalog: SeedCatalog,
        indexing: IndexingPipeline,
        runs: RunRepository,
    ) -> None:
        self._catalog = catalog
        self._indexing = indexing
        self._runs = runs

    async def execute(self, run: MonitoringRun) -> MonitoringRun:
        if run.status is not RunStatus.RUNNING:
            raise ValueError("TariffPipeline requires a claimed running run")
        offerings = self._catalog.enabled_for(run.command.product)
        if run.command.offering_id is not None:
            offerings = tuple(
                item
                for item in offerings
                if item.offering_id is run.command.offering_id
            )
        succeeded = 0
        review_required = 0
        failed = 0
        for offering in offerings:
            execution = await self._runs.create_offering_execution(
                run.id,
                offering.product,
                offering.offering_id,
            )
            execution = await self._runs.start_offering_execution(
                execution.id,
                stage="acquisition",
            )
            try:
                result = await self._indexing.refresh(
                    offering,
                    run.id,
                    execution.id,
                )
            except OfferingPipelineError as exc:
                failed += 1
                await self._runs.fail_offering_execution(
                    execution.id,
                    stage=exc.stage,
                    failure_code=exc.failure_code,
                    failure_detail=exc.cause_type,
                    audit_payload={
                        "stage": exc.stage,
                        "exception_type": exc.cause_type,
                    },
                )
                continue
            except Exception as exc:
                failed += 1
                await self._runs.fail_offering_execution(
                    execution.id,
                    stage="internal",
                    failure_code=RunFailureCode.INTERNAL_ERROR.value,
                    failure_detail=type(exc).__name__,
                    audit_payload={
                        "stage": "internal",
                        "exception_type": type(exc).__name__,
                    },
                )
                continue
            if result.publication.offering_status is OfferingRunStatus.SUCCEEDED:
                succeeded += 1
            else:
                review_required += 1

        total = len(offerings)
        if succeeded == total:
            status = RunStatus.SUCCEEDED
        elif succeeded or review_required:
            status = RunStatus.PARTIAL_SUCCESS
        else:
            status = RunStatus.FAILED
        return await self._runs.finish(
            run.id,
            status,
            failure_code=(
                OfferingFailureCode.VALIDATION_FAILED.value
                if status is RunStatus.FAILED
                else None
            ),
            summary={
                "offering_count": total,
                "succeeded": succeeded,
                "review_required": review_required,
                "failed": failed,
            },
        )


def _manifest_item(
    *,
    run_id: UUID,
    offering_execution_id: UUID,
    offering: SeedCatalogEntry,
    document,
    embedded_by_key: dict[str, EmbeddedKnowledgeDocument],
) -> SourceManifestItem:
    embedded = embedded_by_key.get(document.id)
    return SourceManifestItem(
        id=uuid4(),
        run_id=run_id,
        offering_execution_id=offering_execution_id,
        product=offering.product,
        offering_id=offering.offering_id,
        source_url=document.source_url,
        final_url=document.source_url,
        document_key=document.id,
        document_id=document_version_id(embedded) if embedded else None,
        content_sha256=document.content_sha256,
        status=(
            ManifestItemStatus.INDEXED if embedded else ManifestItemStatus.EXCLUDED
        ),
        selected=embedded is not None,
        reason_code=("source.selected" if embedded else "source.not_selected"),
    )
