from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CrawlModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ProductCategory(StrEnum):
    CONSUMER = "consumer"
    MORTGAGE = "mortgage"


class CrawlStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class CrawlLinkType(StrEnum):
    DOCUMENT = "document"
    SUPPORTING_PAGE = "supporting_page"
    LANGUAGE_VARIANT = "language_variant"
    EXTERNAL = "external"
    IGNORE = "ignore"


class LinkOrigin(StrEnum):
    ATTRIBUTE = "attribute"
    DATA_ATTRIBUTE = "data_attribute"
    INLINE_SCRIPT = "inline_script"


class PageSourceType(StrEnum):
    PRODUCT_PAGE = "product_page"
    SUPPORTING_PAGE = "supporting_page"


class ProductSeed(CrawlModel):
    product_id: str = Field(min_length=1, max_length=100)
    category: ProductCategory
    name: str = Field(min_length=1, max_length=250)
    url_en: HttpUrl
    aliases: tuple[str, ...] = ()


class DiscoveredLink(CrawlModel):
    original_url: str = Field(min_length=1, max_length=4000)
    normalized_url: str = Field(min_length=1, max_length=4000)
    referrer_url: str = Field(min_length=1, max_length=4000)
    tag: str = Field(min_length=1, max_length=30)
    attribute: str = Field(min_length=1, max_length=30)
    anchor_text: str | None = Field(default=None, max_length=1000)
    context: str | None = Field(default=None, max_length=2000)
    origin: LinkOrigin
    in_main_content: bool
    classification: CrawlLinkType = CrawlLinkType.IGNORE
    classification_reason: str = Field(default="unclassified", max_length=250)


class PageResource(CrawlModel):
    source_type: PageSourceType
    source_url: str
    final_url: str
    canonical_url: str
    title: str | None
    language: str | None
    status_code: int = 200
    size_bytes: int = Field(ge=0)
    sha256: str
    retrieved_at: datetime
    referrer_url: str | None = None
    discovered_url: str | None = None
    content: bytes = Field(repr=False)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("sha256 must be a lowercase SHA-256 hex digest")
        return normalized


class DocumentResource(CrawlModel):
    sha256: str
    original_urls: tuple[str, ...] = Field(min_length=1)
    urls: tuple[str, ...] = Field(min_length=1)
    final_url: str
    referrer_urls: tuple[str, ...] = Field(min_length=1)
    content_type: str
    size_bytes: int = Field(gt=0)
    retrieved_at: datetime
    anchor_texts: tuple[str, ...] = ()
    contexts: tuple[str, ...] = ()
    language_hints: tuple[str, ...] = ()
    content: bytes = Field(repr=False)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("sha256 must be a lowercase SHA-256 hex digest")
        return normalized


class ExternalReference(CrawlModel):
    original_url: str
    url: str
    referrer_url: str
    anchor_text: str | None = None


class CalculatorReference(CrawlModel):
    original_url: str
    url: str
    referrer_url: str
    anchor_text: str | None = None


class CrawlIssue(CrawlModel):
    reason: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)
    url: str | None = None
    status_code: int | None = None


class ProductSourceInventory(CrawlModel):
    product_id: str
    product_name: str
    category: ProductCategory
    status: CrawlStatus
    product_page_en: PageResource | None = None
    product_page_hy: PageResource | None = None
    supporting_pages: tuple[PageResource, ...] = ()
    documents: tuple[DocumentResource, ...] = ()
    calculators: tuple[CalculatorReference, ...] = ()
    external_references: tuple[ExternalReference, ...] = ()
    warnings: tuple[CrawlIssue, ...] = ()
    errors: tuple[CrawlIssue, ...] = ()


class CrawlRunResult(CrawlModel):
    started_at: datetime
    completed_at: datetime
    inventories: tuple[ProductSourceInventory, ...]
