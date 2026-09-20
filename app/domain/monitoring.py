from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    field_validator,
    model_validator,
)

from app.domain.knowledge import EmbeddedKnowledgeDocument, IndexWriteResult
from app.domain.models import OfferingId, ProductType


class MonitoringModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class RunTrigger(StrEnum):
    API = "api"
    SCHEDULE = "schedule"
    ADK = "adk"
    USER = "user"  # Backwards-compatible value used by the initial migration.


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    SUCCEEDED = "succeeded"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {
            RunStatus.SUCCEEDED,
            RunStatus.PARTIAL_SUCCESS,
            RunStatus.FAILED,
        }


class OfferingRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    CANDIDATE_REVIEW = "candidate_review"
    FAILED = "failed"


class SnapshotStatus(StrEnum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


class ManifestItemStatus(StrEnum):
    INDEXED = "indexed"
    UNCHANGED = "unchanged"
    EXCLUDED = "excluded"
    FAILED = "failed"


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    AMBIGUOUS_PRODUCT = "ambiguous_product"


class RunFailureCode(StrEnum):
    ACTIVE_RUN_EXISTS = "run.active_run_exists"
    IDEMPOTENCY_REUSED = "run.idempotency_reused"
    CLAIM_CONFLICT = "run.claim_conflict"
    INVALID_TRANSITION = "run.invalid_transition"
    PERSISTENCE_FAILED = "run.persistence_failed"
    INTERNAL_ERROR = "run.internal_error"


class OfferingFailureCode(StrEnum):
    NOT_CONFIGURED = "offering.not_configured"
    ACQUISITION_FAILED = "offering.acquisition_failed"
    NORMALIZATION_FAILED = "offering.normalization_failed"
    SOURCE_DISCOVERY_FAILED = "offering.source_discovery_failed"
    SEMANTIC_EXTRACTION_FAILED = "offering.semantic_extraction_failed"
    VALIDATION_FAILED = "offering.validation_failed"


class SourceFailureCode(StrEnum):
    URL_REJECTED = "source.url_rejected"
    TIMEOUT = "source.timeout"
    TRANSPORT = "source.transport"
    HTTP_STATUS = "source.http_status"
    NOT_FOUND = "source.not_found"
    MIME_REJECTED = "source.mime_rejected"
    SIZE_REJECTED = "source.size_rejected"
    REDIRECT_REJECTED = "source.redirect_rejected"
    SIGNATURE_REJECTED = "source.signature_rejected"
    PARSING_FAILED = "source.parsing_failed"
    PDF_EXTRACTION_FAILED = "source.pdf_extraction_failed"
    MODEL_FAILED = "source.model_failed"
    MALFORMED_STRUCTURED_OUTPUT = "source.malformed_structured_output"
    VALIDATION_FAILED = "source.validation_failed"


class IndexingFailureCode(StrEnum):
    INVALID_DOCUMENT = "indexing.invalid_document"
    EMBEDDING_FAILED = "indexing.embedding_failed"
    PUBLICATION_FAILED = "indexing.publication_failed"


class SnapshotFailureCode(StrEnum):
    INVALID_SCHEMA = "snapshot.invalid_schema"
    MISSING_EVIDENCE = "snapshot.missing_evidence"
    CONFLICTING_VALUES = "snapshot.conflicting_values"
    REVIEW_REQUIRED = "snapshot.review_required"
    PUBLICATION_FAILED = "snapshot.publication_failed"


class AnswerFailureCode(StrEnum):
    AMBIGUOUS_PRODUCT = "answer.ambiguous_product"
    INSUFFICIENT_EVIDENCE = "answer.insufficient_evidence"
    INVALID_CITATION = "answer.invalid_citation"
    GENERATION_FAILED = "answer.generation_failed"


FailureCode = (
    RunFailureCode
    | OfferingFailureCode
    | SourceFailureCode
    | IndexingFailureCode
    | SnapshotFailureCode
    | AnswerFailureCode
)


def validate_offering_product(
    product: ProductType, offering_id: OfferingId | None
) -> None:
    if offering_id is not None and offering_id.product is not product:
        raise ValueError(
            f"offering {offering_id.value} does not belong to {product.value}"
        )


class RunCommand(MonitoringModel):
    product: ProductType
    offering_id: OfferingId | None = None
    trigger: RunTrigger
    query: str | None = Field(default=None, min_length=2, max_length=500)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError(
                "query must contain at least two non-whitespace characters"
            )
        return normalized

    @model_validator(mode="after")
    def validate_scope(self) -> RunCommand:
        validate_offering_product(self.product, self.offering_id)
        return self


class MonitoringRun(MonitoringModel):
    id: UUID
    command: RunCommand
    status: RunStatus
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure_code: str | None = Field(default=None, max_length=100)
    failure_detail: str | None = Field(default=None, max_length=2000)
    summary: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("queued_at", "started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("run timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_lifecycle(self) -> MonitoringRun:
        if self.status in {RunStatus.RUNNING, RunStatus.AWAITING_REVIEW} and (
            self.started_at is None
        ):
            raise ValueError("running or review-waiting run requires started_at")
        if self.status.is_terminal and self.completed_at is None:
            raise ValueError("terminal run requires completed_at")
        if self.started_at is not None and self.started_at < self.queued_at:
            raise ValueError("started_at must not precede queued_at")
        if (
            self.completed_at is not None
            and self.started_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at must not precede started_at")
        return self


class RunSubmissionResult(MonitoringModel):
    run: MonitoringRun
    created: bool
    reused_reason: RunFailureCode | None = None


class ClaimedRun(MonitoringModel):
    run: MonitoringRun
    worker_id: str = Field(min_length=1, max_length=200)


class OfferingExecution(MonitoringModel):
    id: UUID
    run_id: UUID
    product: ProductType
    offering_id: OfferingId
    status: OfferingRunStatus
    current_stage: str | None = Field(default=None, max_length=100)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    source_count: int = Field(default=0, ge=0)
    document_count: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    review_count: int = Field(default=0, ge=0)
    failure_code: str | None = Field(default=None, max_length=100)
    failure_detail: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_scope(self) -> OfferingExecution:
        validate_offering_product(self.product, self.offering_id)
        return self


class SourceManifestItem(MonitoringModel):
    id: UUID
    run_id: UUID
    offering_execution_id: UUID
    product: ProductType
    offering_id: OfferingId
    source_url: HttpUrl
    final_url: HttpUrl | None = None
    document_key: str | None = Field(default=None, max_length=500)
    document_id: UUID | None = None
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    status: ManifestItemStatus
    selected: bool = False
    reason_code: str | None = Field(default=None, max_length=100)
    warning_codes: tuple[str, ...] = ()
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scope(self) -> SourceManifestItem:
        validate_offering_product(self.product, self.offering_id)
        return self


class SnapshotAttempt(MonitoringModel):
    id: UUID
    run_id: UUID
    offering_execution_id: UUID
    bank: str = Field(default="ameria", min_length=1, max_length=100)
    product: ProductType
    offering_id: OfferingId
    status: SnapshotStatus
    normalized_tariff: dict[str, JsonValue]
    evidence: tuple[dict[str, JsonValue], ...] = ()
    semantic_extraction: dict[str, JsonValue] = Field(default_factory=dict)
    validation: dict[str, JsonValue] = Field(default_factory=dict)
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_accepted_snapshot_id: UUID | None = None
    created_at: datetime
    accepted_at: datetime | None = None

    @model_validator(mode="after")
    def validate_state(self) -> SnapshotAttempt:
        validate_offering_product(self.product, self.offering_id)
        if self.status is SnapshotStatus.ACCEPTED and self.accepted_at is None:
            raise ValueError("accepted snapshot requires accepted_at")
        if self.status is not SnapshotStatus.ACCEPTED and self.accepted_at is not None:
            raise ValueError("only an accepted snapshot may have accepted_at")
        return self


class SnapshotChange(MonitoringModel):
    field: str = Field(min_length=1, max_length=200)
    previous: JsonValue = None
    current: JsonValue = None
    previous_display: str | None = Field(default=None, max_length=2000)
    current_display: str | None = Field(default=None, max_length=2000)
    previous_evidence: tuple[dict[str, JsonValue], ...] = ()
    current_evidence: tuple[dict[str, JsonValue], ...] = ()


class SnapshotChangeSet(MonitoringModel):
    id: UUID
    run_id: UUID
    product: ProductType
    offering_id: OfferingId
    previous_snapshot_id: UUID | None = None
    current_snapshot_id: UUID
    changes: tuple[SnapshotChange, ...]
    created_at: datetime

    @model_validator(mode="after")
    def validate_scope(self) -> SnapshotChangeSet:
        validate_offering_product(self.product, self.offering_id)
        return self


class OfferingPublication(MonitoringModel):
    offering_execution_id: UUID
    documents: tuple[EmbeddedKnowledgeDocument, ...]
    snapshot: SnapshotAttempt
    changes: SnapshotChangeSet | None = None
    manifests: tuple[SourceManifestItem, ...] = ()
    audit_metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_publication(self) -> OfferingPublication:
        if self.snapshot.offering_execution_id != self.offering_execution_id:
            raise ValueError("snapshot belongs to a different offering execution")
        for document in self.documents:
            if document.run_id != self.snapshot.run_id:
                raise ValueError("document belongs to a different run")
            if document.product is not self.snapshot.product:
                raise ValueError("document belongs to a different product")
            if document.offering_id is not self.snapshot.offering_id:
                raise ValueError("document belongs to a different offering")
        for manifest in self.manifests:
            if (
                manifest.run_id != self.snapshot.run_id
                or manifest.offering_execution_id != self.offering_execution_id
                or manifest.product is not self.snapshot.product
                or manifest.offering_id is not self.snapshot.offering_id
            ):
                raise ValueError("manifest belongs to a different publication")
        if self.changes is not None:
            if self.snapshot.status is not SnapshotStatus.ACCEPTED:
                raise ValueError("only accepted snapshots may publish changes")
            if (
                self.changes.run_id != self.snapshot.run_id
                or self.changes.current_snapshot_id != self.snapshot.id
                or self.changes.product is not self.snapshot.product
                or self.changes.offering_id is not self.snapshot.offering_id
            ):
                raise ValueError("change set belongs to a different publication")
        return self


class PublicationResult(MonitoringModel):
    snapshot_id: UUID
    document_results: tuple[IndexWriteResult, ...]
    offering_status: OfferingRunStatus


class AnswerCitation(MonitoringModel):
    chunk_id: str = Field(min_length=1, max_length=200)
    evidence_id: str | None = Field(default=None, max_length=200)
    source_url: HttpUrl
    document_name: str = Field(min_length=1, max_length=1000)
    excerpt: str = Field(min_length=1, max_length=1500)
    page: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, max_length=500)


class QuestionCommand(MonitoringModel):
    query: str = Field(min_length=2, max_length=1000)
    product: ProductType | None = None
    offering_id: OfferingId | None = None

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError(
                "query must contain at least two non-whitespace characters"
            )
        return normalized

    @model_validator(mode="after")
    def validate_scope(self) -> QuestionCommand:
        if self.offering_id is not None and self.product is None:
            raise ValueError("offering_id requires product")
        if self.product is not None:
            validate_offering_product(self.product, self.offering_id)
        return self


class AnswerResult(MonitoringModel):
    status: AnswerStatus
    answer: str | None = Field(default=None, max_length=20_000)
    product: ProductType | None = None
    offering_id: OfferingId | None = None
    citations: tuple[AnswerCitation, ...] = ()
    as_of: datetime | None = None
    failure_code: AnswerFailureCode | None = None
    audit_metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_result(self) -> AnswerResult:
        if self.product is not None:
            validate_offering_product(self.product, self.offering_id)
        if self.status is AnswerStatus.ANSWERED:
            if not self.answer or not self.citations or self.as_of is None:
                raise ValueError(
                    "answered result requires answer, citations, and as_of"
                )
            if self.failure_code is not None:
                raise ValueError("answered result cannot contain a failure code")
        elif self.answer is not None or self.citations:
            raise ValueError("non-answered result cannot contain answer or citations")
        return self


def json_payload(value: BaseModel | dict[str, Any]) -> dict[str, JsonValue]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value
