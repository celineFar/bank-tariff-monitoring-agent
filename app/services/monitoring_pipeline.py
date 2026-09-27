from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Sequence
from datetime import date
from decimal import Decimal
from enum import StrEnum
from time import perf_counter
from typing import Protocol, TypeVar
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.domain.acquisition import AcquisitionWarningCode, PageArtifact
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
    SourceFailureCode,
    SourceManifestItem,
)
from app.domain.normalization import NormalizationWarningCode, NormalizedSourceBundle
from app.domain.pdf_extraction import PdfLinkSelection
from app.domain.pipeline import IndexingRefreshResult, SourceManifest, StageTiming
from app.domain.review import (
    ReviewCandidate,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.domain.semantic_extraction import (
    SemanticExtractionPlan,
    SemanticExtractionResult,
)
from app.domain.source_discovery import OfferingContext, SourceDiscoveryResult
from app.repositories.contracts import (
    MonitoringSnapshotRepository,
    OfferingPublicationRepository,
    ReviewRepository,
    RunRepository,
)
from app.services.failure_mapping import (
    bounded_failure_detail,
    describe_failure,
    source_failure_code,
)
from app.services.knowledge_index import EmbeddingQuotaExhausted
from app.services.knowledge_projection import KnowledgeProjectionService
from app.services.monitoring_progress import (
    PipelineProgress,
    ProgressKind,
    ProgressSink,
    report_safely,
)
from app.services.normalized_renderer import render_normalized_markdown
from app.services.pipeline_audit_archive import AuditContext, PipelineAuditArchive
from app.services.review_evidence import cited_evidence_set, evidence_items
from app.services.snapshot_lifecycle import (
    build_snapshot_attempt,
    compare_accepted_snapshots,
    evidence_changed,
    non_reviewable_extraction_failure,
    tariff_fields,
)
from app.services.source_selection import (
    build_selected_source_bundle,
    select_sources,
)
from app.services.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer()
T = TypeVar("T")


class AcquisitionPort(Protocol):
    async def acquire(self, url: str) -> PageArtifact: ...


class NormalizationPort(Protocol):
    async def normalize(
        self,
        artifact: PageArtifact,
        *,
        pdf_selection: PdfLinkSelection | None = None,
    ) -> NormalizedSourceBundle: ...


class PdfLinkSelectionPort(Protocol):
    async def select(
        self, artifact: PageArtifact, offering: OfferingContext
    ) -> PdfLinkSelection: ...


class SourceDiscoveryPort(Protocol):
    async def discover(
        self,
        bundle: NormalizedSourceBundle,
        offering: OfferingContext,
        *,
        as_of: date | None = None,
    ) -> SourceDiscoveryResult: ...


class SemanticExtractionPort(Protocol):
    async def plan(
        self,
        bundle: NormalizedSourceBundle,
        discovery: SourceDiscoveryResult,
        offering: OfferingContext | None = None,
    ) -> SemanticExtractionPlan: ...

    async def extract(
        self,
        bundle: NormalizedSourceBundle,
        discovery: SourceDiscoveryResult,
        *,
        retrieved_at,
        offering: OfferingContext | None = None,
    ) -> SemanticExtractionResult: ...


class KnowledgeEmbeddingPort(Protocol):
    async def embed(self, document: KnowledgeDocument) -> EmbeddedKnowledgeDocument: ...


class OfferingPipelineError(RuntimeError):
    def __init__(self, stage: str, failure_code: str, cause: Exception) -> None:
        super().__init__(f"{stage} failed: {type(cause).__name__}")
        self.stage = stage
        self.failure_code = failure_code
        self.cause_type = type(cause).__name__
        reason = getattr(cause, "reason", None)
        self.cause_reason = reason.value if isinstance(reason, StrEnum) else None
        # Counts such as "tables 3 -> 0": what an incomplete acquisition lacked.
        # Never source text, so safe to persist.
        self.cause_reasons = tuple(getattr(cause, "reasons", ()) or ())
        # `ClientError` alone cannot tell an operator that a model was retired,
        # so keep the transport status too. The provider's message stays in the
        # logs; `docs/failure-behavior.md` keeps it out of stored details.
        self.cause_detail = bounded_failure_detail(cause)
        self.cause_log_detail = describe_failure(cause)


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
        runs: RunRepository | None = None,
        audit_archive: PipelineAuditArchive | None = None,
        large_rate_change_percentage_points: float = 3.0,
        review_rank_gap: float = 0.05,
        pdf_selection: PdfLinkSelectionPort | None = None,
        catalog: SeedCatalog | None = None,
    ) -> None:
        self._acquisition = acquisition
        self._pdf_selection = pdf_selection
        # The other offerings, for source discovery's cross-sell rule.
        self._catalog = catalog
        self._normalization = normalization
        self._discovery = discovery
        self._extraction = extraction
        self._projection = projection
        self._embedder = embedder
        self._snapshots = snapshots
        self._publications = publications
        self._runs = runs
        self._audit_archive = audit_archive
        self._review_rank_gap = review_rank_gap
        self._large_rate_change_percentage_points = Decimal(
            str(large_rate_change_percentage_points)
        )

    async def refresh(
        self,
        offering: SeedCatalogEntry,
        run_id: UUID,
        offering_execution_id: UUID,
        *,
        progress: ProgressSink | None = None,
    ) -> IndexingRefreshResult:
        timings: list[StageTiming] = []

        def report(kind: ProgressKind, name: str, elapsed_ms: int = 0):
            return report_safely(
                progress,
                PipelineProgress(
                    kind=kind,
                    run_id=run_id,
                    product=offering.product,
                    offering_id=offering.offering_id,
                    stage=name,
                    elapsed_ms=elapsed_ms,
                ),
            )

        async def stage(name: str, failure_code, operation: Awaitable[T]) -> T:
            # The persisted stage stays: the run-status API still reads it.
            if self._runs is not None:
                await self._runs.start_offering_execution(
                    offering_execution_id, stage=name
                )
            await report(ProgressKind.STAGE_STARTED, name)
            # Every stage funnels through here, so one span covers all of them.
            # Nested ADK runners inside a stage open their spans under the
            # ambient context, which makes their model calls children of it.
            with tracer.start_as_current_span(f"stage {name}") as span:
                span.set_attribute("tariff.stage", name)
                span.set_attribute("tariff.run_id", str(run_id))
                span.set_attribute("tariff.offering_id", offering.offering_id.value)
                try:
                    result = await self._stage(name, failure_code, operation, timings)
                except OfferingPipelineError as exc:
                    span.set_attribute("tariff.failure_code", exc.failure_code)
                    raise
            await report(ProgressKind.STAGE_COMPLETED, name, timings[-1].duration_ms)
            return result

        artifact = await stage(
            "acquisition",
            OfferingFailureCode.ACQUISITION_FAILED,
            self._acquisition.acquire(str(offering.seed_url)),
        )
        if self._runs is not None:
            try:
                await self._runs.record_acquisition(
                    offering_execution_id,
                    retrieved_at=artifact.retrieved_at,
                    reused=artifact.reused,
                )
            except Exception:
                # Informational: the run's result does not depend on it.
                logger.warning(
                    "Could not record the acquisition time of %s",
                    offering.offering_id.value,
                    exc_info=True,
                )
        offering_context = OfferingContext.from_catalog_entry(
            offering,
            page_title=artifact.title,
            page_blocks=artifact.blocks,
            catalog=self._catalog,
        )
        pdf_selection = None
        if self._pdf_selection is not None and artifact.downloadable_documents:
            # Source discovery's first step: which linked PDFs belong to this
            # offering, from their links, before any transcription is paid for.
            pdf_selection = await stage(
                "pdf_selection",
                OfferingFailureCode.SOURCE_DISCOVERY_FAILED,
                self._pdf_selection.select(artifact, offering_context),
            )
        bundle = await stage(
            "normalization",
            OfferingFailureCode.NORMALIZATION_FAILED,
            self._normalization.normalize(artifact, pdf_selection=pdf_selection),
        )
        audit = self._audit_archive
        audit_context = (
            AuditContext(
                run_id=run_id,
                offering_execution_id=offering_execution_id,
                product=offering.product,
                offering_id=offering.offering_id,
                seed_url=str(offering.seed_url),
            )
            if audit is not None
            else None
        )
        if audit is not None and audit_context is not None:
            await audit.record_normalization(audit_context, artifact, bundle)
        try:
            discovery = await stage(
                "source_discovery",
                OfferingFailureCode.SOURCE_DISCOVERY_FAILED,
                self._discovery.discover(
                    bundle,
                    offering_context,
                    as_of=artifact.retrieved_at.date(),
                ),
            )
        except OfferingPipelineError as exc:
            if audit is not None and audit_context is not None:
                await audit.record_source_discovery(
                    audit_context, bundle, None, error=exc.__cause__ or exc
                )
            raise
        if audit is not None and audit_context is not None:
            await audit.record_source_discovery(audit_context, bundle, discovery)
        # The plan is captured before extraction: afterwards its batches are
        # cache hits, and the evidence overlay would report them as unsent.
        plan = (
            await self._audit_plan(bundle, discovery, offering_context)
            if audit is not None
            else None
        )
        try:
            extraction = await stage(
                "semantic_extraction",
                OfferingFailureCode.SEMANTIC_EXTRACTION_FAILED,
                self._extraction.extract(
                    bundle,
                    discovery,
                    retrieved_at=artifact.retrieved_at,
                    offering=offering_context,
                ),
            )
        except OfferingPipelineError as exc:
            if audit is not None and audit_context is not None and plan is not None:
                await audit.record_semantic_extraction(
                    audit_context,
                    bundle,
                    discovery,
                    plan,
                    None,
                    error=exc.__cause__ or exc,
                )
            raise
        if audit is not None and audit_context is not None and plan is not None:
            await audit.record_semantic_extraction(
                audit_context, bundle, discovery, plan, extraction
            )
        for reused in extraction.reused_review_decisions:
            # A field answered by a remembered decision instead of a new review
            # (SE12) is recorded, so the reuse is visible in the run's history.
            try:
                await self._runs.record_audit(
                    run_id,
                    "review_decision_reused",
                    offering_execution_id=offering_execution_id,
                    payload={"offering_id": offering.offering_id.value, **reused},
                )
            except Exception:
                logger.warning(
                    "could not audit a reused review decision", exc_info=True
                )
        extraction_failure = non_reviewable_extraction_failure(extraction)
        if extraction_failure is not None:
            raise OfferingPipelineError(
                "semantic_extraction",
                OfferingFailureCode.SEMANTIC_EXTRACTION_FAILED.value,
                ValueError(extraction_failure),
            )
        previous = await stage(
            "previous_snapshot",
            RunFailureCode.PERSISTENCE_FAILED,
            self._snapshots.get_latest_accepted(
                bank="ameria",
                product=offering.product,
                offering_id=offering.offering_id,
                before_run_id=run_id,
            ),
        )
        selected_bundle = build_selected_source_bundle(bundle, discovery)
        snapshot = build_snapshot_attempt(
            run_id=run_id,
            offering_execution_id=offering_execution_id,
            product=offering.product,
            offering_id=offering.offering_id,
            result=extraction,
            previous_accepted_snapshot_id=previous.id if previous else None,
            previous_accepted_snapshot=previous,
            large_rate_change_percentage_points=(
                self._large_rate_change_percentage_points
            ),
            review_rank_gap=self._review_rank_gap,
            selected_sources_markdown=render_normalized_markdown(selected_bundle),
        )
        unavailable = _unavailable_linked_documents(artifact, bundle)
        lost = _fields_lost(previous, snapshot) if unavailable else ()
        if lost:
            # A linked PDF that failed this once reads as if its values were
            # withdrawn: publishing would record "value -> not stated", retire
            # the document, and the next good run would record the reverse.
            raise OfferingPipelineError(
                "validation",
                SourceFailureCode.LINKED_DOCUMENT_UNAVAILABLE.value,
                LinkedDocumentUnavailable(unavailable, lost),
            )
        if snapshot.status is SnapshotStatus.REVIEW_REQUIRED and not _review_tasks(
            snapshot
        ):
            # Not acceptable, yet no question a person could answer: publishing
            # it would park a candidate that no review can ever activate, and
            # pause the run with nothing to ask.
            raise OfferingPipelineError(
                "validation",
                OfferingFailureCode.VALIDATION_FAILED.value,
                ValueError("candidate needs review but raised no review signal"),
            )
        # The same selection extraction used: the RAG index holds only what
        # source discovery selected for this offering, with its labels.
        selection = select_sources(discovery)
        source_documents = self._projection.project_sources(
            run_id=run_id,
            product=offering.product,
            offering_id=offering.offering_id,
            bundle=selected_bundle,
            retrieved_at=artifact.retrieved_at,
            language=offering.language or artifact.language or "en",
            labels=selection.items,
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
        embedded, index_deferred = await stage(
            "embedding",
            "indexing.embedding_failed",
            (
                self._embed_all_or_defer(documents)
                if snapshot.status is SnapshotStatus.ACCEPTED
                # Content under review is stored as text only: nothing is spent
                # on vectors a reviewer may reject. Approval embeds it (IX5).
                else self._text_only(documents)
            ),
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
            warning_codes=(
                *(warning.code.value for warning in artifact.warnings),
                *(warning.code.value for warning in bundle.warnings),
                *(("indexing.embedding_deferred",) if index_deferred else ()),
            ),
            timings=tuple(timings),
        )
        provenance_changed = evidence_changed(previous, snapshot)
        publication = await stage(
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
                        "acquisition_warnings": [
                            warning.model_dump(mode="json")
                            for warning in artifact.warnings
                        ],
                    },
                )
            ),
        )
        return IndexingRefreshResult(
            manifest=manifest.model_copy(update={"timings": tuple(timings)}),
            snapshot=snapshot,
            publication=publication,
            provenance_changed=provenance_changed,
        )

    async def _audit_plan(
        self,
        bundle: NormalizedSourceBundle,
        discovery: SourceDiscoveryResult,
        offering: OfferingContext | None = None,
    ) -> SemanticExtractionPlan | None:
        """Plan deterministically for the audit overlay without failing the run."""
        try:
            return await self._extraction.plan(bundle, discovery, offering)
        except Exception:  # pragma: no cover - audit output is best effort
            logger.warning(
                "Failed to build the semantic-extraction plan for the audit trail",
                exc_info=True,
            )
            return None

    async def _embed_all_or_defer(
        self, documents: Sequence[KnowledgeDocument]
    ) -> tuple[tuple[EmbeddedKnowledgeDocument, ...], bool]:
        """Embed the corpus, or publish it as text when the provider is out of quota.

        A quota refusal says the request was well-formed and the window has
        moved, so losing a run that was acquired, extracted and validated is the
        wrong trade. The documents are published anyway: those embedded before
        the refusal with their vectors, the rest as text only. The snapshot's
        set is activated as usual, so lexical search serves the new tariff at
        once, and the worker's `embed_missing` sweep fills the vectors when the
        quota returns (IX7).

        Every other embedding failure still raises: a malformed response or a
        dimension mismatch is a defect, not a window to wait out.
        """
        embedded: list[EmbeddedKnowledgeDocument] = []
        for index, document in enumerate(documents):
            try:
                embedded.append(await self._embedder.embed(document))
            except EmbeddingQuotaExhausted:
                logger.warning(
                    "embedding deferred for lack of provider quota; publishing "
                    "%s of %s documents as text for the embedding sweep",
                    len(documents) - index,
                    len(documents),
                )
                embedded.extend(
                    EmbeddedKnowledgeDocument.text_only(item)
                    for item in documents[index:]
                )
                return tuple(embedded), True
        return tuple(embedded), False

    @staticmethod
    async def _text_only(
        documents: Sequence[KnowledgeDocument],
    ) -> tuple[tuple[EmbeddedKnowledgeDocument, ...], bool]:
        return tuple(
            EmbeddedKnowledgeDocument.text_only(item) for item in documents
        ), False

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
            code = source_failure_code(exc, stage=stage).value
            if stage in {"embedding", "publication", "previous_snapshot"}:
                code = (
                    failure_code.value
                    if hasattr(failure_code, "value")
                    else failure_code
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
        reviews: ReviewRepository | None = None,
    ) -> None:
        self._catalog = catalog
        self._indexing = indexing
        self._runs = runs
        self._reviews = reviews

    async def execute(
        self,
        run: MonitoringRun,
        *,
        progress: ProgressSink | None = None,
    ) -> MonitoringRun:
        if run.status is not RunStatus.RUNNING:
            raise ValueError("TariffPipeline requires a claimed running run")
        offerings = self._catalog.enabled_for(run.command.product)
        if run.command.offering_id is not None:
            offerings = tuple(
                item
                for item in offerings
                if item.offering_id is run.command.offering_id
            )
        tracker = _StageTracker(progress)

        async def report(kind: ProgressKind, offering=None, **fields) -> None:
            await report_safely(
                tracker,
                PipelineProgress(
                    kind=kind,
                    run_id=run.id,
                    product=run.command.product,
                    offering_id=offering.offering_id if offering else None,
                    **fields,
                ),
            )

        await report(
            ProgressKind.RUN_STARTED,
            detail=f"{len(offerings)} offering{'s' if len(offerings) != 1 else ''}",
        )
        started = perf_counter()
        succeeded = 0
        review_required = 0
        review_ids: list[UUID] = []
        failed = 0
        failure_codes: list[str] = []
        execution = None
        try:
            for offering in offerings:
                execution = None
                execution = await self._runs.create_offering_execution(
                    run.id,
                    offering.product,
                    offering.offering_id,
                )
                execution = await self._runs.start_offering_execution(
                    execution.id,
                    stage="acquisition",
                )
                await report(ProgressKind.OFFERING_STARTED, offering)
                try:
                    # Parents every stage span of this offering, so one run with
                    # several offerings stays readable as separate subtrees.
                    with tracer.start_as_current_span(
                        f"offering {offering.offering_id.value}"
                    ) as span:
                        span.set_attribute("tariff.run_id", str(run.id))
                        span.set_attribute("tariff.product", offering.product.value)
                        span.set_attribute(
                            "tariff.offering_id", offering.offering_id.value
                        )
                        result = await self._indexing.refresh(
                            offering,
                            run.id,
                            execution.id,
                            progress=tracker,
                        )
                except OfferingPipelineError as exc:
                    failed += 1
                    failure_codes.append(exc.failure_code)
                    logger.warning(
                        "offering failed run_id=%s offering_id=%s stage=%s code=%s"
                        " reason=%s",
                        run.id,
                        offering.offering_id.value,
                        exc.stage,
                        exc.failure_code,
                        exc.cause_reason or exc.cause_log_detail,
                    )
                    await self._runs.fail_offering_execution(
                        execution.id,
                        stage=exc.stage,
                        failure_code=exc.failure_code,
                        failure_detail=(
                            f"{exc.cause_type}:{exc.cause_reason}"
                            if exc.cause_reason
                            else exc.cause_detail
                        ),
                        audit_payload={
                            "stage": exc.stage,
                            "exception_type": exc.cause_type,
                            "detail": exc.cause_detail,
                            **(
                                {"reason": exc.cause_reason} if exc.cause_reason else {}
                            ),
                            **(
                                {"reasons": list(exc.cause_reasons)}
                                if exc.cause_reasons
                                else {}
                            ),
                        },
                    )
                    await report(
                        ProgressKind.OFFERING_FAILED,
                        offering,
                        stage=exc.stage,
                        failure_code=exc.failure_code,
                    )
                    continue
                except Exception as exc:
                    failed += 1
                    failure_codes.append(RunFailureCode.INTERNAL_ERROR.value)
                    await self._runs.fail_offering_execution(
                        execution.id,
                        stage="internal",
                        failure_code=RunFailureCode.INTERNAL_ERROR.value,
                        failure_detail=bounded_failure_detail(exc),
                        audit_payload={
                            "stage": "internal",
                            "exception_type": type(exc).__name__,
                            "detail": bounded_failure_detail(exc),
                        },
                    )
                    await report(
                        ProgressKind.OFFERING_FAILED,
                        offering,
                        stage="internal",
                        failure_code=RunFailureCode.INTERNAL_ERROR.value,
                    )
                    continue
                if result.publication.offering_status is OfferingRunStatus.SUCCEEDED:
                    succeeded += 1
                    await report(ProgressKind.OFFERING_SUCCEEDED, offering)
                else:
                    review_required += 1
                    if self._reviews is None:
                        raise RuntimeError(
                            "review repository is required for candidate data"
                        )
                    created = 0
                    for review in _review_tasks(result.snapshot):
                        persisted = await self._reviews.create(review)
                        review_ids.append(persisted.id)
                        created += 1
                    await report(
                        ProgressKind.OFFERING_REVIEW,
                        offering,
                        detail=f"{created} review{'s' if created != 1 else ''}",
                    )
                execution = None
        except asyncio.CancelledError:
            await self._cancel(
                run,
                execution_id=execution.id if execution is not None else None,
                stage=tracker.current_stage or "starting",
                summary={
                    "offering_count": len(offerings),
                    "succeeded": succeeded,
                    "review_required": review_required,
                    "failed": failed,
                    "review_ids": [str(review_id) for review_id in review_ids],
                },
            )
            raise

        total = len(offerings)
        summary = {
            "offering_count": total,
            "succeeded": succeeded,
            "review_required": review_required,
            "failed": failed,
            "review_ids": [str(review_id) for review_id in review_ids],
        }
        elapsed_ms = max(0, round((perf_counter() - started) * 1000))
        if review_required:
            paused = await self._runs.pause_for_review(run.id, summary=summary)
            await report(
                ProgressKind.RUN_FINISHED,
                elapsed_ms=elapsed_ms,
                detail=RunStatus.AWAITING_REVIEW.value,
            )
            return paused
        if succeeded == total:
            status = RunStatus.SUCCEEDED
        elif succeeded or review_required:
            status = RunStatus.PARTIAL_SUCCESS
        else:
            status = RunStatus.FAILED
        finished = await self._runs.finish(
            run.id,
            status,
            failure_code=(
                (
                    failure_codes[0]
                    if len(set(failure_codes)) == 1
                    else OfferingFailureCode.VALIDATION_FAILED.value
                )
                if status is RunStatus.FAILED
                else None
            ),
            summary=summary,
        )
        await report(
            ProgressKind.RUN_FINISHED,
            elapsed_ms=elapsed_ms,
            detail=status.value,
            failure_code=finished.failure_code,
        )
        return finished

    async def _cancel(
        self,
        run: MonitoringRun,
        *,
        execution_id: UUID | None,
        stage: str,
        summary: dict[str, object],
    ) -> None:
        """Close a cancelled run so nothing is left `running` behind the caller.

        Runs inside the cancelled task's `except CancelledError`, before the
        cancellation is re-raised. Each write is guarded: a cleanup failure is
        logged, never allowed to replace the cancellation.
        """
        code = RunFailureCode.CANCELLED.value
        logger.info("run cancelled run_id=%s stage=%s", run.id, stage)
        if execution_id is not None:
            try:
                await self._runs.fail_offering_execution(
                    execution_id,
                    stage=stage,
                    failure_code=code,
                    failure_detail="Cancelled by the caller",
                    audit_payload={"stage": stage, "reason": "cancelled"},
                )
            except Exception:
                logger.warning(
                    "could not fail cancelled offering execution %s",
                    execution_id,
                    exc_info=True,
                )
        try:
            await self._runs.finish(
                run.id,
                RunStatus.FAILED,
                failure_code=code,
                failure_detail="Cancelled by the caller",
                summary=summary,
            )
        except Exception:
            logger.warning("could not finish cancelled run %s", run.id, exc_info=True)
        try:
            await self._runs.record_audit(
                run.id,
                "run.cancelled",
                reason_code=code,
                payload={"stage": stage},
            )
        except Exception:
            logger.warning("could not audit cancelled run %s", run.id, exc_info=True)


class _StageTracker:
    """Forwards progress and remembers the stage in flight, for cancellation."""

    def __init__(self, sink: ProgressSink | None) -> None:
        self._sink = sink
        self.current_stage: str | None = None

    async def report(self, progress: PipelineProgress) -> None:
        if progress.kind is ProgressKind.STAGE_STARTED:
            self.current_stage = progress.stage
        await report_safely(self._sink, progress)


class LinkedDocumentUnavailable(ValueError):
    """Values the last accepted snapshot had are missing while a linked document
    could not be read; `reasons` are counts and names, never source text."""

    def __init__(self, documents: tuple[str, ...], fields: tuple[str, ...]) -> None:
        super().__init__("linked document unavailable")
        self.reasons = (
            f"{len(documents)} linked document(s) unavailable",
            "fields no longer found: " + ", ".join(fields),
        )


_UNREADABLE_PDF = frozenset(
    {
        NormalizationWarningCode.ARTIFACT_UNAVAILABLE,
        NormalizationWarningCode.PDF_MODEL_REQUIRED,
        NormalizationWarningCode.PDF_MODEL_FAILED,
    }
)


def _unavailable_linked_documents(
    artifact: PageArtifact, bundle: NormalizedSourceBundle
) -> tuple[str, ...]:
    """Linked documents this run could not download or read.

    A dead link (404) is not one: it is the same on every fetch.
    """
    failed = [
        warning.detail.split(":", 1)[0]
        for warning in artifact.warnings
        if warning.code is AcquisitionWarningCode.LINKED_DOCUMENT_FAILED
    ]
    failed.extend(
        warning.source_id
        for warning in bundle.warnings
        if warning.code in _UNREADABLE_PDF
    )
    return tuple(dict.fromkeys(item for item in failed if item))


def _fields_lost(previous, current) -> tuple[str, ...]:
    """Fields the previous accepted snapshot found that this one does not."""
    if previous is None:
        return ()
    before = tariff_fields(previous.normalized_tariff)
    after = tariff_fields(current.normalized_tariff)

    def found(value) -> bool:
        return isinstance(value, dict) and value.get("status") == "found"

    return tuple(
        name
        for name, value in sorted(before.items())
        if found(value) and not found(after.get(name))
    )


def _review_tasks(snapshot) -> tuple[ReviewTask, ...]:
    signals = snapshot.validation.get("review_signals", [])
    tasks: list[ReviewTask] = []
    for raw_signal in signals if isinstance(signals, list) else ():
        if not isinstance(raw_signal, dict):
            continue
        try:
            reason = ReviewReason(str(raw_signal["reason"]))
            issue_scope = str(raw_signal["issue_scope"])
        except (KeyError, ValueError):
            continue
        candidates: list[ReviewCandidate] = []
        raw_candidates = raw_signal.get("candidates", [])
        if isinstance(raw_candidates, list):
            for raw_candidate in raw_candidates:
                if not isinstance(raw_candidate, dict):
                    continue
                references = raw_candidate.get("evidence_references", [])
                if not isinstance(references, list) or not references:
                    continue
                candidates.append(
                    ReviewCandidate(
                        candidate_id=str(raw_candidate["candidate_id"]),
                        field=str(raw_signal.get("field", issue_scope)),
                        value=raw_candidate.get("value"),
                        evidence_references=tuple(str(item) for item in references),
                        conditions={
                            "source_type": raw_candidate.get("source_type"),
                            "quote": raw_candidate.get("quote"),
                            "conditions": raw_candidate.get("conditions", []),
                        },
                    )
                )
        # References, not a copy of the snapshot's evidence (RV7): the passages'
        # content is read from the snapshot, which never changes once created.
        evidence: dict[str, object] = {
            "set": _signal_evidence_set(snapshot, raw_signal)
        }
        for key in ("failed_checks", "proposed_value"):
            if raw_signal.get(key):
                evidence[key] = raw_signal[key]
        # A rate signal carries the jump it detected, and nothing else on the
        # review does: it has no candidates. Without this the reviewer is asked
        # to confirm a change without being told its size.
        if all(key in raw_signal for key in ("previous", "current")):
            evidence["rate_change"] = {
                "previous": str(raw_signal["previous"]),
                "current": str(raw_signal["current"]),
                "absolute_percentage_point_change": str(
                    raw_signal.get("absolute_percentage_point_change", "")
                ),
            }
        key = f"{snapshot.id}:{reason.value}:{issue_scope}"
        tasks.append(
            ReviewTask(
                id=uuid5(NAMESPACE_URL, key),
                idempotency_key=key,
                run_id=snapshot.run_id,
                offering_execution_id=snapshot.offering_execution_id,
                snapshot_id=snapshot.id,
                product=snapshot.product,
                offering_id=snapshot.offering_id,
                reason=reason,
                issue_scope=issue_scope,
                candidates=tuple(candidates),
                evidence=evidence,
                status=ReviewStatus.PENDING,
                created_at=snapshot.created_at,
                updated_at=snapshot.created_at,
            )
        )
    return tuple(tasks)


def _signal_evidence_set(snapshot, signal: dict) -> dict:
    """The signal's evidence set; a signal stored before sets existed gets one
    from its references (RV4)."""
    raw = signal.get("evidence_set")
    if isinstance(raw, dict):
        return raw
    references = signal.get("evidence_references")
    return cited_evidence_set(
        evidence_items(snapshot.evidence),
        [str(item) for item in references] if isinstance(references, list) else [],
        why="cited",
    ).model_dump(mode="json")


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
