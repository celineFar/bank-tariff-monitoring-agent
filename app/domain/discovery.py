from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.crawl import (
    CrawlIssue,
    CrawlStatus,
    ProductCategory,
    ProductSourceInventory,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INGESTION_NAMESPACE = UUID("c6ee138f-1718-4969-bbb2-83607526f39b")


class DiscoveryModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class SourceCandidateType(StrEnum):
    PRODUCT_PAGE = "product_page"
    SUPPORTING_PAGE = "supporting_page"
    DOCUMENT = "document"
    PAGE = "page"


class DiscoveryOrigin(StrEnum):
    REGISTRY = "registry"
    PAGE_LINK = "page_link"
    SITEMAP = "sitemap"


class CandidateRetrievalStatus(StrEnum):
    RETRIEVED = "retrieved"
    NOT_RETRIEVED = "not_retrieved"
    FAILED = "failed"


class SourceCandidate(DiscoveryModel):
    product_id: str = Field(min_length=1, max_length=100)
    candidate_type: SourceCandidateType
    origin: DiscoveryOrigin
    original_url: str = Field(min_length=1, max_length=4000)
    normalized_url: str = Field(min_length=1, max_length=4000)
    discovery_path: tuple[str, ...] = Field(min_length=1)
    anchor_text: str | None = Field(default=None, max_length=1000)
    title: str | None = Field(default=None, max_length=1000)
    context: str | None = Field(default=None, max_length=2000)
    match_signals: tuple[str, ...] = Field(min_length=1)
    retrieval_status: CandidateRetrievalStatus
    status_code: int | None = None
    content_sha256: str | None = None
    mime_type: str | None = None

    @field_validator("content_sha256")
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("content_sha256 must be a lowercase SHA-256 hex digest")
        return normalized

    @model_validator(mode="after")
    def validate_retrieval_metadata(self) -> SourceCandidate:
        retrieved = self.retrieval_status is CandidateRetrievalStatus.RETRIEVED
        if retrieved and (self.content_sha256 is None or self.mime_type is None):
            raise ValueError("retrieved candidates require checksum and MIME type")
        if not retrieved and (
            self.content_sha256 is not None or self.mime_type is not None
        ):
            raise ValueError("unretrieved candidates cannot reference content")
        return self


class ProductDiscoveryResult(DiscoveryModel):
    product_id: str
    product_name: str
    category: ProductCategory
    candidates: tuple[SourceCandidate, ...]
    inventory: ProductSourceInventory = Field(repr=False)
    warnings: tuple[CrawlIssue, ...] = ()
    errors: tuple[CrawlIssue, ...] = ()


class OfficialSourceDiscoveryRun(DiscoveryModel):
    started_at: datetime
    completed_at: datetime
    products: tuple[ProductDiscoveryResult, ...]
    sitemap_urls_retrieved: tuple[str, ...] = ()
    warnings: tuple[CrawlIssue, ...] = ()


class StoredArtifact(DiscoveryModel):
    storage_key: str = Field(min_length=1, max_length=1000)
    sha256: str
    mime_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)
    created: bool

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("sha256 must be a lowercase SHA-256 hex digest")
        return normalized


class IngestedSource(DiscoveryModel):
    product_id: str
    candidate_type: SourceCandidateType
    source_url: str
    final_url: str
    language: str | None = None
    referrer_urls: tuple[str, ...] = ()
    retrieved_at: datetime
    artifact: StoredArtifact


class IngestedProduct(DiscoveryModel):
    product_id: str
    product_name: str
    category: ProductCategory
    crawl_status: CrawlStatus
    candidate_count: int = Field(ge=0)
    stored_source_count: int = Field(ge=0)
    warnings: tuple[CrawlIssue, ...] = ()
    errors: tuple[CrawlIssue, ...] = ()


class SourceIngestionResult(DiscoveryModel):
    run_id: UUID
    monitoring_run_id: UUID | None = None
    started_at: datetime
    completed_at: datetime
    manifest_key: str
    products: tuple[IngestedProduct, ...]
    sources: tuple[IngestedSource, ...]
    candidates: tuple[SourceCandidate, ...]
    warnings: tuple[CrawlIssue, ...] = ()

    @model_validator(mode="after")
    def validate_persisted_content_references(self) -> SourceIngestionResult:
        artifact_hashes = {source.artifact.sha256 for source in self.sources}
        missing = {
            candidate.content_sha256
            for candidate in self.candidates
            if candidate.retrieval_status is CandidateRetrievalStatus.RETRIEVED
            and candidate.content_sha256 not in artifact_hashes
        }
        if missing:
            raise ValueError(
                "retrieved candidates must reference artifacts stored by this ingestion"
            )
        return self


class IngestionWriteResult(DiscoveryModel):
    run_id: UUID
    artifacts_created: int = Field(ge=0)
    artifacts_reused: int = Field(ge=0)
    products_upserted: int = Field(ge=0)
    candidates_upserted: int = Field(ge=0)
    origins_upserted: int = Field(ge=0)


class IngestionRunSummary(DiscoveryModel):
    run_id: UUID
    monitoring_run_id: UUID | None = None
    status: CrawlStatus
    manifest_key: str
    started_at: datetime
    completed_at: datetime
    product_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)


class PersistedArtifact(DiscoveryModel):
    artifact_id: UUID
    storage_key: str
    sha256: str
    mime_type: str
    size_bytes: int = Field(gt=0)
    first_seen_at: datetime
    last_seen_at: datetime


class PersistedSourceOrigin(DiscoveryModel):
    ingestion_run_id: UUID
    artifact_id: UUID
    product_id: str
    candidate_type: SourceCandidateType
    source_url: str
    final_url: str
    language: str | None = None
    referrer_urls: tuple[str, ...] = ()
    retrieved_at: datetime
    artifact: PersistedArtifact


def source_artifact_id(content_sha256: str) -> UUID:
    normalized = content_sha256.casefold()
    if not _SHA256.fullmatch(normalized):
        raise ValueError("content_sha256 must be a lowercase SHA-256 hex digest")
    return uuid5(_INGESTION_NAMESPACE, f"artifact\x1f{normalized}")


def source_candidate_id(run_id: UUID, candidate: SourceCandidate) -> UUID:
    identity = "\x1f".join(
        (
            "candidate",
            str(run_id),
            candidate.product_id,
            candidate.normalized_url,
            candidate.candidate_type.value,
        )
    )
    return uuid5(_INGESTION_NAMESPACE, identity)


def source_origin_id(run_id: UUID, source: IngestedSource) -> UUID:
    identity = "\x1f".join(
        (
            "origin",
            str(run_id),
            source.product_id,
            source.artifact.sha256,
            source.source_url,
            source.final_url,
        )
    )
    return uuid5(_INGESTION_NAMESPACE, identity)
