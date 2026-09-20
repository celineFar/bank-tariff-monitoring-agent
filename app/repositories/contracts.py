from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.knowledge import (
    DocumentVersionSummary,
    EmbeddedKnowledgeDocument,
    IndexWriteResult,
)
from app.domain.models import (
    KnowledgeDocumentKind,
    OfferingId,
    ProductType,
    TariffSnapshot,
)
from app.domain.monitoring import (
    ClaimedRun,
    MonitoringRun,
    OfferingExecution,
    OfferingPublication,
    PublicationResult,
    RunCommand,
    RunStatus,
    RunSubmissionResult,
    SnapshotAttempt,
    SnapshotChangeSet,
)
from app.domain.pdf_extraction import PdfExtractionResponse
from app.domain.retrieval import RetrievalCandidate
from app.domain.semantic_extraction import ExtractionBatchResponse
from app.domain.source_discovery import SourceAssessment


class SnapshotRepository(Protocol):
    async def get_latest(self, product: ProductType) -> TariffSnapshot | None: ...
    async def save(self, snapshot: TariffSnapshot) -> UUID: ...


class RunRepository(Protocol):
    async def submit(
        self, command: RunCommand, *, idempotency_key: str | None = None
    ) -> RunSubmissionResult: ...

    async def get(self, run_id: UUID) -> MonitoringRun | None: ...

    async def claim_next(self, worker_id: str) -> ClaimedRun | None: ...

    async def recover_abandoned(self, *, before: datetime) -> int: ...

    async def finish(
        self,
        run_id: UUID,
        status: RunStatus,
        *,
        failure_code: str | None = None,
        failure_detail: str | None = None,
        summary: dict[str, object] | None = None,
    ) -> MonitoringRun: ...

    async def create_offering_execution(
        self,
        run_id: UUID,
        product: ProductType,
        offering_id: OfferingId,
    ) -> OfferingExecution: ...

    async def start_offering_execution(
        self, offering_execution_id: UUID, *, stage: str = "starting"
    ) -> OfferingExecution: ...

    async def fail_offering_execution(
        self,
        offering_execution_id: UUID,
        *,
        stage: str,
        failure_code: str,
        failure_detail: str | None = None,
        audit_payload: dict[str, object] | None = None,
    ) -> OfferingExecution: ...


class MonitoringSnapshotRepository(Protocol):
    async def save_attempt(self, snapshot: SnapshotAttempt) -> UUID: ...

    async def get_latest_accepted(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_id: OfferingId,
        before_run_id: UUID | None = None,
    ) -> SnapshotAttempt | None: ...

    async def save_changes(self, changes: SnapshotChangeSet) -> UUID: ...

    async def list_latest_accepted(
        self,
        *,
        bank: str,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
    ) -> tuple[SnapshotAttempt, ...]: ...

    async def has_newer_pending_review(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_id: OfferingId,
        accepted_at: datetime | None,
    ) -> bool: ...

    async def list_accepted_history(
        self,
        *,
        bank: str,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int,
    ) -> tuple[SnapshotAttempt, ...]: ...

    async def list_changes(
        self,
        *,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int,
    ) -> tuple[SnapshotChangeSet, ...]: ...

    async def get_latest_change_before(
        self,
        *,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
        before: datetime,
    ) -> SnapshotChangeSet | None: ...


class OfferingPublicationRepository(Protocol):
    async def publish(self, publication: OfferingPublication) -> PublicationResult: ...


class ReviewRepository(Protocol):
    async def create(self, run_id: UUID, reason: str, evidence: dict) -> UUID: ...
    async def decide(
        self, review_id: UUID, decision: str, reviewer: str, comment: str | None
    ) -> None: ...


class KnowledgeStoreRepository(Protocol):
    async def upsert_document(
        self, document: EmbeddedKnowledgeDocument
    ) -> IndexWriteResult: ...

    async def list_document_versions(
        self, bank: str, product: ProductType, document_key: str
    ) -> tuple[DocumentVersionSummary, ...]: ...


class HybridRetrievalRepository(Protocol):
    async def search_candidates(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_id: OfferingId | None,
        document_kinds: Sequence[KnowledgeDocumentKind],
        lexical_query: str,
        query_embedding: Sequence[float],
        limit: int,
    ) -> Sequence[RetrievalCandidate]: ...


class SourceDiscoveryRepository(Protocol):
    async def get_exact(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]: ...

    async def get_structural_priors(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        structural_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]: ...

    async def save(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        assessments: Sequence[SourceAssessment],
    ) -> None: ...


class PdfExtractionRepository(Protocol):
    async def get_exact(
        self,
        *,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
    ) -> PdfExtractionResponse | None: ...

    async def save(
        self,
        *,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
        response: PdfExtractionResponse,
    ) -> None: ...


class SemanticExtractionRepository(Protocol):
    async def get_exact(
        self,
        *,
        product: ProductType,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        fingerprints: Sequence[str],
    ) -> dict[str, ExtractionBatchResponse]: ...

    async def save(
        self,
        *,
        product: ProductType,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        values: Sequence[tuple[str, ExtractionBatchResponse]],
    ) -> None: ...
