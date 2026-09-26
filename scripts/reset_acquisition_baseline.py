"""Accept a redesigned bank page by clearing its acquisition baseline.

When a seed page's acquisition drops sharply against the last good one -- its
tariff tables gone, most PDF links gone -- the offering fails with
`source.incomplete_content` and keeps failing. That is deliberate: a broken
render and a real redesign look the same to the pipeline, and deciding which
one it is belongs to a person. After checking the page, run:

    uv run python -m scripts.reset_acquisition_baseline <offering_id>

The next acquisition that passes the absolute floor records a new baseline.
The reset is written to `audit_events` with who ran it and the inventory that
was cleared. This is an operator tool only; it is never exposed to the model.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import load_settings
from app.config.seed_catalog import load_seed_catalog
from app.repositories.acquisition_baselines import (
    PostgresAcquisitionBaselineRepository,
)


async def reset(offering_id: str, operator: str) -> int:
    settings = load_settings()
    catalog = load_seed_catalog(allowed_hosts=settings.http.allowed_source_hosts)
    offering = next(
        (item for item in catalog.offerings if item.offering_id.value == offering_id),
        None,
    )
    if offering is None:
        known = ", ".join(sorted(item.offering_id.value for item in catalog.offerings))
        print(f"Unknown offering {offering_id!r}. Known: {known}", file=sys.stderr)
        return 2
    engine = create_async_engine(settings.database.url.get_secret_value())
    try:
        previous = await PostgresAcquisitionBaselineRepository(
            async_sessionmaker(engine, expire_on_commit=False)
        ).reset(str(offering.seed_url), reset_by=operator, offering_id=offering_id)
    finally:
        await engine.dispose()
    cleared = (
        json.dumps(previous.model_dump(mode="json")) if previous else "no baseline"
    )
    print(f"Reset the acquisition baseline of {offering_id} ({offering.seed_url}).")
    print(f"Cleared: {cleared}. The next passing run records a new baseline.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("offering_id", help="the seed catalog offering id")
    parser.add_argument(
        "--operator",
        default=getpass.getuser(),
        help="who is resetting it, for the audit record (default: current user)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(reset(args.offering_id, args.operator)))


if __name__ == "__main__":
    main()
