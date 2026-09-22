"""Audit or rebuild accepted tariff projections without Gemini calls.

Usage: uv run python scripts/backfill_structured_tariffs.py --batch-size 50
       uv run python scripts/backfill_structured_tariffs.py --apply --batch-size 50
The default is a read-only projection audit. --apply writes one offering atomically.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.services.structured_backfill import StructuredProjectionBackfill


async def _run(batch_size: int, apply: bool, offering_id: str | None):
    settings = get_settings()
    engine = create_async_engine(settings.database.url.get_secret_value())
    try:
        backfill = StructuredProjectionBackfill(async_sessionmaker(engine))
        scopes = await backfill.scopes()
        results = []
        for bank, product, offering in scopes:
            if offering_id is not None and offering != offering_id:
                continue
            results.append(
                asdict(
                    await backfill.run_scope(
                        bank,
                        product,
                        offering,
                        batch_size=batch_size,
                        apply=apply,
                    )
                )
            )
        return {"apply": apply, "scopes": results}
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--offering-id")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 500:
        parser.error("batch-size must be 1..500")
    print(
        json.dumps(
            asyncio.run(_run(args.batch_size, args.apply, args.offering_id)),
            default=str,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
