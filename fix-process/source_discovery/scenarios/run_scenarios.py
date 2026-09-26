"""Run the source-discovery fix scenarios and write `results/Sxx.json`.

    uv run python fix-process/source_discovery/scenarios/run_scenarios.py [S01 ...]

No scenario spends Gemini budget. The Gemini key is removed from the process
and `google.genai.Client` is replaced by one that records the attempt and
raises, so any model call fails the scenario. Scenarios about Gemini's own
answers (S03, S04, the first half of S05) read the recorded Phase 7 run in
`data/discovery-check-after*.json`; the others drive the real code with fake
classifiers on the captured seed pages (`fix-process/normalization/.cache-live-2`).

S01 runs the Postgres tests against the scratch `tariff_acquisition_test`
database on the dev container; its password is read into memory only.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
CACHE = ROOT / "fix-process/normalization/.cache-live-2"
sys.path.insert(0, str(ROOT))

# --- The Gemini guard: no key, and no client can be created. -----------------
os.environ["GEMINI_API_KEY"] = ""
os.environ.pop("GOOGLE_API_KEY", None)

import google.genai  # noqa: E402

GEMINI_ATTEMPTS: list[str] = []


class _RefusingClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        GEMINI_ATTEMPTS.append("google.genai.Client")
        raise RuntimeError("Gemini is disabled in the source-discovery scenarios")


google.genai.Client = _RefusingClient  # type: ignore[misc]

from app.config import SourceDiscoverySettings, load_settings  # noqa: E402
from app.config.seed_catalog import load_seed_catalog  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.domain.models import OfferingId  # noqa: E402
from app.domain.normalization import NormalizedBlockType  # noqa: E402
from app.domain.source_discovery import (  # noqa: E402
    Authority,
    DecisionSource,
    DiscoveryBatch,
    DiscoveryBatchResponse,
    EffectivePeriod,
    InformationRole,
    ModelSourceAssessment,
    OfferingContext,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.knowledge_projection import KnowledgeProjectionService  # noqa: E402
from app.services.normalization import StructuralNormalizationService  # noqa: E402
from app.services.source_discovery import (  # noqa: E402
    FallbackSourceDiscoveryService,
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)
from app.services.source_selection import (  # noqa: E402
    build_selected_source_bundle,
    select_sources,
)

SEED_CATALOG = load_seed_catalog()
CATALOG = {entry.offering_id.value: entry for entry in SEED_CATALOG.offerings}
PARSER = HtmlArtifactParser(load_settings().http.allowed_source_hosts)
AS_OF = date(2026, 9, 26)


def _write(sid: str, passed: bool, details: dict[str, Any], started: float) -> None:
    RESULTS.mkdir(exist_ok=True)
    payload = {
        "scenario": sid,
        "passed": passed,
        "gemini_attempts": len(GEMINI_ATTEMPTS),
        "gemini_cost_usd": 0.0,
        "wall_seconds": round(time.monotonic() - started, 1),
        **details,
    }
    (RESULTS / f"{sid}.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n"
    )
    print(
        f"{sid}: {'PASS' if passed else 'FAIL'} {json.dumps(details, default=str)[:300]}"
    )


async def _bundle(seed: str):
    """A seed page as this branch reads it: re-parsed, normalized, no PDFs."""
    artifact = PageArtifact.model_validate_json(
        (CACHE / f"{seed}.artifact.json").read_text()
    )
    parsed = PARSER.parse(
        artifact.rendered_html or "", source_url=str(artifact.final_url)
    )
    artifact = artifact.model_copy(
        update={
            "blocks": parsed.blocks,
            "tables": parsed.tables,
            "links": parsed.links,
            "downloadable_documents": (),
        }
    )
    normalizer = StructuralNormalizationService(
        artifact_reader=None, pdf_extractor=None
    )
    return artifact, await normalizer.normalize(artifact)


def _offering(seed: str, artifact: PageArtifact) -> OfferingContext:
    return OfferingContext.from_catalog_entry(
        CATALOG[seed],
        page_title=artifact.title,
        page_blocks=artifact.blocks,
        catalog=SEED_CATALOG,
    )


class _Accepting:
    """Accepts every item as the current product; counts what it is asked."""

    def __init__(self) -> None:
        self.items: list[str] = []
        self.calls = 0

    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        self.calls += 1
        self.items.extend(item.source_id for item in batch.items)
        return DiscoveryBatchResponse(
            items=tuple(self._answer(item) for item in batch.items)
        )

    def _answer(self, item) -> ModelSourceAssessment:
        return ModelSourceAssessment(
            source_id=item.source_id,
            product_association=ProductAssociation.CURRENT_PRODUCT,
            role=InformationRole.PRODUCT_TERMS,
            relevance=Relevance.RELEVANT,
            authority=Authority.OFFICIAL_PRODUCT_CONTENT,
            temporal_status=TemporalStatus.CURRENT,
            reason="scenario classifier",
        )


def _service(classifier, repository=None, model: str = "scenario-model", **settings):
    return SourceDiscoveryService(
        classifier,
        repository or InMemorySourceDiscoveryRepository(),
        SourceDiscoverySettings(**settings),
        model_name=model,
    )


# --- S01 ---------------------------------------------------------------------------


async def s01() -> None:
    started = time.monotonic()
    password = subprocess.run(
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
    files = [
        "tests/unit/test_source_discovery_fixes.py",
        "tests/unit/test_source_discovery.py",
        "tests/unit/test_pdf_link_selection.py",
        "tests/unit/test_source_selection.py",
        "tests/unit/test_knowledge_projection.py",
        "tests/unit/test_monitoring_pipeline.py",
        "tests/unit/test_gemini_pdf_extraction.py",
        "tests/unit/test_file_llm_caches.py",
        "tests/unit/test_config.py",
        "tests/unit/test_normalization_pdf_fixes.py",
        "tests/integration/test_source_discovery_postgres.py",
        "tests/integration/test_knowledge_store_postgres.py",
        "tests/integration/test_monitoring_repository_postgres.py",
    ]
    env = {
        **os.environ,
        "TEST_DATABASE_URL": (
            f"postgresql+asyncpg://tariff:{password}@localhost:5434/"
            "tariff_acquisition_test"
        ),
    }
    completed = subprocess.run(
        ["uv", "run", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", *files],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    summary = completed.stdout.strip().splitlines()[-1]
    passed = completed.returncode == 0 and "skipped" not in summary
    _write("S01", passed, {"files": len(files), "summary": summary}, started)


# --- S02 ---------------------------------------------------------------------------


async def s02() -> None:
    started = time.monotonic()
    output = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "fix-process/source_discovery/survey/probe_discovery.py",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout
    (RESULTS / "S02-probe-output-now.txt").write_text(output)
    rows = [line for line in output.splitlines() if " candidates=" in line]
    chrome = sum(
        int(line.split("gemini_items_with_chrome=")[1].split()[0]) for line in rows
    )
    cut = sum(int(line.split("cut>3000=")[1].split()[0]) for line in rows)
    shared = sum(
        int(line.split("shared_structural_groups=")[1])
        for line in output.splitlines()
        if "shared_structural_groups=" in line
    )
    details = {
        "seeds": len(rows),
        "gemini_items_with_site_chrome": chrome,
        "gemini_items_seen_only_in_part": cut,
        "shared_structural_fingerprints_within_a_page": shared,
    }
    _write(
        "S02",
        len(rows) == 13 and chrome == 0 and cut == 0 and shared == 0,
        details,
        started,
    )


# --- S03 and S04: the recorded Gemini run -------------------------------------------

FOUR_MORTGAGE_PAGES = (
    "mortgage_primary",
    "mortgage_construction",
    "mortgage_renovation",
    "mortgage_secondary_market",
)


async def s03() -> None:
    started = time.monotonic()
    run = json.loads(
        # The final Phase 8 Gemini pass: all 13 seeds, final code and labels.
        (BASE / "data/discovery-check-final.json").read_text()
    )
    before = json.loads(
        (BASE / "data/discovery-check-before-final-labels.json").read_text()
    )
    express = {
        seed: next(
            table["outcome"]
            for table in run["seeds"][seed]["tables"]
            if (table["title"] or "").startswith("Express Home Mortgage Loan")
        )
        for seed in FOUR_MORTGAGE_PAGES
    }
    own_tables = [
        (seed, table["title"], table["outcome"])
        for seed, value in run["seeds"].items()
        for table in value["tables"]
        if table["expected"] == "current"
    ]
    wrong_own = [
        row for row in own_tables if row[2] not in {"current", "unknown", "generic"}
    ]
    section_leaks = [
        (seed, failure["path"][-60:], failure["text"][:60])
        for seed, value in run["seeds"].items()
        for failure in value["failures"]
        if failure["kind"] == "leak" and failure["item"] == "block"
    ]
    details = {
        "express_table": express,
        "own_tables_current": f"{len(own_tables) - len(wrong_own)} of {len(own_tables)}",
        "own_tables_wrong": wrong_own,
        "leaks_after": run["totals"]["leak"],
        "leaks_before": before["totals"]["leak"],
        "section_leaks_after": section_leaks,
    }
    passed = (
        all(outcome == "related" for outcome in express.values())
        and not wrong_own
        and not section_leaks
    )
    _write("S03", passed, details, started)


async def s04() -> None:
    """Link selection, then the Phase 8 content check of every kept PDF."""
    started = time.monotonic()
    run = json.loads((BASE / "data/discovery-check-after.json").read_text())
    content = json.loads((BASE / "data/pdf-content-check-phase8.json").read_text())
    checked = {(row["seed"], row["file"]): row for row in content["rows"]}
    labels = json.loads((BASE / "data/seed-discovery-labels.json").read_text())["seeds"]
    rows = []
    for seed, value in run["seeds"].items():
        for pdf in value["pdfs"]:
            label = labels[seed]["pdfs"].get(pdf["file"], pdf["label"])
            row = checked.get((seed, pdf["file"]))
            own = bool(
                pdf["selected"]
                and row is not None
                and row["relevance"] != "irrelevant"
                and row["association"] in {"current_product", "unknown"}
                and row["temporal"] not in {"possibly_stale", "future"}
            )
            rows.append((seed, pdf["file"], label, pdf["selected"], own))
    lost = [r for r in rows if r[2] in {"current_product", "shared_terms"} and not r[4]]
    leaked = [
        r
        for r in rows
        if r[2] in {"related_product", "irrelevant", "historical"} and r[4]
    ]
    details = {
        "links": len(rows),
        "transcribed": sum(1 for r in rows if r[3]),
        "kept_as_offering_terms": sum(1 for r in rows if r[4]),
        "own_or_shared_lost": lost,
        "sibling_irrelevant_or_expired_kept": leaked,
        "link_selector_usage": run.get("pdf_selector_usage"),
        "content_check_usage": content["usage"],
    }
    _write("S04", not lost and not leaked, details, started)


# --- S05 ---------------------------------------------------------------------------


async def s05() -> None:
    started = time.monotonic()
    run = json.loads((BASE / "data/discovery-check-after.json").read_text())
    rerun = run["cache_rerun"]
    artifact, bundle = await _bundle("mortgage_primary")
    offering = _offering("mortgage_primary", artifact)
    repository = InMemorySourceDiscoveryRepository()
    classifier = _Accepting()
    await _service(classifier, repository).discover(bundle, offering, as_of=AS_OF)
    first = len(classifier.items)
    classifier.items.clear()

    # A new block at the top of the page renumbers every later block (the
    # parser's ids are positional): b1 -> b2, b2 -> b3, ...
    page = bundle.documents[0]
    shifted = []
    for block in page.blocks:
        new_id = f"b{int(block.id[1:]) + 1}" if block.id[1:].isdigit() else block.id
        refs = tuple(
            ref.model_copy(update={"source_item_id": new_id})
            for ref in block.source_refs
        )
        shifted.append(block.model_copy(update={"id": new_id, "source_refs": refs}))
    banner = shifted[0].model_copy(
        update={
            "id": "b1",
            "type": NormalizedBlockType.PARAGRAPH,
            "text": "New autumn banner: apply before 31 October",
            "raw_text": "New autumn banner: apply before 31 October",
            "heading_path": (),
            "site_chrome": False,
            "source_refs": (
                shifted[0].source_refs[0].model_copy(update={"source_item_id": "b1"}),
            ),
        }
    )
    first_heading = next(
        index
        for index, block in enumerate(shifted)
        if block.type is NormalizedBlockType.HEADING
    )
    shifted.insert(first_heading + 1, banner)
    changed = bundle.model_copy(
        update={"documents": (page.model_copy(update={"blocks": tuple(shifted)}),)}
    )
    await _service(classifier, repository).discover(changed, offering, as_of=AS_OF)
    details = {
        "recorded_rerun": rerun,
        "items_first_run": first,
        "items_after_inserting_a_block": classifier.items,
    }
    passed = (
        rerun["discovery_calls"] == 0
        and rerun["pdf_selector_calls"] == 0
        and len(classifier.items) == 1
    )
    _write("S05", passed, details, started)


# --- S06 ---------------------------------------------------------------------------


class _DatedCampaign(_Accepting):
    """Reads the online consumer-finance offer as valid 15.04.26 to 12.01.27."""

    def _answer(self, item) -> ModelSourceAssessment:
        answer = super()._answer(item)
        return answer.model_copy(
            update={
                "effective_periods": (
                    EffectivePeriod(
                        raw="The offer is valid from 15.04.26 to 12.01.27",
                        start=date(2026, 4, 15),
                        end=date(2027, 1, 12),
                    ),
                )
            }
        )


async def s06() -> None:
    started = time.monotonic()
    artifact, bundle = await _bundle("online_consumer_finance")
    offering = _offering("online_consumer_finance", artifact)
    classifier = _DatedCampaign()
    service = _service(classifier, InMemorySourceDiscoveryRepository())

    def statuses(result: SourceDiscoveryResult) -> set[str]:
        return {
            assessment.temporal_status.value
            for assessment in result.assessments
            if assessment.decision_source in {DecisionSource.LLM, DecisionSource.CACHE}
        }

    now = await service.discover(bundle, offering, as_of=date(2026, 9, 26))
    calls = classifier.calls
    later = await service.discover(bundle, offering, as_of=date(2027, 1, 13))
    details = {
        "on_2026_09_26": sorted(statuses(now)),
        "on_2027_01_13": sorted(statuses(later)),
        "new_calls_for_the_second_date": classifier.calls - calls,
        "selected_items_after_expiry": len(select_sources(later).items),
    }
    passed = (
        statuses(now) == {"current"}
        and statuses(later) == {"possibly_stale"}
        and classifier.calls == calls
    )
    _write("S06", passed, details, started)


# --- S07 ---------------------------------------------------------------------------


class _OneBadItem(_Accepting):
    """Answers every batch holding one item with an invented id, always."""

    def __init__(self, bad_source_id: str) -> None:
        super().__init__()
        self.bad = bad_source_id

    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        self.calls += 1
        if any(item.source_id == self.bad for item in batch.items):
            answers = [self._answer(item) for item in batch.items]
            answers[0] = answers[0].model_copy(update={"source_id": "invented"})
            return DiscoveryBatchResponse(items=tuple(answers))
        self.items.extend(item.source_id for item in batch.items)
        return DiscoveryBatchResponse(
            items=tuple(self._answer(item) for item in batch.items)
        )


async def s07() -> None:
    started = time.monotonic()
    artifact, bundle = await _bundle("mortgage_primary")
    offering = _offering("mortgage_primary", artifact)
    probe = await _service(None).plan(bundle, offering)
    bad = probe.batches[1].items[3].source_id
    repository = InMemorySourceDiscoveryRepository()
    broken = _OneBadItem(bad)
    successor = _Accepting()
    service = FallbackSourceDiscoveryService(
        (
            _service(broken, repository, "first-model"),
            _service(successor, repository, "second-model"),
        )
    )
    result = await service.discover(bundle, offering, as_of=AS_OF)
    saved_by_first = sum(1 for key in repository._exact if key[4] == "first-model")
    details = {
        "batches": len(probe.batches),
        "bad_item": bad,
        "calls_to_first_model": broken.calls,
        "items_the_first_model_answered_and_saved": saved_by_first,
        "answered_by": result.model_name,
        "second_model_items": len(successor.items),
    }
    passed = (
        saved_by_first > 0
        and result.model_name == "second-model"
        and saved_by_first >= len(probe.llm_candidates) - len(probe.batches[1].items)
    )
    _write("S07", passed, details, started)


# --- S08 ---------------------------------------------------------------------------


async def s08() -> None:
    started = time.monotonic()
    run = json.loads((BASE / "data/discovery-check-after.json").read_text())
    findings: dict[str, Any] = {}
    passed = True
    for seed in ("mortgage_primary", "consumer_standard"):
        _artifact, bundle = await _bundle(seed)
        page = bundle.documents[0]
        recorded = {
            item: SourceAssessment.model_validate(value)
            for item, value in run["seeds"][seed]["assessments"].items()
        }
        discovery = SourceDiscoveryResult(
            product=CATALOG[seed].product,
            input_content_hash=bundle.acquisition_content_hash,
            policy_version="2",
            prompt_version="2",
            model_name=run["model"],
            assessments=tuple(recorded.values()),
            llm_batch_count=0,
            reused_assessment_count=0,
        )
        documents = KnowledgeProjectionService().project_sources(
            run_id=uuid4(),
            product=CATALOG[seed].product,
            offering_id=OfferingId(seed),
            bundle=build_selected_source_bundle(bundle, discovery),
            retrieved_at=datetime.now(UTC),
            language="en",
            labels=select_sources(discovery).items,
        )
        text = "\n".join(chunk.content for d in documents for chunk in d.chunks)
        chrome = [
            block.text[:40]
            for block in page.blocks
            if block.site_chrome and len(block.text) > 25 and block.text in text
        ]
        express = (
            "Express Home Mortgage Loan (Purchase, Construction and Renovation)" in text
        )
        associations = sorted(
            {
                value
                for d in documents
                for chunk in d.chunks
                for value in _as_list(chunk.metadata.get("product_associations"))
            }
        )
        findings[seed] = {
            "chunks": sum(len(d.chunks) for d in documents),
            "site_chrome_text_indexed": chrome,
            "express_table_indexed": express,
            "chunk_associations": associations,
        }
        passed = (
            passed
            and not chrome
            and not express
            and "related_product" not in associations
        )
    _write("S08", passed, findings, started)


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


SCENARIOS = {
    "S01": s01,
    "S02": s02,
    "S03": s03,
    "S04": s04,
    "S05": s05,
    "S06": s06,
    "S07": s07,
    "S08": s08,
}


async def main(selected: list[str]) -> None:
    for sid in selected or list(SCENARIOS):
        await SCENARIOS[sid]()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
