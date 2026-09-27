"""Active chunks stored without a vector, and filling them (IX5, IX7).

A chunk is stored text-only when its run needed review (approval activates it
unembedded) or when the provider was out of quota. Only vectors are written
here; document versions stay immutable.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.knowledge import EMBEDDING_DIMENSIONS
from app.domain.models import OfferingId


class PostgresChunkEmbeddingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_missing(
        self, *, offering_id: OfferingId | None, limit: int
    ) -> tuple[tuple[str, str], ...]:
        if limit <= 0:
            return ()
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        """
                        SELECT c.id, c.content
                        FROM knowledge_chunks AS c
                        JOIN knowledge_documents AS d ON d.id = c.document_id
                        WHERE c.is_active AND c.embedding IS NULL
                          AND (
                              CAST(:offering_id AS text) IS NULL
                              OR d.offering_id = CAST(:offering_id AS text)
                          )
                        ORDER BY c.created_at, c.id
                        LIMIT :limit
                        """
                    ),
                    {
                        "offering_id": offering_id.value if offering_id else None,
                        "limit": limit,
                    },
                )
            ).all()
        return tuple((row.id, row.content) for row in rows)

    async def fill(self, vectors: Mapping[str, Sequence[float]]) -> int:
        if not vectors:
            return 0
        filled = 0
        async with self._session_factory() as session, session.begin():
            for identifier, vector in vectors.items():
                if len(vector) != EMBEDDING_DIMENSIONS:
                    raise ValueError(
                        f"every embedding must have {EMBEDDING_DIMENSIONS} dimensions"
                    )
                filled += (
                    await session.execute(
                        text(
                            """
                            UPDATE knowledge_chunks
                            SET embedding = CAST(:embedding AS vector),
                                updated_at = now()
                            WHERE id = :id AND embedding IS NULL
                            """
                        ),
                        {
                            "id": identifier,
                            "embedding": "["
                            + ",".join(str(float(value)) for value in vector)
                            + "]",
                        },
                    )
                ).rowcount
        return filled
