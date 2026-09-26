"""Run the acquisition scenarios and write one JSON result per scenario.

    uv run python fix-process/acquisition/scenarios/run_scenarios.py S02 S03 ...

Acquisition makes no model calls, so every scenario must cost $0 of Gemini. The
harness enforces that rather than assuming it: it removes the API key before
settings load and replaces the Gemini client constructor with one that records
the attempt and raises. Database scenarios run against a scratch database,
`tariff_acquisition_scenarios`, rebuilt from the migrations.

"Cost" per scenario is what was actually spent: Gemini calls, HTTP requests to
the bank (static pages and PDFs), browser renders, bytes kept, and wall time.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RESULTS = Path(__file__).resolve().parent / "results"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def _database_url(name: str) -> str:
    raw = next(
        line.split("=", 1)[1].strip()
        for line in (ROOT / ".env").read_text().splitlines()
        if line.startswith("DATABASE_URL=")
    )
    password = raw.split("://", 1)[1].split("@", 1)[0].split(":", 1)[1]
    return f"postgresql+asyncpg://tariff:{password}@localhost:5434/{name}"


SCENARIO_DB = _database_url("tariff_acquisition_scenarios")
TEST_DB = _database_url("tariff_acquisition_test")

# --- The Gemini guard: no key, and no client can be created. -----------------
os.environ["GEMINI_API_KEY"] = ""
os.environ.pop("GOOGLE_API_KEY", None)
os.environ["DATABASE_URL"] = SCENARIO_DB

import google.genai  # noqa: E402
import google.genai.client  # noqa: E402

GEMINI_ATTEMPTS: list[str] = []


def _refuse_gemini(*args: Any, **kwargs: Any) -> None:
    GEMINI_ATTEMPTS.append("google.genai.Client")
    raise RuntimeError("Gemini is disabled in the acquisition scenarios")


google.genai.Client.__init__ = _refuse_gemini  # type: ignore[method-assign]
google.genai.client.Client.__init__ = _refuse_gemini  # type: ignore[method-assign]

import asyncpg  # noqa: E402
import httpx  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.config.seed_catalog import load_seed_catalog  # noqa: E402
from app.domain.acquisition import AcquisitionWarningCode, PageArtifact  # noqa: E402
from app.repositories.acquisition_baselines import (  # noqa: E402
    PostgresAcquisitionBaselineRepository,
)
from app.repositories.acquisition_snapshots import (  # noqa: E402
    PostgresAcquisitionSnapshotRepository,
)
from app.services.acquisition import build_acquisition_service  # noqa: E402
from app.services.acquisition_completeness import (  # noqa: E402
    CompletenessGatedAcquisitionService,
)
from app.services.acquisition_freshness import (  # noqa: E402
    FreshnessGatedAcquisitionService,
)
from app.services.artifact_store import FileSystemArtifactStore  # noqa: E402
from app.services.failure_mapping import source_failure_code  # noqa: E402
from app.services.pdf_downloader import PdfDownloader  # noqa: E402

CATALOG = load_seed_catalog()
SEEDS = {entry.offering_id.value: str(entry.seed_url) for entry in CATALOG.offerings}


class Meter:
    """What a scenario spent."""

    def __init__(self) -> None:
        self.started = time.monotonic()
        self.bank_requests = 0
        self.renders = 0
        self.bytes_kept = 0
        self.gemini_before = len(GEMINI_ATTEMPTS)

    async def on_request(self, request: httpx.Request) -> None:
        self.bank_requests += 1

    def keep(self, artifact: PageArtifact) -> None:
        self.bytes_kept += len((artifact.raw_html or "").encode())
        self.bytes_kept += len((artifact.rendered_html or "").encode())
        self.bytes_kept += sum(
            item.size_bytes for item in artifact.downloadable_documents
        )
        self.bytes_kept += sum(item.size_bytes for item in artifact.network_payloads)

    def report(self) -> dict[str, Any]:
        return {
            "gemini_calls": len(GEMINI_ATTEMPTS) - self.gemini_before,
            "gemini_usd": 0.0,
            "bank_http_requests": self.bank_requests,
            "browser_renders": self.renders,
            "megabytes_kept": round(self.bytes_kept / 1_048_576, 2),
            "wall_seconds": round(time.monotonic() - self.started, 1),
        }


class CountingRenderer:
    def __init__(self, inner: Any, meter: Meter) -> None:
        self._inner = inner
        self._meter = meter

    async def render(self, url: str):
        self._meter.renders += 1
        return await self._inner.render(url)


def _settings(**acquisition: Any):
    settings = load_settings()
    return settings.model_copy(
        update={
            "acquisition": settings.acquisition.model_copy(update=acquisition),
            "application": settings.application.model_copy(
                update={"artifact_temp_dir": Path(tempfile.mkdtemp(prefix="acq-"))}
            ),
        }
    )


def _service(client: httpx.AsyncClient, settings, meter: Meter, *, pdf=None):
    service = build_acquisition_service(client, settings)
    if service._browser_renderer is not None:
        service._browser_renderer = CountingRenderer(service._browser_renderer, meter)
    if pdf is not None:
        service._pdf_downloader = pdf
    return service


def _client(meter: Meter) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=20, follow_redirects=False, event_hooks={"request": [meter.on_request]}
    )


def _summary(artifact: PageArtifact) -> dict[str, Any]:
    return {
        "mode": artifact.acquisition_mode.value,
        "inventory": artifact.inventory.model_dump(),
        "page_content_hash": artifact.page_content_hash[:16],
        "content_hash": artifact.content_hash[:16],
        "documents_downloaded": len(artifact.downloadable_documents),
        "interactions": artifact.interactions,
        "reused": artifact.reused,
        "warnings": [f"{w.code.value}: {w.detail}" for w in artifact.warnings],
    }


def _failure(exc: Exception) -> dict[str, Any]:
    return {
        "failure_code": source_failure_code(exc, stage="acquisition").value,
        "reason": getattr(getattr(exc, "reason", None), "value", None),
        "reasons": list(getattr(exc, "reasons", ()) or ()),
        "message": str(exc)[:300],
    }


def _without_survey_cap(summary: dict[str, Any]) -> dict[str, Any]:
    # Downloads are switched off with a cap of 0; the warning that causes says
    # nothing about the page.
    summary["warnings"] = [
        w
        for w in summary["warnings"]
        if not w.startswith(AcquisitionWarningCode.LINKED_DOCUMENT_CAP_REACHED.value)
    ]
    return summary


def _write(sid: str, passed: bool, details: dict[str, Any], meter: Meter) -> None:
    payload = {"scenario": sid, "passed": passed, "cost": meter.report(), **details}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{sid}.json").write_text(
        json.dumps(payload, indent=1, default=str) + "\n"
    )
    print(f"{sid}: {'PASS' if passed else 'FAIL'} {json.dumps(payload['cost'])}")


async def _fresh_schema(url: str) -> None:
    dsn = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    admin = await asyncpg.connect(dsn.rsplit("/", 1)[0] + "/postgres")
    try:
        name = url.rsplit("/", 1)[1]
        if not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", name):
            await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()
    connection = await asyncpg.connect(dsn)
    try:
        await connection.execute(
            "DROP SCHEMA public CASCADE; CREATE SCHEMA public; "
            "CREATE EXTENSION IF NOT EXISTS vector"
        )
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            await connection.execute(migration.read_text())
    finally:
        await connection.close()


async def _sql(query: str, *args: Any) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(
        SCENARIO_DB.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        return await connection.fetch(query, *args)
    finally:
        await connection.close()


# --- Scenarios ----------------------------------------------------------------


async def s01() -> None:
    meter = Meter()
    files = [
        "tests/unit/test_acquisition.py",
        "tests/unit/test_acquisition_identity.py",
        "tests/unit/test_acquisition_completeness.py",
        "tests/unit/test_acquisition_freshness.py",
        "tests/unit/test_browser_render_dom.py",
        "tests/unit/test_browser_renderer_rules.py",
        "tests/unit/test_failure_mapping.py",
        "tests/unit/test_source_urls.py",
        "tests/unit/test_html_parser.py",
        "tests/unit/test_monitoring_pipeline.py",
        "tests/unit/test_monitoring_node.py",
        "tests/integration/test_acquisition_snapshots_postgres.py",
        "tests/integration/test_acquisition_baselines_postgres.py",
    ]
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", *files],
        capture_output=True,
        text=True,
        env={**os.environ, "TEST_DATABASE_URL": TEST_DB},
    )
    tail = [line for line in completed.stdout.splitlines() if line.strip()][-3:]
    skipped = [line for line in completed.stdout.splitlines() if "SKIPPED" in line]
    passed = completed.returncode == 0 and not skipped
    _write(
        "S01", passed, {"files": files, "pytest_tail": tail, "skipped": skipped}, meter
    )


async def s02_s03() -> None:
    first: dict[str, Any] = {}
    for sid in ("S02", "S03"):
        meter = Meter()
        rows: dict[str, Any] = {}
        async with _client(meter) as client:
            service = _service(client, _settings(max_linked_documents=0), meter)
            for offering, url in SEEDS.items():
                try:
                    artifact = await service.acquire(url)
                except Exception as exc:
                    rows[offering] = _failure(exc)
                else:
                    meter.keep(artifact)
                    rows[offering] = _without_survey_cap(_summary(artifact))
        if sid == "S02":
            first = rows
            ok = [
                o
                for o, r in rows.items()
                if r.get("mode") == "browser"
                and r["inventory"]["main_chars"] >= 1500
                and (
                    r["inventory"]["tables"]
                    or r["inventory"]["pdf_links"]
                    or r["inventory"]["payloads"]
                )
            ]
            _write("S02", len(ok) == len(SEEDS), {"seeds": rows, "passing": ok}, meter)
        else:
            compare = {
                o: {
                    "page_id_first": first[o].get("page_content_hash"),
                    "page_id_second": r.get("page_content_hash"),
                    "page_id_same": first[o].get("page_content_hash")
                    == r.get("page_content_hash")
                    and r.get("page_content_hash") is not None,
                    "content_hash_same": first[o].get("content_hash")
                    == r.get("content_hash"),
                    "inventory_first": first[o].get("inventory"),
                    "inventory_second": r.get("inventory"),
                }
                for o, r in rows.items()
            }
            same = [o for o, c in compare.items() if c["page_id_same"]]
            _write("S03", len(same) == len(SEEDS), {"comparison": compare}, meter)


async def s04() -> None:
    meter = Meter()
    details: dict[str, Any] = {}
    async with _client(meter) as client:
        full = _service(client, _settings(max_linked_documents=40), meter)
        for offering in ("mortgage_online", "mortgage_construction"):
            artifact = await full.acquire(SEEDS[offering])
            meter.keep(artifact)
            details[offering] = _summary(artifact)
        capped = _service(client, _settings(max_linked_documents=5), meter)
        artifact = await capped.acquire(SEEDS["overdraft"])
        meter.keep(artifact)
        details["overdraft_cap_5"] = _summary(artifact)
    full_ok = all(
        d["documents_downloaded"] == d["inventory"]["pdf_links"] and not d["warnings"]
        for k, d in details.items()
        if k != "overdraft_cap_5"
    )
    capped = details["overdraft_cap_5"]
    cap_ok = capped["documents_downloaded"] == 5 and [
        w.split(":", 1)[0] for w in capped["warnings"]
    ] == [AcquisitionWarningCode.LINKED_DOCUMENT_CAP_REACHED.value]
    _write("S04", full_ok and cap_ok, details, meter)


async def s05() -> None:
    meter = Meter()
    details: dict[str, Any] = {}
    empty = tempfile.mkdtemp(prefix="no-browsers-")
    async with _client(meter) as client:
        previous = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = empty
        try:
            await _service(client, _settings(), meter).acquire(SEEDS["overdraft"])
            details["a_no_browser"] = {"artifact_returned": True}
        except Exception as exc:
            details["a_no_browser"] = {"artifact_returned": False, **_failure(exc)}
        finally:
            if previous is None:
                os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
            else:
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = previous
        try:
            await _service(
                client, _settings(browser_navigation_timeout_seconds=0.01), meter
            ).acquire(SEEDS["overdraft"])
            details["b_navigation_timeout"] = {"artifact_returned": True}
        except Exception as exc:
            details["b_navigation_timeout"] = {
                "artifact_returned": False,
                **_failure(exc),
            }
    passed = (
        details["a_no_browser"].get("failure_code") == "source.browser_unavailable"
        and details["b_navigation_timeout"].get("failure_code")
        == "source.browser_failed"
        and not any(d["artifact_returned"] for d in details.values())
    )
    _write("S05", passed, details, meter)


async def s06() -> None:
    meter = Meter()
    rows: dict[str, Any] = {}
    async with _client(meter) as client:
        service = _service(
            client, _settings(browser_enabled=False, max_linked_documents=0), meter
        )
        for offering, url in SEEDS.items():
            try:
                artifact = await service.acquire(url)
                rows[offering] = {"accepted": True, **_summary(artifact)}
            except Exception as exc:
                rows[offering] = {"accepted": False, **_failure(exc)}
    passed = all(
        r.get("failure_code") == "source.incomplete_content" and r.get("reasons")
        for r in rows.values()
    )
    _write("S06", passed, {"seeds": rows}, meter)


def _db():
    engine = create_async_engine(SCENARIO_DB)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def s07() -> None:
    await _fresh_schema(SCENARIO_DB)
    meter = Meter()
    url = SEEDS["overdraft"]
    steps: dict[str, Any] = {}
    engine, sessions = _db()
    baselines = PostgresAcquisitionBaselineRepository(sessions)
    try:
        async with _client(meter) as client:
            settings = _settings(max_linked_documents=0)
            gate = CompletenessGatedAcquisitionService(
                _service(client, settings, meter), baselines, settings.acquisition
            )
            artifact = await gate.acquire(url)
            meter.keep(artifact)
            recorded = await baselines.get(url)
            steps["1_first_acquire"] = {
                "inventory": artifact.inventory.model_dump(),
                "baseline_recorded": recorded.model_dump() if recorded else None,
            }
            await _sql(
                "UPDATE acquisition_baselines SET inventory = jsonb_set(inventory, "
                "'{pdf_links}', '25')"
            )
            steps["2_baseline_raised"] = (await baselines.get(url)).model_dump()
            try:
                await gate.acquire(url)
                steps["3_after_drop"] = {"failed": False}
            except Exception as exc:
                steps["3_after_drop"] = {"failed": True, **_failure(exc)}
            steps["3_baseline_after_failure"] = (await baselines.get(url)).model_dump()
            reset = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.reset_acquisition_baseline",
                    "overdraft",
                    "--operator",
                    "scenario-S07",
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
                env={**os.environ},
            )
            audit = await _sql(
                "SELECT event_type, payload->>'reset_by' AS by, "
                "payload->'previous_inventory'->>'pdf_links' AS pdf FROM audit_events"
            )
            steps["4_reset"] = {
                "exit_code": reset.returncode,
                "stdout": reset.stdout.strip().splitlines()[-2:],
                "baseline_after_reset": await baselines.get(url),
                "audit_events": [dict(row) for row in audit],
            }
            artifact = await gate.acquire(url)
            meter.keep(artifact)
            row = (
                await _sql(
                    "SELECT reset_by, inventory::text AS inv FROM acquisition_baselines"
                )
            )[0]
            steps["5_after_reset"] = {
                "inventory": artifact.inventory.model_dump(),
                "baseline": json.loads(row["inv"]),
                "reset_by_kept": row["reset_by"],
            }
    finally:
        await engine.dispose()
    live = steps["1_first_acquire"]["inventory"]
    passed = (
        steps["1_first_acquire"]["baseline_recorded"] == live
        and steps["3_after_drop"].get("failure_code") == "source.incomplete_content"
        and any(
            r.startswith("pdf_links 25 -> ") for r in steps["3_after_drop"]["reasons"]
        )
        and steps["3_baseline_after_failure"]["pdf_links"] == 25
        and steps["4_reset"]["exit_code"] == 0
        and steps["4_reset"]["baseline_after_reset"] is None
        and steps["4_reset"]["audit_events"][0]["event_type"]
        == "acquisition.baseline_reset"
        and steps["5_after_reset"]["baseline"] == steps["5_after_reset"]["inventory"]
        and steps["5_after_reset"]["reset_by_kept"] == "scenario-S07"
    )
    _write("S07", passed, {"steps": steps}, meter)


async def s08() -> None:
    await _fresh_schema(SCENARIO_DB)
    meter = Meter()
    url = SEEDS["overdraft"]
    steps: dict[str, Any] = {}
    engine, sessions = _db()
    snapshots = PostgresAcquisitionSnapshotRepository(sessions)
    baselines = PostgresAcquisitionBaselineRepository(sessions)
    count = "SELECT count(*) AS n FROM acquisition_snapshots"
    try:
        async with _client(meter) as client:

            def chain(settings, *, pdf=None):
                return FreshnessGatedAcquisitionService(
                    CompletenessGatedAcquisitionService(
                        _service(client, settings, meter, pdf=pdf),
                        baselines,
                        settings.acquisition,
                    ),
                    snapshots,
                    freshness_hours=1.0,
                    artifact_reader=FileSystemArtifactStore(
                        settings.application.artifact_temp_dir
                    ),
                )

            normal = chain(_settings(max_linked_documents=0))
            before = (meter.bank_requests, meter.renders)
            artifact = await normal.acquire(url)
            meter.keep(artifact)
            steps["a1_first"] = {
                "reused": artifact.reused,
                "stored": (await _sql(count))[0]["n"],
                "bank_requests": meter.bank_requests - before[0],
                "renders": meter.renders - before[1],
            }
            before = (meter.bank_requests, meter.renders)
            again = await normal.acquire(url)
            steps["a2_second"] = {
                "reused": again.reused,
                "same_retrieved_at": again.retrieved_at == artifact.retrieved_at,
                "bank_requests": meter.bank_requests - before[0],
                "renders": meter.renders - before[1],
            }
            await _sql("DELETE FROM acquisition_snapshots")
            settings = _settings(max_linked_documents=2)
            failing_pdf = PdfDownloader(
                client, settings.http.model_copy(update={"max_download_bytes": 1_000})
            )
            partial = await chain(settings, pdf=failing_pdf).acquire(url)
            steps["b1_partial"] = {
                "warnings": [f"{w.code.value}: {w.detail}" for w in partial.warnings],
                "stored": (await _sql(count))[0]["n"],
            }
            before = (meter.bank_requests, meter.renders)
            await chain(_settings(max_linked_documents=0)).acquire(url)
            steps["b2_next_fetches_again"] = {
                "bank_requests": meter.bank_requests - before[0],
                "renders": meter.renders - before[1],
            }
            await _sql("DELETE FROM acquisition_snapshots")
            try:
                await chain(
                    _settings(browser_enabled=False, max_linked_documents=0)
                ).acquire(url)
                steps["c_gate_failure"] = {"failed": False}
            except Exception as exc:
                steps["c_gate_failure"] = {"failed": True, **_failure(exc)}
            steps["c_gate_failure"]["stored"] = (await _sql(count))[0]["n"]
    finally:
        await engine.dispose()
    failed_downloads = [
        w
        for w in steps["b1_partial"]["warnings"]
        if w.startswith("acquisition.linked_document_failed")
    ]
    passed = (
        steps["a1_first"]["reused"] is False
        and steps["a1_first"]["stored"] == 1
        and steps["a2_second"]["reused"] is True
        and steps["a2_second"]["same_retrieved_at"]
        and steps["a2_second"]["bank_requests"] == 0
        and steps["a2_second"]["renders"] == 0
        and len(failed_downloads) == 2
        and steps["b1_partial"]["stored"] == 0
        and steps["b2_next_fetches_again"]["renders"] == 1
        and steps["c_gate_failure"].get("failure_code") == "source.incomplete_content"
        and steps["c_gate_failure"]["stored"] == 0
    )
    _write("S08", passed, {"steps": steps}, meter)


async def s09() -> None:
    from app.domain.models import OfferingId, ProductType
    from app.domain.monitoring import RunCommand, RunTrigger
    from app.repositories.monitoring import PostgresRunRepository
    from app.services.monitoring_pipeline import IndexingPipeline, TariffPipeline

    class StopAfterAcquisition:
        async def normalize(self, artifact):
            raise RuntimeError("scenario harness: stopped before normalization")

    await _fresh_schema(SCENARIO_DB)
    meter = Meter()
    runs_out: dict[str, Any] = {}
    engine, sessions = _db()
    runs = PostgresRunRepository(sessions)
    try:
        async with _client(meter) as client:

            def pipeline(settings):
                acquisition = FreshnessGatedAcquisitionService(
                    CompletenessGatedAcquisitionService(
                        _service(client, settings, meter),
                        PostgresAcquisitionBaselineRepository(sessions),
                        settings.acquisition,
                    ),
                    PostgresAcquisitionSnapshotRepository(sessions),
                    freshness_hours=settings.acquisition.freshness_hours,
                )
                indexing = IndexingPipeline(
                    acquisition=acquisition,
                    normalization=StopAfterAcquisition(),
                    discovery=None,
                    extraction=None,
                    projection=None,
                    embedder=None,
                    snapshots=None,
                    publications=None,
                    runs=runs,
                )
                return TariffPipeline(catalog=CATALOG, indexing=indexing, runs=runs)

            plans = (
                ("run_1_fresh", _settings(max_linked_documents=0, freshness_hours=1.0)),
                (
                    "run_2_within_window",
                    _settings(max_linked_documents=0, freshness_hours=1.0),
                ),
                (
                    "run_3_browser_disabled",
                    _settings(
                        browser_enabled=False, max_linked_documents=0, freshness_hours=0
                    ),
                ),
            )
            for label, settings in plans:
                submitted = await runs.submit(
                    RunCommand(
                        product=ProductType.CONSUMER_LOAN,
                        offering_id=OfferingId.OVERDRAFT,
                        trigger=RunTrigger.API,
                    )
                )
                claimed = await runs.claim(submitted.run.id, "scenario-S09")
                assert claimed is not None
                finished = await pipeline(settings).execute(claimed.run)
                rows = await _sql(
                    "SELECT status, current_stage, failure_code, source_retrieved_at, "
                    "acquisition_reused FROM offering_executions WHERE run_id = $1",
                    finished.id,
                )
                audit = await _sql(
                    "SELECT payload FROM audit_events WHERE run_id = $1 "
                    "AND payload ? 'reasons'",
                    finished.id,
                )
                runs_out[label] = {
                    "run_status": finished.status.value,
                    "execution": {k: str(v) for k, v in dict(rows[0]).items()},
                    "audit_reasons": [
                        json.loads(r["payload"])["reasons"] for r in audit
                    ],
                }
        usage = (await _sql("SELECT count(*) AS n FROM model_call_usage"))[0]["n"]
    finally:
        await engine.dispose()
    r1, r2, r3 = (runs_out[k]["execution"] for k in runs_out)
    passed = (
        r1["current_stage"] == "normalization"
        and r1["acquisition_reused"] == "False"
        and r1["source_retrieved_at"] != "None"
        and r2["acquisition_reused"] == "True"
        and r2["source_retrieved_at"] == r1["source_retrieved_at"]
        and r3["current_stage"] == "acquisition"
        and r3["failure_code"] == "source.incomplete_content"
        and bool(runs_out["run_3_browser_disabled"]["audit_reasons"])
        and usage == 0
    )
    _write("S09", passed, {"runs": runs_out, "model_call_usage_rows": usage}, meter)


async def s10() -> None:
    meter = Meter()
    urls = [
        "http://ameriabank.am/en/personal/loans/consumer-loans/overdraft",
        "https://example.com/tariffs",
        "https://ameriabank.am.example.com/tariffs",
        "https://185.24.0.1/tariffs",
        "https://user:secret@ameriabank.am/tariffs",
        "https://ameriabank.am:8443/en/personal/loans/consumer-loans/overdraft",
    ]
    rows: dict[str, Any] = {}
    async with _client(meter) as client:
        service = _service(client, _settings(), meter)
        for url in urls:
            try:
                await service.acquire(url)
                rows[url] = {"rejected": False}
            except Exception as exc:
                rows[url] = {"rejected": True, **_failure(exc)}
    passed = (
        all(r.get("failure_code") == "source.url_rejected" for r in rows.values())
        and meter.bank_requests == 0
        and meter.renders == 0
    )
    _write("S10", passed, {"urls": rows}, meter)


SCENARIOS = {
    "S01": s01,
    "S02": s02_s03,
    "S04": s04,
    "S05": s05,
    "S06": s06,
    "S07": s07,
    "S08": s08,
    "S09": s09,
    "S10": s10,
}


async def main(selected: list[str]) -> None:
    for sid in selected or list(SCENARIOS):
        if sid == "S03":
            continue  # runs together with S02
        await SCENARIOS[sid]()
    print(f"Gemini client attempts in this process: {len(GEMINI_ATTEMPTS)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
