"""Run the semantic-extraction scenarios that need no Gemini call.

    uv run python fix-process/semantic_extraction/scenarios/run_scenarios.py [S01 S03 ...]

Each writes `results/SXX.json` with `passed` and the measurements behind it.
S06 (live extraction) and the live half of S05 are run with
`survey/check_extraction_labels.py`; S10 is computed from their reports.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BASE / "survey"))
os.chdir(ROOT)

TEST_DB = "postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_acquisition_test"


def _write(name: str, passed: bool, details: dict[str, Any]) -> None:
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{name}.json").write_text(
        json.dumps(
            {"scenario": name, "passed": passed, **details}, indent=1, default=str
        )
        + "\n"
    )
    print(f"{name}: {'PASS' if passed else 'FAIL'}")


def _pytest(*args: str) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            *args,
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "TEST_DATABASE_URL": TEST_DB},
    )
    summary = completed.stdout.strip().splitlines()[-1] if completed.stdout else ""
    counts = {
        key: int(value)
        for value, key in re.findall(
            r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)", summary
        )
    }
    failures = re.findall(r"^(?:FAILED|ERROR) (\S+)", completed.stdout, re.MULTILINE)
    return {"summary": summary, "counts": counts, "failures": failures}


def s01() -> None:
    result = _pytest("tests/unit", "tests/integration")
    known = {
        "tests/integration/test_agent.py::test_agent_stream",
        "tests/integration/test_server_e2e.py::test_adk_run_sse",
        "tests/integration/test_server_e2e.py::test_a2a_chat_stream",
        "tests/integration/test_server_e2e.py::test_agent_card",
    }
    unexpected = [item for item in result["failures"] if item not in known]
    xfail_markers = len(
        re.findall(
            r"mark\.xfail",
            (ROOT / "tests/unit/test_semantic_extraction_fixes.py").read_text(),
        )
    )
    _write(
        "S01",
        not unexpected and xfail_markers == 0,
        {
            **result,
            "unexpected_failures": unexpected,
            "se_xfail_markers_left": xfail_markers,
        },
    )


def s02() -> None:
    result = _pytest("tests/unit/test_semantic_extraction_fixes.py")
    tests = [
        "se13",
        "se16",
        "se15",
        "se14",
        "se17",
        "se18",
        "se10",
        "se11",
        "se1_",
        "se2_",
        "se4_",
        "se21",
        "se20",
        "se25",
    ]
    _write(
        "S02",
        result["counts"].get("failed", 0) == 0
        and result["counts"].get("passed", 0) > 0,
        {**result, "covered_items": tests},
    )


def _probe(*args: str) -> str:
    completed = subprocess.run(
        [sys.executable, str(BASE / "survey/probe_evidence_recall.py"), *args],
        capture_output=True,
        text=True,
    )
    return completed.stdout


def s03() -> None:
    runs = {}
    for label, args in (
        ("full", ["--mode", "full", "--label", "s03-full"]),
        ("budgeted", ["--mode", "budgeted", "--label", "s03-budgeted"]),
        ("full_pdfs", ["--mode", "full", "--pdfs", "--label", "s03-full-pdfs"]),
        (
            "budgeted_pdfs",
            ["--mode", "budgeted", "--pdfs", "--label", "s03-budgeted-pdfs"],
        ),
    ):
        output = _probe(*args)
        match = re.search(r"reaching their batch: (\d+)/(\d+)", output)
        facts = json.loads(
            (
                BASE / f"data/evidence-recall-s03-{label.replace('_', '-')}.json"
            ).read_text()
        )
        own_block_siblings = sum(
            1 for fact in facts["facts"] if fact["status"] == "sibling_in_own_block"
        )
        runs[label] = {
            "sent": int(match.group(1)),
            "facts": int(match.group(2)),
            "sibling_facts_in_own_block": own_block_siblings,
            "sizes": re.search(r"calls per offering.*", output).group(0),
        }
    passed = (
        runs["full"]["sent"] == runs["full"]["facts"]
        and runs["full_pdfs"]["sent"] == runs["full_pdfs"]["facts"]
        and runs["budgeted"]["sent"] >= 0.95 * runs["budgeted"]["facts"]
        and all(run["sibling_facts_in_own_block"] == 0 for run in runs.values())
    )
    _write("S03", passed, {"runs": runs})


def s04() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "fix-process/normalization/survey/check_ground_truth.py",
            "semantic-s04",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "SURVEY_CACHE": "fix-process/normalization/.cache-live-2"},
    )
    total = re.search(r"TOTAL: (\d+) of (\d+) checks failed", completed.stdout)
    truth = json.loads(
        (ROOT / "fix-process/normalization/data/seed-ground-truth.json").read_text()
    )
    cell_facts = sum(
        len(table.get("cells", []))
        for seed in truth["seeds"].values()
        for table in seed["tables"]
    )
    _write(
        "S04",
        total is not None and total.group(1) == "0",
        {
            "failed": int(total.group(1)),
            "checks": int(total.group(2)),
            "column_path_facts": cell_facts,
        },
    )


async def _s05() -> dict[str, Any]:
    import replay
    from check_extraction_labels import FakeExtractor

    from app.config import SemanticExtractionSettings, load_settings
    from app.domain.acquisition import PageArtifact
    from app.services.extraction_evidence import build_evidence_catalog
    from app.services.html_parser import HtmlArtifactParser
    from app.services.normalization import StructuralNormalizationService
    from app.services.semantic_extraction import (
        InMemorySemanticExtractionRepository,
        SemanticExtractionService,
    )
    from app.services.source_selection import build_selected_source_bundle

    replay.forbid_gemini()
    settings = load_settings()
    parser = HtmlArtifactParser(settings.http.allowed_source_hosts)
    catalog = replay.catalog()
    base = await replay.load_seed("mortgage_primary", parser, catalog)
    artifact = replay.cdl.reparsed(
        PageArtifact.model_validate_json(
            (replay.CACHE / "mortgage_primary.artifact.json").read_text()
        ),
        parser,
    )
    html = re.sub(
        r"(<body[^>]*>)",
        r'\1<p data-acquisition-visible="true">A new promotion this month.</p>',
        artifact.rendered_html or "",
        count=1,
    )
    shifted = replay.cdl.reparsed(
        artifact.model_copy(
            update={"rendered_html": html, "page_content_hash": "f" * 64}
        ),
        parser,
    )
    bundle = await StructuralNormalizationService(
        artifact_reader=None, pdf_extractor=None
    ).normalize(shifted.model_copy(update={"downloadable_documents": ()}))
    discovery = base.discovery.model_copy(
        update={
            "input_content_hash": bundle.acquisition_content_hash,
            "assessments": tuple(
                assessment.model_copy(update={"document_id": bundle.documents[0].id})
                for assessment in base.discovery.assessments
            ),
        }
    )

    def table_ids(b, d) -> set[str]:
        evidence = build_evidence_catalog(build_selected_source_bundle(b, d), d)
        return {
            item.evidence_id
            for item in evidence
            if item.source_item_id.startswith("t1:")
        }

    before, after = table_ids(base.bundle, base.discovery), table_ids(bundle, discovery)
    extractor = FakeExtractor({"mortgage_primary": "mortgage"})
    extractor.seed = "mortgage_primary"
    service = SemanticExtractionService(
        extractor,
        InMemorySemanticExtractionRepository(),
        SemanticExtractionSettings(),
        model_name="fake",
    )
    await service.extract(
        base.bundle, base.discovery, retrieved_at=base.artifact.retrieved_at
    )
    first_calls = extractor.calls
    await service.extract(
        base.bundle, base.discovery, retrieved_at=base.artifact.retrieved_at
    )
    return {
        "table_evidence_ids": len(before),
        "unchanged_after_insertion": before == after,
        "first_run_calls": first_calls,
        "second_run_calls": extractor.calls - first_calls,
    }


def s05() -> None:
    details = asyncio.run(_s05())
    live = BASE / "data/extraction-check-after-rerun.json"
    if live.exists():
        details["live_rerun"] = json.loads(live.read_text())["usage"]
    passed = (
        details["unchanged_after_insertion"]
        and details["second_run_calls"] == 0
        and ("live_rerun" not in details or details["live_rerun"]["calls"] == 0)
    )
    _write("S05", passed, details)


def s07() -> None:
    result = _pytest("tests/unit/test_semantic_extraction_fixes.py", "-k", "se12")
    _write("S07", result["counts"].get("passed", 0) == 1, result)


async def _s08() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from app.services.semantic_extraction import (
        FallbackSemanticExtractionService,
        InMemorySemanticExtractionRepository,
    )
    from app.services.snapshot_lifecycle import non_reviewable_extraction_failure
    from tests.unit import test_semantic_extraction_fixes as fixes

    bundle, discovery = fixes._mortgage_bundle(
        "Interest rate 14%; loan amount AMD 3,000,000"
    )
    repository = InMemorySemanticExtractionRepository()
    both_fail = FallbackSemanticExtractionService(
        (
            fixes._service(
                fixes._FailsCoreFinancial(), repository, model_name="model-a"
            ),
            fixes._service(
                fixes._FailsCoreFinancial(), repository, model_name="model-b"
            ),
        )
    )
    result = await both_fail.extract(bundle, discovery, retrieved_at=fixes.RETRIEVED_AT)
    cached_statuses = dict(repository.validation_statuses)
    return {
        "failure_code": non_reviewable_extraction_failure(result),
        "calls_cached": len(cached_statuses),
        "calls_in_offering": 3,
        "review_items_with_foreign_raw_output": sum(
            1
            for item in result.review_items
            if item.raw_response and "model-" in item.raw_response
        ),
    }


def s08() -> None:
    fallback = _pytest(
        "tests/unit/test_semantic_extraction_fixes.py", "-k", "se25 or se13"
    )
    details = {"fallback_tests": fallback, **asyncio.run(_s08())}
    passed = (
        fallback["counts"].get("failed", 0) == 0
        and details["failure_code"] == "semantic_extraction.execution_failed"
        and details["calls_cached"] == 2
        and details["review_items_with_foreign_raw_output"] == 0
    )
    _write("S08", passed, details)


def s09() -> None:
    result = _pytest("tests/unit/test_semantic_extraction_fixes.py", "-k", "se18")
    _write(
        "S09",
        result["counts"].get("failed", 0) == 0
        and result["counts"].get("passed", 0) >= 3,
        result,
    )


SCENARIOS = {
    "S01": s01,
    "S02": s02,
    "S03": s03,
    "S04": s04,
    "S05": s05,
    "S07": s07,
    "S08": s08,
    "S09": s09,
}


if __name__ == "__main__":
    for name in sys.argv[1:] or SCENARIOS:
        SCENARIOS[name]()
