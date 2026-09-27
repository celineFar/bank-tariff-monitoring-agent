"""Shared plumbing for the stop experiments: fake Gemini, test DB, processes.

Everything runs against the disposable `db-test` service (tmpfs, port 5433)
and the local fake Gemini; nothing reaches Google.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
PYTHON = str(ROOT / ".venv" / "bin" / "python")
DB_DSN = "postgresql://tariff:tariff@127.0.0.1:5433/tariff_monitor_test"
DB_URL = "postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test"
FAKE_PORT = int(os.environ.get("STOP_FAKE_PORT", "8765"))


def app_env(log_file: Path | None = None) -> dict[str, str]:
    """Environment for the application: test DB, fake Gemini, scratch dirs."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GOOGLE_", "GEMINI_", "OTEL_"))
    }
    OUT.mkdir(parents=True, exist_ok=True)
    env.update(
        DATABASE_URL=DB_URL,
        SESSION_SERVICE_URI=DB_URL,
        GEMINI_API_KEY="fake-key-local-only",
        GOOGLE_API_KEY="fake-key-local-only",
        GOOGLE_GENAI_USE_VERTEXAI="false",
        GOOGLE_GEMINI_BASE_URL=f"http://127.0.0.1:{FAKE_PORT}",
        ARTIFACT_TEMP_DIR=str(OUT / "artifacts"),
        PIPELINE_AUDIT_DIR=str(OUT / "pipeline-audit"),
        PYTHONUNBUFFERED="1",
    )
    if log_file is not None:
        env["LOG_FILE"] = str(log_file)
    return env


class FakeGeminiProcess:
    def __init__(self, name: str) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        self.log_path = OUT / f"{name}.gemini.jsonl"
        self.config_path = OUT / f"{name}.gemini-config.json"
        self.log_path.write_text("")
        self.configure()
        self._process: subprocess.Popen | None = None

    def configure(self, **config) -> None:
        self.config_path.write_text(json.dumps(config))

    def __enter__(self) -> FakeGeminiProcess:
        self._process = subprocess.Popen(
            [
                PYTHON,
                str(HERE / "fake_gemini.py"),
                "--port",
                str(FAKE_PORT),
                "--log",
                str(self.log_path),
                "--config",
                str(self.config_path),
            ],
            cwd=ROOT,
        )
        time.sleep(1.5)
        return self

    def __exit__(self, *exc) -> None:
        assert self._process is not None
        self._process.terminate()
        self._process.wait(10)

    def events(self) -> list[dict]:
        return [
            json.loads(line)
            for line in self.log_path.read_text().splitlines()
            if line.strip()
        ]

    def requests(self, role: str | None = None, after: float = 0.0) -> list[dict]:
        return [
            item
            for item in self.events()
            if item["event"] == "request"
            and item["t"] > after
            and (role is None or item["role"] == role)
        ]

    def wait_for(self, role: str, timeout: float = 120.0, after: float = 0.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            found = self.requests(role, after)
            if found:
                return found[0]
            time.sleep(0.1)
        raise TimeoutError(f"no {role} request within {timeout}s")


async def db() -> asyncpg.Connection:
    return await asyncpg.connect(DB_DSN)


ADK_TABLES = {"adk_internal_metadata", "sessions", "events", "app_states", "user_states"}


async def reset_db(keep: tuple[str, ...] = ()) -> None:
    """Empty every application table; ADK's session tables and `keep` stay."""
    conn = await db()
    try:
        tables = [
            row["tablename"]
            for row in await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            if row["tablename"] not in ADK_TABLES and row["tablename"] not in keep
        ]
        if tables:
            await conn.execute(
                "TRUNCATE " + ", ".join(f'"{name}"' for name in tables) + " CASCADE"
            )
    finally:
        await conn.close()


async def run_rows() -> list[dict]:
    conn = await db()
    try:
        runs = await conn.fetch(
            "SELECT id, status, error_code, claimed_by, failure_detail,"
            " queued_at, completed_at FROM monitoring_runs ORDER BY queued_at"
        )
        result = []
        for run in runs:
            executions = await conn.fetch(
                "SELECT offering_id, status, current_stage, failure_code"
                " FROM offering_executions WHERE run_id = $1",
                run["id"],
            )
            audits = await conn.fetch(
                "SELECT event_type, payload FROM audit_events WHERE run_id = $1"
                " ORDER BY id",
                run["id"],
            )
            result.append(
                {
                    "id": str(run["id"]),
                    "status": run["status"],
                    "error_code": run["error_code"],
                    "claimed_by": run["claimed_by"],
                    "executions": [dict(item) for item in executions],
                    "audits": [
                        (item["event_type"], json.loads(item["payload"] or "{}"))
                        for item in audits
                    ],
                }
            )
        return result
    finally:
        await conn.close()


async def table_counts(*tables: str) -> dict[str, int]:
    conn = await db()
    try:
        return {
            name: await conn.fetchval(f'SELECT count(*) FROM "{name}"')
            for name in tables
        }
    finally:
        await conn.close()


def descendants(pid: int) -> list[tuple[int, str]]:
    """(pid, command) of every live descendant, from /proc."""
    children: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
            ppid = int(stat.rsplit(")", 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            continue
        children.setdefault(ppid, []).append(int(entry.name))
    found: list[tuple[int, str]] = []
    stack = list(children.get(pid, []))
    while stack:
        child = stack.pop()
        try:
            command = (Path("/proc") / str(child) / "cmdline").read_bytes()
        except OSError:
            continue
        found.append((child, command.replace(b"\0", b" ").decode(errors="replace")[:120]))
        stack.extend(children.get(child, []))
    return found


def cpu_seconds(pid: int) -> float:
    stat = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    return (int(stat[11]) + int(stat[12])) / os.sysconf("SC_CLK_TCK")


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    state = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[0]
    return state != "Z"


def kill_tree(pid: int) -> None:
    for child, _ in descendants(pid):
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
