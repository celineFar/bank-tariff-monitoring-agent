"""Candidate signals for the HTML page quality score (N20, Q3), per seed.

    uv run python fix-process/normalization/survey/quality_signals.py [repo-root]

Every signal can be computed at normalization time from the page alone (no
ground truth). Run it on two checkouts (before/after the fixes) to see which
signals separate a bad bundle from a good one; the proposal is in the plan's
Phase 2 notes. Prints JSON.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))
# SURVEY_CACHE picks another capture folder (a live re-check keeps its own).
CACHE = Path(
    os.environ.get("SURVEY_CACHE", Path(__file__).resolve().parents[1] / ".cache")
)

from bs4 import BeautifulSoup, Comment, NavigableString, Tag  # noqa: E402

from app.domain.acquisition import PageArtifact  # noqa: E402
from app.services.block_normalizer import normalize_block  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.table_normalizer import normalize_table  # noqa: E402

_SPACE = re.compile(r"\s+")
# Words glued across an element boundary: "loanUp", "Amount12", "USD8".
_GLUED = re.compile(r"[a-z][A-Z][a-z]|[A-Za-z]{2}\d{2,}")
_DIGIT = re.compile(r"\d")


def _visible_main_chars(html: str) -> tuple[int, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    for element in body.select("script, style, noscript, template"):
        element.decompose()
    texts = []
    for node in body.find_all(string=True):
        if isinstance(node, Comment) or not isinstance(node, NavigableString):
            continue
        parent = node.parent
        if not isinstance(parent, Tag):
            continue
        chain = [parent, *parent.parents]
        if any(
            isinstance(p, Tag) and p.get("data-acquisition-visible") == "false"
            for p in chain
        ):
            continue
        if any(
            isinstance(p, Tag) and p.name in {"nav", "header", "footer"} for p in chain
        ):
            continue
        text = _SPACE.sub(" ", str(node)).strip()
        if len(text) >= 3:
            texts.append(text)
    return sum(len(t) for t in texts), texts


def signals(artifact: PageArtifact) -> dict[str, float]:
    html = artifact.rendered_html or ""
    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url=str(artifact.final_url)
    )
    blocks = [normalize_block(block) for block in parsed.blocks]
    tables = [normalize_table(table) for table in parsed.tables]
    covered = _SPACE.sub(
        " ",
        " ".join(
            [b.text for b in blocks]
            + [c.text for t in tables for r in t.rows for c in r.cells]
        ),
    )
    total_chars, texts = _visible_main_chars(html)
    uncovered_chars = sum(len(t) for t in texts if t not in covered)
    rows = [r for t in tables for r in t.rows]
    notes = [n for t in tables for n in t.notes]
    glued = [b for b in blocks if not b.table_id and _GLUED.search(b.text)]
    return {
        "text_coverage": round(1 - uncovered_chars / total_chars, 4)
        if total_chars
        else 1.0,
        "blocks_with_glued_words": len(glued),
        "tables": len(tables),
        "tables_without_rows": sum(1 for t in tables if not t.rows),
        "tables_column_n_headers": sum(
            1
            for t in tables
            if t.headers and t.headers[0] == "Column 1" and len(t.headers) > 1
        ),
        "rows": len(rows),
        "notes_without_marker_with_digits": sum(
            1 for n in notes if not n.marker and _DIGIT.search(n.text)
        ),
        "notes": len(notes),
    }


def main() -> None:
    out = {}
    for path in sorted(CACHE.glob("*.artifact.json")):
        artifact = PageArtifact.model_validate_json(path.read_text())
        out[path.name.removesuffix(".artifact.json")] = signals(artifact)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
