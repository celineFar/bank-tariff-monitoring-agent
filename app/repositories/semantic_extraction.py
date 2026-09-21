from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.models import ProductType
from app.domain.semantic_extraction import ExtractionBatchResponse


class SemanticExtractionBase(DeclarativeBase):
    pass


class SemanticExtractionRecord(SemanticExtractionBase):
    __tablename__ = "semantic_extraction_batches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String(50), nullable=False)
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
            "product",
            "schema_version",
            "prompt_version",
            "model_name",
            "content_fingerprint",
            name="semantic_extraction_batches_exact_uq",
        ),
    )


class PostgresSemanticExtractionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_exact(
        self,
        *,
        product: ProductType,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        fingerprints: Sequence[str],
    ) -> dict[str, ExtractionBatchResponse]:
        if not fingerprints:
            return {}
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        SemanticExtractionRecord.content_fingerprint,
                        SemanticExtractionRecord.response,
                    ).where(
                        SemanticExtractionRecord.product == product.value,
                        SemanticExtractionRecord.schema_version == schema_version,
                        SemanticExtractionRecord.prompt_version == prompt_version,
                        SemanticExtractionRecord.model_name == model_name,
                        SemanticExtractionRecord.content_fingerprint.in_(
                            tuple(fingerprints)
                        ),
                    )
                )
            ).all()
        return {
            row.content_fingerprint: ExtractionBatchResponse.model_validate(
                row.response
            )
            for row in rows
        }

    async def save(
        self,
        *,
        product: ProductType,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        values: Sequence[tuple[str, ExtractionBatchResponse]],
    ) -> None:
        if not values:
            return
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            for fingerprint, response in values:
                await session.execute(
                    insert(SemanticExtractionRecord)
                    .values(
                        product=product.value,
                        schema_version=schema_version,
                        prompt_version=prompt_version,
                        model_name=model_name,
                        content_fingerprint=fingerprint,
                        response=response.model_dump(mode="json"),
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_update(
                        constraint="semantic_extraction_batches_exact_uq",
                        set_={
                            "response": response.model_dump(mode="json"),
                            "updated_at": now,
                        },
                    )
                )
