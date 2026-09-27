from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from uuid import UUID, uuid5

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    field_validator,
    model_validator,
)

from app.domain.models import KnowledgeDocumentKind, OfferingId, ProductType

EMBEDDING_DIMENSIONS = 768
# Part of every document version's identity (IX2): bump it when the projection
# (chunking, rendering, chunk metadata) changes, so the next run stores new
# versions instead of reusing rows projected by the old code.
PROJECTION_SCHEMA_VERSION = "2"
_KNOWLEDGE_NAMESPACE = UUID("8f7205ab-684c-4f2e-a183-e1f14c3bd3ec")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class KnowledgeChunk(KnowledgeModel):
    ordinal: int = Field(ge=0)
    content: str = Field(min_length=1)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, max_length=500)
    language: str = Field(min_length=2, max_length=35)
    extraction_method: str = Field(min_length=1, max_length=100)
    quality_score: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("content", "language", "extraction_method")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("section")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_page_range(self) -> KnowledgeChunk:
        if self.page_end is not None and self.page_start is None:
            raise ValueError("page_end requires page_start")
        if (
            self.page_start is not None
            and self.page_end is not None
            and self.page_end < self.page_start
        ):
            raise ValueError("page_end must not precede page_start")
        return self


class KnowledgeDocument(KnowledgeModel):
    run_id: UUID
    bank: str = Field(default="ameria", min_length=1, max_length=100)
    product: ProductType
    offering_id: OfferingId | None = None
    document_kind: KnowledgeDocumentKind = KnowledgeDocumentKind.SOURCE
    document_key: str = Field(min_length=1, max_length=500)
    document_name: str = Field(min_length=1, max_length=1000)
    source_url: HttpUrl
    final_url: HttpUrl
    mime_type: str = Field(min_length=1, max_length=255)
    content_sha256: str
    retrieved_at: datetime
    extraction_method: str = Field(min_length=1, max_length=100)
    quality_score: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    chunks: tuple[KnowledgeChunk, ...] = Field(min_length=1)

    @field_validator(
        "bank",
        "document_key",
        "document_name",
        "mime_type",
        "extraction_method",
    )
    @classmethod
    def strip_document_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("content_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("content_sha256 must be a lowercase SHA-256 hex digest")
        return normalized

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_unique_chunk_locations(self) -> KnowledgeDocument:
        ordinals = [chunk.ordinal for chunk in self.chunks]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("chunk ordinals must be unique within a document")
        return self

    @property
    def projection_sha256(self) -> str:
        """Hash of the projected chunks, with the schema version.

        `content_sha256` is the raw source; this is what the index holds. The
        same bytes projected into other chunks -- another discovery selection,
        other labels, newer projection code -- are another version (IX2).
        """
        payload = {
            "schema": PROJECTION_SCHEMA_VERSION,
            "chunks": [chunk.model_dump(mode="json") for chunk in self.chunks],
        }
        return hashlib.sha256(
            json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
        ).hexdigest()


class IndexWriteResult(KnowledgeModel):
    document_id: UUID
    document_created: bool
    chunks_created: int = Field(ge=0)
    chunks_updated: int = Field(ge=0)
    chunks_retired: int = Field(ge=0)
    versions_retired: int = Field(ge=0)


def document_version_id(document: KnowledgeDocument) -> UUID:
    """One version: one projection of one source's bytes, for one offering."""
    identity = "\x1f".join(
        (
            document.bank.lower(),
            document.product.value,
            document.offering_id.value if document.offering_id else "",
            document.document_kind.value,
            document.document_key,
            document.content_sha256,
            document.projection_sha256,
        )
    )
    return uuid5(_KNOWLEDGE_NAMESPACE, identity)


def chunk_id(document: KnowledgeDocument, chunk: KnowledgeChunk) -> str:
    """A chunk is its version's ordinal; versions are immutable (IX2)."""
    return version_chunk_id(document_version_id(document), chunk.ordinal)


def version_chunk_id(version_id: UUID, ordinal: int) -> str:
    """`chunk_id` for a version id computed once (hashing a version is O(chunks))."""
    return hashlib.sha256(f"{version_id}:{ordinal}".encode()).hexdigest()


def chunk_content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
