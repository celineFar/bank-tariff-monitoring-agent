from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AcquisitionModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class SourceType(StrEnum):
    PAGE = "page"
    PDF = "pdf"
    API = "api"
    LINKED_DOCUMENT = "linked_document"


class ContentBlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    KEY_VALUE = "key_value"
    TABLE = "table"
    ACCORDION = "accordion"
    CARD = "card"
    LINK = "link"
    OTHER = "other"


class AcquisitionMode(StrEnum):
    STATIC = "static"
    BROWSER = "browser"


class SourceLocator(AcquisitionModel):
    source_url: HttpUrl
    source_type: SourceType
    block_id: str | None = None
    css_selector: str | None = None
    xpath: str | None = None
    pdf_page: int | None = Field(default=None, ge=1)
    json_path: str | None = None


class ContentBlock(AcquisitionModel):
    id: str = Field(min_length=1, max_length=100)
    type: ContentBlockType
    text: str = Field(min_length=1)
    markdown: str | None = None
    heading_path: tuple[str, ...] = ()
    parent_id: str | None = None
    link_ids: tuple[str, ...] = ()
    locator: SourceLocator
    visible: bool


class TableCellArtifact(AcquisitionModel):
    id: str = Field(min_length=1, max_length=100)
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    rowspan: int = Field(default=1, ge=1)
    colspan: int = Field(default=1, ge=1)
    tag: str = Field(pattern=r"^(td|th)$")
    is_header: bool = False
    text: str
    markdown: str
    link_ids: tuple[str, ...] = ()
    locator: SourceLocator


class TableArtifact(AcquisitionModel):
    id: str = Field(min_length=1, max_length=100)
    caption: str | None = None
    title: str | None = None
    column_count: int = Field(default=0, ge=0)
    headers: tuple[str, ...] = ()
    markdown_headers: tuple[str, ...] = ()
    headers_inferred: bool = False
    rows: tuple[tuple[str, ...], ...] = ()
    markdown_rows: tuple[tuple[str, ...], ...] = ()
    notes: tuple[str, ...] = ()
    markdown_notes: tuple[str, ...] = ()
    cells: tuple[TableCellArtifact, ...] = ()
    locator: SourceLocator


class LinkArtifact(AcquisitionModel):
    id: str = Field(min_length=1, max_length=100)
    url: HttpUrl
    text: str = ""
    title: str | None = None
    rel: tuple[str, ...] = ()
    declared_mime_type: str | None = None
    same_allowlisted_source: bool
    downloadable: bool
    locator: SourceLocator


class ImageArtifact(AcquisitionModel):
    id: str = Field(min_length=1, max_length=100)
    url: HttpUrl
    alt: str = ""
    title: str | None = None
    width: str | None = None
    height: str | None = None
    same_allowlisted_source: bool
    decorative: bool
    locator: SourceLocator


class InteractiveControlArtifact(AcquisitionModel):
    id: str = Field(min_length=1, max_length=100)
    element: str = Field(min_length=1, max_length=50)
    role: str | None = None
    text: str = ""
    aria_label: str | None = None
    aria_expanded: bool | None = None
    aria_controls: str | None = None
    disabled: bool = False
    locator: SourceLocator


class StoredArtifact(AcquisitionModel):
    role: str = Field(min_length=1, max_length=100)
    sha256: str
    size_bytes: int = Field(ge=0)
    media_type: str = Field(min_length=1, max_length=255)
    relative_path: str = Field(min_length=1)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("sha256 must be a lowercase SHA-256 hex digest")
        return normalized


class DocumentArtifact(AcquisitionModel):
    source_url: HttpUrl
    final_url: HttpUrl
    document_name: str = Field(min_length=1, max_length=1000)
    mime_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=1)
    sha256: str
    retrieved_at: datetime
    artifact: StoredArtifact

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("sha256 must be a lowercase SHA-256 hex digest")
        return normalized


class NetworkPayload(AcquisitionModel):
    url: HttpUrl
    method: str = Field(min_length=1, max_length=20)
    status_code: int = Field(ge=100, le=599)
    mime_type: str = Field(min_length=1, max_length=255)
    body_text: str
    size_bytes: int = Field(ge=0)
    sha256: str
    retrieved_at: datetime
    locator: SourceLocator
    artifact: StoredArtifact | None = None

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("sha256 must be a lowercase SHA-256 hex digest")
        return normalized


class PageArtifact(AcquisitionModel):
    url: HttpUrl
    canonical_url: HttpUrl
    final_url: HttpUrl
    title: str | None = None
    language: str | None = None
    acquisition_mode: AcquisitionMode
    raw_html: str | None
    rendered_html: str | None
    markdown: str | None
    blocks: tuple[ContentBlock, ...]
    tables: tuple[TableArtifact, ...]
    links: tuple[LinkArtifact, ...]
    images: tuple[ImageArtifact, ...] = ()
    interactive_controls: tuple[InteractiveControlArtifact, ...] = ()
    downloadable_documents: tuple[DocumentArtifact, ...]
    network_payloads: tuple[NetworkPayload, ...]
    stored_artifacts: tuple[StoredArtifact, ...] = ()
    warnings: tuple[str, ...] = ()
    retrieved_at: datetime
    content_hash: str

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("content_hash must be a lowercase SHA-256 hex digest")
        return normalized
