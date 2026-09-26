from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import pairwise

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
    structure: _Structure | None = None

    for position, (row_index, slots) in enumerate(grid):
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

        if structure is None:
            structure = _Structure.start(table, header_rows, width)
        normalized_cells = tuple(_normalized_cell(slot, table_ref) for slot in slots)
        if not any(cell.text for cell in normalized_cells):
            continue
        qualifies = structure.is_qualifier_row(slots, normalized_cells, grid, position)
        normalized_cells = structure.with_column_paths(slots, normalized_cells)
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
        row_id = f"{table.id}:row:{row_index}"
        rows.append(
            NormalizedTableRow(
                id=row_id,
                cells=normalized_cells,
                section=row_section,
                label_path=structure.label_path(normalized_cells),
                continues=structure.continued_row(slots, normalized_cells, rows),
                qualifies=qualifies,
            )
        )
        structure.record(row_id, slots)
        if qualifies:
            structure.apply_qualifier(slots, normalized_cells)
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
            stub_columns=structure.stub if structure else 0,
            column_paths=structure.header_paths if structure else (),
            rows=tuple(rows),
            notes=tuple(notes),
            source_refs=(table_ref,),
        ),
        tuple(reasons),
    )


_QUALIFIER_VALUE_CHARS = 40
_HEADER_CELL_CHARS = 60
# Column names a transcription model invents when a PDF table has no header row;
# they name nothing, so they never become a column path.
_PLACEHOLDER_HEADERS = frozenset(
    {"details", "description", "item", "value", "category", "sub-category", "terms"}
)


class _Structure:
    """What a data cell's position means: its column headers, the qualifier row
    in force, and the label columns (the stub) that name its row.

    Values are tied to headers here, where the grid is known, so that later
    readers never have to count columns (SE1).
    """

    def __init__(
        self,
        stub: int,
        header_paths: tuple[tuple[str, ...], ...],
        width: int,
    ) -> None:
        self.stub = stub
        self.header_paths = header_paths
        self.width = width
        self._qualifier: dict[int, str] = {}
        self._stub_cells: dict[str, tuple[str | None, ...]] = {}

    @classmethod
    def start(
        cls,
        table: TableArtifact,
        header_rows: list[tuple[_Slot | None, ...]],
        width: int,
    ) -> _Structure:
        paths: list[tuple[str, ...]] = []
        for column in range(width):
            parts: list[str] = []
            for slots in header_rows:
                slot = slots[column]
                text = normalize_text(slot.cell.text) if slot is not None else ""
                if text and text not in parts:
                    parts.append(text)
            paths.append(tuple(parts))
        if header_rows:
            first = header_rows[0][0]
            span = first.cell.colspan if first is not None else 1
            stub = span if span < width else 1
        elif width >= 3 and any(cell.rowspan > 1 for cell in table.cells):
            stub = 2
        else:
            stub = 1
        return cls(min(stub, max(width - 1, 1)), tuple(paths), width)

    def _column_path(self, column: int) -> tuple[str, ...]:
        if column < self.stub:
            return ()
        qualifier = self._qualifier.get(column)
        base = self.header_paths[column] if column < len(self.header_paths) else ()
        return (*base, qualifier) if qualifier else base

    def with_column_paths(
        self,
        slots: tuple[_Slot | None, ...],
        cells: tuple[NormalizedTableCell, ...],
    ) -> tuple[NormalizedTableCell, ...]:
        updated = list(cells)
        for column, slot in enumerate(slots):
            if slot is None or slot.colspan_continuation or not cells[column].text:
                continue
            covered = range(
                column, min(slot.cell.column_index + slot.cell.colspan, self.width)
            )
            paths = [self._column_path(index) for index in covered]
            path = _common_prefix(paths)
            if path:
                updated[column] = cells[column].model_copy(update={"column_path": path})
        return tuple(updated)

    def label_path(self, cells: tuple[NormalizedTableCell, ...]) -> tuple[str, ...]:
        labels: list[str] = []
        for cell in cells[: self.stub]:
            if cell.text and cell.text not in labels:
                labels.append(cell.text)
        return tuple(labels)

    def record(self, row_id: str, slots: tuple[_Slot | None, ...]) -> None:
        self._stub_cells[row_id] = tuple(
            slot.cell.id if slot is not None else None for slot in slots[: self.stub]
        )

    def continued_row(
        self,
        slots: tuple[_Slot | None, ...],
        cells: tuple[NormalizedTableCell, ...],
        rows: list[NormalizedTableRow],
    ) -> str | None:
        """The row above, when this row completes it under the same labels.

        The labels are carried down by rowspans from the row above; that row's
        values are short words (rate types such as "Fixed"), and every value of
        this row carries a number. Two list items under one label (repayment
        methods, insurance clauses) are not a continuation.
        """
        values = [cell for cell in cells[self.stub :] if cell.text]
        if not rows or not values or not all(cell.scalar_candidates for cell in values):
            return None
        previous = rows[-1]
        stub_slots = slots[: self.stub]
        if not stub_slots or not all(
            slot is not None and slot.carried for slot in stub_slots
        ):
            return None
        if self._stub_cells.get(previous.id) != tuple(
            slot.cell.id for slot in stub_slots if slot is not None
        ):
            return None
        previous_values = [
            _LEADING_NUMBERING_RE.sub("", cell.text)
            for cell in previous.cells[self.stub :]
            if cell.text
        ]
        if not previous_values or any(
            len(value) > _QUALIFIER_VALUE_CHARS or re.search(r"\d", value)
            for value in previous_values
        ):
            return None
        return previous.id

    def is_qualifier_row(
        self,
        slots: tuple[_Slot | None, ...],
        cells: tuple[NormalizedTableCell, ...],
        grid: list[tuple[int, tuple[_Slot | None, ...]]],
        position: int,
    ) -> bool:
        """Whether the row names the value columns (`Currency | AMD | USD | EUR`).

        Two or more distinct, short, digit-free value cells in separate
        columns, followed by a row with separate values in those columns.
        """
        values = self._value_cells(slots)
        if len(values) < 2:
            return False
        texts = [
            _LEADING_NUMBERING_RE.sub("", cells[column].text) for column, _ in values
        ]
        if (
            any(
                not text or len(text) > _QUALIFIER_VALUE_CHARS or re.search(r"\d", text)
                for text in texts
            )
            or len(set(texts)) < 2
        ):
            return False
        columns = {column for column, _ in values}
        for _, next_slots in grid[position + 1 :]:
            if not _direct_meaningful_cells(next_slots):
                continue
            following = {column for column, _ in self._value_cells(next_slots)}
            return len(following & columns) >= 2
        return False

    def apply_qualifier(
        self,
        slots: tuple[_Slot | None, ...],
        cells: tuple[NormalizedTableCell, ...],
    ) -> None:
        labels = self.label_path(cells)
        label = _LEADING_NUMBERING_RE.sub("", labels[-1]) if labels else ""
        qualifier: dict[int, str] = {}
        for column, cell in self._value_cells(slots):
            value = _LEADING_NUMBERING_RE.sub("", cells[column].text)
            text = f"{label}: {value}" if label else value
            for index in range(column, min(column + cell.colspan, self.width)):
                qualifier[index] = text
        self._qualifier = qualifier

    def _value_cells(
        self, slots: tuple[_Slot | None, ...]
    ) -> list[tuple[int, TableCellArtifact]]:
        found: list[tuple[int, TableCellArtifact]] = []
        seen: set[str] = set()
        for column, slot in enumerate(slots):
            if (
                column < self.stub
                or slot is None
                or slot.carried
                or slot.colspan_continuation
                or slot.cell.id in seen
                or not normalize_text(slot.cell.text)
            ):
                continue
            seen.add(slot.cell.id)
            found.append((column, slot.cell))
        return found


@dataclass(frozen=True)
class TextTableStructure:
    """The SE1 structure of a table given as text rows (a PDF transcription)."""

    stub: int
    column_paths: tuple[tuple[str, ...], ...]
    cell_paths: tuple[tuple[tuple[str, ...], ...], ...]
    qualifies: tuple[bool, ...]
    continues: tuple[int | None, ...]


def _reads_as_header(row: tuple[str, ...]) -> bool:
    texts = [normalize_text(cell) for cell in row if normalize_text(cell)]
    return bool(texts) and all(
        len(text) <= _HEADER_CELL_CHARS and not extract_scalar_candidates(text)
        for text in texts
    )


def structure_text_table(
    header_rows: tuple[tuple[str, ...], ...],
    rows: tuple[tuple[str, ...], ...],
) -> TextTableStructure:
    """Column paths, qualifier rows and continuations for a rectangular text table.

    The same rules as `_Structure` for HTML tables, on cell texts: a PDF table
    arrives with its header rows and its spanned label cells already repeated.
    """
    # A transcription model sometimes offers a data row as a header row
    # ("1.1.1. (i) Purchase of residential property…", "Maximum amount: AMD 15
    # million"). Only rows that read as headers -- short cells, no amounts or
    # rates -- name columns.
    header_rows = tuple(row for row in header_rows if _reads_as_header(row))
    width = max((len(row) for row in (*header_rows, *rows)), default=0)
    paths: list[tuple[str, ...]] = []
    for column in range(width):
        parts: list[str] = []
        for header in header_rows:
            text = normalize_text(header[column]) if column < len(header) else ""
            if (
                text
                and text not in parts
                and text.casefold() not in _PLACEHOLDER_HEADERS
            ):
                parts.append(text)
        paths.append(tuple(parts))
    spanning_stub = bool(
        header_rows
        and width >= 3
        and normalize_text(header_rows[0][0])
        and normalize_text(header_rows[0][0]) == normalize_text(header_rows[0][1])
    )
    repeated_labels = sum(
        1
        for above, below in pairwise(rows)
        if normalize_text(above[0])
        and normalize_text(above[0]) == normalize_text(below[0])
    )
    stub = 2 if width >= 3 and (spanning_stub or repeated_labels >= 2) else 1

    def words(text: str) -> str:
        return _LEADING_NUMBERING_RE.sub("", normalize_text(text))

    def has_digit(text: str) -> bool:
        return bool(re.search(r"\d", text))

    qualifier: dict[int, str] = {}
    cell_paths: list[tuple[tuple[str, ...], ...]] = []
    qualifies: list[bool] = []
    continues: list[int | None] = []
    for index, row in enumerate(rows):
        values = [
            (column, words(row[column]))
            for column in range(stub, len(row))
            if normalize_text(row[column])
        ]
        texts = [text for _, text in values]
        following = next(
            (
                [c for c in range(stub, len(later)) if normalize_text(later[c])]
                for later in rows[index + 1 :]
                if any(normalize_text(cell) for cell in later)
            ),
            [],
        )
        is_qualifier = (
            len(values) >= 2
            and len(set(texts)) >= 2
            and all(
                text and len(text) <= _QUALIFIER_VALUE_CHARS and not has_digit(text)
                for text in texts
            )
            and len({column for column, _ in values} & set(following)) >= 2
        )
        cell_paths.append(
            tuple(
                ()
                if column < stub or not normalize_text(cell)
                else (
                    (*paths[column], qualifier[column])
                    if column in qualifier and not is_qualifier
                    else paths[column]
                )
                for column, cell in enumerate(row)
            )
        )
        qualifies.append(is_qualifier)
        previous = rows[index - 1] if index else None
        previous_values = (
            [words(cell) for cell in previous[stub:] if normalize_text(cell)]
            if previous is not None
            else []
        )
        continues.append(
            index - 1
            if previous is not None
            and values
            and all(has_digit(text) for text in texts)
            and tuple(map(normalize_text, previous[:stub]))
            == tuple(map(normalize_text, row[:stub]))
            and previous_values
            and all(
                len(text) <= _QUALIFIER_VALUE_CHARS and not has_digit(text)
                for text in previous_values
            )
            else None
        )
        if is_qualifier:
            label = words(row[stub - 1]) if stub else ""
            qualifier = {
                column: f"{label}: {text}" if label else text for column, text in values
            }
    return TextTableStructure(
        stub=stub,
        column_paths=tuple(paths),
        cell_paths=tuple(cell_paths),
        qualifies=tuple(qualifies),
        continues=tuple(continues),
    )


def _common_prefix(paths: list[tuple[str, ...]]) -> tuple[str, ...]:
    if not paths:
        return ()
    prefix: list[str] = []
    for parts in zip(*paths, strict=False):
        if len(set(parts)) != 1:
            break
        prefix.append(parts[0])
    shortest = min(len(path) for path in paths)
    return tuple(prefix[:shortest])


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
