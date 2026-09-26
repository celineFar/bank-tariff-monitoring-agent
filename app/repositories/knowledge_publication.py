"""Document versions, snapshot sets and activation for the RAG index.

Called inside the caller's transaction, under the offering's publication
advisory lock: the offering publication repository (a run's documents) and the
review repository (an approval's activation and a rejection's clean-up).

- A version row is immutable: one projection of one source's bytes. Storing it
  again only refreshes bookkeeping and fills vectors still missing (IX2).
- A snapshot owns the versions it was built from (`snapshot_documents`).
- Activating a snapshot makes its set the offering's whole active index and
  retires everything else of the offering (IX1).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.knowledge import (
    EmbeddedKnowledgeDocument,
    IndexWriteResult,
    chunk_content_sha256,
    document_version_id,
    version_chunk_id,
)
from app.repositories.knowledge_records import (
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    validate_embeddings,
)


async def store_document_version(
    session: AsyncSession,
    document: EmbeddedKnowledgeDocument,
    now: datetime,
) -> IndexWriteResult:
    """Insert a version if absent; never change an existing version's content.

    New rows start inactive (`pending_review`); only `activate_snapshot_set`
    makes a version searchable. On an existing row, the upsert refreshes
    bookkeeping (last seen, retrieval time, document metadata) and fills a
    chunk's vector if it has none yet.
    """
    validate_embeddings(document)
    version_id = document_version_id(document)
    chunk_ids = tuple(
        version_chunk_id(version_id, chunk.ordinal) for chunk in document.chunks
    )
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:document_identity, 0))"),
        {"document_identity": str(version_id)},
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
                    KnowledgeChunkRecord.id.in_(chunk_ids)
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
            offering_id=(
                document.offering_id.value if document.offering_id is not None else None
            ),
            document_kind=document.document_kind.value,
            document_key=document.document_key,
            document_name=document.document_name,
            source_url=str(document.source_url),
            final_url=str(document.final_url),
            mime_type=document.mime_type,
            content_sha256=document.content_sha256,
            projection_sha256=document.projection_sha256,
            retrieved_at=document.retrieved_at,
            extraction_method=document.extraction_method,
            quality_score=document.quality_score,
            extra_metadata=document.metadata,
            is_active=False,
            publication_state="pending_review",
            first_seen_at=now,
            last_seen_at=now,
            retired_at=None,
        )
        .on_conflict_do_update(
            index_elements=[KnowledgeDocumentRecord.id],
            set_={
                "last_seen_run_id": document.run_id,
                "last_seen_at": now,
                "retrieved_at": document.retrieved_at,
                "metadata": document.metadata,
            },
        )
    )
    for identifier, chunk in zip(chunk_ids, document.chunks, strict=True):
        statement = insert(KnowledgeChunkRecord).values(
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
            embedding=list(chunk.embedding) if chunk.embedding is not None else None,
            is_active=False,
            retired_at=None,
            created_at=now,
            updated_at=now,
        )
        if chunk.embedding is None:
            await session.execute(statement.on_conflict_do_nothing())
            continue
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[KnowledgeChunkRecord.id],
                set_={
                    "embedding": func.coalesce(
                        KnowledgeChunkRecord.embedding, statement.excluded.embedding
                    ),
                    "updated_at": now,
                },
                where=KnowledgeChunkRecord.embedding.is_(None),
            )
        )
    chunks_created = len(set(chunk_ids) - existing_chunk_ids)
    return IndexWriteResult(
        document_id=version_id,
        document_created=document_created,
        chunks_created=chunks_created,
        chunks_updated=len(chunk_ids) - chunks_created,
        chunks_retired=0,
        versions_retired=0,
    )


async def link_snapshot_documents(
    session: AsyncSession, snapshot_id: UUID, document_ids: Sequence[UUID]
) -> None:
    """Record the versions a snapshot was built from."""
    for document_id in dict.fromkeys(document_ids):
        await session.execute(
            text(
                """
                INSERT INTO snapshot_documents (snapshot_id, document_id)
                VALUES (:snapshot_id, :document_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"snapshot_id": snapshot_id, "document_id": document_id},
        )


_OFFERING_SCOPE = """
    WITH snapshot AS (
        SELECT lower(bank) AS bank, product, offering_id
        FROM tariff_snapshots
        WHERE id = :snapshot_id
    ), outside AS (
        SELECT d.id
        FROM knowledge_documents AS d
        JOIN snapshot AS s
          ON d.bank = s.bank
         AND d.product = s.product
         AND d.offering_id = s.offering_id
        WHERE d.is_active
          AND d.id NOT IN (
              SELECT document_id FROM snapshot_documents
              WHERE snapshot_id = :snapshot_id
          )
    )
"""


async def activate_snapshot_set(
    session: AsyncSession, snapshot_id: UUID, now: datetime
) -> tuple[int, int]:
    """Make the snapshot's set the offering's whole active index.

    Retires every active document of the offering outside the set (a changed
    page's old version, a PDF no longer linked, the previous summary), then
    activates the set. Returns (documents retired, documents activated).
    """
    parameters = {"snapshot_id": snapshot_id, "now": now}
    await session.execute(
        text(
            _OFFERING_SCOPE
            + """
            UPDATE knowledge_chunks
            SET is_active = false, retired_at = :now, updated_at = :now
            WHERE document_id IN (SELECT id FROM outside) AND is_active
            """
        ),
        parameters,
    )
    retired = (
        await session.execute(
            text(
                _OFFERING_SCOPE
                + """
                UPDATE knowledge_documents
                SET is_active = false, publication_state = 'retired',
                    retired_at = :now
                WHERE id IN (SELECT id FROM outside)
                """
            ),
            parameters,
        )
    ).rowcount
    activated = (
        await session.execute(
            text(
                """
                UPDATE knowledge_documents
                SET is_active = true, publication_state = 'active', retired_at = NULL
                WHERE id IN (
                    SELECT document_id FROM snapshot_documents
                    WHERE snapshot_id = :snapshot_id
                )
                  AND NOT is_active
                """
            ),
            parameters,
        )
    ).rowcount
    await session.execute(
        text(
            """
            UPDATE knowledge_chunks
            SET is_active = true, retired_at = NULL, updated_at = :now
            WHERE document_id IN (
                SELECT document_id FROM snapshot_documents
                WHERE snapshot_id = :snapshot_id
            )
              AND NOT is_active
            """
        ),
        parameters,
    )
    return retired, activated


async def discard_snapshot_documents(session: AsyncSession, snapshot_id: UUID) -> int:
    """Drop a rejected or superseded snapshot's set and its never-published versions.

    A version is deleted (chunks by cascade) only when it never became active and
    no other snapshot still names it: a version shared with a pending or
    accepted snapshot stays (IX9). Returns the number of documents deleted.
    """
    return (
        await session.execute(
            text(
                """
                WITH released AS (
                    DELETE FROM snapshot_documents
                    WHERE snapshot_id = :snapshot_id
                    RETURNING document_id
                )
                DELETE FROM knowledge_documents AS d
                WHERE d.id IN (SELECT document_id FROM released)
                  AND d.publication_state = 'pending_review'
                  AND NOT d.is_active
                  AND NOT EXISTS (
                      SELECT 1 FROM snapshot_documents AS other
                      WHERE other.document_id = d.id
                        AND other.snapshot_id <> :snapshot_id
                  )
                """
            ),
            {"snapshot_id": snapshot_id},
        )
    ).rowcount


def publication_lock_key(bank: str, product: str, offering_id: str) -> str:
    return f"publication:{bank.lower()}:{product}:{offering_id}"


async def lock_offering_publication(
    session: AsyncSession, *, bank: str, product: str, offering_id: str
) -> None:
    """The offering's publication lock, held until the transaction ends.

    Everything that changes an offering's index or its pending reviews takes it
    first, before any row lock: publication, approval, rejection, supersession.
    One order everywhere means no deadlock between a run publishing (which
    supersedes reviews, IX4) and a reviewer deciding.
    """
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
        {"lock_key": publication_lock_key(bank, product, offering_id)},
    )


async def lock_review_publication(session: AsyncSession, review_id: UUID) -> None:
    """`lock_offering_publication` for a review's offering, before locking the review."""
    scope = (
        await session.execute(
            text(
                """
                SELECT coalesce(s.bank, 'ameria') AS bank, r.product, r.offering_id
                FROM human_reviews AS r
                LEFT JOIN tariff_snapshots AS s ON s.id = r.snapshot_id
                WHERE r.id = :review_id
                """
            ),
            {"review_id": review_id},
        )
    ).first()
    if scope is not None and scope.product and scope.offering_id:
        await lock_offering_publication(
            session,
            bank=scope.bank,
            product=scope.product,
            offering_id=scope.offering_id,
        )
