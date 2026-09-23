"""Read redacted model usage/cost aggregates from PostgreSQL.

Usage: uv run python scripts/model_cost_report.py --days 7 --budget-usd 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.services.model_call_usage import PostgresModelCallUsageRepository


async def _report(days: int, budget: Decimal | None) -> dict[str, object]:
    settings = get_settings()
    engine = create_async_engine(settings.database.url.get_secret_value())
    try:
        repository = PostgresModelCallUsageRepository(async_sessionmaker(engine))
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        groups = await repository.totals(from_time=start, to_time=end)
        result: dict[str, object] = {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "groups": groups,
        }
        if budget is not None:
            result["budget"] = await repository.budget_status(
                from_time=start, to_time=end, threshold_usd=budget
            )
        return result
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--budget-usd", type=Decimal)
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be positive")
    if args.budget_usd is not None and args.budget_usd <= 0:
        parser.error("--budget-usd must be positive")
    print(
        json.dumps(
            asyncio.run(_report(args.days, args.budget_usd)), default=str, indent=2
        )
    )


if __name__ == "__main__":
    main()
