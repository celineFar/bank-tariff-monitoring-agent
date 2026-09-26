"""The HTML quality score: how much of a seed page's recorded structure survived.

Each seed page was read once, by a person, and what normalization must produce
from it was recorded (fix-process/normalization/data/seed-ground-truth.json).
The runtime baseline keeps only the *structure* of that record -- which tables
exist, their titles, header rows, sections and footnotes, which row labels carry
a value, which text blocks exist -- never tariff values, so a rate the bank
changes is a tariff change, not a drop in normalization quality.

`score_page` counts the baseline checks a normalized page document passes. The
score is `passed / checks`; a page with no baseline has no score (`None`).
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.domain.normalization import NormalizedDocument, NormalizedTable

DEFAULT_NORMALIZATION_BASELINE_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "normalization_baseline.json"
)
_SPACE = re.compile(r"\s+")
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RowExpectation(_Model):
    """A row whose cells contain `label`, under `section` when given."""

    label: str = Field(min_length=1)
    section: str | None = None
    # The row also has a non-empty cell that is not the label.
    has_value: bool = True


class NoteExpectation(_Model):
    marker: str | None = None
    starts: str = Field(min_length=1)


class TableExpectation(_Model):
    # Text that picks the table: part of its title, a cell, or a note.
    find: str = Field(min_length=1)
    title: str | None = None
    # The real column headers, or None when the table has no header row (its
    # headers may then be invented, but must be flagged as such).
    header_row: tuple[str, ...] | None = None
    min_rows: int = Field(default=0, ge=0)
    rows: tuple[RowExpectation, ...] = ()
    notes: tuple[NoteExpectation, ...] = ()

    @property
    def checks(self) -> int:
        return (
            2  # found, header row
            + (1 if self.title else 0)
            + (1 if self.min_rows else 0)
            + len(self.rows)
            + len(self.notes)
        )


class BlockExpectation(_Model):
    text: str = Field(min_length=1)


class PageBaseline(_Model):
    offering_id: str = Field(min_length=1)
    # The seed URL and any other URL the page is known by (canonical, final).
    urls: tuple[str, ...] = Field(min_length=1)
    recorded_on: str
    tables: tuple[TableExpectation, ...] = ()
    blocks: tuple[BlockExpectation, ...] = ()

    @property
    def checks(self) -> int:
        return sum(table.checks for table in self.tables) + len(self.blocks)


class NormalizationBaseline(_Model):
    pages: tuple[PageBaseline, ...] = ()

    def for_urls(self, *urls: str) -> PageBaseline | None:
        wanted = {_url_key(url) for url in urls if url}
        for page in self.pages:
            if wanted & {_url_key(url) for url in page.urls}:
                return page
        return None


class BaselineScore(_Model):
    score: float = Field(ge=0, le=1)
    checks: int = Field(ge=0)
    failures: tuple[str, ...] = ()


def load_normalization_baseline(
    path: Path = DEFAULT_NORMALIZATION_BASELINE_PATH,
) -> NormalizationBaseline:
    return NormalizationBaseline.model_validate_json(path.read_text(encoding="utf-8"))


def score_page(document: NormalizedDocument, baseline: PageBaseline) -> BaselineScore:
    failures: list[str] = []
    for expectation in baseline.tables:
        failures.extend(_table_failures(expectation, document.tables))
    block_texts = [_n(block.text) for block in document.blocks]
    for block in baseline.blocks:
        if not any(_n(block.text) in text for text in block_texts):
            failures.append(f"no block with {block.text!r}")
    checks = baseline.checks
    passed = max(checks - len(failures), 0)
    return BaselineScore(
        score=round(passed / checks, 4) if checks else 1.0,
        checks=checks,
        failures=tuple(failures),
    )


def _table_failures(
    expectation: TableExpectation, tables: tuple[NormalizedTable, ...]
) -> list[str]:
    label = f"table {expectation.find[:40]!r}"
    table = next(
        (table for table in tables if _n(expectation.find) in _table_text(table)), None
    )
    if table is None:
        # Every check of a missing table fails.
        return [f"{label} not found"] + [f"{label}: unchecked"] * (
            expectation.checks - 1
        )
    failures: list[str] = []
    if expectation.title and _n(expectation.title) not in _n(table.title):
        failures.append(f"{label} title {table.title!r} lacks {expectation.title!r}")
    if expectation.header_row is None:
        if table.headers and not table.headers_inferred:
            failures.append(f"{label} has no header row, got {table.headers}")
    else:
        headers = _n(" | ".join(table.headers))
        if table.headers_inferred or not all(
            _n(header) in headers for header in expectation.header_row
        ):
            failures.append(f"{label} headers {table.headers}")
    if expectation.min_rows and len(table.rows) < expectation.min_rows:
        failures.append(f"{label} has {len(table.rows)} rows < {expectation.min_rows}")
    for row in expectation.rows:
        if not _has_row(table, row):
            where = f" under {row.section!r}" if row.section else ""
            failures.append(f"{label} no row {row.label!r}{where}")
    for note in expectation.notes:
        found = [n for n in table.notes if _n(n.text).startswith(_n(note.starts))]
        if not found or not any(
            (n.marker or "").translate(_SUPERSCRIPTS) == (note.marker or "")
            for n in found
        ):
            failures.append(f"{label} no note {note.marker} {note.starts[:40]!r}")
    return failures


def _has_row(table: NormalizedTable, expectation: RowExpectation) -> bool:
    label = _n(expectation.label)
    section = _n(expectation.section)
    for row in table.rows:
        texts = [_n(cell.text) for cell in row.cells]
        if not any(label in text for text in texts):
            continue
        if section and section not in _n(row.section):
            continue
        if expectation.has_value and not any(
            text and label not in text for text in texts
        ):
            continue
        return True
    return False


def _table_text(table: NormalizedTable) -> str:
    parts = [table.title or "", *table.headers]
    parts += [cell.text for row in table.rows for cell in row.cells]
    parts += [note.text for note in table.notes]
    return _n(" ".join(parts))


def _n(value: str | None) -> str:
    return _SPACE.sub(" ", value or "").strip()


def _url_key(url: str) -> str:
    return str(url).split("#", 1)[0].rstrip("/").lower()
