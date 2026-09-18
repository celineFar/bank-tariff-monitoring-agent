from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from io import BytesIO

import pytest
from pydantic import ValidationError
from pypdf import PdfWriter

from app.config import PdfExtractionSettings, SourceDiscoverySettings
from app.domain.acquisition import DocumentArtifact, StoredArtifact
from app.domain.models import ProductType
from app.domain.normalization import NormalizedSourceBundle
from app.domain.pdf_extraction import (
    PdfAdmissionRelevance,
    PdfExtractedBlock,
    PdfExtractedBlockType,
    PdfExtractedPage,
    PdfExtractedTable,
    PdfExtractedTableRow,
    PdfExtractionResponse,
    PdfInputMode,
    PdfModelExtractionResponse,
    PdfModelItem,
    PdfModelItemKind,
    PdfTemporalStatus,
)
from app.domain.source_discovery import ProductAssociation, TemporalStatus
from app.repositories.file_pdf_extraction import FileSystemPdfExtractionRepository
from app.services.gemini_pdf_extractor import _to_domain_response
from app.services.pdf_admission import assess_pdf_metadata
from app.services.pdf_extraction import (
    GeminiPdfExtractionService,
    InMemoryPdfExtractionRepository,
)
from app.services.pdf_input_probe import probe_pdf_input
from app.services.source_discovery import (
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)


def _blank_pdf() -> bytes:
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(stream)
    return stream.getvalue()


def _document(
    content: bytes,
    *,
    link_text: str = "Consumer loan terms",
    heading_path: tuple[str, ...] = ("Loan terms",),
    nearby_text: str = "",
    final_url: str = "https://ameriabank.am/terms.pdf",
) -> DocumentArtifact:
    checksum = hashlib.sha256(content).hexdigest()
    return DocumentArtifact(
        source_url=final_url,
        final_url=final_url,
        document_name=link_text,
        mime_type="application/pdf",
        size_bytes=len(content),
        sha256=checksum,
        retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
        artifact=StoredArtifact(
            role="linked_document",
            sha256=checksum,
            size_bytes=len(content),
            media_type="application/pdf",
            relative_path=f"{checksum[:2]}/{checksum}.pdf",
        ),
        link_text=link_text,
        origin_heading_path=heading_path,
        nearby_text=nearby_text,
    )


def test_metadata_admission_separates_relevance_from_currentness() -> None:
    document = _document(
        _blank_pdf(),
        heading_path=("Previous terms",),
        final_url="https://ameriabank.am/previous-loans/consumer-loan.pdf",
    )

    admission = assess_pdf_metadata(document, as_of=date(2026, 9, 18))

    assert admission.relevance is PdfAdmissionRelevance.RELEVANT
    assert admission.temporal_status is PdfTemporalStatus.HISTORICAL
    assert "content discovery is unnecessary" in admission.reason


@pytest.mark.parametrize(
    ("period", "expected"),
    (
        ("Terms from 01.01.2026 to 31.12.2026", PdfTemporalStatus.CURRENT),
        ("Terms from 01.01.2024 to 31.12.2024", PdfTemporalStatus.HISTORICAL),
        ("Terms from 01.01.2027 to 31.12.2027", PdfTemporalStatus.FUTURE),
    ),
)
def test_explicit_link_context_controls_temporal_status(
    period: str, expected: PdfTemporalStatus
) -> None:
    admission = assess_pdf_metadata(
        _document(_blank_pdf(), nearby_text=period), as_of=date(2026, 9, 18)
    )

    assert admission.temporal_status is expected
    assert admission.effective_periods


def test_probe_reports_blank_pdf_as_unknown_without_using_text_downstream() -> None:
    probe = probe_pdf_input(_blank_pdf())

    assert probe.page_count == 1
    assert probe.document_mode is PdfInputMode.UNKNOWN
    assert probe.pages[0].native_text_characters == 0


def test_pdf_response_rejects_non_rectangular_tables() -> None:
    with pytest.raises(ValidationError, match="consistent width"):
        PdfExtractedTable(
            headers=("Item", "Terms"),
            rows=(PdfExtractedTableRow(cells=("Rate",)),),
        )


def test_shallow_model_response_is_converted_and_all_pages_are_retained() -> None:
    response = _to_domain_response(
        PdfModelExtractionResponse(
            items=[
                PdfModelItem(
                    page_number=1,
                    kind=PdfModelItemKind.TABLE,
                    text="",
                    heading_path=[],
                    title="Terms",
                    headers=["Item", "Value"],
                    rows=[["Currency", "AMD"]],
                    notes=["Applies from approval."],
                ),
                PdfModelItem(
                    page_number=1,
                    kind=PdfModelItemKind.NOTE,
                    text="Footnote 1",
                    heading_path=[],
                    title="",
                    headers=[],
                    rows=[],
                    notes=[],
                ),
            ]
        ),
        page_count=2,
    )

    assert tuple(page.page_number for page in response.pages) == (1, 2)
    assert response.pages[0].tables[0].rows[0].cells == ("Currency", "AMD")
    assert response.pages[0].notes == ("Footnote 1",)
    assert response.pages[1].blocks == ()


def test_shallow_model_response_repairs_ragged_rows_without_losing_cells() -> None:
    response = _to_domain_response(
        PdfModelExtractionResponse(
            items=[
                PdfModelItem(
                    page_number=1,
                    kind=PdfModelItemKind.TABLE,
                    text="",
                    heading_path=[],
                    title="Terms",
                    headers=["Item", "Value"],
                    rows=[["Section"], ["Currency", "AMD", "Condition"]],
                    notes=[],
                )
            ]
        ),
        page_count=1,
    )

    table = response.pages[0].tables[0]
    assert table.headers == ("Item", "Value", "Column 3")
    assert table.rows[0].cells == ("Section", "", "")
    assert table.rows[1].cells == ("Currency", "AMD", "Condition")


@pytest.mark.asyncio
async def test_file_pdf_cache_reuses_an_exact_response(tmp_path) -> None:
    repository = FileSystemPdfExtractionRepository(tmp_path)
    response = PdfExtractionResponse(
        pages=(PdfExtractedPage(page_number=1),)
    )
    keys = {
        "document_sha256": "a" * 64,
        "schema_version": "2",
        "prompt_version": "2",
        "model_name": "gemini-3.1-flash-lite",
        "content_fingerprint": "b" * 64,
    }

    await repository.save(**keys, response=response)

    assert await repository.get_exact(**keys) == response


@pytest.mark.asyncio
async def test_cached_gemini_response_becomes_page_addressable_normalized_data() -> None:
    content = _blank_pdf()
    document = _document(content)
    repository = InMemoryPdfExtractionRepository()
    service = GeminiPdfExtractionService(
        PdfExtractionSettings(fallback_model_names=()),
        repository,
        api_key="fixture-key",
    )
    plan = service.plan(document, content, document_id="document:0")
    response = PdfExtractionResponse(
        pages=(
            PdfExtractedPage(
                page_number=1,
                blocks=(
                    PdfExtractedBlock(
                        type=PdfExtractedBlockType.HEADING,
                        text="Consumer loan terms",
                    ),
                ),
                tables=(
                    PdfExtractedTable(
                        title="Loan terms",
                        headers=("Section", "Item", "Terms"),
                        rows=(
                            PdfExtractedTableRow(
                                cells=("Loan terms", "Currency", "AMD")
                            ),
                        ),
                        notes=("1. Effective annual rate depends on the term.",),
                    ),
                ),
                notes=("2. Applies to applications submitted online.",),
            ),
        )
    )
    await repository.save(
        document_sha256=document.sha256,
        schema_version=plan.schema_version,
        prompt_version=plan.prompt_version,
        model_name=plan.model_names[0],
        content_fingerprint=plan.content_fingerprint,
        response=response,
    )

    outcome = await service.extract(
        document, content, document_id="document:0"
    )

    assert outcome.reused is True
    assert outcome.normalized_document.extraction_method.startswith("gemini_pdf:")
    assert outcome.normalized_document.blocks[0].source_refs[0].locator.pdf_page == 1
    assert outcome.normalized_document.blocks[1].text.startswith("2. Applies")
    table = outcome.normalized_document.tables[0]
    assert table.headers == ("Section", "Item", "Terms")
    assert tuple(cell.text for cell in table.rows[0].cells) == (
        "Loan terms",
        "Currency",
        "AMD",
    )
    assert table.notes[0].source_refs[0].locator.pdf_page == 1


@pytest.mark.asyncio
async def test_relevant_historical_pdf_skips_discovery_llm_but_not_temporal_rules() -> None:
    content = _blank_pdf()
    document = _document(
        content,
        heading_path=("Previous terms",),
        final_url="https://ameriabank.am/previous-loans/consumer-loan.pdf",
    )
    pdf_repository = InMemoryPdfExtractionRepository()
    pdf_service = GeminiPdfExtractionService(
        PdfExtractionSettings(fallback_model_names=()),
        pdf_repository,
        api_key="fixture-key",
    )
    plan = pdf_service.plan(document, content, document_id="document:0")
    await pdf_repository.save(
        document_sha256=document.sha256,
        schema_version=plan.schema_version,
        prompt_version=plan.prompt_version,
        model_name=plan.model_names[0],
        content_fingerprint=plan.content_fingerprint,
        response=PdfExtractionResponse(
            pages=(
                PdfExtractedPage(
                    page_number=1,
                    blocks=(
                        PdfExtractedBlock(
                            type=PdfExtractedBlockType.PARAGRAPH,
                            text="Historical rate: 18%",
                        ),
                    ),
                ),
            )
        ),
    )
    outcome = await pdf_service.extract(
        document, content, document_id="document:0"
    )
    bundle = NormalizedSourceBundle(
        canonical_url="https://ameriabank.am/loan",
        acquisition_content_hash="a" * 64,
        documents=(outcome.normalized_document,),
    )
    discovery = SourceDiscoveryService(
        None,
        InMemorySourceDiscoveryRepository(),
        SourceDiscoverySettings(),
        model_name="configured-model",
    )

    discovery_plan = await discovery.plan(bundle, ProductType.CONSUMER_LOAN)
    result = await discovery.discover(bundle, ProductType.CONSUMER_LOAN)

    assert discovery_plan.llm_candidates == ()
    direct = discovery_plan.deterministic_assessments[0]
    assert direct.product_association is ProductAssociation.HISTORICAL_VERSION
    assert direct.temporal_status is TemporalStatus.POSSIBLY_STALE
    assert result.extraction_context.items == ()
