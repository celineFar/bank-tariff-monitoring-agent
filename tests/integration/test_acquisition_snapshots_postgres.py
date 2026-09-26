import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.acquisition import (
    AcquisitionInventory,
    AcquisitionMode,
    PageArtifact,
)
from app.repositories.acquisition_snapshots import (
    PostgresAcquisitionSnapshotRepository,
)

URL = "https://ameriabank.am/en/personal/loans/consumer-loans/overdraft?tab=terms"


def _artifact(retrieved_at: datetime, content_hash: str) -> PageArtifact:
    return PageArtifact(
        url=URL,
        canonical_url=URL,
        final_url=URL,
        title="Overdraft",
        language="en",
        acquisition_mode=AcquisitionMode.BROWSER,
        raw_html="<html><body><h1>Overdraft</h1></body></html>",
        rendered_html=None,
        markdown="# Overdraft",
        blocks=(),
        tables=(),
        links=(),
        downloadable_documents=(),
        network_payloads=(),
        retrieved_at=retrieved_at,
        inventory=AcquisitionInventory(main_chars=0, tables=0, pdf_links=0, payloads=0),
        content_hash=content_hash,
        page_content_hash="b" * 64,
    )


@pytest.mark.asyncio
async def test_acquisition_snapshot_round_trips_and_keeps_only_the_latest() -> None:
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
        repository = PostgresAcquisitionSnapshotRepository(async_sessionmaker(engine))
        assert await repository.get_latest(URL) is None

        earlier = datetime(2026, 9, 22, 17, 0, tzinfo=UTC)
        await repository.save(URL, _artifact(earlier, "a" * 64))
        stored = await repository.get_latest(URL)
        assert stored is not None
        assert stored.content_hash == "a" * 64
        assert stored.retrieved_at == earlier
        assert stored.raw_html == "<html><body><h1>Overdraft</h1></body></html>"

        # This is a reuse window, not a history: a second acquisition of the
        # same URL replaces the first rather than accumulating beside it.
        later = earlier + timedelta(minutes=30)
        await repository.save(URL, _artifact(later, "d" * 64))
        replaced = await repository.get_latest(URL)
        assert replaced is not None
        assert replaced.content_hash == "d" * 64
        assert replaced.retrieved_at == later

        async with engine.connect() as session:
            rows = await session.exec_driver_sql(
                "SELECT count(*) FROM acquisition_snapshots"
            )
            assert rows.scalar_one() == 1
    finally:
        await engine.dispose()
