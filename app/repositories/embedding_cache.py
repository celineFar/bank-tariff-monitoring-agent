"""Content-addressed cache for successful, complete document embeddings."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class PostgresEmbeddingCache:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def get_many(
        self,
        model_id: str,
        dimensions: int,
        task_type: str,
        hashes: Sequence[str],
    ) -> dict[str, tuple[float, ...]]:
        if not hashes:
            return {}
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    text(
                        """SELECT content_sha256, embedding::text AS embedding
                        FROM embedding_cache
                        WHERE model_id = :model_id AND dimensions = :dimensions
                          AND task_type = :task_type
                          AND content_sha256 = ANY(:hashes)"""
                    ),
                    {
                        "model_id": model_id,
                        "dimensions": dimensions,
                        "task_type": task_type,
                        "hashes": list(hashes),
                    },
                )
            ).all()
        return {
            row.content_sha256: tuple(
                float(value) for value in json.loads(row.embedding)
            )
            for row in rows
        }

    async def put_many(
        self,
        model_id: str,
        dimensions: int,
        task_type: str,
        values: Mapping[str, Sequence[float]],
    ) -> None:
        if not values:
            return
        async with self._sessions() as session, session.begin():
            for checksum, embedding in values.items():
                if len(embedding) != dimensions:
                    raise ValueError("embedding cache vector has wrong dimensions")
                await session.execute(
                    text(
                        """INSERT INTO embedding_cache (
                            model_id, dimensions, task_type, content_sha256, embedding
                        ) VALUES (
                            :model_id, :dimensions, :task_type, :checksum,
                            CAST(:embedding AS vector)
                        ) ON CONFLICT DO NOTHING"""
                    ),
                    {
                        "model_id": model_id,
                        "dimensions": dimensions,
                        "task_type": task_type,
                        "checksum": checksum,
                        "embedding": "["
                        + ",".join(str(value) for value in embedding)
                        + "]",
                    },
                )
