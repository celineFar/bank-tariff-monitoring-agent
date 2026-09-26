"""Check PDF admission against the hand labels in `data/seed-pdf-labels.json`.

    uv run python fix-process/normalization/survey/check_pdf_labels.py [label]

For every PDF linked from the captured seeds, rebuild its link context with the
*current* parser and acquisition code (so changes to how context is built are
tested), run metadata admission as of the labels' date, and compare what would
be skipped with the labels. The gate: no PDF labelled `current` or `future` may
be skipped. With a label argument the result is written to
`data/pdf-label-check-<label>.json`.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
# SURVEY_CACHE picks another capture folder (a live re-check keeps its own).
CACHE = Path(os.environ.get("SURVEY_CACHE", BASE / ".cache"))
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.domain.pdf_extraction import (  # noqa: E402
    PdfAdmissionRelevance,
    PdfTemporalStatus,
)
from app.services.acquisition import AcquisitionService  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.pdf_admission import assess_pdf_metadata  # noqa: E402


def run() -> dict[str, Any]:
    labels = json.loads((BASE / "data" / "seed-pdf-labels.json").read_text())
    as_of = date.fromisoformat(labels["as_of"])
    skip_historical = load_settings().pdf_extraction.skip_historical
    parser = HtmlArtifactParser(load_settings().http.allowed_source_hosts)
    decisions: dict[str, dict[str, Any]] = {}
    for path in sorted(CACHE.glob("*.artifact.json")):
        seed = path.name.removesuffix(".artifact.json")
        artifact = PageArtifact.model_validate_json(path.read_text())
        parsed = parser.parse(
            artifact.rendered_html or "", source_url=str(artifact.final_url)
        )
        for document in artifact.downloadable_documents:
            origin = (
                AcquisitionService._document_origin(parsed, document.link_id)
                if document.link_id
                else {}
            )
            rebuilt = document.model_copy(
                update={
                    "origin_block_id": None,
                    "origin_heading_path": (),
                    "nearby_text": "",
                    **origin,
                }
            )
            admission = assess_pdf_metadata(rebuilt, as_of=as_of)
            skipped = admission.relevance is PdfAdmissionRelevance.IRRELEVANT or (
                skip_historical
                and admission.temporal_status is PdfTemporalStatus.HISTORICAL
            )
            entry = decisions.setdefault(
                document.sha256, {"skipped_in": [], "admitted_in": [], "admission": []}
            )
            (entry["skipped_in"] if skipped else entry["admitted_in"]).append(seed)
            entry["admission"].append(
                f"{seed}: {admission.relevance.value}/{admission.temporal_status.value}"
            )
    wrongly_skipped, missed_historical, missed_irrelevant = [], [], []
    for sha, spec in labels["pdfs"].items():
        decision = decisions.get(sha)
        if decision is None:
            continue
        row = {"file": spec["file"], "label": spec["label"], **decision}
        if spec["label"] in {"current", "future"} and decision["skipped_in"]:
            wrongly_skipped.append(row)
        elif spec["label"] == "historical" and decision["admitted_in"]:
            missed_historical.append(row)
        elif spec["label"] == "irrelevant" and decision["admitted_in"]:
            missed_irrelevant.append(row)
    counts: dict[str, int] = {}
    for spec in labels["pdfs"].values():
        counts[spec["label"]] = counts.get(spec["label"], 0) + 1
    return {
        "as_of": labels["as_of"],
        "skip_historical": skip_historical,
        "labels": counts,
        "gate_passed": not wrongly_skipped,
        "current_or_future_skipped": wrongly_skipped,
        "historical_transcribed": missed_historical,
        "irrelevant_transcribed": missed_irrelevant,
    }


def main() -> None:
    result = run()
    print(f"labels: {result['labels']}  skip_historical={result['skip_historical']}")
    print(
        f"GATE (no current/future PDF skipped): {'PASS' if result['gate_passed'] else 'FAIL'}"
    )
    for key in (
        "current_or_future_skipped",
        "historical_transcribed",
        "irrelevant_transcribed",
    ):
        print(f"{key}: {len(result[key])}")
        for row in result[key]:
            print(f"   - {row['file']}: {row['admission'][0]}")
    if len(sys.argv) > 1:
        (BASE / "data" / f"pdf-label-check-{sys.argv[1]}.json").write_text(
            json.dumps(result, indent=1, ensure_ascii=False) + "\n"
        )


if __name__ == "__main__":
    main()
