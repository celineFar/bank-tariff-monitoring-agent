"""Report deterministic structured-retrieval metrics for the 25 target questions.

Model-free and read-only; it uses the synthetic evaluation corpus, not the
database. Model call, token, cache-saving, and cost figures come from
`scripts/model_cost_report.py` against the usage ledger.

Usage: uv run python scripts/structured_eval_metrics.py [--full]
"""

from __future__ import annotations

import argparse
import asyncio
import json

from tests.eval.structured_metrics import measure


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full", action="store_true", help="include the per-question outcomes"
    )
    args = parser.parse_args()
    report = asyncio.run(measure()).as_dict()
    if not args.full:
        report.pop("outcomes")
    print(json.dumps(report, default=str, indent=2))


if __name__ == "__main__":
    main()
