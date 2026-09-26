"""Dump what each captured seed page visibly contains, for building the ground truth.

    uv run python fix-process/normalization/survey/dom_inventory.py

Independent of the parser under test: a plain BeautifulSoup walk over the
rendered HTML saved by `capture_seeds.py`. Writes one Markdown file per seed to
`fix-process/normalization/.cache/inventory/`, listing in document order the
visible headings, tables (row by row, cells separated by ` | `, with rowspan and
colspan marks), definition lists, and accordion-like title/panel pairs. A person
reads these files to write `data/seed-ground-truth.json`.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[3]
# SURVEY_CACHE picks another capture folder (a live re-check keeps its own).
CACHE = Path(
    os.environ.get("SURVEY_CACHE", Path(__file__).resolve().parents[1] / ".cache")
)
sys.path.insert(0, str(ROOT))

from app.domain.acquisition import PageArtifact  # noqa: E402

_SPACE = re.compile(r"\s+")
_CHROME = {"nav", "header", "footer"}


def _text(node: Tag) -> str:
    return _SPACE.sub(" ", node.get_text(" ", strip=True)).strip()


def _hidden(node: Tag) -> bool:
    return any(
        isinstance(p, Tag) and p.get("data-acquisition-visible") == "false"
        for p in (node, *node.parents)
    )


def _chrome(node: Tag) -> bool:
    return any(isinstance(p, Tag) and p.name in _CHROME for p in (node, *node.parents))


def _table_lines(table: Tag) -> list[str]:
    lines = []
    caption = table.find("caption")
    if isinstance(caption, Tag):
        lines.append(f"  caption: {_text(caption)}")
    for row in table.find_all("tr"):
        if row.find_parent("table") is not table:
            continue
        cells = []
        for cell in row.find_all(["td", "th"], recursive=False):
            marks = []
            if cell.get("rowspan") not in (None, "1"):
                marks.append(f"rs{cell.get('rowspan')}")
            if cell.get("colspan") not in (None, "1"):
                marks.append(f"cs{cell.get('colspan')}")
            if cell.name == "th":
                marks.append("th")
            if cell.find("table"):
                marks.append("NESTED")
            prefix = f"[{','.join(marks)}]" if marks else ""
            cells.append(f"{prefix}{_text(cell)[:160]}")
        lines.append("  | " + " | ".join(cells))
    return lines


def inventory(artifact: PageArtifact) -> str:
    soup = BeautifulSoup(artifact.rendered_html or "", "html.parser")
    body = soup.body or soup
    for element in body.select("script, style, noscript, template"):
        element.decompose()
    out = [f"# {artifact.final_url}", ""]
    for element in body.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "table", "dl"]):
        if _hidden(element) or _chrome(element):
            continue
        if element.name == "table":
            if element.find_parent("table") is not None:
                out.append("TABLE (nested)")
            else:
                out.append("TABLE")
            out.extend(_table_lines(element))
        elif element.name == "dl":
            out.append("DL")
            for dt in element.find_all("dt"):
                dd = dt.find_next_sibling("dd")
                out.append(f"  {_text(dt)} => {_text(dd) if dd else ''}")
        else:
            out.append(f"{'#' * int(element.name[1])} {_text(element)[:200]}")
    out.append("")
    out.append("## Visible main text outside tables (first 8000 chars)")
    parts = [
        _SPACE.sub(" ", str(node)).strip()
        for node in body.find_all(string=True)
        if isinstance(node.parent, Tag)
        and not _hidden(node.parent)
        and not _chrome(node.parent)
        and node.parent.find_parent("table") is None
        and node.parent.name != "table"
    ]
    out.append(" / ".join(part for part in parts if part)[:8000])
    return "\n".join(out) + "\n"


def main() -> None:
    target = CACHE / "inventory"
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(CACHE.glob("*.artifact.json")):
        artifact = PageArtifact.model_validate_json(path.read_text())
        name = path.name.removesuffix(".artifact.json")
        (target / f"{name}.md").write_text(inventory(artifact))
        print(name)


if __name__ == "__main__":
    main()
