from __future__ import annotations

import hashlib

from app.domain.normalization import NormalizedSourceBundle
from app.domain.semantic_extraction import EvidenceItem
from app.domain.source_discovery import (
    SourceAssessment,
    SourceDiscoveryResult,
)
from app.services.source_selection import (
    assessment_precedence,
    selected_assessments_by_source_item,
)


def build_evidence_catalog(
    bundle: NormalizedSourceBundle,
    discovery: SourceDiscoveryResult,
) -> tuple[EvidenceItem, ...]:
    assessments = selected_assessments_by_source_item(discovery.assessments)
    evidence: list[EvidenceItem] = []
    for document in bundle.documents:
        table_paths = {
            block.table_id: block.heading_path
            for block in document.blocks
            if block.table_id is not None
        }
        for block in document.blocks:
            assessment = assessments.get(block.id)
            if assessment is None:
                continue
            section = " > ".join(block.heading_path) or None
            evidence.append(
                _evidence_item(
                    document.id,
                    block.id,
                    block.text,
                    section,
                    block.source_refs[0].locator,
                    assessment,
                )
            )
        for table in document.tables:
            assessment = assessments.get(table.id)
            if assessment is None:
                continue
            # Where the table sits (its heading path) and what it is called; never
            # the table's own flattened text, which is no label at all.
            section = _table_section(table_paths.get(table.id, ()), table.title)
            headers = " | ".join(table.headers)
            for row in table.rows:
                values = " | ".join(cell.text for cell in row.cells)
                content = f"Headers: {headers}\nRow: {values}" if headers else values
                if row.section:
                    # The in-table section tells rows with the same label apart
                    # ("Fee | 0%" under "AMD loans" and under "USD loans").
                    content = f"Section: {row.section}\n{content}"
                evidence.append(
                    _evidence_item(
                        document.id,
                        row.id,
                        content,
                        section,
                        row.cells[0].source_refs[0].locator,
                        assessment,
                    )
                )
            for index, note in enumerate(table.notes):
                evidence.append(
                    _evidence_item(
                        document.id,
                        f"{table.id}:note:{index}",
                        _note_content(note.marker, note.text),
                        section,
                        note.source_refs[0].locator,
                        assessment,
                    )
                )
    unique = {item.evidence_id: item for item in evidence}
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (item.precedence, item.document_id, item.source_item_id),
        )
    )


def _table_section(heading_path: tuple[str, ...], title: str | None) -> str | None:
    parts = tuple(part for part in (*heading_path, title) if part)
    return " > ".join(dict.fromkeys(parts)) or None


_SUPERSCRIPTS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _note_content(marker: str | None, text: str) -> str:
    """A footnote as the page shows it, marker first, so the model can tie
    "12%¹" in a row to the note that explains it."""
    if not marker:
        return text
    shown = marker.translate(_SUPERSCRIPTS) if marker.isdigit() else marker
    return f"{shown} {text}"


def _evidence_item(
    document_id: str,
    source_item_id: str,
    content: str,
    section: str | None,
    locator,
    assessment: SourceAssessment,
) -> EvidenceItem:
    identity = f"{document_id}\x1f{source_item_id}\x1f{content}"
    evidence_id = "ev_" + hashlib.sha256(identity.encode()).hexdigest()[:24]
    return EvidenceItem(
        evidence_id=evidence_id,
        document_id=document_id,
        source_item_id=source_item_id,
        content=content,
        section=section,
        role=assessment.role,
        authority=assessment.authority,
        temporal_status=assessment.temporal_status,
        precedence=assessment_precedence(assessment),
        product_association=assessment.product_association,
        effective_periods=assessment.effective_periods,
        conditions=assessment.conditions,
        locator=locator,
    )
