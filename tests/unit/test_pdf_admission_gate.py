"""The Q4 gate: metadata admission never skips a current PDF.

Every PDF linked from the 13 seed pages on 2026-09-26 was labelled by hand
(fix-process/normalization/data/seed-pdf-labels.json). The fixture holds each
link's admission inputs as the parser and acquisition build them. Regenerate
it with fix-process/normalization/survey/export_pdf_gate_fixture.py.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.domain.acquisition import DocumentArtifact, StoredArtifact
from app.domain.pdf_extraction import PdfAdmissionRelevance, PdfTemporalStatus
from app.services.pdf_admission import assess_pdf_metadata

FIXTURE = json.loads(
    (
        Path(__file__).parents[1] / "fixtures" / "pdf_admission_seed_labels.json"
    ).read_text()
)
AS_OF = date.fromisoformat(FIXTURE["as_of"])


def _skipped(case: dict) -> bool:
    document = DocumentArtifact(
        source_url=case["final_url"],
        final_url=case["final_url"],
        document_name=case["document_name"],
        mime_type="application/pdf",
        size_bytes=1,
        sha256="0" * 64,
        retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        artifact=StoredArtifact(
            role="linked_document",
            size_bytes=1,
            media_type="application/pdf",
            relative_path="x.pdf",
            sha256="0" * 64,
        ),
        link_text=case["link_text"],
        link_title=case["link_title"],
        origin_heading_path=tuple(case["origin_heading_path"]),
        nearby_text=case["nearby_text"],
    )
    admission = assess_pdf_metadata(document, as_of=AS_OF)
    return (
        admission.relevance is PdfAdmissionRelevance.IRRELEVANT
        or admission.temporal_status is PdfTemporalStatus.HISTORICAL
    )


@pytest.mark.parametrize(
    "case",
    [case for case in FIXTURE["cases"] if case["label"] in {"current", "future"}],
    ids=lambda case: f"{case['seed']}:{case['file']}",
)
def test_a_current_pdf_is_never_skipped(case: dict) -> None:
    assert not _skipped(case)


@pytest.mark.parametrize(
    "case",
    [case for case in FIXTURE["cases"] if case["label"] == "historical"],
    ids=lambda case: f"{case['seed']}:{case['file']}",
)
def test_a_superseded_pdf_is_skipped(case: dict) -> None:
    assert _skipped(case)
