"""Shared database and seeding helpers for the deliverable demonstrations."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.catalog import SeedCatalog, SeedCatalogEntry
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    RunCommand,
    RunStatus,
    RunTrigger,
    SnapshotAttempt,
)
from app.domain.semantic_extraction import SemanticExtractionResult
from app.repositories.monitoring import (
    PostgresRunRepository,
    PostgresSnapshotRepository,
)
from app.services.snapshot_lifecycle import build_snapshot_attempt
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


async def claim_execution(
    sessions: async_sessionmaker[AsyncSession],
    product: ProductType,
    offering_id: OfferingId,
) -> tuple[UUID, UUID]:
    """Open one offering execution the way a worker does, and return its ids."""
    runs = PostgresRunRepository(sessions)
    submitted = await runs.submit(
        RunCommand(product=product, offering_id=offering_id, trigger=RunTrigger.API)
    )
    claimed = await runs.claim_next("demonstration")
    if claimed is None:
        raise DemonstrationError(f"no run could be claimed for {offering_id.value}")
    execution = await runs.create_offering_execution(
        submitted.run.id, product, offering_id
    )
    execution = await runs.start_offering_execution(execution.id)
    return submitted.run.id, execution.id


async def accept_snapshot(
    sessions: async_sessionmaker[AsyncSession],
    spec: SnapshotSpec,
    *,
    previous: SnapshotAttempt | None = None,
) -> SnapshotAttempt:
    """Move one synthetic offering through the real run lifecycle to accepted."""
    run_id, execution_id = await claim_execution(
        sessions, spec.product, spec.offering_id
    )
    snapshot = build_snapshot(spec).model_copy(
        update={
            "run_id": run_id,
            "offering_execution_id": execution_id,
            "previous_accepted_snapshot_id": previous.id if previous else None,
        }
    )
    await PostgresSnapshotRepository(sessions).save_attempt(snapshot)
    await PostgresRunRepository(sessions).finish(run_id, RunStatus.SUCCEEDED)
    return snapshot


async def store_extraction(
    sessions: async_sessionmaker[AsyncSession],
    offering: SeedCatalogEntry,
    extraction: SemanticExtractionResult,
    *,
    previous: SnapshotAttempt | None = None,
) -> SnapshotAttempt:
    """Run one real extraction result through snapshot admission and persist it.

    The snapshot status is decided by `build_snapshot_attempt`, the same
    deterministic admission the monitoring pipeline applies, so a demonstration
    never hand-marks an extraction as accepted.
    """
    run_id, execution_id = await claim_execution(
        sessions, offering.product, offering.offering_id
    )
    snapshot = build_snapshot_attempt(
        run_id=run_id,
        offering_execution_id=execution_id,
        product=offering.product,
        offering_id=offering.offering_id,
        result=extraction,
        previous_accepted_snapshot_id=previous.id if previous else None,
        previous_accepted_snapshot=previous,
    )
    await PostgresSnapshotRepository(sessions).save_attempt(snapshot)
    await PostgresRunRepository(sessions).finish(run_id, RunStatus.SUCCEEDED)
    return snapshot


def offering_for_url(catalog: SeedCatalog, url: str) -> SeedCatalogEntry:
    """Find the catalog offering a recorded capture belongs to."""
    entry = catalog.find_by_seed_url(url)
    if entry is None:
        raise DemonstrationError(
            f"{url} is not a seed URL in the catalog, so the capture cannot be "
            "tied to an offering. Record a capture for a catalog seed URL."
        )
    return entry


def money(value) -> str:
    return f"{value:,}".replace(",", " ")


CONSUMER = OfferingId.CONSUMER_STANDARD
