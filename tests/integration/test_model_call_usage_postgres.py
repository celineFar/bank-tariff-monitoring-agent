"""The call ledger is additive and safe across duplicate worker retries."""

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.model_call_usage import (
    ModelCallUsage,
    PostgresModelCallUsageRepository,
)

pytestmark = pytest.mark.postgres


@pytest.mark.asyncio
async def test_usage_ledger_is_idempotent_and_aggregates_known_and_unknown_cost() -> (
    None
):
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
        repository = PostgresModelCallUsageRepository(async_sessionmaker(engine))
        now = datetime(2026, 9, 22, tzinfo=UTC)
        usage = ModelCallUsage(
            call_id="call-1",
            attempt=1,
            called_at=now,
            stage="rag.answer_generation",
            operation="generate_content",
            model_id="gemini-3.7-flash",
            outcome="succeeded",
            latency_ms=100,
            input_tokens=1000,
            output_tokens=200,
        )
        await repository.record(usage)
        await repository.record(usage)
        await repository.record(
            ModelCallUsage(
                call_id="call-2",
                attempt=1,
                called_at=now,
                stage="rag.answer_generation",
                operation="generate_content",
                model_id="gemini-3.7-flash",
                outcome="failed",
                latency_ms=20,
                error_class="TimeoutError",
            )
        )
        totals = await repository.totals(
            from_time=now - timedelta(days=1), to_time=now + timedelta(days=1)
        )
        assert len(totals) == 1
        assert totals[0]["calls"] == 2
        assert totals[0]["failures"] == 1
        assert totals[0]["unknown_calls"] == 1
        assert totals[0]["known_cost_usd"] == Decimal("0.0015")
    finally:
        await engine.dispose()
