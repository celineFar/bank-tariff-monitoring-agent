from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.acquisition import TableArtifact, TableCellArtifact
from app.domain.normalization import (
    NormalizedNote,
    NormalizedTable,
    NormalizedTableCell,
    NormalizedTableRow,
    SourceReference,
    normalize_multiline_text,
    normalize_text,
)
from app.services.scalar_normalizer import extract_scalar_candidates

_LIST_ITEM_RE = re.compile(r"^(?:[-•▪◦]|â€¢|\d+[.)])\s*(.+)$")
_NOTE_MARKER_RE = re.compile(
    r"^(?P<marker>(?:\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹*†‡])+)[.)]?\s*(?P<body>.+)$",
    re.DOTALL,
)
_SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


@dataclass(frozen=True)
class _Slot:
    cell: TableCellArtifact
    carried: bool
    colspan_continuation: bool = False


def normalize_table(table: TableArtifact) -> NormalizedTable:
    """Expand rowspans, remove phantom columns, and separate notes from data."""
    width = _meaningful_width(table)
    table_ref = SourceReference(source_item_id=table.id, locator=table.locator)
    if width == 0:
        return NormalizedTable(
            id=table.id,
            title=_optional_text(table.title or table.caption),
            source_refs=(table_ref,),
        )

    grid = _reconstruct_grid(table.cells, width)
    title = _optional_text(table.title or table.caption)
    headers: tuple[str, ...] = ()
    headers_inferred = False
    rows: list[NormalizedTableRow] = []
    notes: list[NormalizedNote] = []
    seen_rows: set[tuple[str, ...]] = set()

    for row_index, slots in grid:
        direct = _direct_meaningful_cells(slots)
        if not direct:
            # A browser table can contain a physical row made solely from empty
            # phantom cells while rowspans carry older values through it.
            continue

        if _is_full_width_cell(direct, width):
            cell = direct[0]
            cell_text = normalize_multiline_text(cell.text)
            if not rows and not headers and title is None:
                title = cell_text or None
            elif cell_text:
                notes.append(_note(cell_text, cell))
            continue

        if not rows and _is_header_row(slots, direct, width):
            headers = tuple(_slot_text(slot) for slot in slots)
            continue

        normalized_cells = tuple(_normalized_cell(slot, table_ref) for slot in slots)
        signature = tuple(cell.text for cell in normalized_cells)
        if not any(signature) or signature in seen_rows:
            continue
        if _is_list_continuation(slots, rows, normalized_cells):
            previous = rows[-1]
            merged_cell = _merge_cells(previous.cells[-1], normalized_cells[-1])
            rows[-1] = previous.model_copy(
                update={"cells": (*previous.cells[:-1], merged_cell)}
            )
            continue
        seen_rows.add(signature)
        rows.append(
            NormalizedTableRow(
                id=f"{table.id}:row:{row_index}",
                cells=normalized_cells,
            )
        )

    if not headers:
        acquired_headers = tuple(
            normalize_text(value) for value in table.headers[:width]
        )
        if len(acquired_headers) == width and any(acquired_headers):
            headers = acquired_headers
            headers_inferred = table.headers_inferred
        elif width == 3 and any(cell.rowspan > 1 for cell in table.cells):
            headers = ("Section", "Item", "Terms")
            headers_inferred = True
        elif width > 3 and any(cell.rowspan > 1 for cell in table.cells):
            headers = (
                "Section",
                "Item",
                *(f"Terms {index}" for index in range(1, width - 1)),
            )
            headers_inferred = True
        else:
            headers = tuple(f"Column {index + 1}" for index in range(width))
            headers_inferred = True

    for raw_note in table.notes:
        text = normalize_multiline_text(raw_note)
        if not text:
            continue
        marker, body = _split_note(text)
        if any(
            existing.text == body and existing.marker == marker for existing in notes
        ):
            continue
        notes.append(
            NormalizedNote(
                marker=marker,
                raw_text=raw_note,
                text=body,
                source_refs=(table_ref,),
            )
        )

    return NormalizedTable(
        id=table.id,
        title=title,
        headers=headers,
        headers_inferred=headers_inferred,
        rows=tuple(rows),
        notes=tuple(notes),
        source_refs=(table_ref,),
    )


def _meaningful_width(table: TableArtifact) -> int:
    occupied = [
        cell.column_index + cell.colspan
        for cell in table.cells
        if normalize_text(cell.text) or normalize_text(cell.markdown)
    ]
    if occupied:
        return max(occupied)
    populated_rows = [
        len(tuple(value for value in row if normalize_text(value)))
        for row in table.rows
    ]
    return max(populated_rows, default=0)


def _reconstruct_grid(
    cells: tuple[TableCellArtifact, ...], width: int
) -> list[tuple[int, tuple[_Slot | None, ...]]]:
    origins: dict[int, list[TableCellArtifact]] = {}
    final_row = 0
    for cell in cells:
        origins.setdefault(cell.row_index, []).append(cell)
        final_row = max(final_row, cell.row_index + cell.rowspan)

    active: dict[int, tuple[TableCellArtifact, int]] = {}
    result: list[tuple[int, tuple[_Slot | None, ...]]] = []
    for row_index in range(final_row):
        slots: list[_Slot | None] = [None] * width
        for column, (cell, remaining) in tuple(active.items()):
            if column < width:
                slots[column] = _Slot(cell=cell, carried=True)
            if remaining <= 1:
                del active[column]
            else:
                active[column] = (cell, remaining - 1)

        for cell in sorted(
            origins.get(row_index, ()), key=lambda value: value.column_index
        ):
            for offset in range(cell.colspan):
                column = cell.column_index + offset
                if column >= width:
                    continue
                slots[column] = _Slot(
                    cell=cell,
                    carried=False,
                    colspan_continuation=offset > 0,
                )
                if cell.rowspan > 1:
                    active[column] = (cell, cell.rowspan - 1)
        result.append((row_index, tuple(slots)))
    return result


def _direct_meaningful_cells(
    slots: tuple[_Slot | None, ...],
) -> list[TableCellArtifact]:
    found: list[TableCellArtifact] = []
    seen: set[str] = set()
    for slot in slots:
        if (
            slot is None
            or slot.carried
            or slot.colspan_continuation
            or slot.cell.id in seen
            or not (
                normalize_text(slot.cell.text) or normalize_text(slot.cell.markdown)
            )
        ):
            continue
        found.append(slot.cell)
        seen.add(slot.cell.id)
    return found


def _is_full_width_cell(cells: list[TableCellArtifact], width: int) -> bool:
    return len(cells) == 1 and cells[0].column_index == 0 and cells[0].colspan >= width


def _is_header_row(
    slots: tuple[_Slot | None, ...], cells: list[TableCellArtifact], width: int
) -> bool:
    return (
        all(cell.is_header for cell in cells)
        and len(cells) > 1
        and all(slot is not None for slot in slots[:width])
    )


def _slot_text(slot: _Slot | None) -> str:
    if slot is None or slot.colspan_continuation:
        return ""
    return normalize_text(slot.cell.text)


def _normalized_cell(
    slot: _Slot | None, table_ref: SourceReference
) -> NormalizedTableCell:
    if slot is None:
        return NormalizedTableCell(raw_text="", text="", source_refs=(table_ref,))
    source_ref = SourceReference(source_item_id=slot.cell.id, locator=slot.cell.locator)
    if slot.colspan_continuation:
        return NormalizedTableCell(raw_text="", text="", source_refs=(source_ref,))
    text = normalize_multiline_text(slot.cell.text)
    markdown = normalize_multiline_text(slot.cell.markdown)
    return NormalizedTableCell(
        raw_text=slot.cell.text,
        text=text,
        markdown=markdown,
        list_items=_list_items(slot.cell.text),
        scalar_candidates=extract_scalar_candidates(text),
        source_refs=(source_ref,),
    )


def _list_items(value: str) -> tuple[str, ...]:
    items: list[str] = []
    separated = re.sub(r"\s{2,}(?=\d+[.)])", "\n", value.replace("\r", "\n"))
    for line in separated.split("\n"):
        match = _LIST_ITEM_RE.match(line.strip())
        if match and (item := normalize_text(match.group(1))):
            items.append(item)
    return tuple(items)


def _is_list_continuation(
    slots: tuple[_Slot | None, ...],
    rows: list[NormalizedTableRow],
    cells: tuple[NormalizedTableCell, ...],
) -> bool:
    if len(slots) < 2 or not rows:
        return False
    prefix_is_carried = all(slot is not None and slot.carried for slot in slots[:-1])
    last_is_direct = slots[-1] is not None and not slots[-1].carried
    same_prefix = tuple(cell.text for cell in rows[-1].cells[:-1]) == tuple(
        cell.text for cell in cells[:-1]
    )
    return (
        prefix_is_carried
        and last_is_direct
        and same_prefix
        and bool(rows[-1].cells[-1].list_items)
        and bool(cells[-1].list_items)
    )


def _merge_cells(
    first: NormalizedTableCell, second: NormalizedTableCell
) -> NormalizedTableCell:
    source_refs = tuple(
        {
            (reference.source_item_id, str(reference.locator)): reference
            for reference in (*first.source_refs, *second.source_refs)
        }.values()
    )
    separator = "\n" if first.text and second.text else ""
    return NormalizedTableCell(
        raw_text=f"{first.raw_text}{separator}{second.raw_text}",
        text=f"{first.text}{separator}{second.text}",
        markdown=f"{first.markdown}{separator}{second.markdown}".strip(),
        list_items=(*first.list_items, *second.list_items),
        scalar_candidates=(*first.scalar_candidates, *second.scalar_candidates),
        source_refs=source_refs,
    )


def _note(text: str, cell: TableCellArtifact) -> NormalizedNote:
    marker, body = _split_note(text)
    return NormalizedNote(
        marker=marker,
        raw_text=cell.text,
        text=body,
        source_refs=(SourceReference(source_item_id=cell.id, locator=cell.locator),),
    )


def _split_note(text: str) -> tuple[str | None, str]:
    match = _NOTE_MARKER_RE.match(text)
    if not match:
        return None, text
    return (
        match.group("marker").translate(_SUPERSCRIPT_DIGITS),
        normalize_multiline_text(match.group("body")),
    )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return normalize_text(value) or None
