from __future__ import annotations

from app.domain.pdf_extraction import (
    PdfExtractedBlock,
    PdfExtractedBlockType,
    PdfExtractedPage,
    PdfExtractionResponse,
)
from app.services.pipeline_audit import (
    human_filename,
    render_diff_markdown,
    render_pdf_response_markdown,
)
from scripts.demonstrate_end_to_end import _next_run_directory


def test_human_filename_is_readable_and_cannot_escape_directory() -> None:
    assert (
        human_filename(
            "../Mortgage terms: primary market.pdf", index=1, extension=".pdf"
        )
        == "002_Mortgage_terms_primary_market.pdf"
    )


def test_diff_report_labels_source_and_normalized_changes() -> None:
    report = render_diff_markdown(
        "Normalization",
        (("Page", "Rate: 13%\n", "Rate: 13.5%\n"),),
    )

    assert "<del>13%</del>" in report
    assert "<ins>13.5%</ins>" in report
    assert "```diff" not in report
    assert "normalized document itself" in report


def test_pdf_response_markdown_keeps_page_and_block_text() -> None:
    response = PdfExtractionResponse(
        pages=(
            PdfExtractedPage(
                page_number=2,
                blocks=(
                    PdfExtractedBlock(
                        type=PdfExtractedBlockType.PARAGRAPH,
                        text="Loan amount AMD 30 million",
                    ),
                ),
            ),
        )
    )

    markdown = render_pdf_response_markdown(
        "Mortgage terms", "https://ameriabank.am/terms.pdf", response
    )

    assert "## PDF page 2" in markdown
    assert "Loan amount AMD 30 million" in markdown
    assert "https://ameriabank.am/terms.pdf" in markdown


def test_end_to_end_runs_use_incrementing_directories(tmp_path) -> None:
    root = tmp_path / "end-to-end"
    first = _next_run_directory(root)
    second = _next_run_directory(root)
    (root / "run_010").mkdir()
    after_gap = _next_run_directory(root)

    assert first.name == "run_001"
    assert second.name == "run_002"
    assert after_gap.name == "run_011"
    assert first.is_dir()
    assert second.is_dir()
