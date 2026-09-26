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

# A list item: a bullet, or a short number followed by `.` or `)` and a space.
# "12.5% annual" and "01.03.2025" are values, not items.
_LIST_ITEM_RE = re.compile(r"^(?:[•▪◦]\s*|-\s+|\d{1,2}[.)]\s+)(.+)$")
# A footnote marker: superscript digits, `*`/`†`/`‡`, `1)`, or one or two digits
# directly followed by a capital letter ("1 In case…", "5This service…"). A
# note that starts with an amount ("5 000 000 AMD…") has no marker.
_NOTE_MARKER_RE = re.compile(
    r"^(?P<marker>[⁰¹²³⁴⁵⁶⁷⁸⁹]+|[*†‡]+|\d{1,2}\)|\d{1,2}(?=\s?[A-ZԱ-ՖА-Я«\"“]))"
    r"\s*(?P<body>.+)$",
    re.DOTALL,
)
_SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_LEADING_NUMBERING_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
_SENTENCE_PUNCTUATION_RE = re.compile(r"[.;:!?,](?:\s|$)")
_MAX_LABEL_CHARS = 100


@dataclass(frozen=True)
class _Slot:
    cell: TableCellArtifact
    carried: bool
    colspan_continuation: bool = False


@dataclass(frozen=True)
class _SubSection:
    label: str
    # The cell carried in column 0 when the label appeared; the label ends with it.
    anchor_cell_id: str


def normalize_table(table: TableArtifact) -> NormalizedTable:
    return normalize_table_with_report(table)[0]


def normalize_table_with_report(
    table: TableArtifact,
) -> tuple[NormalizedTable, tuple[str, ...]]:
    """Expand rowspans, remove phantom columns, and separate titles, headers,
    section labels and notes from data.

    Returns the table and the reasons it is ambiguous (invented headers, rows
    dropped as duplicates), which normalization reports as `AMBIGUOUS_TABLE`.
    """
    width = _meaningful_width(table)
    table_ref = SourceReference(source_item_id=table.id, locator=table.locator)
    base_titles = [table.context_title or table.title, table.caption]
    if width == 0:
        return (
            NormalizedTable(
                id=table.id,
                title=_join_titles(base_titles),
                source_refs=(table_ref,),
            ),
            (),
        )

    grid = _reconstruct_grid(table.cells, width)
    has_html_headers = any(cell.is_header or cell.row_header for cell in table.cells)
    own_title: str | None = None
    header_rows: list[tuple[_Slot | None, ...]] = []
    rows: list[NormalizedTableRow] = []
    notes: list[NormalizedNote] = []
    reasons: list[str] = []
    section: str | None = None
    section_cell: TableCellArtifact | None = None
    section_rows = 0
    sub_section: _SubSection | None = None

    for row_index, slots in grid:
        direct = _direct_meaningful_cells(slots)
        if not direct:
            # A browser table can contain a physical row made solely from empty
            # phantom cells while rowspans carry older values through it.
            continue

        if sub_section is not None and not _anchored(slots, sub_section):
            sub_section = None

        label_cell = _label_cell(slots, direct, width)
        if label_cell is not None:
            text = normalize_multiline_text(label_cell.text)
            if (
                label_cell.column_index == 0
                and not rows
                and not header_rows
                and own_title is None
                and section is None
            ):
                own_title = text
                continue
            if _looks_like_label(text):
                if label_cell.column_index == 0:
                    if section is not None and section_rows == 0 and section_cell:
                        # A label with no rows under it was a remark, not a section.
                        notes.append(_note(section, section_cell))
                    section, section_cell, section_rows = text, label_cell, 0
                    sub_section = None
                else:
                    carried = slots[0]
                    assert carried is not None
                    sub_section = _SubSection(text, carried.cell.id)
                continue
            if label_cell.column_index == 0:
                notes.append(_note(text, label_cell))
                continue

        if not rows and _is_header_row(slots, direct, width, has_html_headers):
            header_rows.append(slots)
            continue

        normalized_cells = tuple(_normalized_cell(slot, table_ref) for slot in slots)
        if not any(cell.text for cell in normalized_cells):
            continue
        row_section = (
            " > ".join(
                part
                for part in (section, sub_section.label if sub_section else None)
                if part
            )
            or None
        )
        list_column = (
            _list_continuation_column(slots, rows[-1], normalized_cells, row_section)
            if rows
            else None
        )
        if list_column is not None:
            rows[-1] = _merge_list_row(rows[-1], normalized_cells, list_column)
            section_rows += 1
            continue
        signature = tuple(cell.text for cell in normalized_cells)
        if (
            rows
            and rows[-1].section == row_section
            and tuple(cell.text for cell in rows[-1].cells) == signature
        ):
            reasons.append(f"row {row_index} repeats the row above and was dropped")
            continue
        rows.append(
            NormalizedTableRow(
                id=f"{table.id}:row:{row_index}",
                cells=normalized_cells,
                section=row_section,
            )
        )
        section_rows += 1

    if section is not None and section_rows == 0 and section_cell is not None:
        notes.append(_note(section, section_cell))

    headers: tuple[str, ...]
    headers_inferred = False
    if header_rows:
        headers = _combined_headers(header_rows, width)
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
    if headers_inferred:
        reasons.insert(0, f"no header row; headers invented: {' | '.join(headers)}")

    return (
        NormalizedTable(
            id=table.id,
            title=_join_titles([*base_titles, own_title]),
            headers=headers,
            headers_inferred=headers_inferred,
            rows=tuple(rows),
            notes=tuple(notes),
            source_refs=(table_ref,),
        ),
        tuple(reasons),
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
                slots[column] = _Slot(
                    cell=cell,
                    carried=True,
                    colspan_continuation=column > cell.column_index,
                )
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


def _label_cell(
    slots: tuple[_Slot | None, ...], direct: list[TableCellArtifact], width: int
) -> TableCellArtifact | None:
    """The one cell of a row that is a title, section label or note, if any.

    Either it spans the whole table from column 0, or it starts in column 1
    (the item column) under a carried section cell and spans to the end. A
    single cell starting further right is a value under a carried item, not a
    label. A one-column table has no such rows.
    """
    if width < 2 or len(direct) != 1:
        return None
    cell = direct[0]
    if cell.column_index + cell.colspan < width:
        return None
    if cell.column_index == 0:
        return cell
    if cell.column_index == 1 and width > 2:
        carried = slots[0]
        if carried is not None and carried.carried:
            return cell
    return None


def _looks_like_label(text: str) -> bool:
    """A short heading-like phrase: no sentence punctuation, no numbers, no
    footnote marker, not a list item."""
    if not text or "\n" in text or _NOTE_MARKER_RE.match(text):
        return False
    body = _LEADING_NUMBERING_RE.sub("", text)
    return (
        len(body) <= _MAX_LABEL_CHARS
        and not _SENTENCE_PUNCTUATION_RE.search(body)
        and not _LIST_ITEM_RE.match(body)
        and not extract_scalar_candidates(body)
    )


def _anchored(slots: tuple[_Slot | None, ...], sub_section: _SubSection) -> bool:
    first = slots[0]
    return (
        first is not None
        and first.carried
        and first.cell.id == sub_section.anchor_cell_id
    )


def _is_header_row(
    slots: tuple[_Slot | None, ...],
    cells: list[TableCellArtifact],
    width: int,
    has_html_headers: bool,
) -> bool:
    if not cells or any(slot is None for slot in slots[:width]):
        return False
    if len(cells) < 2 and width > 1:
        return False
    if has_html_headers:
        return all(cell.is_header and not cell.row_header for cell in cells)
    # No HTML header cells anywhere: a first row set wholly in bold, with no
    # numbers in it, is the header row the author meant.
    return all(cell.bold for cell in cells) and not any(
        extract_scalar_candidates(normalize_text(cell.text)) for cell in cells
    )


def _combined_headers(
    header_rows: list[tuple[_Slot | None, ...]], width: int
) -> tuple[str, ...]:
    """One header per column, stacking header rows: `Rate / AMD`."""
    headers: list[str] = []
    for column in range(width):
        parts: list[str] = []
        for slots in header_rows:
            slot = slots[column]
            text = normalize_text(slot.cell.text) if slot is not None else ""
            if text and text not in parts:
                parts.append(text)
        headers.append(" / ".join(parts))
    return tuple(headers)


def _join_titles(parts: list[str | None]) -> str | None:
    """Join title parts, dropping one that another part already contains."""
    cleaned = [text for part in parts if part and (text := normalize_text(part))]
    kept: list[str] = []
    for text in cleaned:
        core = _LEADING_NUMBERING_RE.sub("", text)
        if any(
            core in other
            for other in cleaned
            if other != text and len(other) > len(text)
        ):
            continue
        if text not in kept:
            kept.append(text)
    return " — ".join(kept) or None


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
    separated = re.sub(r"\s{2,}(?=\d{1,2}[.)]\s)", "\n", value.replace("\r", "\n"))
    for line in separated.split("\n"):
        match = _LIST_ITEM_RE.match(line.strip())
        if match and (item := normalize_text(match.group(1))):
            items.append(item)
    return tuple(items)


def _list_continuation_column(
    slots: tuple[_Slot | None, ...],
    previous: NormalizedTableRow,
    cells: tuple[NormalizedTableCell, ...],
    section: str | None,
) -> int | None:
    """The column a row only adds list items to, if the row is such a row.

    One cell is new in the row; every other column repeats the row above
    (carried by a rowspan, or empty in both); and that column of the row
    above is a list too, so the new items continue it. Any column can hold
    the list, not only the last.
    """
    if previous.section != section:
        return None
    direct = {slot.cell.id for slot in slots if slot is not None and not slot.carried}
    columns = [
        index
        for index, slot in enumerate(slots)
        if slot is not None and not slot.carried and not slot.colspan_continuation
    ]
    if len(direct) != 1 or len(columns) != 1:
        return None
    column = columns[0]
    spanned = {
        index
        for index, slot in enumerate(slots)
        if slot is not None and not slot.carried and slot.colspan_continuation
    }
    others_match = all(
        previous.cells[index].text == cells[index].text
        for index in range(len(cells))
        if index != column and index not in spanned
    )
    if others_match and previous.cells[column].list_items and cells[column].list_items:
        return column
    return None


def _merge_list_row(
    previous: NormalizedTableRow,
    cells: tuple[NormalizedTableCell, ...],
    column: int,
) -> NormalizedTableRow:
    merged = list(previous.cells)
    merged[column] = _merge_cells(previous.cells[column], cells[column])
    return previous.model_copy(update={"cells": tuple(merged)})


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
    marker = match.group("marker").rstrip(")").translate(_SUPERSCRIPT_DIGITS)
    return marker, normalize_multiline_text(match.group("body"))
