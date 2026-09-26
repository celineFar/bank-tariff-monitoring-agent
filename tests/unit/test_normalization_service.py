from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.acquisition import (
    AcquisitionInventory,
    AcquisitionMode,
    ContentBlock,
    ContentBlockType,
    LinkArtifact,
    PageArtifact,
    SourceLocator,
    SourceType,
    TableArtifact,
    TableCellArtifact,
)
from app.services.artifact_store import FileSystemArtifactStore
from app.services.normalization import (
    NoPdfExtractor,
    StructuralNormalizationService,
)


@pytest.mark.asyncio
async def test_service_preserves_table_and_link_relationships() -> None:
    url = "https://ameriabank.am/loan"
    locator = SourceLocator(source_url=url, source_type=SourceType.PAGE, block_id="b1")
    table = TableArtifact(
        id="t1",
        title="Terms",
        column_count=2,
        headers=("Item", "Value"),
        cells=(
            TableCellArtifact(
                id="c1",
                row_index=0,
                column_index=0,
                tag="td",
                text="Term",
                markdown="Term",
                locator=locator,
            ),
            TableCellArtifact(
                id="c2",
                row_index=0,
                column_index=1,
                tag="td",
                text="up to 60 months",
                markdown="up to 60 months",
                locator=locator,
            ),
        ),
        locator=locator,
    )
    block = ContentBlock(
        id="b1",
        type=ContentBlockType.TABLE,
        text="Term up to 60 months",
        link_ids=("l1",),
        locator=locator,
        visible=True,
    )
    link = LinkArtifact(
        id="l1",
        url=f"{url}#terms",
        raw_href="#terms",
        fragment="terms",
        text="Terms",
        same_allowlisted_source=True,
        downloadable=False,
        locator=locator,
    )
    artifact = PageArtifact(
        url=url,
        canonical_url=url,
        final_url=url,
        title="Loan",
        acquisition_mode=AcquisitionMode.BROWSER,
        raw_html=None,
        rendered_html="<table></table>",
        markdown=None,
        blocks=(block,),
        tables=(table,),
        links=(link,),
        downloadable_documents=(),
        retrieved_at=datetime.now(UTC),
        inventory=AcquisitionInventory(main_chars=0, tables=0, pdf_links=0),
        content_hash="a" * 64,
        page_content_hash="b" * 64,
    )

    bundle = await StructuralNormalizationService(
        artifact_reader=FileSystemArtifactStore(Path(".")),
        pdf_extractor=NoPdfExtractor(),
    ).normalize(artifact)

    document = bundle.documents[0]
    assert document.blocks[0].table_id == "t1"
    assert document.blocks[0].link_ids == ("l1",)
    assert document.links[0].raw_href == "#terms"
    assert document.links[0].fragment == "terms"
    assert document.tables[0].rows[0].cells[1].scalar_candidates[0].operator == "<="
