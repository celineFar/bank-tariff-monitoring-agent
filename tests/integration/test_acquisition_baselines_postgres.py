import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import AcquisitionSettings
from app.domain.acquisition import AcquisitionInventory, AcquisitionMode, PageArtifact
from app.repositories.acquisition_baselines import (
    PostgresAcquisitionBaselineRepository,
)
from app.services.acquisition_completeness import CompletenessGatedAcquisitionService
from app.services.acquisition_errors import AcquisitionError

URL = "https://ameriabank.am/en/personal/loans/consumer-loans/overdraft"
NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
GOOD = AcquisitionInventory(main_chars=13_136, tables=3, pdf_links=10)
REDESIGNED = AcquisitionInventory(main_chars=9_000, tables=0, pdf_links=4)


class _Acquisition:
    def __init__(self) -> None:
        self.inventory = GOOD

    async def acquire(self, url: str) -> PageArtifact:
        return PageArtifact(
            url=url,
            canonical_url=url,
            final_url=url,
            acquisition_mode=AcquisitionMode.BROWSER,
            raw_html="<html></html>",
            rendered_html=None,
            markdown=None,
            blocks=(),
            tables=(),
            links=(),
            downloadable_documents=(),
            inventory=self.inventory,
            retrieved_at=NOW,
            content_hash="a" * 64,
            page_content_hash="b" * 64,
        )


@pytest.mark.asyncio
async def test_a_drop_fails_until_an_operator_resets_the_baseline() -> None:
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
        baselines = PostgresAcquisitionBaselineRepository(async_sessionmaker(engine))
        acquisition = _Acquisition()
        gate = CompletenessGatedAcquisitionService(
            acquisition, baselines, AcquisitionSettings()
        )

        await gate.acquire(URL)
        assert await baselines.get(URL) == GOOD

        acquisition.inventory = REDESIGNED
        with pytest.raises(AcquisitionError) as caught:
            await gate.acquire(URL)
        assert caught.value.reasons == ("tables 3 -> 0", "pdf_links 10 -> 4 (-60%)")
        assert await baselines.get(URL) == GOOD

        cleared = await baselines.reset(
            URL,
            reset_by="operator@example",
            offering_id="overdraft",
            reset_at=NOW + timedelta(hours=1),
        )
        assert cleared == GOOD
        assert await baselines.get(URL) is None

        await gate.acquire(URL)
        assert await baselines.get(URL) == REDESIGNED

        async with engine.connect() as session:
            row = (
                await session.exec_driver_sql(
                    "SELECT reset_by, recorded_at IS NOT NULL FROM acquisition_baselines"
                )
            ).one()
            assert tuple(row) == ("operator@example", True)
            event = (
                await session.exec_driver_sql(
                    "SELECT event_type, payload->>'offering_id', "
                    "payload->'previous_inventory'->>'tables' FROM audit_events"
                )
            ).one()
            assert tuple(event) == ("acquisition.baseline_reset", "overdraft", "3")
    finally:
        await engine.dispose()
