"""Run the normalization scenarios and write one JSON result per scenario.

    uv run python fix-process/normalization/scenarios/run_scenarios.py S01 S03 ...

Normalization of a page needs no model. Linked PDFs do (Gemini transcription),
so every scenario runs under a Gemini guard: the API key is removed before
settings load, and the Gemini client constructor is replaced with one that
records the attempt and raises. The PDF path is tested with real Gemini output
replayed from the stored transcriptions in `tariff_rt` (read-only), not with new
calls. Every scenario must therefore cost $0 of Gemini; the result records the
attempts counted.

"Cost" per scenario is what was actually spent: Gemini client attempts, HTTP
requests to the bank (pages and PDFs), browser renders, data held, wall time.
Database access is read-only, except S01's tests, which use the scratch
`tariff_acquisition_test` database.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def _database_password() -> str:
    # The dev database runs in Docker; its password is in the container's
    # environment. It is read into memory only, never written anywhere.
    return subprocess.run(
        [
            "docker",
            "exec",
            "bank-tariff-monitoring-agent-db-1",
            "sh",
            "-c",
            "echo $POSTGRES_PASSWORD",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


PASSWORD = _database_password()
ASYNCPG_URL = "postgresql://tariff:{pw}@localhost:5434/{db}"
TEST_DB = (
    f"postgresql+asyncpg://tariff:{PASSWORD}@localhost:5434/tariff_acquisition_test"
)

# --- The Gemini guard: no key, and no client can be created. -----------------
os.environ["GEMINI_API_KEY"] = ""
os.environ.pop("GOOGLE_API_KEY", None)

import google.genai  # noqa: E402
import google.genai.client  # noqa: E402

GEMINI_ATTEMPTS: list[str] = []


def _refuse_gemini(*args: Any, **kwargs: Any) -> None:
    GEMINI_ATTEMPTS.append("google.genai.Client")
    raise RuntimeError("Gemini is disabled in the normalization scenarios")


google.genai.Client.__init__ = _refuse_gemini  # type: ignore[method-assign]
google.genai.client.Client.__init__ = _refuse_gemini  # type: ignore[method-assign]

import asyncpg  # noqa: E402
import httpx  # noqa: E402

from app.config import PdfExtractionSettings, load_settings  # noqa: E402
from app.config.seed_catalog import load_seed_catalog  # noqa: E402
from app.domain.acquisition import (  # noqa: E402
    AcquisitionInventory,
    PageArtifact,
    StoredArtifact,
)
from app.domain.normalization import (  # noqa: E402
    NormalizationWarningCode,
    NormalizedSourceBundle,
)
from app.domain.pdf_extraction import (  # noqa: E402
    PdfAdmissionRelevance,
    PdfExtractionResponse,
    PdfTemporalStatus,
)
from app.services.acquisition import build_acquisition_service  # noqa: E402
from app.services.acquisition_completeness import compare_inventory  # noqa: E402
from app.services.extraction_evidence import build_evidence_catalog  # noqa: E402
from app.services.normalization import (  # noqa: E402
    NoPdfExtractor,
    StructuralNormalizationService,
)
from app.services.normalization_baseline import (  # noqa: E402
    load_normalization_baseline,
)
from app.services.pdf_admission import assess_pdf_metadata  # noqa: E402
from app.services.pdf_extraction import GeminiPdfExtractionService  # noqa: E402

SEEDS = {
    entry.offering_id.value: str(entry.seed_url)
    for entry in load_seed_catalog().offerings
    if entry.enabled
}
LIVE = [BASE / ".cache-scenario-1", BASE / ".cache-scenario-2"]
REFERENCE = BASE / ".cache"  # the Phase 0 capture: stored before the fixes


class Meter:
    """What a scenario spent."""

    def __init__(self) -> None:
        self.started = time.monotonic()
        self.bank_requests = 0
        self.renders = 0
        self.bytes_held = 0
        self.gemini_before = len(GEMINI_ATTEMPTS)

    async def on_request(self, request: httpx.Request) -> None:
        self.bank_requests += 1

    def report(self) -> dict[str, Any]:
        return {
            "gemini_calls": len(GEMINI_ATTEMPTS) - self.gemini_before,
            "gemini_usd": 0.0,
            "bank_http_requests": self.bank_requests,
            "browser_renders": self.renders,
            "megabytes_held": round(self.bytes_held / 1_048_576, 2),
            "wall_seconds": round(time.monotonic() - self.started, 1),
        }


def _write(sid: str, passed: bool, details: dict[str, Any], meter: Meter) -> None:
    payload = {"scenario": sid, "passed": passed, "cost": meter.report(), **details}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{sid}.json").write_text(
        json.dumps(payload, indent=1, default=str, ensure_ascii=False) + "\n"
    )
    print(sid, "PASS" if passed else "FAIL", payload["cost"])


class _CapturedPdfs:
    def __init__(self, cache: Path) -> None:
        self._cache = cache

    async def read(self, artifact: StoredArtifact) -> bytes:
        return (self._cache / "pdfs" / f"{artifact.sha256}.pdf").read_bytes()


def _artifacts(cache: Path) -> dict[str, PageArtifact]:
    return {
        path.name.removesuffix(".artifact.json"): PageArtifact.model_validate_json(
            path.read_text()
        )
        for path in sorted(cache.glob("*.artifact.json"))
    }


def _survey(script: str, cache: Path, label: str | None = None) -> str:
    completed = subprocess.run(
        [
            sys.executable,
            f"fix-process/normalization/survey/{script}",
            *([label] if label else []),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "SURVEY_CACHE": str(cache)},
    )
    return completed.stdout


def _no_pdf_service(cache: Path) -> StructuralNormalizationService:
    return StructuralNormalizationService(
        artifact_reader=_CapturedPdfs(cache),
        pdf_extractor=NoPdfExtractor(),
        baseline=load_normalization_baseline(),
    )


# --- S01 -------------------------------------------------------------------------


async def s01() -> None:
    meter = Meter()
    files = [
        "tests/unit/test_normalization_fixes.py",
        "tests/unit/test_normalization_pdf_fixes.py",
        "tests/unit/test_normalization_baseline.py",
        "tests/unit/test_pdf_admission_gate.py",
        "tests/unit/test_normalization.py",
        "tests/unit/test_normalization_service.py",
        "tests/unit/test_normalized_renderer.py",
        "tests/unit/test_html_parser.py",
        "tests/unit/test_ocr_fallback.py",
        "tests/unit/test_gemini_pdf_extraction.py",
        "tests/unit/test_semantic_extraction.py",
        "tests/unit/test_discovery_prefilter.py",
        "tests/unit/test_source_discovery.py",
        "tests/unit/test_knowledge_projection.py",
        "tests/unit/test_acquisition.py",
        "tests/unit/test_acquisition_identity.py",
        "tests/unit/test_acquisition_completeness.py",
        "tests/unit/test_acquisition_freshness.py",
        "tests/unit/test_browser_render_dom.py",
        "tests/unit/test_config.py",
        "tests/integration/test_acquisition_snapshots_postgres.py",
        "tests/integration/test_acquisition_baselines_postgres.py",
    ]
    files = [name for name in files if (ROOT / name).exists()]
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", *files],
        capture_output=True,
        text=True,
        env={**os.environ, "TEST_DATABASE_URL": TEST_DB},
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    skipped = [line for line in lines if line.startswith("SKIPPED")]
    # Tests of the optional OCR engine (tesseract, pypdfium2: the `ocr` extra)
    # skip on a host without it; nothing else may.
    unexpected = [
        line
        for line in skipped
        if "tesseract" not in line.lower() and "pypdfium2" not in line.lower()
    ]
    passed = completed.returncode == 0 and not unexpected
    _write(
        "S01",
        passed,
        {"files": files, "pytest_tail": lines[-2:], "skipped": skipped},
        meter,
    )


# --- S02 -------------------------------------------------------------------------


async def s02() -> None:
    meter = Meter()
    completed = subprocess.run(
        [sys.executable, "fix-process/normalization/data/probe_normalization.py"],
        capture_output=True,
        text=True,
    )
    now = completed.stdout
    before = (BASE / "data" / "probe-output-before.txt").read_text()
    # Each confirmed problem as it showed before, and what must be true now.
    cases = {
        "N6 merged table text": (
            "TermAmount12500 000 AMD" in before,
            "12500 000" not in now and "Term | Amount" in now,
        ),
        "N6 card title": (
            "Consumer loanUp to" in before,
            "'title': 'Consumer loan'" in now,
        ),
        "N1 row-header table": (
            "headers=('Term', '60 months')" in before,
            "['Interest rate', '12%']" in now,
        ),
        "N3 amount kept in note": (
            "text= '000 000 AMD" in before,
            "text= '5 000 000 AMD is the maximum" in now,
        ),
        "N10 title not repeated": (
            "note marker= None text= 'Consumer loan tariffs'" in before,
            "note marker= None text= 'Consumer loan tariffs'" not in now,
        ),
        "N9 single column rows": (
            "note marker= None text= 'Rate 12%'" in before,
            "['Rate 12%']" in now,
        ),
        "N13 no false list items": (
            "('5% annual',)" in before,
            "('5% annual',)" not in now and "('03.2025',)" not in now,
        ),
        "N8 nested table": (
            "['AMD', '12%']" in before.split("=== nested table")[1].split("===")[0],
            "[table t2]" in now,
        ),
        "N2 sections": (
            "note marker= None text= 'USD loans'" in before,
            "note marker= None text= 'USD loans'" not in now,
        ),
        "N7 heading leak": (
            "b5 paragraph path=('Mortgage rates',)" in before,
            "path=('Consumer',) text='Rate 18%'" in now,
        ),
        "N4 bare div text": (
            "Service fee 1% of loan amount" not in before,
            "Service fee 1% of loan amount" in now,
        ),
        "N14 dt/dd pair": (
            "fields={}" in before.split("=== dt/dd")[1].split("===")[0],
            "'key': 'Interest rate', 'value': '12%'" in now,
        ),
    }
    results = {
        name: {"reproduced_before": was, "fixed_now": is_}
        for name, (was, is_) in cases.items()
    }
    passed = completed.returncode == 0 and all(
        row["reproduced_before"] and row["fixed_now"] for row in results.values()
    )
    (RESULTS / "S02-probe-output-now.txt").write_text(now)
    _write("S02", passed, {"cases": results}, meter)


# --- S03 and S04: two fresh live captures -------------------------------------------


async def _capture(target: Path, meter: Meter) -> dict[str, Any]:
    settings = load_settings()
    artifact_dir = Path(tempfile.mkdtemp(prefix="norm-scenario-"))
    settings = settings.model_copy(
        update={
            "acquisition": settings.acquisition.model_copy(
                update={"max_linked_documents": 40}
            ),
            "application": settings.application.model_copy(
                update={"artifact_temp_dir": artifact_dir}
            ),
        }
    )
    (target / "pdfs").mkdir(parents=True, exist_ok=True)
    failures: dict[str, str] = {}
    async with httpx.AsyncClient(
        timeout=30, follow_redirects=False, event_hooks={"request": [meter.on_request]}
    ) as client:
        service = build_acquisition_service(client, settings)
        for offering, url in SEEDS.items():
            try:
                meter.renders += 1
                artifact = await service.acquire(url)
            except Exception as exc:  # recorded as a scenario failure
                failures[offering] = f"{type(exc).__name__}: {exc}"[:300]
                continue
            meter.bytes_held += len((artifact.rendered_html or "").encode())
            meter.bytes_held += sum(
                d.size_bytes for d in artifact.downloadable_documents
            )
            (target / f"{offering}.artifact.json").write_text(
                artifact.model_dump_json()
            )
            for document in artifact.downloadable_documents:
                source = artifact_dir / document.artifact.relative_path
                destination = target / "pdfs" / f"{document.sha256}.pdf"
                if source.exists() and not destination.exists():
                    destination.write_bytes(source.read_bytes())
    return failures


async def _normalize_all(cache: Path) -> dict[str, dict[str, Any]]:
    service = _no_pdf_service(cache)
    rows: dict[str, dict[str, Any]] = {}
    for seed, artifact in _artifacts(cache).items():
        bundle = await service.normalize(artifact)
        page = bundle.documents[0]
        rows[seed] = {
            "mode": artifact.acquisition_mode.value,
            "inventory": artifact.inventory.model_dump(),
            "page_id": page.id,
            "content_hash": artifact.content_hash[:16],
            "normalized_page": page.model_dump_json(),
            "quality_score": page.quality_score,
            "warnings": sorted({w.code.value for w in bundle.warnings}),
            "baseline_failures": [
                w.message
                for w in bundle.warnings
                if w.code is NormalizationWarningCode.BASELINE_MISMATCH
            ],
            "blocks": len(page.blocks),
            "tables": len(page.tables),
            "rows": sum(len(t.rows) for t in page.tables),
            "pdf_documents": len(bundle.documents) - 1,
        }
    return rows


async def s03() -> None:
    meter = Meter()
    failures = await _capture(LIVE[0], meter)
    rows = await _normalize_all(LIVE[0])
    truth = _survey("check_ground_truth.py", LIVE[0])
    total = next((line for line in truth.splitlines() if line.startswith("TOTAL")), "")
    ground_truth_ok = total.startswith("TOTAL: 0 of")
    passed = (
        not failures
        and len(rows) == len(SEEDS)
        and all(row["mode"] == "browser" for row in rows.values())
        and all(row["quality_score"] == 1.0 for row in rows.values())
        and ground_truth_ok
    )
    _write(
        "S03",
        passed,
        {
            "acquisition_failures": failures,
            "ground_truth": total,
            "seeds": {
                seed: {k: v for k, v in row.items() if k != "normalized_page"}
                for seed, row in rows.items()
            },
        },
        meter,
    )


async def s04() -> None:
    meter = Meter()
    failures = await _capture(LIVE[1], meter)
    first = await _normalize_all(LIVE[0])
    second = await _normalize_all(LIVE[1])
    comparison = {
        seed: {
            "same_page_id": first[seed]["page_id"] == second[seed]["page_id"],
            "same_content_hash": first[seed]["content_hash"]
            == second[seed]["content_hash"],
            "same_normalized_page": first[seed]["normalized_page"]
            == second[seed]["normalized_page"],
            "same_warnings": first[seed]["warnings"] == second[seed]["warnings"],
            "quality_scores": [
                first[seed]["quality_score"],
                second[seed]["quality_score"],
            ],
        }
        for seed in first
        if seed in second
    }
    passed = (
        not failures
        and len(comparison) == len(SEEDS)
        and all(
            row["same_page_id"] and row["same_normalized_page"] and row["same_warnings"]
            for row in comparison.values()
        )
    )
    _write(
        "S04",
        passed,
        {"acquisition_failures": failures, "comparison": comparison},
        meter,
    )


# --- S05: PDF admission on the fresh capture -----------------------------------------


async def s05() -> None:
    meter = Meter()
    labels_file = json.loads((BASE / "data" / "seed-pdf-labels.json").read_text())
    labels, as_of = labels_file["pdfs"], date.fromisoformat(labels_file["as_of"])
    rows: list[dict[str, Any]] = []
    for seed, artifact in _artifacts(LIVE[0]).items():
        for document in artifact.downloadable_documents:
            admission = assess_pdf_metadata(document, as_of=as_of)
            skipped = admission.relevance is PdfAdmissionRelevance.IRRELEVANT or (
                admission.temporal_status is PdfTemporalStatus.HISTORICAL
            )
            label = labels.get(document.sha256, {}).get("label", "unlabelled")
            rows.append(
                {
                    "seed": seed,
                    "file": str(document.final_url).rsplit("/", 1)[-1],
                    "label": label,
                    "skipped": skipped,
                    "admission": f"{admission.relevance.value}/"
                    f"{admission.temporal_status.value}",
                }
            )
    # Warnings the service raises for the skipped ones, end to end.
    service = StructuralNormalizationService(
        artifact_reader=_CapturedPdfs(LIVE[0]),
        pdf_extractor=GeminiPdfExtractionService(
            PdfExtractionSettings(), _ReplayRepository({}), api_key=None
        ),
    )
    skip_warnings = 0
    for artifact in _artifacts(LIVE[0]).values():
        bundle = await service.normalize(artifact)
        skip_warnings += sum(
            1
            for w in bundle.warnings
            if w.code
            in {
                NormalizationWarningCode.PDF_SKIPPED_HISTORICAL,
                NormalizationWarningCode.PDF_SKIPPED_IRRELEVANT,
            }
        )
    current_skipped = [
        r for r in rows if r["label"] in {"current", "future"} and r["skipped"]
    ]
    historical_kept = [
        r for r in rows if r["label"] == "historical" and not r["skipped"]
    ]
    unlabelled = [r for r in rows if r["label"] == "unlabelled"]
    skipped_count = sum(1 for r in rows if r["skipped"])
    passed = (
        not current_skipped and not historical_kept and skip_warnings == skipped_count
    )
    _write(
        "S05",
        passed,
        {
            "pdf_links": len(rows),
            "skipped": skipped_count,
            "skip_warnings": skip_warnings,
            "current_or_future_skipped": current_skipped,
            "historical_transcribed": historical_kept,
            "unlabelled": unlabelled,
            "irrelevant_transcribed": [
                r for r in rows if r["label"] == "irrelevant" and not r["skipped"]
            ],
        },
        meter,
    )


# --- S06: real Gemini output, replayed -----------------------------------------------


class _ReplayRepository:
    """Serves stored Gemini transcriptions by PDF hash and model, whatever the
    fingerprint, and never saves. A miss means a new model call would be
    needed: the Gemini guard then refuses it."""

    def __init__(self, stored: dict[tuple[str, str], PdfExtractionResponse]) -> None:
        self._stored = stored
        self.hits = 0

    async def get_exact(self, *, document_sha256, model_name, **_: Any):
        response = self._stored.get((document_sha256, model_name))
        self.hits += response is not None
        return response

    async def save(self, **_: Any) -> None:
        raise AssertionError("a replay never saves")


async def _stored_transcriptions() -> list[asyncpg.Record]:
    connection = await asyncpg.connect(ASYNCPG_URL.format(pw=PASSWORD, db="tariff_rt"))
    try:
        return await connection.fetch(
            "SELECT DISTINCT ON (document_sha256) document_sha256, model_name, "
            "content_fingerprint, response::text AS response "
            "FROM pdf_extraction_cache ORDER BY document_sha256, updated_at DESC"
        )
    finally:
        await connection.close()


async def s06() -> None:
    meter = Meter()
    records = await _stored_transcriptions()
    stored = {
        (
            row["document_sha256"],
            row["model_name"],
        ): PdfExtractionResponse.model_validate_json(row["response"])
        for row in records
    }
    repository = _ReplayRepository(stored)
    extractor = GeminiPdfExtractionService(
        PdfExtractionSettings(), repository, api_key="replay-only"
    )
    service = StructuralNormalizationService(
        artifact_reader=_CapturedPdfs(LIVE[0]), pdf_extractor=extractor
    )
    documents: dict[str, dict[str, Any]] = {}
    replayable = {sha for sha, _ in stored}
    for seed, artifact in _artifacts(LIVE[0]).items():
        subset = tuple(
            d for d in artifact.downloadable_documents if d.sha256 in replayable
        )
        if not subset:
            continue
        bundle = await service.normalize(
            artifact.model_copy(update={"downloadable_documents": subset})
        )
        for document in bundle.documents[1:]:
            warnings = [w for w in bundle.warnings if w.source_id == document.id]
            cells = [c for t in document.tables for r in t.rows for c in r.cells]
            documents.setdefault(
                document.content_sha256[:12],
                {
                    "seed": seed,
                    "name": document.name[:80],
                    "method": document.extraction_method,
                    "quality_score": document.quality_score,
                    "blocks": len(document.blocks),
                    "tables": len(document.tables),
                    "cells": len(cells),
                    "cells_citing_themselves": sum(
                        1 for c in cells if ":cell:" in c.source_refs[0].source_item_id
                    ),
                    "headers_clean": all(
                        h == " ".join(h.split())
                        for t in document.tables
                        for h in t.headers
                    ),
                    "warnings": [
                        f"{w.code.value}: {w.message[:120]}" for w in warnings
                    ],
                },
            )
    transcribed = [
        d for d in documents.values() if d["method"].startswith("gemini_pdf:")
    ]
    passed = (
        len(GEMINI_ATTEMPTS) == meter.gemini_before
        and transcribed
        and all(d["cells"] == d["cells_citing_themselves"] for d in transcribed)
        and all(d["headers_clean"] for d in transcribed)
    )
    _write(
        "S06",
        passed,
        {
            "stored_transcriptions": len(records),
            "replay_hits": repository.hits,
            "documents": documents,
        },
        meter,
    )


# --- S07: PDF failure handling without Gemini -----------------------------------------


class _Bug:
    async def extract(self, document, content, *, document_id):
        raise KeyError("a mapping bug")


async def s07() -> None:
    meter = Meter()
    artifact = _artifacts(LIVE[0])["mortgage_express"]
    documents = artifact.downloadable_documents
    outcomes: dict[str, Any] = {}

    # 1. No key, no OCR engine on this host: every admitted PDF needs a model.
    no_key = StructuralNormalizationService(
        artifact_reader=_CapturedPdfs(LIVE[0]),
        pdf_extractor=GeminiPdfExtractionService(
            PdfExtractionSettings(), _ReplayRepository({}), api_key=None
        ),
    )
    bundle = await no_key.normalize(artifact)
    outcomes["no_key"] = sorted(
        w.code.value for w in bundle.warnings if "PDF" in w.code.value
    )

    # 2. A file that is not a PDF.
    class _Garbage:
        async def read(self, stored: StoredArtifact) -> bytes:
            return b"%PDF-1.7 truncated"

    unreadable = StructuralNormalizationService(
        artifact_reader=_Garbage(),
        pdf_extractor=GeminiPdfExtractionService(
            PdfExtractionSettings(), _ReplayRepository({}), api_key="unused"
        ),
    )
    bundle = await unreadable.normalize(
        artifact.model_copy(update={"downloadable_documents": documents[:1]})
    )
    outcomes["unreadable"] = [
        w.code.value
        for w in bundle.warnings
        if "BASELINE" not in w.code.value and "AMBIGUOUS" not in w.code.value
    ]

    # 3. A bug in the PDF path fails the stage instead of becoming a warning.
    buggy = StructuralNormalizationService(
        artifact_reader=_CapturedPdfs(LIVE[0]), pdf_extractor=_Bug()
    )
    try:
        await buggy.normalize(artifact)
        outcomes["bug"] = "no exception"
    except KeyError as exc:
        outcomes["bug"] = f"raised {type(exc).__name__}"

    # 4. Offline tools: NoPdfExtractor.
    bundle = await _no_pdf_service(LIVE[0]).normalize(artifact)
    outcomes["no_pdf_extractor"] = sorted(
        {w.code.value for w in bundle.warnings if "PDF" in w.code.value}
    )

    admitted = sum(
        1
        for d in documents
        if assess_pdf_metadata(d, as_of=d.retrieved_at.date()).temporal_status
        is not PdfTemporalStatus.HISTORICAL
    )
    passed = (
        outcomes["no_key"].count("PDF_MODEL_REQUIRED") == admitted
        and outcomes["unreadable"] == ["ARTIFACT_UNAVAILABLE"]
        and outcomes["bug"] == "raised KeyError"
        and outcomes["no_pdf_extractor"] == ["PDF_MODEL_REQUIRED"]
        and len(GEMINI_ATTEMPTS) == meter.gemini_before
    )
    _write(
        "S07",
        passed,
        {"pdf_links": len(documents), "admitted": admitted, "outcomes": outcomes},
        meter,
    )


# --- S08: evidence built from the real bundles ------------------------------------------


def _select_everything(bundle: NormalizedSourceBundle):
    from tests.unit.test_semantic_extraction import _fixture

    _, template = _fixture()
    assessment = template.assessments[0]
    page = bundle.documents[0]
    refs = [block.source_refs[0] for block in page.blocks] + [
        table.source_refs[0] for table in page.tables
    ]
    return template.model_copy(
        update={
            "assessments": (
                assessment.model_copy(
                    update={"document_id": page.id, "source_refs": tuple(refs)}
                ),
            )
        }
    )


async def _evidence(cache: Path) -> dict[str, list[Any]]:
    service = _no_pdf_service(cache)
    out = {}
    for seed, artifact in _artifacts(cache).items():
        bundle = await service.normalize(
            artifact.model_copy(update={"downloadable_documents": ()})
        )
        out[seed] = list(build_evidence_catalog(bundle, _select_everything(bundle)))
    return out


async def s08() -> None:
    meter = Meter()
    first = await _evidence(LIVE[0])
    second = await _evidence(LIVE[1])
    per_seed = {}
    for seed, items in first.items():
        rows = [i for i in items if ":row:" in i.source_item_id]
        notes = [i for i in items if ":note:" in i.source_item_id]
        sections = {i.section for i in rows}
        per_seed[seed] = {
            "evidence_items": len(items),
            "row_items": len(rows),
            "rows_with_section_line": sum(
                1 for i in rows if i.content.startswith("Section: ")
            ),
            "note_items": len(notes),
            "notes_with_marker_shown": sum(
                1 for i in notes if i.content[:1] in "*⁰¹²³⁴⁵⁶⁷⁸⁹†‡"
            ),
            "longest_table_section_label": max(
                (len(s or "") for s in sections), default=0
            ),
            "same_evidence_ids_across_captures": [i.evidence_id for i in items]
            == [i.evidence_id for i in second.get(seed, [])],
        }
    express = per_seed["mortgage_primary"]
    passed = (
        all(row["same_evidence_ids_across_captures"] for row in per_seed.values())
        and all(row["longest_table_section_label"] <= 200 for row in per_seed.values())
        and express["rows_with_section_line"] > 0
        and sum(row["notes_with_marker_shown"] for row in per_seed.values()) > 0
    )
    sample = next(
        (
            i.content
            for i in first["mortgage_primary"]
            if i.content.startswith("Section: ")
        ),
        None,
    )
    note = next(
        (i.content for i in first["mortgage_primary"] if ":note:" in i.source_item_id),
        None,
    )
    _write(
        "S08",
        passed,
        {"seeds": per_seed, "sample_row": sample, "sample_note": note},
        meter,
    )


# --- S09: artifacts and baselines stored before the fixes ------------------------------


async def s09() -> None:
    meter = Meter()
    service = _no_pdf_service(REFERENCE)
    rows = {}
    for seed, artifact in _artifacts(REFERENCE).items():
        bundle = await service.normalize(
            artifact.model_copy(update={"downloadable_documents": ()})
        )
        page = bundle.documents[0]
        rows[seed] = {
            "loaded": True,
            "table_blocks_without_id": sum(
                1
                for b in artifact.blocks
                if b.type.value == "table" and b.table_id is None
            ),
            "table_blocks_linked": sum(1 for b in page.blocks if b.table_id),
            "tables": len(page.tables),
            "quality_score": page.quality_score,
        }
    connection = await asyncpg.connect(
        ASYNCPG_URL.format(pw=PASSWORD, db="tariff_acquisition_scenarios")
    )
    try:
        record = await connection.fetchrow(
            "SELECT inventory::text AS inventory FROM acquisition_baselines "
            "WHERE source_url LIKE '%overdraft%' AND inventory IS NOT NULL"
        )
    finally:
        await connection.close()
    stored_inventory = json.loads(record["inventory"]) if record else None
    today = _artifacts(LIVE[0])["overdraft"].inventory
    reasons = (
        compare_inventory(
            AcquisitionInventory.model_validate(stored_inventory),
            today,
            load_settings().acquisition,
        )
        if stored_inventory
        else None
    )
    passed = (
        len(rows) == len(SEEDS)
        and all(r["table_blocks_linked"] == r["tables"] for r in rows.values())
        and stored_inventory is not None
        and "payloads" in stored_inventory
        and reasons == ()
    )
    _write(
        "S09",
        passed,
        {
            "stored_artifacts": rows,
            "stored_baseline": stored_inventory,
            "today": today.model_dump(),
            "baseline_comparison": reasons,
        },
        meter,
    )


# --- S10: what the first production run will pay for PDFs --------------------------------


async def s10() -> None:
    meter = Meter()
    records = await _stored_transcriptions()
    by_sha = {row["document_sha256"]: row for row in records}
    extractor = GeminiPdfExtractionService(
        PdfExtractionSettings(), _ReplayRepository({}), api_key=None
    )
    rows = []
    seen = set()
    for artifact in _artifacts(LIVE[0]).values():
        for document in artifact.downloadable_documents:
            if document.sha256 in seen:
                continue
            seen.add(document.sha256)
            content = (LIVE[0] / "pdfs" / f"{document.sha256}.pdf").read_bytes()
            plan = extractor.plan(
                document, content, document_id=f"document:{document.sha256[:12]}"
            )
            skipped = extractor._skip_reason(plan) is not None
            stored = by_sha.get(document.sha256)
            rows.append(
                {
                    "file": str(document.final_url).rsplit("/", 1)[-1],
                    "skipped": skipped,
                    "stored_transcription": stored is not None,
                    "stored_fingerprint_still_matches": bool(
                        stored
                        and stored["content_fingerprint"] == plan.content_fingerprint
                    ),
                    "pages": plan.input_probe.page_count,
                }
            )
    admitted = [r for r in rows if not r["skipped"]]
    reusable = [r for r in admitted if r["stored_fingerprint_still_matches"]]
    new_calls = [r for r in admitted if not r["stored_fingerprint_still_matches"]]
    passed = len(GEMINI_ATTEMPTS) == meter.gemini_before
    _write(
        "S10",
        passed,
        {
            "distinct_pdfs": len(rows),
            "skipped_by_admission": len(rows) - len(admitted),
            "admitted": len(admitted),
            "admitted_with_stored_transcription": sum(
                1 for r in admitted if r["stored_transcription"]
            ),
            "reusable_from_cache": len(reusable),
            "would_be_transcribed": len(new_calls),
            "pages_to_transcribe": sum(r["pages"] for r in new_calls),
            "stored_but_fingerprint_changed": [
                r["file"]
                for r in admitted
                if r["stored_transcription"]
                and not r["stored_fingerprint_still_matches"]
            ],
            "pdfs": rows,
        },
        meter,
    )


# --- S11: a late footer module does not rename the page (finding F1) ---------------


async def s11() -> None:
    from bs4 import BeautifulSoup

    from app.services.acquisition import AcquisitionService
    from app.services.html_parser import HtmlArtifactParser

    meter = Meter()
    parser = HtmlArtifactParser(load_settings().http.allowed_source_hosts)
    rows = {}
    for seed, artifact in _artifacts(LIVE[0]).items():
        soup = BeautifulSoup(artifact.rendered_html or "", "html.parser")
        notice = soup.find(string=lambda text: bool(text) and "Dear User" in text)
        if notice is None:
            continue
        module = notice.find_parent(class_="wsc_cm_module_container")
        without = str(soup).replace(str(module), "")
        url = str(artifact.final_url)
        ids = [
            AcquisitionService._page_content_hash(
                canonical_url=str(artifact.canonical_url),
                parsed=parser.parse(html, source_url=url),
            )
            for html in (artifact.rendered_html or "", without)
        ]
        # The main content of the page must still name it: change a table cell.
        changed_tariff = (artifact.rendered_html or "").replace("Annual", "Yearly", 1)
        tariff_id = AcquisitionService._page_content_hash(
            canonical_url=str(artifact.canonical_url),
            parsed=parser.parse(changed_tariff, source_url=url),
        )
        rows[seed] = {
            "notice_removed": "Dear User" not in without,
            "same_page_id_without_notice": ids[0] == ids[1],
            "content_edit_renames": tariff_id != ids[0]
            if changed_tariff != artifact.rendered_html
            else None,
        }
    passed = bool(rows) and all(
        row["notice_removed"]
        and row["same_page_id_without_notice"]
        and row["content_edit_renames"] is not False
        for row in rows.values()
    )
    _write("S11", passed, {"pages_with_the_notice": len(rows), "pages": rows}, meter)


SCENARIOS = {
    "S01": s01,
    "S02": s02,
    "S03": s03,
    "S04": s04,
    "S05": s05,
    "S06": s06,
    "S07": s07,
    "S08": s08,
    "S09": s09,
    "S10": s10,
    "S11": s11,
}


async def main(selected: list[str]) -> None:
    for sid in selected or list(SCENARIOS):
        await SCENARIOS[sid]()
    print(f"Gemini client attempts in this process: {len(GEMINI_ATTEMPTS)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
