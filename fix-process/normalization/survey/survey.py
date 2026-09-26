"""Measure what HTML normalization produces for every captured seed, offline.

    uv run python fix-process/normalization/survey/survey.py before
    uv run python fix-process/normalization/survey/survey.py after

Reads the rendered HTML saved by `capture_seeds.py`, runs the current parser and
normalizers on it (no network, no Gemini), and writes
`fix-process/normalization/data/normalization-survey-<label>.json`.

The "uncovered text" and DOM counts are taken with a separate BeautifulSoup walk,
not with the parser under test, so they measure what the parser misses.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
# SURVEY_CACHE picks another capture folder (a live re-check keeps its own).
CACHE = Path(os.environ.get("SURVEY_CACHE", BASE / ".cache"))
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.services.block_normalizer import normalize_block  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.table_normalizer import normalize_table  # noqa: E402

_SPACE = re.compile(r"\s+")
_CHROME = {"nav", "header", "footer"}


def _norm(value: str) -> str:
    return _SPACE.sub(" ", value).strip()


def _hidden(node: Tag) -> bool:
    for current in (node, *node.parents):
        if (
            isinstance(current, Tag)
            and current.get("data-acquisition-visible") == "false"
        ):
            return True
    return False


def _chrome(node: Tag) -> bool:
    return any(
        isinstance(p, Tag)
        and (
            p.name in _CHROME
            or str(p.get("role") or "") in {"navigation", "banner", "contentinfo"}
        )
        for p in (node, *node.parents)
    )


def _dom_counts(soup: BeautifulSoup, covered: str) -> dict[str, Any]:
    body = soup.body or soup
    for element in body.select("script, style, noscript, template"):
        element.decompose()
    uncovered: list[str] = []
    for node in body.find_all(string=True):
        if (
            not isinstance(node, NavigableString)
            or isinstance(node, Comment)
            or not isinstance(node.parent, Tag)
        ):
            continue
        text = _norm(str(node))
        if len(text) < 3 or _hidden(node.parent) or _chrome(node.parent):
            continue
        if text not in covered:
            uncovered.append(text)
    visible_under_hidden = sum(
        1
        for element in body.find_all(attrs={"data-acquisition-visible": "false"})
        if element.find(attrs={"data-acquisition-visible": "true"}) is not None
    )
    tables = [t for t in body.find_all("table") if not _hidden(t)]
    return {
        "uncovered_text_nodes": len(uncovered),
        "uncovered_text_chars": sum(len(t) for t in uncovered),
        "uncovered_examples": uncovered[:40],
        "dom_tables": len(tables),
        "dom_nested_tables": sum(
            1 for t in tables if t.find_parent("table") is not None
        ),
        "dom_th_scope_row": len(body.select('th[scope="row"]')),
        "dom_dl": len(body.find_all("dl")),
        "dom_nested_li": sum(1 for li in body.find_all("li") if li.find_parent("li")),
        "hidden_elements_with_visible_descendants": visible_under_hidden,
    }


def survey_seed(artifact: PageArtifact, parser: HtmlArtifactParser) -> dict[str, Any]:
    html = artifact.rendered_html or artifact.raw_html or ""
    parsed = parser.parse(html, source_url=str(artifact.final_url))
    blocks = [normalize_block(block) for block in parsed.blocks]
    tables = [normalize_table(table) for table in parsed.tables]
    covered = _norm(
        " ".join(
            [b.text for b in blocks]
            + [c.text for t in tables for r in t.rows for c in r.cells]
            + list(parsed.main_text.split("\n"))
        )
    )
    table_rows = []
    for table in tables:
        table_rows.append(
            {
                "id": table.id,
                "title": table.title,
                "headers": list(table.headers),
                "headers_inferred": table.headers_inferred,
                "rows": len(table.rows),
                "notes": len(table.notes),
                "notes_with_marker": sum(1 for n in table.notes if n.marker),
                "sections": sorted(
                    {getattr(r, "section", None) or "" for r in table.rows} - {""}
                ),
            }
        )
    cell_values = {
        s.value
        for t in tables
        for r in t.rows
        for c in r.cells
        for s in c.scalar_candidates
        if s.value is not None
    }
    phantom = sorted(
        {
            str(s.value)
            for b in blocks
            if b.table_id
            for s in b.scalar_candidates
            if s.value is not None and s.value not in cell_values
        }
    )
    return {
        "blocks": len(blocks),
        "block_types": dict(Counter(b.type.value for b in blocks)),
        "main_chars": len(parsed.main_text),
        "tables": len(tables),
        "table_rows_total": sum(len(t.rows) for t in tables),
        "tables_without_rows": sum(1 for t in tables if not t.rows),
        "tables_with_invented_headers": sum(1 for t in tables if t.headers_inferred),
        "notes_total": sum(len(t.notes) for t in tables),
        "table_block_numbers_not_in_any_cell": phantom,
        "tables_detail": table_rows,
        **_dom_counts(BeautifulSoup(html, "html.parser"), covered),
    }


def main(label: str) -> None:
    settings = load_settings()
    parser = HtmlArtifactParser(settings.http.allowed_source_hosts)
    result: dict[str, Any] = {}
    for path in sorted(CACHE.glob("*.artifact.json")):
        artifact = PageArtifact.model_validate_json(path.read_text())
        result[path.name.removesuffix(".artifact.json")] = survey_seed(artifact, parser)
    out = BASE / "data" / f"normalization-survey-{label}.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str) + "\n")
    totals = Counter()
    for seed in result.values():
        for key in (
            "blocks",
            "tables",
            "table_rows_total",
            "tables_without_rows",
            "tables_with_invented_headers",
            "notes_total",
            "uncovered_text_nodes",
            "uncovered_text_chars",
            "dom_nested_tables",
            "dom_th_scope_row",
            "dom_dl",
            "dom_nested_li",
            "hidden_elements_with_visible_descendants",
        ):
            totals[key] += seed[key]
    print(json.dumps(dict(totals), indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "before")
