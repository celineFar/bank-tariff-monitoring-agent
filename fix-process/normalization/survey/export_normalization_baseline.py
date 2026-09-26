"""Write the runtime normalization baseline from the seed ground truth.

    uv run python fix-process/normalization/survey/export_normalization_baseline.py

Reads `data/seed-ground-truth.json` and writes `app/config/normalization_baseline.json`,
keeping only structure (see app/services/normalization_baseline.py):

- a table is found by its ground-truth anchor, or by its title when the anchor
  quotes a value;
- a fact keeps its first part (the row label) and whether it had a value, and
  drops the values themselves;
- a block fact is kept only when it has no digits (a label, not a figure).

Each page is keyed by its seed URL plus the canonical and final URLs of the
captured page. Re-run after changing the ground truth or recapturing.
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

from app.config.seed_catalog import load_seed_catalog  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.services.normalization_baseline import (  # noqa: E402
    DEFAULT_NORMALIZATION_BASELINE_PATH,
    NormalizationBaseline,
)
from app.services.scalar_normalizer import extract_scalar_candidates  # noqa: E402

_DIGIT = re.compile(r"\d")


def _table(spec: dict[str, Any], templates: dict[str, Any]) -> dict[str, Any]:
    find = spec["find"]
    if extract_scalar_candidates(find) and spec.get("title"):
        find = spec["title"]
    notes = spec.get("notes") or []
    if isinstance(notes, str):
        notes = templates[notes]
    return {
        "find": find,
        "title": spec.get("title"),
        "header_row": spec.get("header_row"),
        "min_rows": spec.get("min_rows", 0),
        "rows": [
            {
                "label": fact["row"][0],
                "section": fact.get("section"),
                "has_value": len(fact["row"]) > 1,
            }
            for fact in spec.get("facts", [])
        ],
        "notes": [{"marker": n["marker"], "starts": n["starts"]} for n in notes],
    }


def main() -> None:
    truth = json.loads((BASE / "data" / "seed-ground-truth.json").read_text())
    templates = truth["templates"]
    seeds = {
        entry.offering_id.value: str(entry.seed_url)
        for entry in load_seed_catalog().offerings
    }
    pages = []
    for offering, spec in truth["seeds"].items():
        urls = [seeds[offering]]
        captured = CACHE / f"{offering}.artifact.json"
        if captured.exists():
            artifact = PageArtifact.model_validate_json(captured.read_text())
            urls += [str(artifact.canonical_url), str(artifact.final_url)]
        tables = [
            _table(templates[t["template"]] if "template" in t else t, templates)
            for t in spec["tables"]
        ]
        pages.append(
            {
                "offering_id": offering,
                "urls": list(dict.fromkeys(urls)),
                "recorded_on": "2026-09-26",
                "tables": tables,
                "blocks": [
                    {"text": block["text"]}
                    for block in spec["blocks"]
                    if not _DIGIT.search(block["text"])
                ],
            }
        )
    baseline = NormalizationBaseline.model_validate({"pages": pages})
    DEFAULT_NORMALIZATION_BASELINE_PATH.write_text(
        baseline.model_dump_json(indent=1, exclude_defaults=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"{len(baseline.pages)} pages, {sum(p.checks for p in baseline.pages)} checks "
        f"-> {DEFAULT_NORMALIZATION_BASELINE_PATH}"
    )


if __name__ == "__main__":
    main()
