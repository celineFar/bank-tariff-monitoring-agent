"""Run the assignment deliverable demonstrations and check their success criteria.

Each scenario maps to a numbered deliverable in
``Project Documents/System Description.md`` section 7. A scenario prints the
steps it performed and then evaluates named criteria; the process exits 0 only
when every criterion of every selected scenario passed.

Scenarios are deterministic and offline. They drive the real application
services against a disposable `_test` database and fixture data, so a live
demonstration does not depend on the bank website or spend model credits.

Usage:
    docker compose --profile test up -d db-test
    for m in migrations/*.sql; do
      docker compose exec -T db-test psql -v ON_ERROR_STOP=1 \
        -U tariff -d tariff_monitor_test < "$m"
    done
    TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test \
      uv run python scripts/run_demonstration.py --scenario all
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from scripts.demonstrations import (
    ScenarioResult,
    change_detection,
    document_processing,
    extraction,
    failures,
    hitl,
    render,
    render_markdown,
)
from scripts.demonstrations.runs import next_run_directory
from scripts.demonstrations.support import DemonstrationError

SCENARIOS = {
    "extraction": (extraction.run, "Deliverable 9 — normal tariff extraction"),
    "change-detection": (
        change_detection.run,
        "Deliverable 10 — tariff change detection",
    ),
    "document-processing": (
        document_processing.run,
        "Deliverable 11 — digital PDF and scanned-page fallback",
    ),
    "hitl": (hitl.run, "Deliverable 12 — human-in-the-loop review"),
    "failures": (failures.run, "Deliverable 13 — controlled failure scenarios"),
}
ORDER = list(SCENARIOS)
DEFAULT_AUDIT_DIRECTORY = Path("artifacts/demonstrations")


async def _run(names: list[str], audit_root: Path | None) -> list[ScenarioResult]:
    # Each invocation claims its own run_NNN, so the transcripts of an earlier
    # run stay on disk instead of being overwritten by this one.
    audit_directory = None if audit_root is None else next_run_directory(audit_root)
    if audit_directory is not None:
        print(f"Writing transcripts to {audit_directory}", flush=True)
    results: list[ScenarioResult] = []
    for name in names:
        runner, _ = SCENARIOS[name]
        result = await runner()
        print(render(result), flush=True)
        if audit_directory is not None:
            path = audit_directory / f"{name}.md"
            path.write_text(render_markdown(result), encoding="utf-8")
            print(f"\nWrote {path}", flush=True)
        results.append(result)
    return results


def _summarize(results: list[ScenarioResult]) -> bool:
    print("")
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    width = max(len(item.deliverable) for item in results)
    for item in results:
        passed = sum(criterion.passed for criterion in item.criteria)
        print(
            f"[{'PASS' if item.passed else 'FAIL'}] "
            f"{item.deliverable:<{width}}  {passed}/{len(item.criteria)} criteria  "
            f"{item.title}"
        )
    overall = all(item.passed for item in results)
    print("")
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    return overall


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=[*ORDER, "all"],
        help="scenario to run; repeatable. Defaults to all.",
    )
    parser.add_argument(
        "--list", action="store_true", help="list the scenarios and exit"
    )
    parser.add_argument(
        "--audit-directory",
        type=Path,
        default=DEFAULT_AUDIT_DIRECTORY,
        help=(
            "transcript container; creates run_NNN inside it and writes one "
            f"markdown transcript per scenario there (default: "
            f"{DEFAULT_AUDIT_DIRECTORY}); pass --no-audit to skip"
        ),
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="print to the terminal only, writing no markdown transcript",
    )
    args = parser.parse_args()

    if args.list:
        for name in ORDER:
            print(f"{name:<22} {SCENARIOS[name][1]}")
        return 0

    chosen = args.scenario or ["all"]
    names = ORDER if "all" in chosen else [n for n in ORDER if n in set(chosen)]
    try:
        audit = None if args.no_audit else args.audit_directory
        results = asyncio.run(_run(names, audit))
    except DemonstrationError as exc:
        print(f"demonstration setup failed: {exc}", file=sys.stderr)
        return 2
    return 0 if _summarize(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
