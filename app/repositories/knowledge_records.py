"""SQLAlchemy records for the evidence document tables (migrations 002, 007, 023, 027).

Writes go through the offering publication repository
(`app/repositories/monitoring.py`) and review activation
(`app/repositories/reviews.py`); there is no second writer (IX15).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class KnowledgeBase(DeclarativeBase):
    pass


Table(
    "monitoring_runs",
    KnowledgeBase.metadata,
    Column("id", Uuid, primary_key=True),
)
Table(
    "tariff_snapshots",
    KnowledgeBase.metadata,
    Column("id", Uuid, primary_key=True),
)


class KnowledgeDocumentRecord(KnowledgeBase):
    __tablename__ = "knowledge_documents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("monitoring_runs.id"), nullable=False
    )
    last_seen_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("monitoring_runs.id"), nullable=False
    )
    bank: Mapped[str] = mapped_column(String(100), nullable=False)
    product: Mapped[str] = mapped_column(String(50), nullable=False)
    offering_id: Mapped[str | None] = mapped_column(String(100))
    document_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    document_key: Mapped[str] = mapped_column(String(500), nullable=False)
    document_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    final_url: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Hash of the projected chunks: the same raw bytes projected differently is
    # another version (IX2).
    projection_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    extraction_method: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    publication_state: Mapped[str] = mapped_column(String(50), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "bank",
            "product",
            "offering_id",
            "document_kind",
            "document_key",
            "content_sha256",
            "projection_sha256",
            name="knowledge_documents_version_uq",
        ),
        Index(
            "knowledge_documents_identity_idx",
            "bank",
            "product",
            "offering_id",
            "document_kind",
            "document_key",
            "is_active",
        ),
    )


class KnowledgeChunkRecord(KnowledgeBase):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(35), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id", "ordinal", name="knowledge_chunks_document_ordinal_uq"
        ),
        Index(
            "knowledge_chunks_document_location_idx",
            "document_id",
            "page_start",
            "section",
            "language",
            "is_active",
        ),
    )


class SnapshotDocumentRecord(KnowledgeBase):
    """The document versions one snapshot was built from (migration 023)."""

    __tablename__ = "snapshot_documents"

    snapshot_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("tariff_snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
