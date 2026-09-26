"""PDF items of the normalization fix plan: N5, N15/N16, N18, N19, N25, N26.

(fix-process/normalization/normalization-fix-plan.md)
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.config import PdfExtractionSettings
from app.domain.acquisition import (
    AcquisitionInventory,
    AcquisitionMode,
    DocumentArtifact,
    PageArtifact,
    StoredArtifact,
)
from app.domain.normalization import NormalizationWarningCode
from app.domain.pdf_extraction import (
    PdfAdmissionRelevance,
    PdfExtractedPage,
    PdfExtractedTable,
    PdfExtractedTableRow,
    PdfExtractionResponse,
    PdfTemporalStatus,
)
from app.services.acquisition import AcquisitionService
from app.services.html_parser import HtmlArtifactParser
from app.services.normalization import StructuralNormalizationService
from app.services.pdf_admission import assess_pdf_metadata
from app.services.pdf_extraction import (
    GeminiPdfExtractionService,
    InMemoryPdfExtractionRepository,
    PdfTranscriptionFailed,
    PdfUnreadable,
    _normalize,
)

DIGITAL = Path("tests/fixtures/pdfs/digital_sample.pdf")
PAGE_URL = "https://ameriabank.am/en/loans"


def _document(
    content: bytes, *, nearby_text: str = "", link_text: str = "Loan terms"
) -> DocumentArtifact:
    checksum = hashlib.sha256(content).hexdigest()
    url = "https://ameriabank.am/terms.pdf"
    return DocumentArtifact(
        source_url=url,
        final_url=url,
        document_name=link_text,
        mime_type="application/pdf",
        size_bytes=len(content),
        sha256=checksum,
        retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        artifact=StoredArtifact(
            role="linked_document",
            sha256=checksum,
            size_bytes=len(content),
            media_type="application/pdf",
            relative_path=f"{checksum[:2]}/{checksum}.pdf",
        ),
        link_text=link_text,
        nearby_text=nearby_text,
    )


def _page(document: DocumentArtifact) -> PageArtifact:
    return PageArtifact(
        url=PAGE_URL,
        canonical_url=PAGE_URL,
        final_url=PAGE_URL,
        acquisition_mode=AcquisitionMode.BROWSER,
        raw_html=None,
        rendered_html="",
        markdown=None,
        blocks=(),
        tables=(),
        links=(),
        downloadable_documents=(document,),
        retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        inventory=AcquisitionInventory(main_chars=0, tables=0, pdf_links=1),
        content_hash="a" * 64,
        page_content_hash="b" * 64,
    )


class _Reader:
    def __init__(self, content: bytes) -> None:
        self._content = content

    async def read(self, artifact: StoredArtifact) -> bytes:
        return self._content


class _Raising:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def extract(self, document, content, *, document_id):
        raise self._error


def _service() -> GeminiPdfExtractionService:
    return GeminiPdfExtractionService(
        PdfExtractionSettings(), InMemoryPdfExtractionRepository(), api_key="test-key"
    )


# --- N16: only expected failures become warnings --------------------------------


@pytest.mark.asyncio
async def test_n16_a_bug_in_the_pdf_path_fails_normalization() -> None:
    content = DIGITAL.read_bytes()
    service = StructuralNormalizationService(
        artifact_reader=_Reader(content), pdf_extractor=_Raising(KeyError("mapping"))
    )
    with pytest.raises(KeyError):
        await service.normalize(_page(_document(content)))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "code"),
    [
        (
            PdfTranscriptionFailed("all models failed"),
            NormalizationWarningCode.PDF_MODEL_FAILED,
        ),
        (PdfUnreadable("not a PDF"), NormalizationWarningCode.ARTIFACT_UNAVAILABLE),
    ],
)
async def test_n16_expected_pdf_failures_are_warnings(error, code) -> None:
    content = DIGITAL.read_bytes()
    service = StructuralNormalizationService(
        artifact_reader=_Reader(content), pdf_extractor=_Raising(error)
    )
    bundle = await service.normalize(_page(_document(content)))
    assert [warning.code for warning in bundle.warnings] == [code]


@pytest.mark.asyncio
async def test_n16_a_corrupt_file_is_unreadable_not_a_model_failure() -> None:
    content = b"%PDF-1.7 truncated"
    service = StructuralNormalizationService(
        artifact_reader=_Reader(content), pdf_extractor=_service()
    )
    bundle = await service.normalize(_page(_document(content)))
    assert [warning.code for warning in bundle.warnings] == [
        NormalizationWarningCode.ARTIFACT_UNAVAILABLE
    ]


# --- N5: a skip is reported, with its basis -----------------------------------------


@pytest.mark.asyncio
async def test_n5_a_skipped_historical_pdf_is_reported() -> None:
    content = DIGITAL.read_bytes()
    document = _document(
        content, nearby_text="Loan terms (effective from 01.01.2023 till 31.12.2023)"
    )
    service = StructuralNormalizationService(
        artifact_reader=_Reader(content), pdf_extractor=_service()
    )
    bundle = await service.normalize(_page(document))
    (warning,) = bundle.warnings
    assert warning.code is NormalizationWarningCode.PDF_SKIPPED_HISTORICAL
    assert "historical" in warning.message
    assert "effective period" in warning.message


# --- N18: pages with a text layer that came back empty ------------------------------


@pytest.mark.asyncio
async def test_n18_an_empty_text_page_is_reported() -> None:
    content = DIGITAL.read_bytes()
    document = _document(content)
    service = _service()
    plan = service.plan(
        document, content, document_id=f"document:{document.sha256[:12]}"
    )
    await service._repository.save(
        document_sha256=document.sha256,
        schema_version=plan.schema_version,
        prompt_version=plan.prompt_version,
        model_name=plan.model_names[0],
        content_fingerprint=plan.content_fingerprint,
        response=PdfExtractionResponse(
            pages=tuple(
                PdfExtractedPage(page_number=number)
                for number in range(1, plan.input_probe.page_count + 1)
            )
        ),
    )
    normalization = StructuralNormalizationService(
        artifact_reader=_Reader(content), pdf_extractor=service
    )
    bundle = await normalization.normalize(_page(document))
    (warning,) = bundle.warnings
    assert warning.code is NormalizationWarningCode.PDF_PAGE_EMPTY
    assert "1" in warning.message


# --- N19 and N25: PDF table cells --------------------------------------------------------


def test_n19_n25_pdf_cells_point_at_themselves_and_are_cleaned() -> None:
    content = DIGITAL.read_bytes()
    document = _document(content)
    plan = _service().plan(document, content, document_id="document:abc")
    response = PdfExtractionResponse(
        pages=(
            PdfExtractedPage(
                page_number=1,
                tables=(
                    PdfExtractedTable(
                        title="  Rates  ",
                        headers=("Item ", " Value"),
                        rows=(PdfExtractedTableRow(cells=("Fee", "0,125%\u00a0")),),
                    ),
                ),
            ),
            *(
                PdfExtractedPage(page_number=number)
                for number in range(2, plan.input_probe.page_count + 1)
            ),
        )
    )
    table = _normalize(document, plan, response, "gemini-test").tables[0]
    assert table.headers == ("Item", "Value")
    assert table.title == "Rates"
    cell = table.rows[0].cells[1]
    assert (
        cell.source_refs[0].source_item_id == "document:abc:page:1:table:0:row:0:cell:1"
    )
    assert cell.scalar_candidates[0].value is not None
    assert str(cell.scalar_candidates[0].value) == "0.125"


# --- N5: each link's context is its own row ----------------------------------------------


def test_n5_links_in_one_table_get_their_own_row_as_context() -> None:
    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        "<html><body><table>"
        '<tr><td>01.01.2023\u201331.12.2023</td><td><a href="/archived.pdf">Terms</a></td></tr>'
        '<tr><td>from 01.03.2025</td><td><a href="/current.pdf">Terms</a></td></tr>'
        "</table></body></html>",
        source_url=PAGE_URL,
    )
    contexts = {
        link.url.path: str(
            AcquisitionService._document_origin(parsed, link.id)["nearby_text"]
        )
        for link in parsed.links
    }
    assert "2023" not in contexts["/current.pdf"]
    assert "2023" in contexts["/archived.pdf"]
    current = _document(b"x", nearby_text=contexts["/current.pdf"], link_text="Terms")
    admission = assess_pdf_metadata(current, as_of=date(2026, 9, 26))
    assert admission.temporal_status is not PdfTemporalStatus.HISTORICAL


# --- N26: whole-word keywords ------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "relevance"),
    [
        ("Treatment of complaints", PdfAdmissionRelevance.AMBIGUOUS),
        ("Feedback form", PdfAdmissionRelevance.AMBIGUOUS),
        ("ATM locations", PdfAdmissionRelevance.IRRELEVANT),
        ("Loan service fees", PdfAdmissionRelevance.RELEVANT),
        ("Սպառողական վարկային պայմաններ", PdfAdmissionRelevance.RELEVANT),
    ],
)
def test_n26_keywords_match_whole_words(text: str, relevance) -> None:
    document = _document(b"x", link_text=text)
    document = document.model_copy(
        update={
            "final_url": "https://ameriabank.am/doc.pdf",
            "source_url": "https://ameriabank.am/doc.pdf",
        }
    )
    assert assess_pdf_metadata(document, as_of=date(2026, 9, 26)).relevance is relevance


@pytest.mark.asyncio
async def test_n21_without_an_extractor_pdfs_are_reported_as_needing_one() -> None:
    from app.services.normalization import NoPdfExtractor

    content = DIGITAL.read_bytes()
    service = StructuralNormalizationService(
        artifact_reader=_Reader(content), pdf_extractor=NoPdfExtractor()
    )
    bundle = await service.normalize(_page(_document(content)))
    assert [warning.code for warning in bundle.warnings] == [
        NormalizationWarningCode.PDF_MODEL_REQUIRED
    ]
