import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from app.domain.discovery import IngestedSource, SourceCandidateType, StoredArtifact
from app.domain.extraction import (
    ExtractedBlockType,
    ExtractedDocument,
    ExtractionStatus,
)
from app.services.content_extractor import (
    ContentExtractionError,
    ContentExtractionErrorCode,
    DocumentContentExtractor,
    _extract_pdf_page,
    _pdf_blocks,
)
from app.services.local_artifact_store import LocalArtifactStore

NOW = datetime(2026, 9, 17, 6, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-finance"
HTML = b"""<!doctype html>
<html lang="en">
  <body>
    <form id="Form">
    <header><p>Bank-wide header</p></header>
    <nav><a href="/other">Unrelated navigation</a></nav>
    <main id="wsc_main_content">
      <h1>Consumer finance</h1>
      <p>See the <a href="/en/terms">full terms</a>.</p>
      <div class="vertical-stack__item-info">
        <h5 class="vertical-stack__item-title">50,000 - 6,000,000 AMD</h5>
        <p class="paragraph-small">Loan amount</p>
      </div>
      <h2>Requirements</h2>
      <ul><li>Applicant must be an adult.</li><li>Proof of income.</li></ul>
      <table>
        <caption>Rates</caption>
        <tr><th>Currency</th><th>Rate</th></tr>
        <tr><td>AMD</td><td>14%</td></tr>
      </table>
      <script>throw new Error('must never be content')</script>
    </main>
    <footer><p>Bank-wide footer</p></footer>
    </form>
  </body>
</html>"""


class RecordingRepository:
    def __init__(self) -> None:
        self.saved: list[ExtractedDocument] = []

    async def save_extraction(self, extraction: ExtractedDocument) -> None:
        self.saved.append(extraction)


def _extractor(
    store: LocalArtifactStore,
    repository: RecordingRepository,
    *,
    clock=None,
) -> DocumentContentExtractor:
    return DocumentContentExtractor(
        store,
        repository,
        min_text_characters_per_page=80,
        clock=clock,
    )


async def _source(store: LocalArtifactStore, content: bytes = HTML) -> IngestedSource:
    checksum = hashlib.sha256(content).hexdigest()
    artifact = await store.put(
        content=content,
        sha256=checksum,
        mime_type="text/html",
    )
    return IngestedSource(
        product_id="consumer.finance",
        candidate_type=SourceCandidateType.PRODUCT_PAGE,
        source_url=URL,
        final_url=URL,
        retrieved_at=NOW,
        artifact=artifact,
    )


def _pdf_bytes(*page_texts: str, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    for text in page_texts:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
        )
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_metadata({"/Title": "Loan terms", "/Author": "Ameriabank"})
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _table_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    drawing = b"""
0.5 w
72 700 m 300 700 l S
72 660 m 300 660 l S
72 620 m 300 620 l S
72 700 m 72 620 l S
180 700 m 180 620 l S
300 700 m 300 620 l S
BT /F1 12 Tf 82 678 Td (Currency) Tj ET
BT /F1 12 Tf 190 678 Td (Rate) Tj ET
BT /F1 12 Tf 82 638 Td (AMD) Tj ET
BT /F1 12 Tf 190 638 Td (14 percent) Tj ET
BT /F1 12 Tf 72 580 Td (Additional loan terms provide sufficient extracted text for this digital PDF page.) Tj ET
"""
    stream = DecodedStreamObject()
    stream.set_data(drawing)
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


async def _pdf_source(store: LocalArtifactStore, content: bytes) -> IngestedSource:
    checksum = hashlib.sha256(content).hexdigest()
    artifact = await store.put(
        content=content,
        sha256=checksum,
        mime_type="application/pdf",
    )
    return IngestedSource(
        product_id="consumer.finance",
        candidate_type=SourceCandidateType.DOCUMENT,
        source_url=f"{URL}/terms.pdf",
        final_url=f"{URL}/terms.pdf",
        language="en",
        retrieved_at=NOW,
        artifact=artifact,
    )


@pytest.mark.asyncio
async def test_extracts_saved_html_to_stable_structured_json(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    repository = RecordingRepository()
    source = await _source(store)
    extractor = _extractor(store, repository, clock=lambda: NOW)

    first = await extractor.extract(source)
    repeated = await extractor.extract(source)

    assert first.language == "en"
    assert first.representation_artifact.storage_key.startswith("extracted/")
    assert first.representation_artifact.storage_key.endswith(".json")
    assert (
        repeated.representation_artifact.sha256 == first.representation_artifact.sha256
    )
    assert repeated.representation_artifact.created is False
    assert [block.block_id for block in repeated.blocks] == [
        block.block_id for block in first.blocks
    ]
    assert len(repository.saved) == 2

    block_types = [block.block_type for block in first.blocks]
    assert block_types == [
        ExtractedBlockType.HEADING,
        ExtractedBlockType.PARAGRAPH,
        ExtractedBlockType.FACT,
        ExtractedBlockType.HEADING,
        ExtractedBlockType.LIST_ITEM,
        ExtractedBlockType.LIST_ITEM,
        ExtractedBlockType.TABLE,
    ]
    fact = first.blocks[2]
    assert fact.label == "Loan amount"
    assert fact.text == "50,000 - 6,000,000 AMD"
    assert fact.section == ("Consumer finance",)
    assert fact.source_locator.css_path == "main#wsc_main_content > div"
    assert first.blocks[1].links[0].target == "https://ameriabank.am/en/terms"
    assert first.blocks[-1].table is not None
    assert first.blocks[-1].table.rows[1].cells == ("AMD", "14%")
    assert all("header" not in block.text.casefold() for block in first.blocks)
    assert all("footer" not in block.text.casefold() for block in first.blocks)
    assert first.statistics.block_count == 7
    assert first.statistics.table_row_count == 2
    assert first.statistics.link_count == 1

    payload = json.loads(await store.read(first.representation_artifact.storage_key))
    assert payload["source_sha256"] == source.artifact.sha256
    assert payload["blocks"][2]["block_type"] == "fact"
    assert payload["blocks"][2]["label"] == "Loan amount"
    assert "representation_artifact" not in payload
    assert "extracted_at" not in payload


@pytest.mark.asyncio
async def test_same_raw_bytes_with_different_provenance_get_distinct_artifacts(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    repository = RecordingRepository()
    first_source = await _source(store)
    second_source = first_source.model_copy(
        update={
            "product_id": "consumer.unsecured",
            "source_url": f"{URL}?origin=shared-document",
            "final_url": f"{URL}?origin=shared-document",
        }
    )
    extractor = _extractor(store, repository, clock=lambda: NOW)

    first = await extractor.extract(first_source)
    second = await extractor.extract(second_source)

    assert first.source_sha256 == second.source_sha256
    assert first.extraction_id != second.extraction_id
    assert (
        first.representation_artifact.storage_key
        != second.representation_artifact.storage_key
    )
    assert first.representation_artifact.created is True
    assert second.representation_artifact.created is True


@pytest.mark.asyncio
async def test_rejects_source_when_saved_bytes_do_not_match_metadata(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    source = await _source(store)
    tampered = source.model_copy(
        update={
            "artifact": StoredArtifact(
                storage_key=source.artifact.storage_key,
                sha256="0" * 64,
                mime_type="text/html",
                size_bytes=source.artifact.size_bytes,
                created=False,
            )
        }
    )
    extractor = _extractor(store, RecordingRepository())

    with pytest.raises(ContentExtractionError) as caught:
        await extractor.extract(tampered)

    assert caught.value.code is ContentExtractionErrorCode.ARTIFACT_INTEGRITY


@pytest.mark.asyncio
async def test_rejects_unregistered_mime_type(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    content = b"binary"
    checksum = hashlib.sha256(content).hexdigest()
    artifact = await store.put(
        content=content,
        sha256=checksum,
        mime_type="application/octet-stream",
    )
    source = IngestedSource(
        product_id="consumer.finance",
        candidate_type=SourceCandidateType.DOCUMENT,
        source_url=f"{URL}/terms.pdf",
        final_url=f"{URL}/terms.pdf",
        retrieved_at=NOW,
        artifact=artifact,
    )

    with pytest.raises(ContentExtractionError) as caught:
        await _extractor(store, RecordingRepository()).extract(source)

    assert caught.value.code is ContentExtractionErrorCode.UNSUPPORTED_MIME_TYPE


@pytest.mark.asyncio
async def test_extracts_pdf_page_by_page_and_persists_stable_json(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    repository = RecordingRepository()
    content = _pdf_bytes(
        "Loan amount is AMD 50,000 to AMD 6,000,000. "
        "This paragraph contains enough public tariff text for deterministic extraction.",
        "Interest rates and repayment conditions are described on this second page. "
        "Additional wording keeps this page above the OCR text threshold.",
    )
    source = await _pdf_source(store, content)

    first = await _extractor(store, repository, clock=lambda: NOW).extract(source)
    repeated = await _extractor(store, repository, clock=lambda: NOW).extract(source)

    assert first.status is ExtractionStatus.SUCCESS
    assert first.statistics.page_count == 2
    assert first.statistics.block_count == 2
    assert first.statistics.text_character_count > 160
    assert first.pages[0].page_number == 1
    assert first.pages[0].width == 612
    assert first.pages[0].height == 792
    assert first.pages[0].blocks[0].source_locator.page == 1
    assert "50,000" in first.pages[0].blocks[0].text
    assert first.pdf_metadata is not None
    assert first.pdf_metadata.title == "Loan terms"
    assert first.pdf_metadata.author == "Ameriabank"
    assert first.ocr.pages_requiring_ocr == ()
    assert first.representation_artifact.storage_key == (
        f"extracted/{source.artifact.sha256[:2]}/{source.artifact.sha256}-"
        f"pdfplumber-1.1-{first.extraction_id}.json"
    )
    assert repeated.representation_artifact.created is False

    payload = json.loads(await store.read(first.representation_artifact.storage_key))
    assert payload["pages"][0]["page_number"] == 1
    assert payload["pages"][0]["text_character_count"] > 80
    assert payload["status"] == "success"


@pytest.mark.asyncio
async def test_marks_low_text_pdf_page_for_later_ocr(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    source = await _pdf_source(store, _pdf_bytes("Short scan label"))

    result = await _extractor(store, RecordingRepository()).extract(source)

    assert result.status is ExtractionStatus.NEEDS_OCR
    assert result.ocr.pages_requiring_ocr == (1,)
    assert result.ocr.reason == "insufficient_text"
    assert result.ocr.page_reasons == {1: ("insufficient_text",)}
    assert result.pages[0].needs_ocr is True


@pytest.mark.asyncio
async def test_extracts_pdf_table_rows_and_cells(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    source = await _pdf_source(store, _table_pdf_bytes())

    result = await _extractor(store, RecordingRepository()).extract(source)

    assert result.statistics.table_count == 1
    assert result.statistics.table_row_count == 2
    table = result.pages[0].tables[0]
    assert table.table.rows[0].cells == ("Currency", "Rate")
    assert table.table.rows[1].cells == ("AMD", "14 percent")
    assert table.source_locator.page == 1
    assert table.source_locator.bounding_box is not None


@pytest.mark.asyncio
async def test_rejects_encrypted_pdf(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    source = await _pdf_source(store, _pdf_bytes("Secret", encrypted=True))

    with pytest.raises(ContentExtractionError) as caught:
        await _extractor(store, RecordingRepository()).extract(source)

    assert caught.value.code is ContentExtractionErrorCode.ENCRYPTED_PDF


@pytest.mark.asyncio
async def test_reports_a_truly_empty_pdf_page_without_requesting_ocr(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    source = await _pdf_source(store, _pdf_bytes(""))

    result = await _extractor(store, RecordingRepository()).extract(source)

    assert result.status is ExtractionStatus.SUCCESS
    assert result.statistics.empty_page_count == 1
    assert result.pages[0].is_empty is True
    assert result.pages[0].is_scanned is False
    assert result.pages[0].needs_ocr is False
    assert result.warnings[0].code == "empty_page"


@pytest.mark.asyncio
async def test_rejects_malformed_pdf(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    source = await _pdf_source(store, b"%PDF-1.7\nnot a complete PDF")

    with pytest.raises(ContentExtractionError) as caught:
        await _extractor(store, RecordingRepository()).extract(source)

    assert caught.value.code is ContentExtractionErrorCode.MALFORMED_PDF


def test_pdf_blocks_preserve_armenian_unicode_and_coordinates() -> None:
    text = "Վարկի գումար՝ 50,000 - 6,000,000 դրամ"  # noqa: RUF001
    blocks = _pdf_blocks(
        "a" * 64,
        1,
        [
            {
                "text": text,
                "x0": 72.0,
                "top": 50.0,
                "x1": 300.0,
                "bottom": 64.0,
                "size": 12.0,
            }
        ],
    )

    assert blocks[0].text == text
    assert blocks[0].source_locator.page == 1
    assert blocks[0].source_locator.bounding_box == (72.0, 50.0, 300.0, 64.0)


def test_image_only_page_is_marked_as_scanned_and_needing_ocr() -> None:
    class ImagePage:
        width = 612
        height = 792
        images = ({"name": "scan"},)

        @staticmethod
        def extract_words(**_kwargs):
            return []

        @staticmethod
        def find_tables():
            return []

    page, reasons = _extract_pdf_page("a" * 64, 1, ImagePage(), 80)

    assert reasons == ("image_only",)
    assert page.image_count == 1
    assert page.is_image_only is True
    assert page.is_scanned is True
    assert page.needs_ocr is True
