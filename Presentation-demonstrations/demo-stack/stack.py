#!/usr/bin/env python3
"""The persistent demonstration stack, and helpers the demonstrations share.

    python3 stack.py up         start db, api and worker (creates the database once)
    python3 stack.py baseline   one real monitoring run, to have accepted data
    python3 stack.py status     what the demo database holds now
    python3 stack.py chat       the chat CLI against the demo stack (reviews)
    python3 stack.py logs       follow the demo worker's log
    python3 stack.py checkpoint save|restore|list [NAME]
                                save or restore monitoring state; caches are kept
    python3 stack.py down       stop the stack; the database is kept
    python3 stack.py destroy    stop it and delete the demo database

Standard library only: it drives `docker compose` and the stack's HTTP API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PROJECT = "tariff-demo"
OVERLAY = HERE / "compose.demo.yml"
API = "http://127.0.0.1:8091/api/v1"
BASELINE_OFFERING = ("consumer_loan", "overdraft")
WORKER_LOG = "/var/log/tariff-monitor/worker.log"


class StackError(RuntimeError):
    pass


def compose(
    *args: str,
    overlays: tuple[Path, ...] = (),
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*compose_command(overlays), *args],
        cwd=REPO,
        check=check,
        text=True,
        capture_output=capture,
    )


def sql(query: str) -> list[dict]:
    """Rows of a read-only query against the demo database, as dicts."""
    wrapped = f"SELECT coalesce(json_agg(q), '[]'::json) FROM ({query}) q"
    result = compose(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "tariff",
        "-d",
        "tariff_monitor",
        "-v",
        "ON_ERROR_STOP=1",
        "-Atc",
        wrapped,
        capture=True,
    )
    return json.loads(result.stdout)


def api(method: str, path: str, body: dict | None = None, headers=None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raise StackError(
            f"{method} {path} -> {exc.code}: {exc.read().decode()}"
        ) from exc


def wait_for_api(timeout: float = 180) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            api("GET", "/healthz")
            return
        except (StackError, OSError):
            time.sleep(2)
    raise StackError(f"the demo API did not become healthy within {timeout:.0f}s")


def submit_run(product: str, offering_id: str, key: str) -> dict:
    submitted = api(
        "POST",
        "/runs",
        {"product": product, "offering_id": offering_id},
        headers={"Idempotency-Key": key},
    )
    return submitted["run"]


def wait_for_run(run_id: str, timeout: float = 1200, quiet: bool = False) -> dict:
    """Poll until the run ends or pauses for review."""
    deadline = time.monotonic() + timeout
    started = time.monotonic()
    last = None
    while time.monotonic() < deadline:
        run = api("GET", f"/runs/{run_id}")
        if run["status"] != last and not quiet:
            print(f"    {time.monotonic() - started:5.0f}s  run {run['status']}")
            last = run["status"]
        if run["status"] in {
            "succeeded",
            "partial_success",
            "failed",
            "awaiting_review",
        }:
            return run
        time.sleep(3)
    raise StackError(f"run {run_id} did not finish within {timeout:.0f}s")


def explain_failure(code: str | None) -> str:
    """The application's own operator sentence for a failure code."""
    script = (
        "import sys; from app.services.failure_mapping import explain_failure_code;"
        "print(explain_failure_code(sys.argv[1] or None))"
    )
    result = compose(
        "exec",
        "-T",
        "api",
        "/code/.venv/bin/python",
        "-W",
        "ignore",
        "-c",
        script,
        code or "",
        capture=True,
    )
    return result.stdout.strip().splitlines()[-1]


def worker_running() -> bool:
    result = compose("ps", "--status", "running", "-q", "worker", capture=True)
    return bool(result.stdout.strip())


def active_runs() -> list[dict]:
    return sql(
        """SELECT id, idempotency_key, status FROM monitoring_runs
           WHERE status IN ('queued', 'running')"""
    )


def require_idle(action: str) -> None:
    """Refuse to disturb a run someone else started on this shared stack."""
    busy = active_runs()
    if busy:
        keys = ", ".join(run["idempotency_key"] or str(run["id"])[:8] for run in busy)
        raise StackError(
            f"cannot {action}: a run is in progress ({keys}); retry when it ends"
        )


def restart_worker(overlays: tuple[Path, ...] = ()) -> None:
    """Recreate the worker with the given overlays (none: the normal worker)."""
    require_idle("restart the worker")
    compose(
        "up",
        "-d",
        "--no-build",
        "--force-recreate",
        "--no-deps",
        "worker",
        overlays=overlays,
        capture=True,
    )
    deadline = time.monotonic() + 60
    while not worker_running():
        if time.monotonic() > deadline:
            raise StackError("the demo worker did not start")
        time.sleep(1)
    # Let it finish importing and start polling the queue.
    time.sleep(8)


def accepted_snapshots() -> list[dict]:
    return sql(
        """SELECT offering_id, count(*) AS accepted, max(created_at) AS latest
           FROM tariff_snapshots WHERE status = 'accepted'
           GROUP BY offering_id ORDER BY offering_id"""
    )


# --------------------------------------------------------------------------
# reporting


class Report:
    """Prints as it goes and keeps the same lines for output/report.md."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def heading(self, text: str) -> None:
        print(f"\n==> {text}", flush=True)
        self.lines += ["", f"## {text}", ""]

    def say(self, text: str = "") -> None:
        print(f"    {text}" if text else "", flush=True)
        self.lines.append(text)

    def table(self, header: list[str], rows: list[list[str]]) -> None:
        widths = [
            max(len(str(cell)) for cell in column)
            for column in zip(header, *rows, strict=True)
        ]
        for row in (header, *rows):
            print(
                "    "
                + "  ".join(str(c).ljust(w) for c, w in zip(row, widths, strict=True))
            )
        self.lines += [
            "| " + " | ".join(header) + " |",
            "|" + "---|" * len(header),
            *("| " + " | ".join(str(c) for c in row) + " |" for row in rows),
            "",
        ]


def current_tariff(product: str, offering_id: str) -> dict:
    """What the API answers now for one offering."""
    result = api("GET", f"/tariffs/current?product={product}&offering_id={offering_id}")
    item = result["items"][0]
    tariff = item.get("normalized_tariff")
    digest = (
        hashlib.sha256(json.dumps(tariff, sort_keys=True).encode()).hexdigest()
        if tariff is not None
        else None
    )
    return {
        "snapshot_id": item.get("snapshot_id"),
        "accepted_at": item.get("accepted_at"),
        "freshness": item.get("freshness"),
        "tariff_sha256": digest,
        "rates": rate_summary(tariff),
        "pending_newer_review": item.get("pending_newer_review", False),
    }


def rate_summary(tariff: dict | None) -> str:
    """The interest rates, to show a person the data being protected.

    Each entry of `interest_rate.value` holds a `{min, max}` rate as strings.
    """
    entries = ((tariff or {}).get("interest_rate") or {}).get("value") or []
    rates = []
    for entry in entries:
        rate = entry.get("value") or {}
        low, high = (
            f"{float(bound):g}" if bound is not None else None
            for bound in (rate.get("min"), rate.get("max"))
        )
        if low and high and low != high:
            rates.append(f"{low}-{high}%")
        elif low or high:
            rates.append(f"{low or high}%")
    return ", ".join(rates) if rates else "none"


# --------------------------------------------------------------------------
# checkpoints
#
# A demonstration that publishes (a change, a review decision) has to start from
# the same state every time. A checkpoint is a dump of the demo database; a
# restore puts back monitoring and chat state only. Adapted from
# demo/bin/baseline.sh on branch demo/all-on-new-system.
#
# Two kinds of table survive a restore: the model caches, because every entry was
# paid for and keeps a repeated demo from re-paying (and from Gemini answering
# differently), and the spend ledger, because it is an audit record. State is
# deleted rather than truncated: the ledger references monitoring_runs ON DELETE
# SET NULL, so a delete keeps every spend row.
#
# Three tables look like caches and are state: review_decision_memory would
# answer a review before it is asked, acquisition_baselines would judge a page
# against a later run's inventory, and snapshot_documents decides a snapshot's
# active documents. Children come before parents.
STATE_TABLES = (
    "fact_evidence",
    "retrieval_units",
    "tariff_facts",
    "offering_profiles",
    "knowledge_chunks",
    "source_manifests",
    "human_reviews",
    "tariff_changes",
    "audit_events",
    "snapshot_documents",
    "knowledge_documents",
    "tariff_snapshots",
    "offering_executions",
    "monitoring_runs",
    "acquisition_snapshots",
    "acquisition_baselines",
    "review_decision_memory",
    "events",
    "sessions",
    "app_states",
    "user_states",
)
CHECKPOINTS = HERE / "runtime" / "checkpoints"
_SCRATCH = "tariff_monitor_checkpoint_scratch"


def _db_shell(script: str, **kwargs) -> subprocess.CompletedProcess[str]:
    return compose("exec", "-T", "db", "sh", "-c", script, **kwargs)


def _tables(database: str) -> set[str]:
    result = _db_shell(
        f'psql -U tariff -d {database} -Atc "SELECT table_name FROM '
        f"information_schema.tables WHERE table_schema = 'public'\"",
        capture=True,
    )
    return set(result.stdout.split())


def save_checkpoint(name: str) -> Path:
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINTS / f"{name}.dump"
    command = [*compose_command(), "exec", "-T", "db", "pg_dump", "-U", "tariff"]
    with path.open("wb") as dump:
        subprocess.run(
            [*command, "-d", "tariff_monitor", "--format=custom"],
            cwd=REPO,
            check=True,
            stdout=dump,
        )
    return path


def restore_checkpoint(name: str) -> None:
    path = CHECKPOINTS / f"{name}.dump"
    if not path.exists():
        raise StackError(f"no checkpoint '{name}' at {path}")
    require_idle(f"restore checkpoint '{name}'")
    _db_shell(
        f"dropdb -U tariff --if-exists {_SCRATCH} && createdb -U tariff {_SCRATCH}",
        capture=True,
    )
    with path.open("rb") as dump:
        subprocess.run(
            [
                *compose_command(),
                "exec",
                "-T",
                "db",
                "pg_restore",
                "-U",
                "tariff",
                "-d",
                _SCRATCH,
                "--no-owner",
            ],
            cwd=REPO,
            stdin=dump,
            capture_output=True,
        )
    live, saved = _tables("tariff_monitor"), _tables(_SCRATCH)
    clear = [table for table in STATE_TABLES if table in live]
    copy = [table for table in clear if table in saved]
    deletes = " ".join(f"DELETE FROM {table};" for table in clear)
    selected = " ".join(f"-t {table}" for table in copy)
    # tariff_snapshots references itself, so pg_dump warns that a data-only dump
    # may not load; --disable-triggers is what makes it load.
    result = _db_shell(
        f'psql -q -v ON_ERROR_STOP=1 -U tariff -d tariff_monitor -c "BEGIN; '
        f'{deletes} COMMIT;" && pg_dump -U tariff --data-only --disable-triggers '
        f"{selected} {_SCRATCH} 2>/dev/null | psql -q -v ON_ERROR_STOP=1 "
        f"-U tariff -d tariff_monitor >/dev/null && dropdb -U tariff {_SCRATCH}",
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        raise StackError(f"restore of '{name}' failed: {result.stderr.strip()}")


def compose_command(overlays: tuple[Path, ...] = ()) -> list[str]:
    command = ["docker", "compose", "-p", PROJECT]
    for path in (REPO / "docker-compose.yml", OVERLAY, *overlays):
        command += ["-f", str(path)]
    return command


# --------------------------------------------------------------------------
# commands


def cmd_up(_: argparse.Namespace) -> None:
    compose("up", "-d", "--no-build", "db", "api", "worker")
    wait_for_api()
    print(f"Demo stack is up: API at {API}, project '{PROJECT}'.")


def cmd_baseline(args: argparse.Namespace) -> None:
    wait_for_api()
    product, offering = args.product, args.offering
    existing = [row for row in accepted_snapshots() if row["offering_id"] == offering]
    if existing and not args.force:
        print(
            f"{offering} already has an accepted snapshot "
            f"({existing[0]['latest']}); nothing to do. Use --force to run again."
        )
        return
    print(f"Baseline: one real monitoring run of {offering} (Gemini is called).")
    run = submit_run(product, offering, f"baseline-{offering}-{int(time.time())}")
    run = wait_for_run(run["id"])
    cost = sql(
        f"SELECT coalesce(sum(estimated_cost_usd), 0) AS usd, count(*) AS calls "
        f"FROM model_call_usage WHERE run_id = '{run['id']}'"
    )[0]
    print(
        f"Run {run['id']}: {run['status']}, {cost['calls']} model calls, ${cost['usd']:.4f}"
    )
    if run["status"] == "awaiting_review":
        print(
            "The run is waiting for a review. Answer it with:\n"
            "    python3 stack.py chat      then type: Review the pending candidates"
        )
    elif run["status"] != "succeeded":
        print(f"Failure: {run.get('failure_code')}: {run.get('failure_detail')}")
        sys.exit(1)


def cmd_status(_: argparse.Namespace) -> None:
    rows = accepted_snapshots()
    if not rows:
        print("No accepted snapshots yet. Run: python3 stack.py baseline")
        return
    print("Accepted snapshots in the demo database:")
    for row in rows:
        print(
            f"  {row['offering_id']:<28} {row['accepted']} accepted, latest {row['latest']}"
        )
    runs = sql(
        """SELECT status, count(*) AS n FROM monitoring_runs
           GROUP BY status ORDER BY status"""
    )
    print("Monitoring runs: " + ", ".join(f"{r['n']} {r['status']}" for r in runs))


def cmd_chat(_: argparse.Namespace) -> None:
    compose(
        "exec",
        "api",
        "env",
        "LOG_FILE=/var/log/tariff-monitor/cli.log",
        "uv",
        "run",
        "python",
        "app/cli_entry.py",
        check=False,
    )


def cmd_logs(_: argparse.Namespace) -> None:
    compose("exec", "worker", "tail", "-n", "50", "-f", WORKER_LOG, check=False)


def cmd_down(_: argparse.Namespace) -> None:
    # Also stops containers a demonstration overlay added, such as the mirror.
    names = compose("ps", "-a", "-q", capture=True).stdout.split()
    extra = subprocess.run(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={PROJECT}",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    ids = sorted(set(names) | set(extra))
    if ids:
        subprocess.run(["docker", "stop", *ids], check=True, capture_output=True)
    print("Stopped. The demo database is kept; `up` resumes it.")


def cmd_destroy(_: argparse.Namespace) -> None:
    compose("down", "--volumes", "--remove-orphans")
    # Volumes a demonstration overlay declared (certificate trust) are not in
    # the base files, so remove them by project label.
    volumes = subprocess.run(
        [
            "docker",
            "volume",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={PROJECT}",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    if volumes:
        subprocess.run(["docker", "volume", "rm", *volumes], check=True)
    print("Removed the demo stack, its database and its volumes.")


def cmd_checkpoint(args: argparse.Namespace) -> None:
    if args.action == "save":
        path = save_checkpoint(args.name)
        print(f"Saved checkpoint '{args.name}' ({path.stat().st_size // 1024} KB).")
    elif args.action == "restore":
        restore_checkpoint(args.name)
        print(f"Restored checkpoint '{args.name}'; caches and the spend ledger kept.")
    else:
        for path in sorted(CHECKPOINTS.glob("*.dump")):
            print(f"  {path.stem}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (
        ("up", cmd_up),
        ("status", cmd_status),
        ("chat", cmd_chat),
        ("logs", cmd_logs),
        ("down", cmd_down),
        ("destroy", cmd_destroy),
    ):
        commands.add_parser(name).set_defaults(handler=handler)
    baseline = commands.add_parser("baseline")
    baseline.add_argument("--product", default=BASELINE_OFFERING[0])
    baseline.add_argument("--offering", default=BASELINE_OFFERING[1])
    baseline.add_argument("--force", action="store_true")
    baseline.set_defaults(handler=cmd_baseline)
    checkpoint = commands.add_parser("checkpoint")
    checkpoint.add_argument("action", choices=("save", "restore", "list"))
    checkpoint.add_argument("name", nargs="?", default="baseline")
    checkpoint.set_defaults(handler=cmd_checkpoint)
    args = parser.parse_args()
    try:
        args.handler(args)
    except StackError as exc:
        sys.exit(f"error: {exc}")


if __name__ == "__main__":
    main()
