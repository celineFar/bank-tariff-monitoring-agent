"""Report operational metrics for monitoring runs from PostgreSQL.

Usage: uv run python scripts/run_metrics_report.py --days 30
       uv run python scripts/run_metrics_report.py --days 7 --section extraction_completeness
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.services.run_metrics import RunMetricsRepository


async def _report(days: int, section: str | None) -> dict[str, object]:
    settings = get_settings()
    engine = create_async_engine(settings.database.url.get_secret_value())
    try:
        repository = RunMetricsRepository(async_sessionmaker(engine))
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        collected = await repository.collect(start, end)
        if section is None:
            return collected
        if section not in collected:
            available = ", ".join(key for key in collected if key != "window")
            raise SystemExit(f"unknown section {section!r}; available: {available}")
        return {"window": collected["window"], section: collected[section]}
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--section",
        help="report a single section instead of all of them",
    )
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be positive")
    print(
        json.dumps(asyncio.run(_report(args.days, args.section)), default=str, indent=2)
    )


if __name__ == "__main__":
    main()
