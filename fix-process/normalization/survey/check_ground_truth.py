"""Check HTML normalization of the captured seeds against `data/seed-ground-truth.json`.

    uv run python fix-process/normalization/survey/check_ground_truth.py [label]

Runs the current parser and normalizers over the pages saved by
`capture_seeds.py` (offline, no Gemini) and reports, per seed, every ground-truth
expectation that fails. With a label, the result is also written to
`data/ground-truth-check-<label>.json`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
# SURVEY_CACHE picks another capture folder (a live re-check keeps its own).
CACHE = Path(os.environ.get("SURVEY_CACHE", BASE / ".cache"))
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.domain.normalization import NormalizedBlock, NormalizedTable  # noqa: E402
from app.services.block_normalizer import normalize_block  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.table_normalizer import normalize_table  # noqa: E402

_SPACE = re.compile(r"\s+")
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def _n(value: str | None) -> str:
    return _SPACE.sub(" ", value or "").strip()


def _table_text(table: NormalizedTable) -> str:
    parts = [table.title or "", *table.headers]
    parts += [cell.text for row in table.rows for cell in row.cells]
    parts += [note.text for note in table.notes]
    return _n(" ".join(parts))


def _row_texts(table: NormalizedTable) -> list[tuple[str, str]]:
    return [
        (
            _n(" | ".join(cell.text for cell in row.cells)),
            _n(getattr(row, "section", None)),
        )
        for row in table.rows
    ]


def check_table(
    spec: dict[str, Any], tables: list[NormalizedTable], templates
) -> list[str]:
    failures: list[str] = []
    candidates = [t for t in tables if _n(spec["find"]) in _table_text(t)]
    if not candidates:
        return [f"table not found: {spec['find']!r}"]
    table = candidates[0]
    label = f"table[{spec['find'][:40]}]"
    if spec.get("title") and _n(spec["title"]) not in _n(table.title):
        failures.append(f"{label} title {table.title!r} lacks {spec['title']!r}")
    header_row = spec.get("header_row")
    if header_row is None:
        if table.headers and not table.headers_inferred:
            failures.append(
                f"{label} has no header row but got headers {table.headers}"
            )
    else:
        headers = _n(" | ".join(table.headers))
        if table.headers_inferred or not all(_n(h) in headers for h in header_row):
            failures.append(f"{label} headers {table.headers} != {header_row}")
    if len(table.rows) < spec.get("min_rows", 0):
        failures.append(f"{label} has {len(table.rows)} rows < {spec['min_rows']}")
    rows = _row_texts(table)
    for fact in spec.get("facts", []):
        wanted = [_n(part) for part in fact["row"]]
        section = _n(fact.get("section"))
        matches = [
            (text, row_section)
            for text, row_section in rows
            if all(part in text for part in wanted)
        ]
        if not matches:
            failures.append(f"{label} no row with {fact['row']}")
        elif section and not any(section in row_section for _, row_section in matches):
            got = sorted({row_section for _, row_section in matches})
            failures.append(
                f"{label} row {fact['row'][:2]} section {got} lacks {section!r}"
            )
    notes = spec.get("notes") or []
    if isinstance(notes, str):
        notes = templates[notes]
    for expected in notes:
        found = [
            n for n in table.notes if _n(n.text).startswith(_n(expected["starts"]))
        ]
        marker = expected["marker"]
        if not found:
            failures.append(f"{label} no note starting {expected['starts'][:40]!r}")
        elif not any(
            (n.marker or "").translate(_SUPERSCRIPTS) == marker for n in found
        ):
            failures.append(
                f"{label} note {expected['starts'][:30]!r} marker "
                f"{[n.marker for n in found]} != {marker!r}"
            )
    if table.title:
        for note in table.notes:
            if _n(note.text) and _n(note.text) in _n(table.title):
                failures.append(f"{label} title repeated as note {note.text[:40]!r}")
    return failures


def check_blocks(
    specs: list[dict[str, Any]], blocks: list[NormalizedBlock]
) -> list[str]:
    failures = []
    for spec in specs:
        text = _n(spec["text"])
        found = [b for b in blocks if text in _n(b.text)]
        if not found:
            failures.append(f"no block with {spec['text']!r}")
        elif spec.get("heading") and not any(
            _n(spec["heading"]) in _n(" > ".join(b.heading_path)) for b in found
        ):
            failures.append(
                f"block {spec['text'][:30]!r} not under {spec['heading']!r}"
            )
    return failures


def run() -> dict[str, Any]:
    truth = json.loads((BASE / "data" / "seed-ground-truth.json").read_text())
    templates = truth["templates"]
    parser = HtmlArtifactParser(load_settings().http.allowed_source_hosts)
    result: dict[str, Any] = {}
    for seed, spec in truth["seeds"].items():
        artifact = PageArtifact.model_validate_json(
            (CACHE / f"{seed}.artifact.json").read_text()
        )
        parsed = parser.parse(
            artifact.rendered_html or "", source_url=str(artifact.final_url)
        )
        blocks = [normalize_block(block) for block in parsed.blocks]
        tables = [normalize_table(table) for table in parsed.tables]
        failures: list[str] = []
        checks = 0
        for table_spec in spec["tables"]:
            if "template" in table_spec:
                table_spec = templates[table_spec["template"]]
            checks += 3 + len(table_spec.get("facts", []))
            notes = table_spec.get("notes") or []
            checks += len(templates[notes] if isinstance(notes, str) else notes)
            failures += check_table(table_spec, tables, templates)
        checks += len(spec["blocks"])
        failures += check_blocks(spec["blocks"], blocks)
        result[seed] = {"checks": checks, "failed": len(failures), "failures": failures}
    return result


def main() -> None:
    result = run()
    total = sum(r["checks"] for r in result.values())
    failed = sum(r["failed"] for r in result.values())
    for seed, r in result.items():
        print(f"{seed}: {r['failed']} of {r['checks']} checks failed")
        for failure in r["failures"]:
            print("   -", failure)
    print(f"TOTAL: {failed} of {total} checks failed")
    if len(sys.argv) > 1:
        out = BASE / "data" / f"ground-truth-check-{sys.argv[1]}.json"
        out.write_text(
            json.dumps(
                {"total": total, "failed": failed, "seeds": result},
                indent=1,
                ensure_ascii=False,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
