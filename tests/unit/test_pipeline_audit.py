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

    assert "-Rate: 13%" in report
    assert "+Rate: 13.5%" in report
    assert "acquired-or-reconstructed" in report
    assert "normalized" in report


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
