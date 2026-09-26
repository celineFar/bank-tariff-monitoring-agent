import json
from datetime import UTC, datetime

from app.domain.acquisition import (
    AcquisitionInventory,
    AcquisitionMode,
    ContentBlock,
    ContentBlockType,
    PageArtifact,
    SourceLocator,
    SourceType,
)
from scripts.demonstrate_acquisition import write_inspection_bundle


def test_writes_manual_inspection_bundle_under_one_output_directory(tmp_path) -> None:
    requested_url = "https://ameriabank.am/en/loan"
    locator = SourceLocator(
        source_url=requested_url,
        source_type=SourceType.PAGE,
        block_id="b1",
        css_selector="body > p:nth-of-type(1)",
        xpath="/html[1]/body[1]/p[1]",
    )
    artifact = PageArtifact(
        url=requested_url,
        canonical_url=requested_url,
        final_url=requested_url,
        title="Սպառողական վարկ",
        language="hy",
        acquisition_mode=AcquisitionMode.STATIC,
        raw_html="<html><body><p>Տոկոս 13%</p></body></html>",
        rendered_html=None,
        markdown="Տոկոս 13%",
        blocks=(
            ContentBlock(
                id="b1",
                type=ContentBlockType.PARAGRAPH,
                text="Տոկոս 13%",
                locator=locator,
                visible=True,
            ),
        ),
        tables=(),
        links=(),
        downloadable_documents=(),
        retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
        inventory=AcquisitionInventory(main_chars=0, tables=0, pdf_links=0),
        content_hash="a" * 64,
        page_content_hash="b" * 64,
    )
    inspection_directory = tmp_path / ".temp" / "acuisition_test"

    output_directory = write_inspection_bundle(
        artifact,
        requested_url=requested_url,
        inspection_directory=inspection_directory,
    )

    assert {path.name for path in inspection_directory.iterdir()} == {
        "source_url.txt",
        "output",
    }
    assert output_directory == inspection_directory / "output"
    assert (inspection_directory / "source_url.txt").read_text(
        encoding="utf-8"
    ) == f"{requested_url}\n"
    assert (
        (output_directory / "raw.html").read_text(encoding="utf-8").startswith("<html>")
    )
    assert (output_directory / "page.md").read_text(encoding="utf-8") == ("Տոկոս 13%")
    blocks = json.loads((output_directory / "blocks.json").read_text(encoding="utf-8"))
    assert blocks[0]["text"] == "Տոկոս 13%"
    assert "Blocks: 1" in (output_directory / "summary.txt").read_text(encoding="utf-8")
