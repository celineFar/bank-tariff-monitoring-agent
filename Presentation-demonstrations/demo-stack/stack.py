#!/usr/bin/env python3
"""The persistent demonstration stack, and helpers the demonstrations share.

    python3 stack.py up         start db, api and worker (creates the database once)
    python3 stack.py baseline   one real monitoring run, to have accepted data
    python3 stack.py status     what the demo database holds now
    python3 stack.py chat       the chat CLI against the demo stack (reviews)
    python3 stack.py logs       follow the demo worker's log
    python3 stack.py down       stop the stack; the database is kept
    python3 stack.py destroy    stop it and delete the demo database

Standard library only: it drives `docker compose` and the stack's HTTP API.
"""

from __future__ import annotations

import argparse
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
    files = [REPO / "docker-compose.yml", OVERLAY, *overlays]
    command = ["docker", "compose", "-p", PROJECT]
    for path in files:
        command += ["-f", str(path)]
    return subprocess.run(
        [*command, *args],
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


def restart_worker(overlays: tuple[Path, ...] = ()) -> None:
    """Recreate the worker with the given overlays (none: the normal worker)."""
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
    compose("stop")
    print("Stopped. The demo database is kept; `up` resumes it.")


def cmd_destroy(_: argparse.Namespace) -> None:
    compose("down", "--volumes")
    print("Removed the demo stack and its database.")


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
    args = parser.parse_args()
    try:
        args.handler(args)
    except StackError as exc:
        sys.exit(f"error: {exc}")


if __name__ == "__main__":
    main()
