import os
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.repositories.embedding_cache import PostgresEmbeddingCache

pytestmark = pytest.mark.postgres


@pytest.mark.asyncio
async def test_embedding_cache_keys_include_model_dimensions_and_task() -> None:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required")
    assert url.endswith("_test")
    connection = await asyncpg.connect(
        url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        await connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        for migration in sorted(Path("migrations").glob("*.sql")):
            await connection.execute(migration.read_text())
    finally:
        await connection.close()
    engine = create_async_engine(url)
    try:
        cache = PostgresEmbeddingCache(async_sessionmaker(engine))
        checksum = "a" * 64
        vector = [0.5] * 768
        await cache.put_many(
            "test-model", 768, "RETRIEVAL_DOCUMENT", {checksum: vector}
        )
        await cache.put_many(
            "test-model", 768, "RETRIEVAL_DOCUMENT", {checksum: vector}
        )
        found = await cache.get_many(
            "test-model", 768, "RETRIEVAL_DOCUMENT", [checksum]
        )
        assert found[checksum] == tuple(vector)
        assert (
            await cache.get_many("other-model", 768, "RETRIEVAL_DOCUMENT", [checksum])
            == {}
        )
        assert (
            await cache.get_many("test-model", 768, "RETRIEVAL_QUERY", [checksum]) == {}
        )
    finally:
        await engine.dispose()
