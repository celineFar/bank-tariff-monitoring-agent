#!/usr/bin/env python3
"""Controlled failures: three real runs fail, and the tariff data is untouched.

Runs against the persistent demonstration stack (../demo-stack). For each
failure the demo worker is restarted with one overlay from failures/, a real
monitoring run is submitted through the API, and its outcome is read back from
the database. Before the first failure and after the last one, the script
fingerprints every table that holds tariff data and asks the API for the current
tariff, then checks that nothing changed.

    python3 failure_demo.py                       # every failure
    python3 failure_demo.py --failure timeout     # one (repeatable)

The overlay is the only artificial part of each failure: the pipeline, the
network, the bank's site and Gemini are real. The normal worker is restored at
the end, even after an error. Writes output/report.md.

Standard library only. Prerequisite, once: ../demo-stack/stack.py up, then
baseline.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "demo-stack"))

import stack  # noqa: E402

OUTPUT = HERE / "output" / "report.md"
PRODUCT, OFFERING = stack.BASELINE_OFFERING
# Every table a monitoring run writes tariff data into.
TARIFF_TABLES = (
    "tariff_snapshots",
    "tariff_facts",
    "fact_evidence",
    "tariff_changes",
    "snapshot_documents",
    "human_reviews",
)
LOG_SIGNAL = re.compile(
    r"error|fail|timeout|timed out|not_found|404|too large|size|refus|retry",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Failure:
    name: str
    title: str
    change: str
    expected_code: str

    @property
    def overlay(self) -> Path:
        return HERE / "failures" / f"{self.name}.yml"


FAILURES = (
    Failure(
        "timeout",
        "The bank's site does not answer",
        "inside the worker, `ameriabank.am` resolves to 192.0.2.1, an address "
        "routed nowhere",
        "source.timeout",
    ),
    Failure(
        "model-failure",
        "The model provider fails",
        "source discovery uses the retired `gemini-2.5-flash-lite`, with no "
        "fallback model",
        "source.model_failed",
    ),
    Failure(
        "size-limit",
        "A safety limit refuses the source",
        "the download size cap is lowered from 25 MB to 50 KB",
        "source.size_rejected",
    ),
)


# --------------------------------------------------------------------------
# state of the demo database


def fingerprints() -> dict[str, dict]:
    """Row count and a digest of every row, per tariff table."""
    union = " UNION ALL ".join(
        f"""SELECT '{table}' AS name, count(*) AS rows,
                   md5(coalesce(string_agg(t::text, '|' ORDER BY t::text), ''))
                     AS digest
            FROM {table} t"""
        for table in TARIFF_TABLES
    )
    return {row["name"]: row for row in stack.sql(union)}


def show_state(report: stack.Report, label: str) -> tuple[dict, dict]:
    tables = fingerprints()
    answer = stack.current_tariff(PRODUCT, OFFERING)
    report.say(f"Tariff tables ({label}):")
    report.table(
        ["Table", "Rows", "Content digest"],
        [
            [name, row["rows"], f"`{row['digest'][:12]}`"]
            for name, row in tables.items()
        ],
    )
    report.say(
        f"`GET /tariffs/current` for {OFFERING}: snapshot "
        f"`{str(answer['snapshot_id'])[:8]}`, accepted {answer['accepted_at']}, "
        f"freshness `{answer['freshness']}`, interest rates {answer['rates']}."
    )
    return tables, answer


# --------------------------------------------------------------------------
# one failure


def run_failure(failure: Failure, stamp: str, report: stack.Report) -> dict:
    report.heading(f"Failure: {failure.title} ({failure.name})")
    report.say(
        f"Artificial part: {failure.change} (`failures/{failure.overlay.name}`)."
    )
    stack.restart_worker((failure.overlay,))
    since = datetime.now(UTC).isoformat()

    run = stack.submit_run(PRODUCT, OFFERING, f"failure-demo-{stamp}-{failure.name}")
    report.say(f"Submitted run `{run['id'][:8]}` through `POST /api/v1/runs`.")
    started = time.monotonic()
    run = stack.wait_for_run(run["id"], timeout=900)
    elapsed = time.monotonic() - started

    run_id = run["id"]
    execution = stack.sql(
        f"""SELECT status, current_stage, failure_code, failure_detail
            FROM offering_executions WHERE run_id = '{run_id}'"""
    )
    execution = execution[0] if execution else {}
    usage = stack.sql(
        f"""SELECT count(*) AS calls,
                   coalesce(sum(estimated_cost_usd), 0) AS usd,
                   string_agg(DISTINCT model_id || ' ' || outcome, ', ') AS outcomes
            FROM model_call_usage WHERE run_id = '{run_id}'"""
    )[0]
    written = stack.sql(
        f"""SELECT (SELECT count(*) FROM tariff_snapshots WHERE run_id = '{run_id}')
                     AS snapshots,
                   (SELECT count(*) FROM tariff_changes WHERE run_id = '{run_id}')
                     AS changes"""
    )[0]
    code = execution.get("failure_code") or run.get("failure_code")
    detail = execution.get("failure_detail") or run.get("failure_detail") or ""

    report.table(
        ["Outcome", "Value"],
        [
            ["Run status", f"`{run['status']}` after {elapsed:.0f}s"],
            ["Failed at stage", f"`{execution.get('current_stage')}`"],
            ["Failure code", f"`{code}` (expected `{failure.expected_code}`)"],
            ["Recorded cause", f"`{detail.replace('|', '/')[:300] or '-'}`"],
            ["Operator is told", stack.explain_failure(code)],
            [
                "Model calls",
                f"{usage['calls']} ({usage['outcomes'] or 'none'}), "
                f"${float(usage['usd']):.4f}",
            ],
            ["Snapshots written", str(written["snapshots"])],
            ["Changes written", str(written["changes"])],
        ],
    )
    logs = stack.compose(
        "logs", "--no-log-prefix", "--since", since, "worker", capture=True
    ).stdout.splitlines()
    evidence = [line for line in logs if LOG_SIGNAL.search(line)][-4:]
    if evidence:
        report.say("Worker log:")
        report.lines.append("```text")
        for line in evidence:
            print(f"      {line[:200]}")
            report.lines.append(line[:300])
        report.lines += ["```", ""]
    return {
        "failure": failure,
        "status": run["status"],
        "code": code,
        "snapshots": written["snapshots"],
        "changes": written["changes"],
        "usd": float(usage["usd"]),
    }


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--failure",
        action="append",
        choices=[failure.name for failure in FAILURES],
        help="run only this failure (repeatable; default: all)",
    )
    args = parser.parse_args()
    selected = [f for f in FAILURES if not args.failure or f.name in args.failure]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")

    report = stack.Report()
    report.lines = [
        "# Controlled failures",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M UTC} by `failure_demo.py` "
        f"against the demonstration stack (Compose project `{stack.PROJECT}`). "
        f"Offering: `{OFFERING}`.",
    ]

    stack.wait_for_api(timeout=30)
    if not any(row["offering_id"] == OFFERING for row in stack.accepted_snapshots()):
        sys.exit(
            f"No accepted {OFFERING} snapshot in the demo database. Run once:\n"
            "    python3 ../demo-stack/stack.py baseline"
        )

    report.heading("Before: what the demo database holds")
    before_tables, before_answer = show_state(report, "before")

    results = []
    try:
        for failure in selected:
            results.append(run_failure(failure, stamp, report))
    finally:
        print("\n    Restoring the normal worker ...", flush=True)
        stack.restart_worker()

    report.heading("After: what the demo database holds")
    after_tables, after_answer = show_state(report, "after")

    report.heading("Was each failure safe?")
    checks: list[tuple[str, bool, str]] = []
    for result in results:
        name = result["failure"].name
        checks.append(
            (
                f"{name}: the run failed",
                result["status"] == "failed",
                f"status `{result['status']}`",
            )
        )
        checks.append(
            (
                f"{name}: failed with the expected code",
                result["code"] == result["failure"].expected_code,
                f"`{result['code']}`",
            )
        )
        checks.append(
            (
                f"{name}: wrote no snapshot and no change",
                result["snapshots"] == 0 and result["changes"] == 0,
                f"{result['snapshots']} snapshots, {result['changes']} changes",
            )
        )
    changed = [
        name
        for name in TARIFF_TABLES
        if before_tables[name]["digest"] != after_tables[name]["digest"]
    ]
    checks.append(
        (
            "every tariff table is byte-for-byte unchanged",
            not changed,
            f"changed: {', '.join(changed)}"
            if changed
            else f"{len(TARIFF_TABLES)} of {len(TARIFF_TABLES)} digests equal",
        )
    )
    same_answer = all(
        before_answer[key] == after_answer[key]
        for key in ("snapshot_id", "accepted_at", "tariff_sha256")
    )
    checks.append(
        (
            "the API still serves the same accepted tariff",
            same_answer,
            f"snapshot `{str(after_answer['snapshot_id'])[:8]}`, rates "
            f"{after_answer['rates']}",
        )
    )
    checks.append(
        (
            "the normal worker is back",
            stack.worker_running(),
            "running without a failure overlay",
        )
    )
    report.table(
        ["", "Check", "Observed"],
        [["PASS" if ok else "FAIL", title, observed] for title, ok, observed in checks],
    )
    spend = sum(result["usd"] for result in results)
    report.say(f"Model spend for these failures: ${spend:.4f}.")
    passed = all(ok for _, ok, _ in checks)
    report.say(f"RESULT: {'PASS' if passed else 'FAIL'}")

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(report.lines).strip() + "\n", encoding="utf-8")
    print(f"\n    Wrote {OUTPUT.relative_to(HERE)}")
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except stack.StackError as exc:
        sys.exit(f"error: {exc}")
