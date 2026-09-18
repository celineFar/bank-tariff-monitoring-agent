from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.models import ProductType
from app.domain.source_discovery import SourceAssessment


class SourceDiscoveryBase(DeclarativeBase):
    pass


class SourceAssessmentRecord(SourceDiscoveryBase):
    __tablename__ = "source_discovery_assessments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_id: Mapped[str] = mapped_column(String(500), nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    structural_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    assessment: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "product",
            "policy_version",
            "prompt_version",
            "model_name",
            "content_fingerprint",
            name="source_discovery_assessments_exact_uq",
        ),
        Index(
            "source_discovery_assessments_structural_idx",
            "product",
            "policy_version",
            "prompt_version",
            "model_name",
            "structural_fingerprint",
            "updated_at",
        ),
    )


class PostgresSourceDiscoveryRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_exact(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]:
        if not content_fingerprints:
            return {}
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        SourceAssessmentRecord.content_fingerprint,
                        SourceAssessmentRecord.assessment,
                    ).where(
                        SourceAssessmentRecord.product == product.value,
                        SourceAssessmentRecord.policy_version == policy_version,
                        SourceAssessmentRecord.prompt_version == prompt_version,
                        SourceAssessmentRecord.model_name == model_name,
                        SourceAssessmentRecord.content_fingerprint.in_(
                            tuple(content_fingerprints)
                        ),
                    )
                )
            ).all()
        return {
            row.content_fingerprint: SourceAssessment.model_validate(row.assessment)
            for row in rows
        }

    async def get_structural_priors(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        structural_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]:
        if not structural_fingerprints:
            return {}
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        SourceAssessmentRecord.structural_fingerprint,
                        SourceAssessmentRecord.assessment,
                    )
                    .where(
                        SourceAssessmentRecord.product == product.value,
                        SourceAssessmentRecord.policy_version == policy_version,
                        SourceAssessmentRecord.prompt_version == prompt_version,
                        SourceAssessmentRecord.model_name == model_name,
                        SourceAssessmentRecord.structural_fingerprint.in_(
                            tuple(structural_fingerprints)
                        ),
                    )
                    .order_by(SourceAssessmentRecord.updated_at.desc())
                )
            ).all()
        results: dict[str, SourceAssessment] = {}
        for row in rows:
            results.setdefault(
                row.structural_fingerprint,
                SourceAssessment.model_validate(row.assessment),
            )
        return results

    async def save(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        assessments: Sequence[SourceAssessment],
    ) -> None:
        if not assessments:
            return
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            for assessment in assessments:
                await session.execute(
                    insert(SourceAssessmentRecord)
                    .values(
                        product=product.value,
                        policy_version=policy_version,
                        prompt_version=prompt_version,
                        model_name=model_name,
                        source_id=assessment.source_id,
                        content_fingerprint=assessment.input_fingerprint,
                        structural_fingerprint=assessment.structural_fingerprint,
                        assessment=assessment.model_dump(mode="json"),
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_update(
                        constraint="source_discovery_assessments_exact_uq",
                        set_={
                            "source_id": assessment.source_id,
                            "structural_fingerprint": assessment.structural_fingerprint,
                            "assessment": assessment.model_dump(mode="json"),
                            "updated_at": now,
                        },
                    )
                )
