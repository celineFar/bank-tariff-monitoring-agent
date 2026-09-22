"""Load the synthetic structured evaluation corpus into a disposable database.

The corpus is fabricated test data, never observed Ameriabank tariffs, so the
script refuses any database whose name does not end in `_test`. It accepts each
offering through the real run lifecycle, records the accepted mortgage change
set, and backfills the structured projections. No model call is made.

Usage:
    TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test \
      uv run python scripts/seed_evaluation_corpus.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.models import OfferingId
from app.domain.monitoring import (
    RunCommand,
    RunStatus,
    RunTrigger,
    SnapshotChange,
    SnapshotChangeSet,
)
from app.repositories.monitoring import (
    PostgresRunRepository,
    PostgresSnapshotRepository,
)
from app.services.structured_backfill import StructuredProjectionBackfill
from tests.fixtures.evaluation_corpus import CORPUS_SPECS, PREVIOUS_MORTGAGE_SPEC
from tests.fixtures.structured_tariffs import build_snapshot


def _database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        raise SystemExit("TEST_DATABASE_URL is required")
    name = make_url(url).database or ""
    if not name.endswith("_test"):
        raise SystemExit("refusing to seed a database that does not end in '_test'")
    return url


async def _accept(sessions, spec):
    runs = PostgresRunRepository(sessions)
    submitted = await runs.submit(
        RunCommand(
            product=spec.product, offering_id=spec.offering_id, trigger=RunTrigger.API
        )
    )
    claimed = await runs.claim_next("eval-seed")
    if claimed is None:
        raise SystemExit(f"could not claim a run for {spec.offering_id.value}")
    execution = await runs.create_offering_execution(
        submitted.run.id, spec.product, spec.offering_id
    )
    execution = await runs.start_offering_execution(execution.id)
    snapshot = build_snapshot(spec).model_copy(
        update={
            "run_id": submitted.run.id,
            "offering_execution_id": execution.id,
        }
    )
    await PostgresSnapshotRepository(sessions).save_attempt(snapshot)
    await runs.finish(submitted.run.id, RunStatus.SUCCEEDED)
    return snapshot


async def _seed(*, reset: bool) -> dict[str, object]:
    engine = create_async_engine(_database_url())
    try:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        if reset:
            async with engine.begin() as connection:
                await connection.execute(text("TRUNCATE monitoring_runs CASCADE"))
        backfill = StructuredProjectionBackfill(sessions)
        previous = await _accept(sessions, PREVIOUS_MORTGAGE_SPEC)
        published = {}
        for spec in CORPUS_SPECS:
            current = await _accept(sessions, spec)
            if spec.offering_id is OfferingId.MORTGAGE_PRIMARY:
                await PostgresSnapshotRepository(sessions).save_changes(
                    SnapshotChangeSet(
                        id=uuid4(),
                        run_id=current.run_id,
                        product=spec.product,
                        offering_id=spec.offering_id,
                        previous_snapshot_id=previous.id,
                        current_snapshot_id=current.id,
                        changes=(
                            SnapshotChange(
                                field="interest_rate",
                                previous="10",
                                current="11",
                                previous_display="10% minimum nominal rate",
                                current_display="11% minimum nominal rate",
                            ),
                        ),
                        created_at=datetime.now(UTC),
                    )
                )
            result = await backfill.run_scope(
                "ameria", spec.product.value, spec.offering_id.value, apply=True
            )
            published[spec.offering_id.value] = result.published
        return {"offerings": published, "previous_versions": 1}
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="truncate monitoring data before seeding",
    )
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_seed(reset=args.reset)), indent=2))


if __name__ == "__main__":
    main()
