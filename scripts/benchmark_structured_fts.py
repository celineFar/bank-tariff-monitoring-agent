"""Benchmark scoped English and Armenian PostgreSQL FTS over accepted projections.

Usage: uv run python scripts/benchmark_structured_fts.py --offering consumer_standard
The result is a local latency sample, not a production SLO measurement.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from time import perf_counter

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.domain.models import OfferingId, ProductType
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
)


async def _benchmark(offering: OfferingId, iterations: int) -> dict[str, object]:
    settings = get_settings()
    engine = create_async_engine(settings.database.url.get_secret_value())
    try:
        repository = PostgresStructuredTariffQueryRepository(async_sessionmaker(engine))
        results = []
        query_pair = (
            (("en", "consumer loan"), ("hy", "սպառողական վարկ"))
            if offering.product is ProductType.CONSUMER_LOAN
            else (("en", "mortgage loan"), ("hy", "հիփոթեքային վարկ"))
        )
        for language, query in query_pair:
            timings = []
            hits = 0
            for _ in range(iterations):
                started = perf_counter()
                found = await repository.lexical_units(
                    bank="ameria",
                    product=offering.product,
                    offering_ids=(offering,),
                    query=query,
                    limit=8,
                )
                timings.append((perf_counter() - started) * 1000)
                hits = len(found)
            sorted_timings = sorted(timings)
            results.append(
                {
                    "language": language,
                    "hits": hits,
                    "median_ms": round(statistics.median(timings), 2),
                    "p95_ms": round(
                        sorted_timings[max(0, int(iterations * 0.95) - 1)], 2
                    ),
                }
            )
        return {
            "offering": offering.value,
            "iterations": iterations,
            "queries": results,
        }
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offering", choices=[item.value for item in OfferingId], required=True
    )
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 100:
        parser.error("iterations must be 1..100")
    print(
        json.dumps(
            asyncio.run(_benchmark(OfferingId(args.offering), args.iterations)),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
