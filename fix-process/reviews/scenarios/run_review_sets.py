"""R03: review evidence sets on the seeds' real evidence catalogs, at no model cost.

    uv run python fix-process/reviews/scenarios/run_review_sets.py

Sources are replayed with their stored assessments and PDF transcriptions
(`fix-process/semantic_extraction/survey/replay.py`); no Gemini client can be built.

- **Part A, real answers.** Seeds whose three extraction calls are all in the live
  extraction cache (`fix-process/semantic_extraction/.cache/extraction-cache.json`,
  Gemini answers paid for in the semantic-extraction validation) are extracted from
  it, and every review they raise is built as the pipeline builds it.
- **Part B, every seed.** An extractor that finds nothing: every required field
  becomes a `missing_required_field` review, seeded from the passages its call read.
  For each labelled field with numbers, the check is whether the review shows a
  passage holding a labelled number (the set's recall). Then a cited set is built from
  the passages that hold the labelled numbers, as for `extraction_invalid`.

Every set is checked against the bounds (RV9), every pause view against the model
limits (R6). The report goes to `results/R03-review-sets.json`.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
SURVEY = ROOT / "fix-process" / "semantic_extraction" / "survey"
sys.path.insert(0, str(SURVEY))
sys.path.insert(0, str(ROOT))

import check_extraction_labels as labels_check  # noqa: E402
import replay  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.domain.models import OfferingId  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.monitoring_pipeline import _review_tasks  # noqa: E402
from app.services.normalized_renderer import render_normalized_markdown  # noqa: E402
from app.services.review_evidence import (  # noqa: E402
    MODEL_EXCERPT_CHARS,
    MODEL_SEED_PASSAGES,
    SECTION_MAX_CHARS,
    TABLE_WHOLE_ROWS,
    build_review_display,
    cited_evidence_set,
)
from app.services.review_resolution import build_review_view  # noqa: E402
from app.services.semantic_extraction import SemanticExtractionService  # noqa: E402
from app.services.snapshot_lifecycle import build_snapshot_attempt  # noqa: E402
from app.services.source_selection import build_selected_source_bundle  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
LABELS = labels_check.LABELS
_NUMBER = re.compile(r"\d{1,3}(?:[ ,]\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?")


class CacheOnly:
    """Answers only from the stored cache; a call it does not hold fails."""

    calls = 0

    async def extract(self, batch):
        self.calls += 1
        raise RuntimeError("not in the extraction cache")


class ReadOnlyCache(labels_check.FileExtractionCache):
    async def save(self, **_: Any) -> None:
        return None


def text_numbers(text: str) -> set[Decimal]:
    numbers: set[Decimal] = set()
    for match in _NUMBER.finditer(text):
        raw = match.group(0)
        raw = (
            raw.replace(" ", "").replace(",", "")
            if re.search(r"[ ,]\d{3}\b", raw)
            else raw.replace(",", ".")
        )
        try:
            numbers.add(Decimal(raw).normalize())
        except InvalidOperation:
            continue
    return numbers


def _snapshot(result, bundle, discovery, offering_id):
    return build_snapshot_attempt(
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=result.product,
        offering_id=OfferingId(offering_id),
        result=result,
        previous_accepted_snapshot_id=None,
        selected_sources_markdown=render_normalized_markdown(
            build_selected_source_bundle(bundle, discovery)
        ),
    )


def review_record(task, snapshot) -> dict[str, Any]:
    by_id = {item["evidence_id"]: item for item in snapshot.evidence}
    evidence_set = task.evidence["set"]
    view = build_review_view(task, snapshot.evidence)
    display = build_review_display(task, snapshot.evidence)
    problems = []
    units = []
    for unit in evidence_set["units"]:
        shown_chars = sum(len(by_id[i]["content"]) for i in unit["evidence_ids"])
        seed_chars = sum(len(by_id[i]["content"]) for i in unit["seed_ids"])
        units.append(
            {
                "kind": unit["kind"],
                "key": unit["key"],
                "shown": len(unit["evidence_ids"]),
                "seeds": len(unit["seed_ids"]),
                "omitted": unit["omitted"],
                "chars": shown_chars,
                "why": unit["why"],
            }
        )
        if unit["kind"] == "table" and len(unit["evidence_ids"]) > TABLE_WHOLE_ROWS:
            problems.append(f"table shows {len(unit['evidence_ids'])} rows")
        if unit["kind"] == "section" and shown_chars > max(
            SECTION_MAX_CHARS, seed_chars
        ):
            problems.append(f"section shows {shown_chars} characters")
    limit = 4 if task.reason.value == "official_source_conflict" else 2
    if len(units) > limit:
        problems.append(f"{len(units)} units")
    if len(view.evidence) > MODEL_SEED_PASSAGES or any(
        len(item.excerpt) > MODEL_EXCERPT_CHARS for item in view.evidence
    ):
        problems.append("model view over its limits")
    if task.reason.value == "missing_required_field" and any(
        unit["why"] != "batch" for unit in units
    ):
        problems.append("missing field set not seeded from its call")
    shown = {i for unit in evidence_set["units"] for i in unit["evidence_ids"]}
    return {
        "reason": task.reason.value,
        "field": task.issue_scope,
        "units": units,
        "unknown_ids": len(evidence_set.get("unknown_ids", [])),
        "shown_passages": len(shown),
        "display_passages": len(display.shown),
        "view_excerpts": len(view.evidence),
        "view_bytes": len(view.model_dump_json()),
        "candidates": len(task.candidates),
        "problems": problems,
        "_shown": shown,
    }


def labelled_recall(seed: str, records: list[dict], snapshot) -> dict[str, Any]:
    """For each labelled field with numbers: does its review show a passage with
    one of the labelled numbers?"""
    by_id = {item["evidence_id"]: item["content"] for item in snapshot.evidence}
    catalog_numbers = {i: text_numbers(content) for i, content in by_id.items()}
    out: dict[str, Any] = {}
    for field, label in LABELS["seeds"][seed]["fields"].items():
        if label.get("status") != "found" or not label.get("numbers"):
            continue
        wanted = {Decimal(str(n)).normalize() for n in label["numbers"]}
        record = next((r for r in records if r["field"] == field), None)
        in_catalog = any(wanted & numbers for numbers in catalog_numbers.values())
        if record is None:
            out[field] = "no_review"
            continue
        shown = record["_shown"]
        hit = any(wanted & catalog_numbers.get(i, set()) for i in shown)
        out[field] = (
            ("shown" if hit else "empty_set" if not shown else "not_shown")
            if in_catalog
            else "value_not_in_catalog"
        )
    return out


def cited_sets(seed: str, snapshot, catalog) -> list[dict[str, Any]]:
    """Sets built from the passages holding each labelled field's numbers."""
    records = []
    for field, label in LABELS["seeds"][seed]["fields"].items():
        if label.get("status") != "found" or not label.get("numbers"):
            continue
        wanted = {Decimal(str(n)).normalize() for n in label["numbers"]}
        seeds = [
            item.evidence_id for item in catalog if wanted & text_numbers(item.content)
        ][:20]
        if not seeds:
            continue
        evidence_set = cited_evidence_set(catalog, seeds, why="cited")
        by_id = {item.evidence_id: item for item in catalog}
        problems = []
        for unit in evidence_set.units:
            chars = sum(len(by_id[i].content) for i in unit.evidence_ids)
            seed_chars = sum(len(by_id[i].content) for i in unit.seed_ids)
            if unit.kind == "table" and len(unit.evidence_ids) > TABLE_WHOLE_ROWS:
                problems.append("table over bound")
            if unit.kind == "section" and chars > max(SECTION_MAX_CHARS, seed_chars):
                problems.append("section over bound")
        records.append(
            {
                "field": field,
                "cited": len(seeds),
                "units": [
                    (u.kind, len(u.evidence_ids), u.omitted) for u in evidence_set.units
                ],
                "problems": problems,
            }
        )
    return records


async def main() -> None:
    replay.forbid_gemini()
    settings = load_settings()
    model = settings.models.generation_model
    parser = HtmlArtifactParser(settings.http.allowed_source_hosts)
    catalog = replay.catalog()
    stored = await replay.stored_transcriptions()
    categories = {seed: value["category"] for seed, value in LABELS["seeds"].items()}
    report: dict[str, Any] = {
        "as_of": datetime.now(UTC).isoformat(),
        "model": model,
        "part_a": {},
        "part_b": {},
    }
    cache = ReadOnlyCache(
        ROOT / "fix-process/semantic_extraction/.cache/extraction-cache.json"
    )
    totals: Counter[str] = Counter()
    for seed in sorted(LABELS["seeds"]):
        replayed = await replay.load_seed(seed, parser, catalog, stored_pdfs=stored)
        # Part A: the live cache's real answers, when it holds all of the seed's calls.
        cached = SemanticExtractionService(
            CacheOnly(), cache, settings.semantic_extraction, model_name=model
        )
        try:
            result = await labels_check._extract(cached, replayed)
        except Exception:
            result = None
        if result is not None and result.reused_batch_count == len(
            result.call_evidence
        ):
            snapshot = _snapshot(result, replayed.bundle, replayed.discovery, seed)
            records = [review_record(t, snapshot) for t in _review_tasks(snapshot)]
            report["part_a"][seed] = {
                "calls_from_cache": result.reused_batch_count,
                "reviews": [
                    {k: v for k, v in r.items() if k != "_shown"} for r in records
                ],
                "markdown_chars": len(snapshot.selected_sources_markdown or ""),
                "evidence_catalog_bytes": len(json.dumps(list(snapshot.evidence))),
            }
            totals["a_reviews"] += len(records)
            totals["a_problems"] += sum(len(r["problems"]) for r in records)
        # Part B: nothing found, every required field reviewed.
        fake = labels_check.FakeExtractor(categories)
        fake.seed = seed
        service = SemanticExtractionService(
            fake,
            labels_check.InMemorySemanticExtractionRepository(),
            settings.semantic_extraction,
            model_name=model,
        )
        result = await labels_check._extract(service, replayed)
        snapshot = _snapshot(result, replayed.bundle, replayed.discovery, seed)
        records = [review_record(t, snapshot) for t in _review_tasks(snapshot)]
        recall = labelled_recall(seed, records, snapshot)
        cited = cited_sets(seed, snapshot, result.evidence_catalog)
        totals["b_reviews"] += len(records)
        totals["b_problems"] += sum(len(r["problems"]) for r in records)
        totals["b_cited_sets"] += len(cited)
        totals["b_cited_problems"] += sum(len(r["problems"]) for r in cited)
        totals.update(f"recall_{value}" for value in recall.values())
        report["part_b"][seed] = {
            "passages": len(snapshot.evidence),
            "evidence_catalog_bytes": len(json.dumps(list(snapshot.evidence))),
            "markdown_chars": len(snapshot.selected_sources_markdown or ""),
            "reviews": [{k: v for k, v in r.items() if k != "_shown"} for r in records],
            "recall": recall,
            "cited_sets": cited,
        }
        print(
            f"{seed:28} passages={len(snapshot.evidence):4} reviews={len(records):2} "
            f"max_shown={max((r['shown_passages'] for r in records), default=0):3} "
            f"max_view_bytes={max((r['view_bytes'] for r in records), default=0):5} "
            f"recall={dict(Counter(recall.values()))}"
        )
    report["totals"] = dict(totals)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "R03-review-sets.json").write_text(
        json.dumps(report, indent=1, default=str)
    )
    print(json.dumps(dict(totals), indent=1))
    print("part A seeds:", sorted(report["part_a"]))


if __name__ == "__main__":
    asyncio.run(main())
