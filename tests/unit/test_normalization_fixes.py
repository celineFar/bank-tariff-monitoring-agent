"""Regression cases from the normalization fix plan.

Each test states the output normalization *should* produce for one confirmed
problem (N-numbers refer to fix-process/normalization/normalization-fix-plan.md).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.normalization import NormalizedBlock, NormalizedTable, ScalarKind
from app.services.block_normalizer import normalize_block
from app.services.html_parser import HtmlArtifactParser
from app.services.scalar_normalizer import extract_scalar_candidates
from app.services.table_normalizer import normalize_table

SOURCE_URL = "https://ameriabank.am/en/test"


def _parse(body: str) -> tuple[list[NormalizedBlock], list[NormalizedTable]]:
    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        f"<html><body>{body}</body></html>", source_url=SOURCE_URL
    )
    return (
        [normalize_block(block, table_id=block.table_id) for block in parsed.blocks],
        [normalize_table(table) for table in parsed.tables],
    )


def _rows(table: NormalizedTable) -> list[tuple[str, ...]]:
    return [tuple(cell.text for cell in row.cells) for row in table.rows]


def _texts(blocks: list[NormalizedBlock]) -> list[str]:
    return [block.text for block in blocks]


# --- N1: header detection ---------------------------------------------------


def test_n1_row_header_table_keeps_every_data_row() -> None:
    _, (table,) = _parse(
        '<table><tr><th scope="row">Interest rate</th><td>12%</td></tr>'
        '<tr><th scope="row">Term</th><td>60 months</td></tr></table>'
    )
    assert _rows(table) == [("Interest rate", "12%"), ("Term", "60 months")]


def test_n1_bold_first_row_with_numbers_is_data() -> None:
    _, (table,) = _parse(
        "<table><tr><td><strong>Rate</strong></td><td><strong>12%</strong></td></tr>"
        "<tr><td>Term</td><td>60 months</td></tr></table>"
    )
    assert ("Rate", "12%") in _rows(table)


def test_n1_stacked_header_rows_are_combined() -> None:
    _, (table,) = _parse(
        '<table><tr><th rowspan="2">Term</th><th colspan="2">Rate</th></tr>'
        "<tr><th>AMD</th><th>USD</th></tr>"
        "<tr><td>12 months</td><td>12%</td><td>8%</td></tr></table>"
    )
    assert table.headers == ("Term", "Rate / AMD", "Rate / USD")
    assert _rows(table) == [("12 months", "12%", "8%")]


# --- N2: section rows inside a table ------------------------------------------


def test_n2_section_rows_label_the_rows_under_them() -> None:
    _, (table,) = _parse(
        "<table><tr><th>Item</th><th>Value</th></tr>"
        '<tr><td colspan="2">AMD loans</td></tr><tr><td>Fee</td><td>0%</td></tr>'
        '<tr><td colspan="2">USD loans</td></tr><tr><td>Fee</td><td>0%</td></tr>'
        "<tr><td>Rate</td><td>9%</td></tr></table>"
    )
    assert [(row.section, *(c.text for c in row.cells)) for row in table.rows] == [
        ("AMD loans", "Fee", "0%"),
        ("USD loans", "Fee", "0%"),
        ("USD loans", "Rate", "9%"),
    ]
    assert table.notes == ()


# --- N3 and N10: notes ---------------------------------------------------------


def test_n3_note_starting_with_an_amount_keeps_it() -> None:
    _, (table,) = _parse(
        "<table><tr><th>Item</th><th>Value</th></tr>"
        "<tr><td>Rate</td><td>12%¹</td></tr>"
        '<tr><td colspan="2">5 000 000 AMD is the maximum amount for unsecured '
        "loans, see the tariff sheet for details</td></tr>"
        '<tr><td colspan="2">¹ Fixed for the first year</td></tr></table>'
    )
    notes = {(note.marker, note.text) for note in table.notes}
    assert (
        None,
        "5 000 000 AMD is the maximum amount for unsecured loans, "
        "see the tariff sheet for details",
    ) in notes
    assert ("1", "Fixed for the first year") in notes


def test_n10_title_row_is_not_repeated_as_a_note() -> None:
    _, (table,) = _parse(
        '<table><caption>Tariffs</caption><tr><td colspan="2">Consumer loan tariffs</td></tr>'
        "<tr><th>Item</th><th>Value</th></tr><tr><td>Rate</td><td>12%</td></tr></table>"
    )
    assert table.title is not None and "Consumer loan tariffs" in table.title
    assert "Tariffs" in table.title
    assert all(note.text != "Consumer loan tariffs" for note in table.notes)


# --- N9: single-column tables ---------------------------------------------------


def test_n9_single_column_table_has_rows() -> None:
    _, (table,) = _parse(
        "<table><tr><th>Loan conditions</th></tr><tr><td>Rate 12%</td></tr>"
        "<tr><td>Term up to 60 months</td></tr></table>"
    )
    assert _rows(table) == [("Rate 12%",), ("Term up to 60 months",)]
    assert table.notes == ()


# --- N13: list items ---------------------------------------------------------------


def test_n13_decimals_and_dates_are_not_list_items() -> None:
    _, (table,) = _parse(
        "<table><tr><th>Item</th><th>Value</th></tr>"
        "<tr><td>Rate</td><td>12.5% annual</td></tr>"
        "<tr><td>Effective</td><td>01.03.2025</td></tr></table>"
    )
    assert all(not cell.list_items for row in table.rows for cell in row.cells)


# --- N8: nested content ---------------------------------------------------------------


def test_n8_nested_table_rows_stay_in_the_nested_table() -> None:
    _, tables = _parse(
        "<table><tr><th>Product</th><th>Terms</th></tr><tr><td>Loan</td><td>"
        "<table><tr><td>AMD</td><td>12%</td></tr><tr><td>USD</td><td>8%</td></tr>"
        "</table></td></tr></table>"
    )
    outer, inner = tables
    assert len(outer.rows) == 1
    assert outer.rows[0].cells[0].text == "Loan"
    assert "AMD" not in outer.rows[0].cells[1].text
    assert _rows(inner) == [("AMD", "12%"), ("USD", "8%")]


def test_n8_nested_list_items_are_not_repeated() -> None:
    blocks, _ = _parse(
        "<ul><li>Documents<ul><li>Passport</li><li>Income 12%</li></ul></li></ul>"
    )
    assert sum("Income 12%" in text for text in _texts(blocks)) == 1


def test_n8_paragraph_inside_dd_is_not_repeated() -> None:
    blocks, _ = _parse("<dl><dt>Rate</dt><dd><p>12%</p></dd></dl>")
    assert sum("12%" in text for text in _texts(blocks)) == 1


# --- N14: dt/dd pairs -------------------------------------------------------------------


def test_n14_dt_dd_pair_is_one_key_value_block() -> None:
    blocks, _ = _parse("<dl><dt>Interest rate</dt><dd>12%</dd></dl>")
    (block,) = blocks
    assert block.fields == {"key": "Interest rate", "value": "12%"}


# --- N6: text boundaries -----------------------------------------------------------------


def test_n6_card_heading_and_body_are_separate_lines() -> None:
    blocks, _ = _parse(
        '<div class="card"><h3>Consumer loan</h3><p>Up to 5 000 000 AMD</p></div>'
    )
    (card,) = blocks
    assert card.fields == {"title": "Consumer loan", "body": "Up to 5 000 000 AMD"}


def test_n6_table_cells_do_not_merge_into_false_numbers() -> None:
    blocks, _ = _parse(
        "<h2>Rates</h2><table><tr><th>Term</th><th>Amount</th></tr>"
        "<tr><td>12</td><td>500 000 AMD</td></tr></table>"
    )
    table_block = next(block for block in blocks if block.table_id)
    values = {scalar.value for scalar in table_block.scalar_candidates}
    assert Decimal("12500000") not in values
    assert Decimal("500000") in values


# --- N7: heading scope ------------------------------------------------------------------------


def test_n7_heading_does_not_leak_into_the_next_accordion() -> None:
    blocks, _ = _parse(
        '<div class="accordion-item"><button class="accordion-header">Mortgage</button>'
        '<div class="accordion-panel"><h4>Mortgage rates</h4><p>Rate 10%</p></div></div>'
        '<div class="accordion-item"><button class="accordion-header">Consumer</button>'
        '<div class="accordion-panel"><p>Rate 18%</p></div></div>'
    )
    consumer = next(block for block in blocks if block.text == "Rate 18%")
    assert "Mortgage rates" not in consumer.heading_path
    assert consumer.heading_path == ("Consumer",)


# --- N4: bare text in a div -----------------------------------------------------------------------


def test_n4_text_directly_in_a_div_becomes_a_block() -> None:
    blocks, _ = _parse(
        '<div class="accordion-item"><div class="accordion-title">Fees</div>'
        '<div class="accordion-content">Service fee 1% of loan amount</div></div>'
    )
    assert "Service fee 1% of loan amount" in _texts(blocks)


# --- N11 and N12: scalars ---------------------------------------------------------------------------


def test_n11_iso_date_is_a_date() -> None:
    (scalar,) = extract_scalar_candidates("Effective 2024-03-01")
    assert scalar.kind is ScalarKind.DATE
    assert scalar.normalized_date == date(2024, 3, 1)


def test_n11_date_range_keeps_both_dates() -> None:
    scalars = extract_scalar_candidates("Valid 01.03.2024 - 31.12.2024")
    assert [s.normalized_date for s in scalars] == [
        date(2024, 3, 1),
        date(2024, 12, 31),
    ]


def test_n11_reversed_range_is_rejected() -> None:
    scalars = extract_scalar_candidates("between 10 - 5%")
    assert all(s.kind is not ScalarKind.RANGE for s in scalars)


def test_n12_zero_comma_three_digits_is_a_decimal() -> None:
    (scalar,) = extract_scalar_candidates("0,125%")
    assert scalar.value == Decimal("0.125")


def test_n12_line_break_ends_a_number() -> None:
    scalars = extract_scalar_candidates("Term 12\n500 000 AMD")
    assert any(s.value == Decimal("500000") and s.unit == "AMD" for s in scalars)


# --- N27, N23 and N4 details ------------------------------------------------------------------------


def test_n27_image_only_cell_reads_the_alt_text() -> None:
    _, (table,) = _parse(
        "<table><tr><th>Service</th><th>Available</th></tr>"
        '<tr><td>Online application</td><td><img src="/ok.svg" alt="Yes"></td></tr></table>'
    )
    assert _rows(table) == [("Online application", "Yes")]


def test_n23_table_blocks_name_their_table_even_after_a_skipped_table() -> None:
    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        "<html><body><table><tr><td> </td></tr></table>"
        "<table><tr><th>Item</th><th>Value</th></tr><tr><td>Rate</td><td>9%</td></tr>"
        "</table></body></html>",
        source_url=SOURCE_URL,
    )
    (block,) = [b for b in parsed.blocks if b.table_id]
    assert block.table_id in {table.id for table in parsed.tables}
    assert "| Rate | 9% |" in (parsed.markdown or "")


def test_n4_container_text_is_not_the_parent_of_blocks_inside_it() -> None:
    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        "<html><body><div>Updated on 06.08.2026<p>Rate 12%</p></div></body></html>",
        source_url=SOURCE_URL,
    )
    by_text = {block.text: block for block in parsed.blocks}
    assert by_text["Updated on 06.08.2026"].parent_id is None
    assert by_text["Rate 12%"].parent_id is None


# --- Phase 2 details: sections, notes, titles, warnings ---------------------------------------------


def test_n2_sub_section_label_ends_with_its_carried_section() -> None:
    _, (table,) = _parse(
        '<table><tr><td rowspan="5">3. Loan terms</td><td>3.1. Currency</td><td>AMD</td></tr>'
        '<tr><td colspan="2">Term and interest rate</td></tr>'
        "<tr><td>3.4. Rate</td><td>13.5%</td></tr>"
        "<tr><td>3.5. APR</td><td>14.39%</td></tr>"
        "<tr><td>3.6. Fee</td><td>1%</td></tr>"
        "<tr><td>4. Repayment</td><td>4.1. Method</td><td>Annuity</td></tr></table>"
    )
    sections = {row.cells[1].text: row.section for row in table.rows}
    assert sections["3.1. Currency"] is None
    assert sections["3.4. Rate"] == "Term and interest rate"
    assert sections["3.6. Fee"] == "Term and interest rate"
    assert sections["4.1. Method"] is None


def test_n2_value_under_a_carried_item_is_not_a_label() -> None:
    _, (table,) = _parse(
        '<table><tr><td rowspan="3">3. Loan terms</td><td rowspan="2">3.4. Rate</td>'
        "<td>Adjustable fixed</td></tr><tr><td>Fixed component 5%</td></tr>"
        "<tr><td>3.5. APR</td><td>14%</td></tr></table>"
    )
    assert all(row.section is None for row in table.rows)
    assert any("Fixed component 5%" in row.cells[2].text for row in table.rows)


def test_n2_label_with_no_rows_under_it_is_a_note() -> None:
    _, (table,) = _parse(
        "<table><tr><th>Item</th><th>Value</th></tr><tr><td>Fee</td><td>0%</td></tr>"
        '<tr><td colspan="2">Subject to change</td></tr></table>'
    )
    assert [note.text for note in table.notes] == ["Subject to change"]
    assert table.rows[0].section is None


@pytest.mark.parametrize(
    ("text", "marker", "body"),
    [
        ("1These terms apply", "1", "These terms apply"),
        ("5This service is available", "5", "This service is available"),
        ("²Depending on the borrower", "2", "Depending on the borrower"),
        ("* Previously known as", "*", "Previously known as"),
        ("5 000 000 AMD is the maximum", None, "5 000 000 AMD is the maximum"),
        ("12 months is the maximum term", None, "12 months is the maximum term"),
        ("1. Express Home Purchase Loan", None, "1. Express Home Purchase Loan"),
    ],
)
def test_n3_footnote_markers(text: str, marker: str | None, body: str) -> None:
    from app.services.table_normalizer import _split_note

    assert _split_note(text) == (marker, body)


def test_n10_title_keeps_the_longer_of_two_matching_parts() -> None:
    from app.services.table_normalizer import _join_titles

    assert (
        _join_titles(
            [
                "Express Home Purchase Loan (primary market)",
                None,
                "1. Express Home Purchase Loan (primary market)",
            ]
        )
        == "1. Express Home Purchase Loan (primary market)"
    )
    assert _join_titles(["Tariffs", None, "Home Purchase Loan"]) == (
        "Tariffs — Home Purchase Loan"
    )


@pytest.mark.asyncio
async def test_n24_invented_headers_and_dropped_rows_are_reported() -> None:
    from datetime import UTC, datetime
    from pathlib import Path

    from app.domain.acquisition import (
        AcquisitionInventory,
        AcquisitionMode,
        PageArtifact,
    )
    from app.domain.normalization import NormalizationWarningCode
    from app.services.artifact_store import FileSystemArtifactStore
    from app.services.normalization import (
        NoPdfExtractor,
        StructuralNormalizationService,
    )

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        "<html><body><table><tr><td>Fee</td><td>0%</td></tr>"
        "<tr><td>Fee</td><td>0%</td></tr></table></body></html>",
        source_url=SOURCE_URL,
    )
    artifact = PageArtifact(
        url=SOURCE_URL,
        canonical_url=SOURCE_URL,
        final_url=SOURCE_URL,
        acquisition_mode=AcquisitionMode.BROWSER,
        raw_html=None,
        rendered_html="",
        markdown=None,
        blocks=parsed.blocks,
        tables=parsed.tables,
        links=(),
        downloadable_documents=(),
        retrieved_at=datetime.now(UTC),
        inventory=AcquisitionInventory(main_chars=0, tables=1, pdf_links=0),
        content_hash="a" * 64,
        page_content_hash="b" * 64,
    )
    bundle = await StructuralNormalizationService(
        artifact_reader=FileSystemArtifactStore(Path(".")),
        pdf_extractor=NoPdfExtractor(),
    ).normalize(artifact)
    (warning,) = bundle.warnings
    assert warning.code is NormalizationWarningCode.AMBIGUOUS_TABLE
    assert warning.source_id == f"page:{'b' * 16}:t1"
    assert "headers invented" in warning.message
    assert "repeats the row above" in warning.message
    assert len(bundle.documents[0].tables[0].rows) == 1


def test_n4_container_text_claims_only_its_own_links() -> None:
    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        '<html><body><div>ATTENTION! Read the terms. <a href="/a.pdf">Notice</a>'
        '<ul><li><a href="/terms.pdf">Terms</a></li></ul></div></body></html>',
        source_url=SOURCE_URL,
    )
    by_text = {block.text: block for block in parsed.blocks}
    links = {link.id: link.url.path for link in parsed.links}
    container = next(b for t, b in by_text.items() if t.startswith("ATTENTION"))
    assert [links[i] for i in container.link_ids] == ["/a.pdf"]
    assert [links[i] for i in by_text["Terms"].link_ids] == ["/terms.pdf"]


@pytest.mark.parametrize(
    ("text", "value", "unit"),
    [
        ("1,000 AMD", Decimal("1000"), "AMD"),
        ("1 000,50 AMD", Decimal("1000.50"), "AMD"),
        ("12,5%", Decimal("12.5"), "percent"),
        ("5\u00a0000\u00a0000 AMD", Decimal("5000000"), "AMD"),
    ],
)
def test_n12_number_forms(text: str, value: Decimal, unit: str) -> None:
    (scalar,) = extract_scalar_candidates(text)
    assert (scalar.value, scalar.unit) == (value, unit)


def test_n11_day_month_name_date() -> None:
    (scalar,) = extract_scalar_candidates("effective from 1 July 2026")
    assert scalar.normalized_date == date(2026, 7, 1)


# --- Phase 5: evidence text ---------------------------------------------------------------------------


def test_evidence_carries_row_sections_note_markers_and_a_real_section() -> None:
    from app.domain.normalization import NormalizedDocument, NormalizedSourceBundle
    from app.domain.source_discovery import SourceDiscoveryResult
    from app.services.extraction_evidence import build_evidence_catalog
    from tests.unit.test_semantic_extraction import _fixture

    blocks, (table,) = _parse(
        "<h2>Terms and conditions</h2><table><tr><th>Item</th><th>Value</th></tr>"
        '<tr><td colspan="2">USD loans</td></tr><tr><td>Rate</td><td>12%¹</td></tr>'
        '<tr><td colspan="2">¹ Fixed for the first year</td></tr></table>'
    )
    _, discovery = _fixture()
    assessment = discovery.assessments[0]
    document = NormalizedDocument(
        id="page",
        name="Loan",
        source_url=SOURCE_URL,
        source_type="page",
        mime_type="text/html",
        content_sha256="c" * 64,
        extraction_method="browser",
        blocks=tuple(blocks),
        tables=(table,),
    )
    discovery = SourceDiscoveryResult.model_validate(
        {
            **discovery.model_dump(),
            "assessments": [
                {
                    **assessment.model_dump(),
                    "source_refs": [table.source_refs[0].model_dump()],
                    "member_source_ids": [],
                }
            ],
        }
    )
    evidence = build_evidence_catalog(
        NormalizedSourceBundle(
            canonical_url=SOURCE_URL,
            acquisition_content_hash="d" * 64,
            documents=(document,),
        ),
        discovery,
    )
    row = next(item for item in evidence if "Rate" in item.content)
    note = next(item for item in evidence if "Fixed for the first year" in item.content)
    assert row.content.startswith("Section: USD loans\n")
    assert note.content == "¹ Fixed for the first year"
    assert row.section == "Terms and conditions"
