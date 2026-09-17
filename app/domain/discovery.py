from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.crawl import CrawlIssue, ProductCategory, ProductSourceInventory

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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
    artifact: StoredArtifact


class SourceIngestionResult(DiscoveryModel):
    run_id: UUID
    started_at: datetime
    completed_at: datetime
    manifest_key: str
    sources: tuple[IngestedSource, ...]
    candidates: tuple[SourceCandidate, ...]
    warnings: tuple[CrawlIssue, ...] = ()
