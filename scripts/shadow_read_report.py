"""Shadow-read the legacy and structured answer paths over representative queries.

Read-only. By default only the structured path runs, so the report costs no
model call. ``--with-legacy`` additionally runs the old RAG path, which does
call Gemini for a query embedding and one answer generation per case.

Usage:
    uv run python scripts/shadow_read_report.py [--with-legacy] [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from app.config import get_settings
from app.runtime import build_application_container
from app.services.structured_shadow_read import (
    DEFAULT_SHADOW_CASES,
    StructuredShadowReader,
)


async def _report(*, with_legacy: bool, limit: int) -> dict[str, object]:
    container = build_application_container(get_settings())
    try:
        reader = StructuredShadowReader(
            container.request_resolver,
            container.structured_query_service,
            container.answer_service if with_legacy else None,
        )
        result = await reader.run(DEFAULT_SHADOW_CASES[:limit])
    finally:
        await container.close()
    return {
        "generated_at": result.generated_at.isoformat(),
        "legacy_enabled": result.legacy_enabled,
        "cases": len(result.observations),
        "agreement_counts": result.agreement_counts,
        "structured_status_counts": result.structured_status_counts,
        "legacy_status_counts": result.legacy_status_counts,
        "structured_answer_rate": round(result.structured_answer_rate, 4),
        "gate_passed": result.gate_passed,
        "gate_reason": result.gate_reason,
        "mismatches": [asdict(item) for item in result.mismatches],
        "observations": [asdict(item) for item in result.observations],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-legacy",
        action="store_true",
        help="also run the legacy RAG path; this spends Gemini credits",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=len(DEFAULT_SHADOW_CASES),
        help="run only the first N representative cases",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(_report(with_legacy=args.with_legacy, limit=args.limit)),
            default=str,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
