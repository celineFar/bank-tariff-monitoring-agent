"""IXS09: chunk shape on the 13 seeds' real captures, at no model cost.

    uv run python fix-process/indexing/scenarios/run_ixs09_projection.py

Each seed's page, PDFs and discovery are replayed as in the semantic-extraction
surveys (`fix-process/semantic_extraction/survey/replay.py`; no Gemini client can
be built). The selected bundle is projected twice with this branch's projection,
and once with the projection as it was before the fix (`a812f69`), both at the
configured chunk size. The checks:

- no chunk exceeds the configured size;
- every chunk of a split table opens with its title or header row;
- a chunk that does not start with a heading, table or summary opens with its
  heading path when its first unit has one;
- projecting twice gives the same versions (`projection_sha256`);
- chunk counts and characters before and after, and the embedding cost of a full
  re-embed (characters / 4 tokens, at the catalog's embedding price).

The report goes to `fix-process/indexing/data/ixs09-projection.json`.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
SURVEY = ROOT / "fix-process" / "semantic_extraction" / "survey"
sys.path.insert(0, str(SURVEY))
sys.path.insert(0, str(ROOT))

import replay  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.knowledge_projection import KnowledgeProjectionService  # noqa: E402
from app.services.model_pricing import MODEL_PRICE_CATALOG  # noqa: E402
from app.services.source_selection import (  # noqa: E402
    build_selected_source_bundle,
    select_sources,
)

REPORT = ROOT / "fix-process/indexing/data/ixs09-projection.json"
BEFORE_COMMIT = "a812f69"
SELF_TITLED = {"heading", "table", "offering_summary"}


def _before_projection_module():
    """The projection module as it was before the fix, loaded under another name."""
    source = subprocess.run(
        ["git", "show", f"{BEFORE_COMMIT}:app/services/knowledge_projection.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    path = Path("/tmp") / "ixs09_knowledge_projection_before.py"
    path.write_text(source)
    spec = importlib.util.spec_from_file_location("projection_before", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


def _project(service, replayed, selected, labels):
    return service.project_sources(
        run_id=uuid4(),
        product=replayed.entry.product,
        offering_id=replayed.entry.offering_id,
        bundle=selected,
        retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        language="en",
        labels=labels,
    )


def _table_starts(chunk) -> bool:
    first = chunk.content.splitlines()[0]
    return first.startswith("### ") or first.startswith("| ")


def _measure(documents, limit: int) -> dict[str, Any]:
    chunks = [chunk for document in documents for chunk in document.chunks]
    table_chunks = [
        chunk for chunk in chunks if chunk.metadata.get("unit_types") == ["table"]
    ]
    opening = [
        chunk
        for chunk in chunks
        if chunk.section
        and chunk.metadata.get("unit_types", ["?"])[0] not in SELF_TITLED
    ]
    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "characters": sum(len(chunk.content) for chunk in chunks),
        "largest_chunk": max((len(chunk.content) for chunk in chunks), default=0),
        "over_limit": sum(len(chunk.content) > limit for chunk in chunks),
        "table_only_chunks": len(table_chunks),
        "table_chunks_without_title_or_header": sum(
            not _table_starts(chunk) for chunk in table_chunks
        ),
        "chunks_opening_mid_section": len(opening),
        "of_which_with_breadcrumb": sum(
            chunk.content.startswith("## ") for chunk in opening
        ),
    }


async def main() -> None:
    replay.forbid_gemini()
    settings = load_settings()
    limit = settings.rag.chunk_size_chars
    parser = HtmlArtifactParser(settings.http.allowed_source_hosts)
    catalog = replay.catalog()
    stored = await replay.stored_transcriptions()
    after = KnowledgeProjectionService(max_chunk_chars=limit)
    before = _before_projection_module().KnowledgeProjectionService(
        max_chunk_chars=limit
    )
    report: dict[str, Any] = {
        "as_of": datetime.now(UTC).isoformat(),
        "chunk_size_chars": limit,
        "seeds": {},
    }
    totals = {"before": {}, "after": {}}
    deterministic = True
    for seed in replay.seeds():
        replayed = await replay.load_seed(seed, parser, catalog, stored_pdfs=stored)
        selected = build_selected_source_bundle(replayed.bundle, replayed.discovery)
        labels = select_sources(replayed.discovery).items
        first = _project(after, replayed, selected, labels)
        second = _project(after, replayed, selected, labels)
        same = [a.projection_sha256 for a in first] == [
            b.projection_sha256 for b in second
        ]
        deterministic &= same
        old = _project(before, replayed, selected, labels)
        row = {
            "before": _measure(old, limit),
            "after": _measure(first, limit),
            "deterministic": same,
            "pdfs_missing_transcription": replayed.pdfs_missing,
        }
        report["seeds"][seed] = row
        for side in ("before", "after"):
            for key, value in row[side].items():
                if key == "largest_chunk":
                    totals[side][key] = max(totals[side].get(key, 0), value)
                else:
                    totals[side][key] = totals[side].get(key, 0) + value
    price = MODEL_PRICE_CATALOG[settings.models.embedding_model][-1]
    for side in ("before", "after"):
        tokens = totals[side]["characters"] / 4
        totals[side]["estimated_tokens"] = round(tokens)
        totals[side]["full_reembed_usd"] = round(
            tokens / 1_000_000 * float(price.input_per_million_tokens_usd), 4
        )
    report["totals"] = totals
    report["deterministic"] = deterministic
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"totals": totals, "deterministic": deterministic}, indent=2))
    for seed, row in report["seeds"].items():
        print(
            f"{seed:34} chunks {row['before']['chunks']:4} -> {row['after']['chunks']:4}"
            f"  largest {row['after']['largest_chunk']:5}"
            f"  bare tables {row['before']['table_chunks_without_title_or_header']:3}"
            f" -> {row['after']['table_chunks_without_title_or_header']:3}"
            f"  breadcrumbs {row['after']['of_which_with_breadcrumb']}"
            f"/{row['after']['chunks_opening_mid_section']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
