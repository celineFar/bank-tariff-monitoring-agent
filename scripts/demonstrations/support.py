"""Shared database and seeding helpers for the deliverable demonstrations."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.models import OfferingId
from app.domain.monitoring import (
    RunCommand,
    RunStatus,
    RunTrigger,
    SnapshotAttempt,
)
from app.repositories.monitoring import (
    PostgresRunRepository,
    PostgresSnapshotRepository,
)
from tests.fixtures.structured_tariffs import SnapshotSpec, build_snapshot


class DemonstrationError(RuntimeError):
    pass


def demonstration_database_url() -> str:
    """Only ever run a demonstration against a disposable `_test` database."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        raise DemonstrationError(
            "TEST_DATABASE_URL is required, for example "
            "postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test"
        )
    name = make_url(url).database or ""
    if not name.endswith("_test"):
        raise DemonstrationError(
            "refusing to run a demonstration against a database that does not "
            "end in '_test'"
        )
    return url


@asynccontextmanager
async def demonstration_sessions(
    *, reset: bool = True
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(demonstration_database_url())
    try:
        if reset:
            async with engine.begin() as connection:
                await connection.execute(text("TRUNCATE monitoring_runs CASCADE"))
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def accept_snapshot(
    sessions: async_sessionmaker[AsyncSession],
    spec: SnapshotSpec,
    *,
    previous: SnapshotAttempt | None = None,
) -> SnapshotAttempt:
    """Move one synthetic offering through the real run lifecycle to accepted."""
    runs = PostgresRunRepository(sessions)
    submitted = await runs.submit(
        RunCommand(
            product=spec.product,
            offering_id=spec.offering_id,
            trigger=RunTrigger.API,
        )
    )
    claimed = await runs.claim_next("demonstration")
    if claimed is None:
        raise DemonstrationError(
            f"no run could be claimed for {spec.offering_id.value}"
        )
    execution = await runs.create_offering_execution(
        submitted.run.id, spec.product, spec.offering_id
    )
    execution = await runs.start_offering_execution(execution.id)
    snapshot = build_snapshot(spec).model_copy(
        update={
            "run_id": submitted.run.id,
            "offering_execution_id": execution.id,
            "previous_accepted_snapshot_id": previous.id if previous else None,
        }
    )
    await PostgresSnapshotRepository(sessions).save_attempt(snapshot)
    await runs.finish(submitted.run.id, RunStatus.SUCCEEDED)
    return snapshot


def money(value) -> str:
    return f"{value:,}".replace(",", " ")


CONSUMER = OfferingId.CONSUMER_STANDARD
