from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.pdf_extraction import PdfExtractionResponse


class PdfExtractionBase(DeclarativeBase):
    pass


class PdfExtractionRecord(PdfExtractionBase):
    __tablename__ = "pdf_extraction_cache"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "document_sha256",
            "schema_version",
            "prompt_version",
            "model_name",
            "content_fingerprint",
            name="pdf_extraction_cache_exact_uq",
        ),
    )


class PostgresPdfExtractionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_exact(
        self,
        *,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
    ) -> PdfExtractionResponse | None:
        async with self._session_factory() as session:
            value = await session.scalar(
                select(PdfExtractionRecord.response).where(
                    PdfExtractionRecord.document_sha256 == document_sha256,
                    PdfExtractionRecord.schema_version == schema_version,
                    PdfExtractionRecord.prompt_version == prompt_version,
                    PdfExtractionRecord.model_name == model_name,
                    PdfExtractionRecord.content_fingerprint == content_fingerprint,
                )
            )
        return PdfExtractionResponse.model_validate(value) if value else None

    async def save(
        self,
        *,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
        response: PdfExtractionResponse,
    ) -> None:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            await session.execute(
                insert(PdfExtractionRecord)
                .values(
                    document_sha256=document_sha256,
                    schema_version=schema_version,
                    prompt_version=prompt_version,
                    model_name=model_name,
                    content_fingerprint=content_fingerprint,
                    response=response.model_dump(mode="json"),
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    constraint="pdf_extraction_cache_exact_uq",
                    set_={
                        "response": response.model_dump(mode="json"),
                        "updated_at": now,
                    },
                )
            )
