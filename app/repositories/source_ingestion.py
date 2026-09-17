from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.crawl import CrawlStatus
from app.domain.discovery import (
    IngestionRunSummary,
    IngestionWriteResult,
    PersistedArtifact,
    PersistedSourceOrigin,
    SourceCandidateType,
    SourceIngestionResult,
    StoredArtifact,
    source_artifact_id,
    source_candidate_id,
    source_origin_id,
)


class SourceIngestionBase(DeclarativeBase):
    pass


Table(
    "monitoring_runs",
    SourceIngestionBase.metadata,
    Column("id", Uuid, primary_key=True),
)


class SourceIngestionRunRecord(SourceIngestionBase):
    __tablename__ = "source_ingestion_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    monitoring_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("monitoring_runs.id")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    manifest_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    product_count: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint("status IN ('success', 'partial', 'failed')"),
        CheckConstraint("completed_at >= started_at"),
    )


class SourceArtifactRecord(SourceIngestionBase):
    __tablename__ = "source_artifacts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class SourceIngestionProductRecord(SourceIngestionBase):
    __tablename__ = "source_ingestion_products"

    ingestion_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("source_ingestion_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(250), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    crawl_status: Mapped[str] = mapped_column(String(20), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    stored_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)


class SourceIngestionCandidateRecord(SourceIngestionBase):
    __tablename__ = "source_ingestion_candidates"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    ingestion_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("source_ingestion_runs.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    candidate_type: Mapped[str] = mapped_column(String(30), nullable=False)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    discovery_path: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    anchor_text: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text)
    match_signals: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    retrieval_status: Mapped[str] = mapped_column(String(20), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    artifact_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("source_artifacts.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id",
            "product_id",
            "normalized_url",
            "candidate_type",
            name="source_ingestion_candidates_identity_uq",
        ),
        Index(
            "source_ingestion_candidates_product_status_idx",
            "product_id",
            "retrieval_status",
        ),
    )


class SourceArtifactOriginRecord(SourceIngestionBase):
    __tablename__ = "source_artifact_origins"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    ingestion_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("source_ingestion_runs.id", ondelete="CASCADE"), nullable=False
    )
    artifact_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("source_artifacts.id"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    candidate_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    final_url: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(35))
    referrer_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id",
            "product_id",
            "artifact_id",
            "source_url",
            "final_url",
            name="source_artifact_origins_identity_uq",
        ),
    )


class PostgresSourceIngestionRepository:
    """Transactional metadata store for local source artifacts and provenance."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_ingestion(
        self, ingestion: SourceIngestionResult
    ) -> IngestionWriteResult:
        artifacts = _unique_artifacts(ingestion)
        now = ingestion.completed_at

        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:run_id, 0))"),
                {"run_id": str(ingestion.run_id)},
            )
            for checksum in sorted(artifacts):
                await session.execute(
                    text(
                        "SELECT pg_advisory_xact_lock("
                        "hashtextextended(:artifact_key, 0))"
                    ),
                    {"artifact_key": f"source-artifact:{checksum}"},
                )
            existing_manifest = await session.scalar(
                select(SourceIngestionRunRecord.manifest_key).where(
                    SourceIngestionRunRecord.id == ingestion.run_id
                )
            )
            if (
                existing_manifest is not None
                and existing_manifest != ingestion.manifest_key
            ):
                raise ValueError(
                    "ingestion run ID is already bound to another manifest"
                )

            existing_artifacts = {
                row.content_sha256: row
                for row in (
                    await session.scalars(
                        select(SourceArtifactRecord).where(
                            SourceArtifactRecord.content_sha256.in_(artifacts)
                        )
                    )
                ).all()
            }
            _validate_existing_artifacts(artifacts, existing_artifacts)

            status = _ingestion_status(ingestion)
            await session.execute(
                insert(SourceIngestionRunRecord)
                .values(
                    id=ingestion.run_id,
                    monitoring_run_id=ingestion.monitoring_run_id,
                    status=status,
                    manifest_key=ingestion.manifest_key,
                    started_at=ingestion.started_at,
                    completed_at=ingestion.completed_at,
                    product_count=len(ingestion.products),
                    candidate_count=len(ingestion.candidates),
                    source_count=len(ingestion.sources),
                    warning_count=len(ingestion.warnings),
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[SourceIngestionRunRecord.id],
                    set_={
                        "monitoring_run_id": ingestion.monitoring_run_id,
                        "status": status,
                        "completed_at": ingestion.completed_at,
                        "product_count": len(ingestion.products),
                        "candidate_count": len(ingestion.candidates),
                        "source_count": len(ingestion.sources),
                        "warning_count": len(ingestion.warnings),
                        "updated_at": now,
                    },
                )
            )

            for checksum, artifact in artifacts.items():
                seen_at = min(
                    source.retrieved_at
                    for source in ingestion.sources
                    if source.artifact.sha256 == checksum
                )
                await session.execute(
                    insert(SourceArtifactRecord)
                    .values(
                        id=source_artifact_id(checksum),
                        content_sha256=checksum,
                        storage_key=artifact.storage_key,
                        mime_type=artifact.mime_type,
                        size_bytes=artifact.size_bytes,
                        first_seen_at=seen_at,
                        last_seen_at=seen_at,
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_update(
                        index_elements=[SourceArtifactRecord.content_sha256],
                        set_={
                            "last_seen_at": func.greatest(
                                SourceArtifactRecord.last_seen_at, seen_at
                            ),
                            "updated_at": now,
                        },
                    )
                )

            for product in ingestion.products:
                await session.execute(
                    insert(SourceIngestionProductRecord)
                    .values(
                        ingestion_run_id=ingestion.run_id,
                        product_id=product.product_id,
                        product_name=product.product_name,
                        category=product.category.value,
                        crawl_status=product.crawl_status,
                        candidate_count=product.candidate_count,
                        stored_source_count=product.stored_source_count,
                        warnings=[
                            item.model_dump(mode="json") for item in product.warnings
                        ],
                        errors=[
                            item.model_dump(mode="json") for item in product.errors
                        ],
                    )
                    .on_conflict_do_update(
                        index_elements=[
                            SourceIngestionProductRecord.ingestion_run_id,
                            SourceIngestionProductRecord.product_id,
                        ],
                        set_={
                            "product_name": product.product_name,
                            "category": product.category.value,
                            "crawl_status": product.crawl_status,
                            "candidate_count": product.candidate_count,
                            "stored_source_count": product.stored_source_count,
                            "warnings": [
                                item.model_dump(mode="json")
                                for item in product.warnings
                            ],
                            "errors": [
                                item.model_dump(mode="json") for item in product.errors
                            ],
                        },
                    )
                )

            for candidate in ingestion.candidates:
                artifact_id = (
                    source_artifact_id(candidate.content_sha256)
                    if candidate.content_sha256 is not None
                    else None
                )
                await session.execute(
                    insert(SourceIngestionCandidateRecord)
                    .values(
                        id=source_candidate_id(ingestion.run_id, candidate),
                        ingestion_run_id=ingestion.run_id,
                        product_id=candidate.product_id,
                        candidate_type=candidate.candidate_type.value,
                        origin=candidate.origin.value,
                        original_url=candidate.original_url,
                        normalized_url=candidate.normalized_url,
                        discovery_path=list(candidate.discovery_path),
                        anchor_text=candidate.anchor_text,
                        title=candidate.title,
                        context=candidate.context,
                        match_signals=list(candidate.match_signals),
                        retrieval_status=candidate.retrieval_status.value,
                        status_code=candidate.status_code,
                        content_sha256=candidate.content_sha256,
                        mime_type=candidate.mime_type,
                        artifact_id=artifact_id,
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_update(
                        index_elements=[SourceIngestionCandidateRecord.id],
                        set_={
                            "original_url": candidate.original_url,
                            "discovery_path": list(candidate.discovery_path),
                            "anchor_text": candidate.anchor_text,
                            "title": candidate.title,
                            "context": candidate.context,
                            "match_signals": list(candidate.match_signals),
                            "retrieval_status": candidate.retrieval_status.value,
                            "status_code": candidate.status_code,
                            "content_sha256": candidate.content_sha256,
                            "mime_type": candidate.mime_type,
                            "artifact_id": artifact_id,
                            "updated_at": now,
                        },
                    )
                )

            for source in ingestion.sources:
                await session.execute(
                    insert(SourceArtifactOriginRecord)
                    .values(
                        id=source_origin_id(ingestion.run_id, source),
                        ingestion_run_id=ingestion.run_id,
                        artifact_id=source_artifact_id(source.artifact.sha256),
                        product_id=source.product_id,
                        candidate_type=source.candidate_type.value,
                        source_url=source.source_url,
                        final_url=source.final_url,
                        language=source.language,
                        referrer_urls=list(source.referrer_urls),
                        retrieved_at=source.retrieved_at,
                        created_at=now,
                    )
                    .on_conflict_do_nothing(
                        index_elements=[SourceArtifactOriginRecord.id]
                    )
                )

        created = len(set(artifacts) - set(existing_artifacts))
        return IngestionWriteResult(
            run_id=ingestion.run_id,
            artifacts_created=created,
            artifacts_reused=len(artifacts) - created,
            products_upserted=len(ingestion.products),
            candidates_upserted=len(ingestion.candidates),
            origins_upserted=len(ingestion.sources),
        )

    async def get_run(self, run_id: UUID) -> IngestionRunSummary | None:
        async with self._session_factory() as session:
            record = await session.get(SourceIngestionRunRecord, run_id)
        if record is None:
            return None
        return IngestionRunSummary(
            run_id=record.id,
            monitoring_run_id=record.monitoring_run_id,
            status=record.status,
            manifest_key=record.manifest_key,
            started_at=record.started_at,
            completed_at=record.completed_at,
            product_count=record.product_count,
            candidate_count=record.candidate_count,
            source_count=record.source_count,
            warning_count=record.warning_count,
        )

    async def get_artifact(self, content_sha256: str) -> PersistedArtifact | None:
        identifier = source_artifact_id(content_sha256)
        async with self._session_factory() as session:
            record = await session.get(SourceArtifactRecord, identifier)
        return _persisted_artifact(record) if record is not None else None

    async def list_product_sources(
        self,
        product_id: str,
        *,
        ingestion_run_id: UUID | None = None,
    ) -> tuple[PersistedSourceOrigin, ...]:
        statement = (
            select(SourceArtifactOriginRecord, SourceArtifactRecord)
            .join(
                SourceArtifactRecord,
                SourceArtifactRecord.id == SourceArtifactOriginRecord.artifact_id,
            )
            .where(SourceArtifactOriginRecord.product_id == product_id)
            .order_by(
                SourceArtifactOriginRecord.retrieved_at.desc(),
                SourceArtifactOriginRecord.source_url,
            )
        )
        if ingestion_run_id is not None:
            statement = statement.where(
                SourceArtifactOriginRecord.ingestion_run_id == ingestion_run_id
            )
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()
        return tuple(
            PersistedSourceOrigin(
                ingestion_run_id=origin.ingestion_run_id,
                artifact_id=origin.artifact_id,
                product_id=origin.product_id,
                candidate_type=SourceCandidateType(origin.candidate_type),
                source_url=origin.source_url,
                final_url=origin.final_url,
                language=origin.language,
                referrer_urls=tuple(origin.referrer_urls),
                retrieved_at=origin.retrieved_at,
                artifact=_persisted_artifact(artifact),
            )
            for origin, artifact in rows
        )


def _unique_artifacts(ingestion: SourceIngestionResult) -> dict[str, StoredArtifact]:
    artifacts: dict[str, StoredArtifact] = {}
    for source in ingestion.sources:
        current = artifacts.get(source.artifact.sha256)
        if current is not None and current.model_dump(
            exclude={"created"}
        ) != source.artifact.model_dump(exclude={"created"}):
            raise ValueError(
                "one checksum was associated with conflicting artifact metadata"
            )
        artifacts[source.artifact.sha256] = source.artifact
    return artifacts


def _validate_existing_artifacts(
    artifacts: dict[str, StoredArtifact],
    existing: dict[str, SourceArtifactRecord],
) -> None:
    for checksum, record in existing.items():
        artifact = artifacts[checksum]
        if (
            record.storage_key != artifact.storage_key
            or record.mime_type != artifact.mime_type
            or record.size_bytes != artifact.size_bytes
        ):
            raise ValueError(
                "persisted artifact metadata conflicts with incoming metadata"
            )


def _ingestion_status(ingestion: SourceIngestionResult) -> CrawlStatus:
    if ingestion.products and all(
        product.crawl_status is CrawlStatus.FAILED for product in ingestion.products
    ):
        return CrawlStatus.FAILED
    if ingestion.warnings or any(
        product.crawl_status is not CrawlStatus.SUCCESS
        for product in ingestion.products
    ):
        return CrawlStatus.PARTIAL
    return CrawlStatus.SUCCESS


def _persisted_artifact(record: SourceArtifactRecord) -> PersistedArtifact:
    return PersistedArtifact(
        artifact_id=record.id,
        storage_key=record.storage_key,
        sha256=record.content_sha256,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        first_seen_at=record.first_seen_at,
        last_seen_at=record.last_seen_at,
    )
