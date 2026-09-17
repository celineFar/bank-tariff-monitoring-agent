from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    Uuid,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.discovery import StoredArtifact, source_artifact_id
from app.domain.extraction import (
    ExtractedDocument,
    ExtractionStatistics,
    ExtractionStatus,
    ExtractionWarning,
    OcrAssessment,
    PersistedExtraction,
)


class ContentExtractionBase(DeclarativeBase):
    pass


Table(
    "source_artifacts",
    ContentExtractionBase.metadata,
    Column("id", Uuid, primary_key=True),
)


class ContentExtractionRecord(ContentExtractionBase):
    __tablename__ = "content_extractions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_artifact_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("source_artifacts.id"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    final_url: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(35))
    source_mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    extractor: Mapped[str] = mapped_column(String(100), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(50), nullable=False)
    representation_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    representation_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    representation_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    statistics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    text_character_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    block_count: Mapped[int] = mapped_column(Integer, nullable=False)
    table_count: Mapped[int] = mapped_column(Integer, nullable=False)
    needs_ocr: Mapped[bool] = mapped_column(Boolean, nullable=False)
    pages_requiring_ocr: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    ocr_assessment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("content_extractions_source_artifact_idx", "source_artifact_id"),
        Index("content_extractions_product_idx", "product_id", "extracted_at"),
        Index("content_extractions_representation_idx", "representation_sha256"),
    )


class PostgresContentExtractionRepository:
    """Idempotent metadata store for immutable extracted representations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_extraction(self, extraction: ExtractedDocument) -> None:
        artifact_id = source_artifact_id(extraction.source_sha256)
        representation = extraction.representation_artifact
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"content-extraction:{extraction.extraction_id}"},
            )
            existing = await session.get(
                ContentExtractionRecord, extraction.extraction_id
            )
            if existing is not None and (
                existing.source_artifact_id != artifact_id
                or existing.representation_sha256 != representation.sha256
                or existing.representation_storage_key != representation.storage_key
                or existing.representation_size_bytes != representation.size_bytes
            ):
                raise ValueError(
                    "extraction ID is already bound to conflicting artifact metadata"
                )

            values = {
                "id": extraction.extraction_id,
                "source_artifact_id": artifact_id,
                "product_id": extraction.product_id,
                "source_url": extraction.source_url,
                "final_url": extraction.final_url,
                "language": extraction.language,
                "source_mime_type": extraction.source_mime_type,
                "extractor": extraction.extractor,
                "extractor_version": extraction.extractor_version,
                "representation_storage_key": representation.storage_key,
                "representation_sha256": representation.sha256,
                "representation_size_bytes": representation.size_bytes,
                "statistics": extraction.statistics.model_dump(mode="json"),
                "warnings": [
                    warning.model_dump(mode="json") for warning in extraction.warnings
                ],
                "status": extraction.status.value,
                "page_count": extraction.statistics.page_count,
                "text_character_count": extraction.statistics.text_character_count,
                "block_count": extraction.statistics.block_count,
                "table_count": extraction.statistics.table_count,
                "needs_ocr": extraction.status is ExtractionStatus.NEEDS_OCR,
                "pages_requiring_ocr": list(extraction.ocr.pages_requiring_ocr),
                "ocr_assessment": extraction.ocr.model_dump(mode="json"),
                "extracted_at": extraction.extracted_at,
                "created_at": extraction.extracted_at,
                "updated_at": extraction.extracted_at,
            }
            await session.execute(
                insert(ContentExtractionRecord)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[ContentExtractionRecord.id],
                    set_={
                        "final_url": extraction.final_url,
                        "language": extraction.language,
                        "statistics": extraction.statistics.model_dump(mode="json"),
                        "warnings": [
                            warning.model_dump(mode="json")
                            for warning in extraction.warnings
                        ],
                        "status": extraction.status.value,
                        "page_count": extraction.statistics.page_count,
                        "text_character_count": extraction.statistics.text_character_count,
                        "block_count": extraction.statistics.block_count,
                        "table_count": extraction.statistics.table_count,
                        "needs_ocr": extraction.status is ExtractionStatus.NEEDS_OCR,
                        "pages_requiring_ocr": list(extraction.ocr.pages_requiring_ocr),
                        "ocr_assessment": extraction.ocr.model_dump(mode="json"),
                        "extracted_at": extraction.extracted_at,
                        "updated_at": extraction.extracted_at,
                    },
                )
            )

    async def get_extraction(self, extraction_id: UUID) -> PersistedExtraction | None:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(ContentExtractionRecord).where(
                    ContentExtractionRecord.id == extraction_id
                )
            )
        if record is None:
            return None
        return PersistedExtraction(
            extraction_id=record.id,
            source_artifact_id=record.source_artifact_id,
            product_id=record.product_id,
            source_url=record.source_url,
            representation_artifact=StoredArtifact(
                storage_key=record.representation_storage_key,
                sha256=record.representation_sha256,
                mime_type="application/json",
                size_bytes=record.representation_size_bytes,
                created=False,
            ),
            extractor=record.extractor,
            extractor_version=record.extractor_version,
            status=ExtractionStatus(record.status),
            ocr=OcrAssessment.model_validate(record.ocr_assessment),
            statistics=ExtractionStatistics.model_validate(record.statistics),
            warnings=tuple(
                ExtractionWarning.model_validate(item) for item in record.warnings
            ),
            extracted_at=record.extracted_at,
        )
