import pytest

from app.domain.acquisition import (
    SourceLocator,
    SourceType,
    TableArtifact,
    TableCellArtifact,
)
from app.domain.normalization import (
    ScalarKind,
    normalize_money_text,
    normalize_percentage,
)
from app.services.scalar_normalizer import extract_scalar_candidates
from app.services.table_normalizer import normalize_table

SOURCE_URL = "https://ameriabank.am/en/test"


def _locator(block_id: str) -> SourceLocator:
    return SourceLocator(
        source_url=SOURCE_URL,
        source_type=SourceType.PAGE,
        block_id=block_id,
    )


def _cell(
    cell_id: str,
    row: int,
    column: int,
    text: str,
    *,
    rowspan: int = 1,
    colspan: int = 1,
) -> TableCellArtifact:
    return TableCellArtifact(
        id=cell_id,
        row_index=row,
        column_index=column,
        rowspan=rowspan,
        colspan=colspan,
        tag="td",
        text=text,
        markdown=text,
        locator=_locator(cell_id),
    )


def test_money_grouping_is_canonical() -> None:
    assert normalize_money_text("10 000 000 amd") == "10000000 AMD"
    assert normalize_money_text("10,000,000 AMD") == "10000000 AMD"


def test_percentage_is_canonical() -> None:
    assert normalize_percentage("13,50 %") == "13.5%"


def test_invalid_percentage_fails() -> None:
    with pytest.raises(ValueError):
        normalize_percentage("unknown")


def test_scalar_candidates_preserve_ranges_operators_and_units() -> None:
    scalars = extract_scalar_candidates(
        "AMD 3,000,000 - AMD 150,000,000; 13%-15%; up to 60 months"
    )

    assert [(scalar.kind, scalar.unit) for scalar in scalars] == [
        (ScalarKind.RANGE, "AMD"),
        (ScalarKind.RANGE, "percent"),
        (ScalarKind.NUMBER, "month"),
    ]
    assert scalars[0].min_value == 3_000_000
    assert scalars[0].max_value == 150_000_000
    assert scalars[2].operator == "<="


def test_table_normalization_expands_rowspan_and_removes_phantom_columns() -> None:
    table = TableArtifact(
        id="t1",
        title="Consumer loan",
        column_count=5,
        cells=(
            _cell("section", 0, 0, "Loan terms²", rowspan=3),
            _cell("currency", 0, 1, "Currency"),
            _cell("amd", 0, 2, "AMD"),
            _cell("phantom-1", 0, 3, ""),
            _cell("phantom-2", 0, 4, ""),
            _cell("limit", 1, 1, "Minimum and maximum loan limits"),
            _cell("limit-value", 1, 2, "AMD 50,000 - AMD 6,000,000"),
            # Carry-only content plus empty DOM cells is not another record.
            _cell("phantom-3", 2, 3, ""),
            _cell("phantom-4", 2, 4, ""),
            _cell("note", 3, 0, "² APR factors", colspan=3),
        ),
        locator=_locator("t1"),
    )

    normalized = normalize_table(table)

    assert normalized.headers == ("Section", "Item", "Terms")
    assert len(normalized.rows) == 2
    assert [cell.text for cell in normalized.rows[1].cells] == [
        "Loan terms²",
        "Minimum and maximum loan limits",
        "AMD 50,000 - AMD 6,000,000",
    ]
    assert normalized.notes[0].raw_text == "² APR factors"
    assert normalized.rows[1].cells[2].scalar_candidates[0].unit == "AMD"


def test_table_normalization_merges_list_rows_under_shared_rowspans() -> None:
    table = TableArtifact(
        id="documents",
        column_count=3,
        cells=(
            _cell("section", 0, 0, "Required documents", rowspan=2),
            _cell("item", 0, 1, "Documents", rowspan=2),
            _cell("identity", 0, 2, "• Identity document"),
            _cell("social", 1, 2, "• Social card"),
        ),
        locator=_locator("documents"),
    )

    normalized = normalize_table(table)

    assert len(normalized.rows) == 1
    assert normalized.rows[0].cells[2].list_items == (
        "Identity document",
        "Social card",
    )
    assert len(normalized.rows[0].cells[2].source_refs) == 2
