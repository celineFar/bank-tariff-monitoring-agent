"""Write knowledge documents straight into the RAG tables, for retrieval tests.

Production writes go through the offering publication repository; tests that only
need rows to search use this instead of building runs, snapshots and publications.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.knowledge import (
    EmbeddedKnowledgeDocument,
    chunk_content_sha256,
    document_version_id,
    version_chunk_id,
)
from app.repositories.knowledge_records import (
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    validate_embeddings,
)


async def store_active_document(
    session_factory: async_sessionmaker[AsyncSession],
    document: EmbeddedKnowledgeDocument,
) -> None:
    """Insert one document version and its chunks as active."""
    validate_embeddings(document)
    version_id = document_version_id(document)
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        session.add(
            KnowledgeDocumentRecord(
                id=version_id,
                run_id=document.run_id,
                last_seen_run_id=document.run_id,
                bank=document.bank.lower(),
                product=document.product.value,
                offering_id=document.offering_id.value
                if document.offering_id
                else None,
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
                is_active=True,
                publication_state="active",
                first_seen_at=now,
                last_seen_at=now,
                retired_at=None,
            )
        )
        await session.flush()
        session.add_all(
            KnowledgeChunkRecord(
                id=version_chunk_id(version_id, chunk.ordinal),
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
                embedding=list(chunk.embedding) if chunk.embedding else None,
                is_active=True,
                retired_at=None,
                created_at=now,
                updated_at=now,
            )
            for chunk in document.chunks
        )
