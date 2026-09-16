from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    Computed,
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
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.knowledge import (
    EMBEDDING_DIMENSIONS,
    DocumentVersionSummary,
    EmbeddedKnowledgeDocument,
    IndexWriteResult,
    chunk_content_sha256,
    chunk_id,
    document_version_id,
)
from app.domain.models import ProductType


class KnowledgeBase(DeclarativeBase):
    pass


Table(
    "monitoring_runs",
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
    document_key: Mapped[str] = mapped_column(String(500), nullable=False)
    document_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    final_url: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    extraction_method: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
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
            "document_key",
            "content_sha256",
            name="knowledge_documents_version_uq",
        ),
        Index(
            "knowledge_documents_identity_idx",
            "bank",
            "product",
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
    search_vector: Mapped[object] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', content)", persisted=True),
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=False
    )
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
        Index(
            "knowledge_chunks_search_gin_idx",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "knowledge_chunks_embedding_hnsw_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class PostgresKnowledgeStore:
    """Transactional PostgreSQL/pgvector store for document versions and chunks."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_document(
        self, document: EmbeddedKnowledgeDocument
    ) -> IndexWriteResult:
        self._validate_embeddings(document)
        version_id = document_version_id(document)
        incoming_chunk_ids = tuple(
            chunk_id(document, chunk) for chunk in document.chunks
        )
        now = datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            await session.execute(
                text(
                    "SELECT pg_advisory_xact_lock("
                    "hashtextextended(:document_identity, 0))"
                ),
                {
                    "document_identity": "\x1f".join(
                        (
                            document.bank.lower(),
                            document.product.value,
                            document.document_key,
                        )
                    )
                },
            )
            document_created = (
                await session.scalar(
                    select(KnowledgeDocumentRecord.id).where(
                        KnowledgeDocumentRecord.id == version_id
                    )
                )
                is None
            )

            existing_chunk_ids = set(
                (
                    await session.scalars(
                        select(KnowledgeChunkRecord.id).where(
                            KnowledgeChunkRecord.id.in_(incoming_chunk_ids)
                        )
                    )
                ).all()
            )

            await session.execute(
                insert(KnowledgeDocumentRecord)
                .values(
                    id=version_id,
                    run_id=document.run_id,
                    last_seen_run_id=document.run_id,
                    bank=document.bank.lower(),
                    product=document.product.value,
                    document_key=document.document_key,
                    document_name=document.document_name,
                    source_url=str(document.source_url),
                    final_url=str(document.final_url),
                    mime_type=document.mime_type,
                    content_sha256=document.content_sha256,
                    retrieved_at=document.retrieved_at,
                    extraction_method=document.extraction_method,
                    quality_score=document.quality_score,
                    extra_metadata=document.metadata,
                    is_active=True,
                    first_seen_at=now,
                    last_seen_at=now,
                    retired_at=None,
                )
                .on_conflict_do_update(
                    index_elements=[KnowledgeDocumentRecord.id],
                    set_={
                        "last_seen_run_id": document.run_id,
                        "document_name": document.document_name,
                        "source_url": str(document.source_url),
                        "final_url": str(document.final_url),
                        "mime_type": document.mime_type,
                        "retrieved_at": document.retrieved_at,
                        "extraction_method": document.extraction_method,
                        "quality_score": document.quality_score,
                        "metadata": document.metadata,
                        "is_active": True,
                        "last_seen_at": now,
                        "retired_at": None,
                    },
                )
            )

            superseded_ids = tuple(
                (
                    await session.scalars(
                        select(KnowledgeDocumentRecord.id).where(
                            KnowledgeDocumentRecord.bank == document.bank.lower(),
                            KnowledgeDocumentRecord.product == document.product.value,
                            KnowledgeDocumentRecord.document_key
                            == document.document_key,
                            KnowledgeDocumentRecord.id != version_id,
                            KnowledgeDocumentRecord.is_active.is_(True),
                        )
                    )
                ).all()
            )
            retired_chunks = 0
            if superseded_ids:
                result = await session.execute(
                    update(KnowledgeChunkRecord)
                    .where(
                        KnowledgeChunkRecord.document_id.in_(superseded_ids),
                        KnowledgeChunkRecord.is_active.is_(True),
                    )
                    .values(is_active=False, retired_at=now, updated_at=now)
                )
                retired_chunks += result.rowcount
                await session.execute(
                    update(KnowledgeDocumentRecord)
                    .where(KnowledgeDocumentRecord.id.in_(superseded_ids))
                    .values(is_active=False, retired_at=now)
                )

            for identifier, chunk in zip(
                incoming_chunk_ids, document.chunks, strict=True
            ):
                await session.execute(
                    insert(KnowledgeChunkRecord)
                    .values(
                        id=identifier,
                        document_id=version_id,
                        ordinal=chunk.ordinal,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        section=chunk.section,
                        language=chunk.language,
                        content=chunk.content,
                        content_sha256=chunk_content_sha256(chunk.content),
                        extraction_method=chunk.extraction_method,
                        quality_score=chunk.quality_score,
                        extra_metadata=chunk.metadata,
                        embedding=list(chunk.embedding),
                        is_active=True,
                        retired_at=None,
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_update(
                        index_elements=[KnowledgeChunkRecord.id],
                        set_={
                            "content": chunk.content,
                            "content_sha256": chunk_content_sha256(chunk.content),
                            "language": chunk.language,
                            "extraction_method": chunk.extraction_method,
                            "quality_score": chunk.quality_score,
                            "metadata": chunk.metadata,
                            "embedding": list(chunk.embedding),
                            "is_active": True,
                            "retired_at": None,
                            "updated_at": now,
                        },
                    )
                )

            result = await session.execute(
                update(KnowledgeChunkRecord)
                .where(
                    KnowledgeChunkRecord.document_id == version_id,
                    KnowledgeChunkRecord.id.not_in(incoming_chunk_ids),
                    KnowledgeChunkRecord.is_active.is_(True),
                )
                .values(is_active=False, retired_at=now, updated_at=now)
            )
            retired_chunks += result.rowcount

            chunks_created = len(set(incoming_chunk_ids) - existing_chunk_ids)
            return IndexWriteResult(
                document_id=version_id,
                document_created=document_created,
                chunks_created=chunks_created,
                chunks_updated=len(incoming_chunk_ids) - chunks_created,
                chunks_retired=retired_chunks,
                versions_retired=len(superseded_ids),
            )

    async def list_document_versions(
        self, bank: str, product: ProductType, document_key: str
    ) -> tuple[DocumentVersionSummary, ...]:
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        KnowledgeDocumentRecord.id,
                        KnowledgeDocumentRecord.content_sha256,
                        KnowledgeDocumentRecord.is_active,
                        KnowledgeDocumentRecord.retrieved_at,
                        KnowledgeDocumentRecord.retired_at,
                    )
                    .where(
                        KnowledgeDocumentRecord.bank == bank.lower(),
                        KnowledgeDocumentRecord.product == product.value,
                        KnowledgeDocumentRecord.document_key == document_key,
                    )
                    .order_by(KnowledgeDocumentRecord.retrieved_at)
                )
            ).all()
        return tuple(
            DocumentVersionSummary(
                id=row.id,
                content_sha256=row.content_sha256,
                is_active=row.is_active,
                retrieved_at=row.retrieved_at,
                retired_at=row.retired_at,
            )
            for row in rows
        )

    @staticmethod
    def _validate_embeddings(document: EmbeddedKnowledgeDocument) -> None:
        if any(
            len(chunk.embedding) != EMBEDDING_DIMENSIONS for chunk in document.chunks
        ):
            raise ValueError(
                f"every embedding must have {EMBEDDING_DIMENSIONS} dimensions"
            )
