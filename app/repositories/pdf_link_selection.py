from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.pdf_extraction import PdfLinkChoice


class PdfLinkSelectionBase(DeclarativeBase):
    pass


class PdfLinkChoiceRecord(PdfLinkSelectionBase):
    """Cached PDF link decisions (migration 020), per offering and link metadata."""

    __tablename__ = "pdf_link_selections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    offering_id: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    link_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    choice: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "offering_id",
            "policy_version",
            "prompt_version",
            "model_name",
            "link_fingerprint",
            name="pdf_link_selections_uq",
        ),
    )


class PostgresPdfLinkSelectionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_many(
        self,
        *,
        offering_id: str,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        link_fingerprints: Sequence[str],
    ) -> dict[str, PdfLinkChoice]:
        if not link_fingerprints:
            return {}
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        PdfLinkChoiceRecord.link_fingerprint,
                        PdfLinkChoiceRecord.choice,
                    ).where(
                        PdfLinkChoiceRecord.offering_id == offering_id,
                        PdfLinkChoiceRecord.policy_version == policy_version,
                        PdfLinkChoiceRecord.prompt_version == prompt_version,
                        PdfLinkChoiceRecord.model_name == model_name,
                        PdfLinkChoiceRecord.link_fingerprint.in_(
                            tuple(link_fingerprints)
                        ),
                    )
                )
            ).all()
        return {
            row.link_fingerprint: PdfLinkChoice.model_validate(row.choice)
            for row in rows
        }

    async def save(
        self,
        *,
        offering_id: str,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        choices: Sequence[PdfLinkChoice],
    ) -> None:
        if not choices:
            return
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            for choice in choices:
                value = choice.model_dump(mode="json")
                await session.execute(
                    insert(PdfLinkChoiceRecord)
                    .values(
                        offering_id=offering_id,
                        policy_version=policy_version,
                        prompt_version=prompt_version,
                        model_name=model_name,
                        link_fingerprint=choice.link_fingerprint,
                        choice=value,
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_update(
                        constraint="pdf_link_selections_uq",
                        set_={"choice": value, "updated_at": now},
                    )
                )
