from __future__ import annotations

import hashlib
import re

from app.domain.acquisition import SourceType
from app.domain.normalization import (
    NormalizedDocument,
    NormalizedSourceBundle,
    NormalizedTable,
    NormalizedTableRow,
)
from app.domain.semantic_extraction import EvidenceItem
from app.domain.source_discovery import (
    SourceAssessment,
    SourceDiscoveryResult,
)
from app.services.source_selection import (
    assessment_precedence,
    selected_assessments_by_source_item,
)

_SUPERSCRIPTS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_MARKER = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+|\*")
_LEADING_NUMBERING = re.compile(r"^\d+(?:\.\d+)*\.?\s+")


def build_evidence_catalog(
    bundle: NormalizedSourceBundle,
    discovery: SourceDiscoveryResult,
) -> tuple[EvidenceItem, ...]:
    """The selected sources as citable evidence, in reading order.

    An item's ID depends on what it says and where it sits in the document's
    structure, never on the page's hash or on its position, so an unchanged
    table keeps its IDs when something else on the page changes (SE10).
    """
    assessments = selected_assessments_by_source_item(discovery.assessments)
    builder = _CatalogBuilder()
    for document in bundle.documents:
        builder.document(document, assessments)
    return builder.items()


class _CatalogBuilder:
    def __init__(self) -> None:
        self._items: list[EvidenceItem] = []
        self._occurrences: dict[str, int] = {}

    def items(self) -> tuple[EvidenceItem, ...]:
        unique = {item.evidence_id: item for item in self._items}
        return tuple(sorted(unique.values(), key=lambda item: item.order))

    def document(
        self,
        document: NormalizedDocument,
        assessments: dict[str, SourceAssessment],
    ) -> None:
        source_key = (
            f"pdf:{document.content_sha256}"
            if document.source_type is SourceType.PDF
            else f"page:{document.source_url}"
        )
        tables = {table.id: table for table in document.tables}
        table_paths = {
            block.table_id: block.heading_path
            for block in document.blocks
            if block.table_id is not None
        }
        emitted: set[str] = set()
        for block in document.blocks:
            if block.table_id in tables and block.table_id not in emitted:
                # A table's rows stand where the table stands in the page.
                emitted.add(block.table_id)
                self._table(
                    document,
                    source_key,
                    tables[block.table_id],
                    table_paths.get(block.table_id, ()),
                    assessments,
                )
            assessment = assessments.get(block.id)
            if assessment is None:
                continue
            self._add(
                document=document,
                source_key=source_key,
                structural_path=block.heading_path,
                source_item_id=block.id,
                content=block.text,
                section=" > ".join(block.heading_path) or None,
                locator=block.source_refs[0].locator,
                assessment=assessment,
            )
        # PDF tables (and any table without a block) follow the document's blocks,
        # page by page as the transcription gave them.
        for table in document.tables:
            if table.id not in emitted:
                self._table(
                    document,
                    source_key,
                    table,
                    table_paths.get(table.id, ()),
                    assessments,
                )

    def _table(
        self,
        document: NormalizedDocument,
        source_key: str,
        table: NormalizedTable,
        heading_path: tuple[str, ...],
        assessments: dict[str, SourceAssessment],
    ) -> None:
        assessment = assessments.get(table.id)
        if assessment is None:
            return
        # Where the table sits (its heading path) and what it is called; never
        # the table's own flattened text, which is no label at all.
        section = _table_section(heading_path, table.title)
        rows_by_id = {row.id: row for row in table.rows}
        for row in table.rows:
            if not row.cells:
                continue
            self._add(
                document=document,
                source_key=source_key,
                structural_path=(
                    *heading_path,
                    table.title or "",
                    row.section or "",
                    *row.label_path,
                ),
                source_item_id=row.id,
                content=render_row(table, row, rows_by_id),
                section=section,
                locator=row.cells[0].source_refs[0].locator,
                assessment=assessment,
            )
        for index, note in enumerate(table.notes):
            self._add(
                document=document,
                source_key=source_key,
                structural_path=(*heading_path, table.title or "", "note"),
                source_item_id=f"{table.id}:note:{index}",
                content=_note_content(note.marker, note.text),
                section=section,
                locator=note.source_refs[0].locator,
                assessment=assessment,
            )

    def _add(
        self,
        *,
        document: NormalizedDocument,
        source_key: str,
        structural_path: tuple[str, ...],
        source_item_id: str,
        content: str,
        section: str | None,
        locator,
        assessment: SourceAssessment,
    ) -> None:
        text = " ".join(content.split())
        if not text:
            return
        key = "\x1f".join((source_key, *structural_path, text))
        occurrence = self._occurrences.get(key, 0)
        self._occurrences[key] = occurrence + 1
        identity = f"{key}\x1e{occurrence}"
        self._items.append(
            EvidenceItem(
                evidence_id="ev_" + hashlib.sha256(identity.encode()).hexdigest()[:24],
                document_id=document.id,
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
                order=len(self._items),
            )
        )


def render_row(
    table: NormalizedTable,
    row: NormalizedTableRow,
    rows_by_id: dict[str, NormalizedTableRow] | None = None,
) -> str:
    """One table row as a record in which every value names its column (SE1).

        Section: Term and interest rate
        3. Loan terms > 3.4. Nominal annual interest rate²
          Currency: AMD → 13.5% (Fixed)
        Notes:
          ² Depending on the creditworthiness …

    A value row that completes the row above (`continues`) carries that row's
    word in the same column. The notes a row cites by marker come with it, so a
    rate is never read without the condition that qualifies it (SE4).
    """
    stub = table.stub_columns or 1
    label_path = row.label_path or tuple(
        dict.fromkeys(cell.text for cell in row.cells[:stub] if cell.text)
    )
    previous = (rows_by_id or {}).get(row.continues or "")
    lines: list[str] = []
    if row.section:
        lines.append(f"Section: {row.section}")
    label = " > ".join(label_path)
    values = [
        (column, cell)
        for column, cell in enumerate(row.cells)
        if column >= stub and cell.text
    ]
    if not any(cell.column_path for _, cell in values):
        joined = " | ".join(
            _with_type(cell.text, previous, column) for column, cell in values
        )
        lines.append(f"{label}: {joined}" if label and joined else label or joined)
    else:
        lines.append(f"{label}:" if label else "Values:")
        for column, cell in values:
            path = " > ".join(cell.column_path)
            value = _with_type(cell.text, previous, column)
            lines.append(f"  {path} → {value}" if path else f"  {value}")
    notes = _cited_notes(table, row)
    if notes:
        lines.append("Notes:")
        lines.extend(f"  {note}" for note in notes)
    return "\n".join(lines)


def _with_type(text: str, previous: NormalizedTableRow | None, column: int) -> str:
    if previous is None or column >= len(previous.cells):
        return text
    word = _LEADING_NUMBERING.sub("", previous.cells[column].text).strip()
    return f"{text} ({word})" if word else text


def _cited_notes(table: NormalizedTable, row: NormalizedTableRow) -> list[str]:
    if not table.notes:
        return []
    text = " ".join(
        [cell.text for cell in row.cells]
        + [part for cell in row.cells for part in cell.column_path]
        + list(row.label_path)
        + [row.section or ""]
    )
    markers = {
        marker.translate(_SUPERSCRIPT_DIGITS) for marker in _MARKER.findall(text)
    }
    return [
        _note_content(note.marker, note.text)
        for note in table.notes
        if note.marker and note.marker in markers
    ]


def _table_section(heading_path: tuple[str, ...], title: str | None) -> str | None:
    parts = tuple(part for part in (*heading_path, title) if part)
    return " > ".join(dict.fromkeys(parts)) or None


def _note_content(marker: str | None, text: str) -> str:
    """A footnote as the page shows it, marker first, so the model can tie
    "12%¹" in a row to the note that explains it."""
    if not marker:
        return text
    shown = marker.translate(_SUPERSCRIPTS) if marker.isdigit() else marker
    return f"{shown} {text}"
