"""List every PDF linked from the captured seeds, for labelling by hand.

    uv run python fix-process/normalization/survey/pdf_inventory.py

For each PDF: the seeds and links it came from, its link context, what today's
metadata admission decides, and the opening text of the PDF itself (pypdf text
layer, no Gemini). Writes `.cache/pdf-inventory.md` for a person to read and
`.cache/pdf-inventory.json` for `check_pdf_labels.py`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
# SURVEY_CACHE picks another capture folder (a live re-check keeps its own).
CACHE = Path(
    os.environ.get("SURVEY_CACHE", Path(__file__).resolve().parents[1] / ".cache")
)
sys.path.insert(0, str(ROOT))

from app.domain.acquisition import PageArtifact  # noqa: E402
from app.services.pdf_admission import assess_pdf_metadata  # noqa: E402

_SPACE = re.compile(r"\s+")


def _pdf_text(sha: str, limit: int = 1500) -> str:
    path = CACHE / "pdfs" / f"{sha}.pdf"
    if not path.exists():
        return "(not downloaded)"
    try:
        reader = PdfReader(BytesIO(path.read_bytes()))
        text = " ".join((page.extract_text() or "") for page in reader.pages[:2])
    except Exception as exc:  # the survey records unreadable files, it doesn't stop
        return f"(unreadable: {exc})"
    return _SPACE.sub(" ", text).strip()[:limit]


def main() -> None:
    by_sha: dict[str, dict[str, Any]] = {}
    for path in sorted(CACHE.glob("*.artifact.json")):
        seed = path.name.removesuffix(".artifact.json")
        artifact = PageArtifact.model_validate_json(path.read_text())
        for document in artifact.downloadable_documents:
            admission = assess_pdf_metadata(
                document, as_of=document.retrieved_at.date()
            )
            entry = by_sha.setdefault(
                document.sha256,
                {
                    "sha256": document.sha256,
                    "links": [],
                    "text": _pdf_text(document.sha256),
                },
            )
            entry["links"].append(
                {
                    "seed": seed,
                    "url": str(document.final_url),
                    "link_text": document.link_text,
                    "heading_path": list(document.origin_heading_path),
                    "nearby_text": document.nearby_text[:600],
                    "admission": {
                        "relevance": admission.relevance.value,
                        "temporal": admission.temporal_status.value,
                        "basis": list(admission.decision_basis),
                    },
                }
            )
    (CACHE / "pdf-inventory.json").write_text(
        json.dumps(by_sha, indent=1, ensure_ascii=False)
    )
    lines = []
    for index, entry in enumerate(by_sha.values(), start=1):
        lines.append(f"## {index}. {entry['sha256'][:12]}")
        for link in entry["links"]:
            lines.append(
                f'- {link["seed"]}: "{link["link_text"]}" <{link["url"]}>\n'
                f"  heading: {' > '.join(link['heading_path'])}\n"
                f"  admission: {link['admission']['relevance']}/"
                f"{link['admission']['temporal']}\n"
                f"  nearby: {link['nearby_text'][:300]}"
            )
        lines.append(f"TEXT: {entry['text'][:900]}")
        lines.append("")
    (CACHE / "pdf-inventory.md").write_text("\n".join(lines))
    print(len(by_sha), "distinct PDFs")


if __name__ == "__main__":
    main()
