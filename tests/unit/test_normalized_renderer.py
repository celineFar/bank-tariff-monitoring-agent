from app.domain.acquisition import SourceLocator, SourceType
from app.domain.normalization import (
    NormalizedDocument,
    NormalizedSourceBundle,
    NormalizedTable,
    NormalizedTableCell,
    NormalizedTableRow,
    SourceReference,
)
from app.services.normalized_renderer import render_normalized_markdown


def test_renderer_escapes_table_delimiters_and_preserves_links() -> None:
    source_url = "https://ameriabank.am/loan"
    reference = SourceReference(
        source_item_id="c1",
        locator=SourceLocator(source_url=source_url, source_type=SourceType.PAGE),
    )
    table = NormalizedTable(
        id="t1",
        headers=("Item", "Terms"),
        rows=(
            NormalizedTableRow(
                id="r1",
                cells=(
                    NormalizedTableCell(
                        raw_text="A | B",
                        text="A | B",
                        source_refs=(reference,),
                    ),
                    NormalizedTableCell(
                        raw_text="Details",
                        text="Details",
                        markdown="[Details](https://ameriabank.am/terms)\nnext",
                        source_refs=(reference,),
                    ),
                ),
            ),
        ),
        source_refs=(reference,),
    )
    document = NormalizedDocument(
        id="page:1",
        name="Loan *terms*",
        source_url=source_url,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256="a" * 64,
        extraction_method="browser",
        tables=(table,),
    )
    bundle = NormalizedSourceBundle(
        canonical_url=source_url,
        acquisition_content_hash="a" * 64,
        documents=(document,),
    )

    markdown = render_normalized_markdown(bundle)

    assert "# Loan \\*terms\\*" in markdown
    assert "| A \\| B | [Details](https://ameriabank.am/terms)<br>next |" in markdown
