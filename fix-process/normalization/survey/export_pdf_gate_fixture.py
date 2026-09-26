"""Write the Q4 gate fixture: every labelled PDF with its admission inputs.

    uv run python fix-process/normalization/survey/export_pdf_gate_fixture.py

Rebuilds each PDF link's context from the captured pages with the current code
and writes `tests/fixtures/pdf_admission_seed_labels.json`, which
`tests/unit/test_pdf_admission_gate.py` checks offline. Re-run after changing
how link context is built, or after relabelling.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.services.acquisition import AcquisitionService  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402


def main() -> None:
    labels = json.loads((BASE / "data" / "seed-pdf-labels.json").read_text())
    parser = HtmlArtifactParser(load_settings().http.allowed_source_hosts)
    cases = []
    for path in sorted(
        Path(os.environ.get("SURVEY_CACHE", BASE / ".cache")).glob("*.artifact.json")
    ):
        seed = path.name.removesuffix(".artifact.json")
        artifact = PageArtifact.model_validate_json(path.read_text())
        parsed = parser.parse(
            artifact.rendered_html or "", source_url=str(artifact.final_url)
        )
        for document in artifact.downloadable_documents:
            label = labels["pdfs"].get(document.sha256)
            if label is None:
                continue
            origin = AcquisitionService._document_origin(parsed, document.link_id or "")
            cases.append(
                {
                    "seed": seed,
                    "file": label["file"],
                    "label": label["label"],
                    "final_url": str(document.final_url),
                    "document_name": document.document_name,
                    "link_text": document.link_text,
                    "link_title": document.link_title,
                    "origin_heading_path": list(origin.get("origin_heading_path", ())),
                    "nearby_text": origin.get("nearby_text", ""),
                }
            )
    out = ROOT / "tests" / "fixtures" / "pdf_admission_seed_labels.json"
    out.write_text(
        json.dumps(
            {
                "as_of": labels["as_of"],
                "source": "fix-process/normalization",
                "cases": cases,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(len(cases), "cases ->", out)


if __name__ == "__main__":
    main()
