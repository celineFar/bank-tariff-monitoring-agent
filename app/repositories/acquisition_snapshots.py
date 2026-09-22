from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.acquisition import PageArtifact


class AcquisitionSnapshotBase(DeclarativeBase):
    pass


def acquisition_url_key(url: str) -> str:
    """Key an acquisition by a digest, not the URL itself.

    Seed URLs carry query strings and can exceed what a btree key accepts, so
    the primary key is a fixed-width digest and the URL is kept alongside it for
    operators reading the table.
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class AcquisitionSnapshotRecord(AcquisitionSnapshotBase):
    __tablename__ = "acquisition_snapshots"

    url_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    artifact: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class PostgresAcquisitionSnapshotRepository:
    """The most recent acquisition of each seed URL, for freshness-gated reuse."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_latest(self, url: str) -> PageArtifact | None:
        async with self._session_factory() as session:
            value = await session.scalar(
                select(AcquisitionSnapshotRecord.artifact).where(
                    AcquisitionSnapshotRecord.url_key == acquisition_url_key(url)
                )
            )
        if value is None:
            return None
        # A stored artifact that no longer satisfies the current model -- an
        # older row written before a field was added -- is not an error: the
        # caller simply acquires again.
        try:
            return PageArtifact.model_validate(value)
        except ValueError:
            return None

    async def save(self, url: str, artifact: PageArtifact) -> None:
        now = datetime.now(UTC)
        values = {
            "url_key": acquisition_url_key(url),
            "source_url": url,
            "content_hash": artifact.content_hash,
            "retrieved_at": artifact.retrieved_at,
            "artifact": artifact.model_dump(mode="json"),
            "created_at": now,
            "updated_at": now,
        }
        async with self._session_factory() as session, session.begin():
            await session.execute(
                insert(AcquisitionSnapshotRecord)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[AcquisitionSnapshotRecord.url_key],
                    set_={
                        "source_url": values["source_url"],
                        "content_hash": values["content_hash"],
                        "retrieved_at": values["retrieved_at"],
                        "artifact": values["artifact"],
                        "updated_at": now,
                    },
                )
            )
