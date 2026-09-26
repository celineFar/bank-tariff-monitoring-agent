"""The scanned-PDF OCR fallback: routing, bounds, provenance, and refusal.

Every test here uses a fake transcriber, so the suite needs no tesseract
binary. The one engine-backed test is marked and skips when the engine or its
language data is absent.
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import OcrSettings, PdfExtractionSettings
from app.domain.acquisition import DocumentArtifact, StoredArtifact
from app.domain.pdf_extraction import (
    OcrPageOutcome,
    OcrPageResult,
    PdfExtractedBlock,
    PdfExtractedBlockType,
    PdfExtractedPage,
    PdfExtractionResponse,
    PdfInputMode,
    PdfTranscriptionSource,
    is_ocr_source_item,
    ocr_block_id,
)
from app.services.pdf_extraction import (
    GeminiPdfExtractionService,
    InMemoryPdfExtractionRepository,
    is_ocr_method,
)
from app.services.pdf_rasterizer import (
    PdfiumPageRasterizer,
    RasterizationResult,
    RasterizedPage,
    SkippedPage,
)

FIXTURES = Path("tests/fixtures/pdfs")
SCANNED = FIXTURES / "scanned_armenian_sample.pdf"
DIGITAL = FIXTURES / "digital_sample.pdf"


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


class FakeTranscriber:
    """Returns a scripted result per page and records what it was asked for."""

    def __init__(
        self,
        results: dict[int, OcrPageResult] | None = None,
        *,
        available: bool = True,
        engine_version: str = "5.5.0-fake",
    ) -> None:
        self.available = available
        self.engine_version = engine_version
        self._results = results or {}
        self.calls: list[int] = []

    async def transcribe(
        self,
        page: RasterizedPage,
        *,
        languages: str,
        timeout_seconds: float,
        min_confidence: float,
    ) -> OcrPageResult:
        self.calls.append(page.page_number)
        scripted = self._results.get(page.page_number)
        if scripted is not None:
            return scripted
        return OcrPageResult(
            page_number=page.page_number,
            outcome=OcrPageOutcome.TRANSCRIBED,
            text=f"Անվանական տոկոսադրույք: 13.5% (page {page.page_number})",
            mean_confidence=91.0,
            word_count=5,
        )


class FakeRasterizer:
    """Renders every requested page without touching a real PDF."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.calls: list[list[int]] = []

    def rasterize_pages(
        self,
        content: bytes,
        page_numbers,
        *,
        dpi: int,
        max_pages: int,
        max_pixels: int,
    ) -> RasterizationResult:
        requested = sorted(set(page_numbers))
        self.calls.append(list(requested))
        allowed = requested[:max_pages]
        return RasterizationResult(
            pages=tuple(
                RasterizedPage(
                    page_number=number,
                    image_png=b"\x89PNG-fake",
                    width=100,
                    height=200,
                    scale=dpi / 72.0,
                )
                for number in allowed
            ),
            skipped=tuple(
                SkippedPage(page_number=number, reason="page cap reached")
                for number in requested[max_pages:]
            ),
        )


def _document(content: bytes) -> DocumentArtifact:
    checksum = hashlib.sha256(content).hexdigest()
    url = "https://ameriabank.am/terms.pdf"
    return DocumentArtifact(
        source_url=url,
        final_url=url,
        document_name="Consumer loan information summary",
        mime_type="application/pdf",
        size_bytes=len(content),
        sha256=checksum,
        retrieved_at=datetime(2026, 9, 22, tzinfo=UTC),
        artifact=StoredArtifact(
            role="linked_document",
            sha256=checksum,
            size_bytes=len(content),
            media_type="application/pdf",
            relative_path=f"{checksum[:2]}/{checksum}.pdf",
        ),
        link_text="Consumer loan information summary",
        origin_heading_path=("Loan terms",),
        nearby_text="",
    )


def _service(
    *,
    ocr_settings: OcrSettings | None = None,
    transcriber: FakeTranscriber | None = None,
    rasterizer: FakeRasterizer | None = None,
) -> GeminiPdfExtractionService:
    return GeminiPdfExtractionService(
        PdfExtractionSettings(),
        InMemoryPdfExtractionRepository(),
        api_key="test-key",
        ocr_settings=ocr_settings if ocr_settings is not None else OcrSettings(),
        ocr_transcriber=transcriber,
        rasterizer=rasterizer,
    )


def _empty_response(page_count: int) -> PdfExtractionResponse:
    return PdfExtractionResponse(
        pages=tuple(
            PdfExtractedPage(page_number=number) for number in range(1, page_count + 1)
        )
    )


def _populated_response(page_count: int) -> PdfExtractionResponse:
    return PdfExtractionResponse(
        pages=tuple(
            PdfExtractedPage(
                page_number=number,
                blocks=(
                    PdfExtractedBlock(
                        type=PdfExtractedBlockType.PARAGRAPH,
                        text=f"Gemini read page {number}",
                    ),
                ),
            )
            for number in range(1, page_count + 1)
        )
    )


# --------------------------------------------------------------------------
# Routing: which pages reach OCR
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_image_only_page_gemini_left_empty_is_sent_to_ocr() -> None:
    content = SCANNED.read_bytes()
    document = _document(content)
    transcriber = FakeTranscriber()
    rasterizer = FakeRasterizer()
    service = _service(transcriber=transcriber, rasterizer=rasterizer)

    plan = service.plan(document, content, document_id="doc-1")
    assert plan.input_probe.document_mode is PdfInputMode.IMAGE_ONLY

    normalized, ocr_result, sources = await service._apply_ocr(
        document,
        plan,
        _normalize_via(service, document, plan, _empty_response(1)),
        content,
    )

    assert transcriber.calls == [1]
    assert ocr_result is not None
    assert ocr_result.transcribed_pages == (1,)
    assert sources == ((1, PdfTranscriptionSource.OCR),)
    assert len(normalized.blocks) == 1
    assert is_ocr_method(normalized.blocks[0].extraction_method)
    assert is_ocr_source_item(normalized.blocks[0].id)
    assert normalized.blocks[0].id == ocr_block_id("doc-1", 1)
    assert normalized.quality_score == 1.0


@pytest.mark.asyncio
async def test_machine_readable_page_with_empty_output_is_not_sent_to_ocr() -> None:
    """OCR cannot fix a text layer Gemini declined to transcribe.

    Re-reading it would only add a second, weaker opinion of the same glyphs.
    """
    content = DIGITAL.read_bytes()
    document = _document(content)
    transcriber = FakeTranscriber()
    service = _service(transcriber=transcriber, rasterizer=FakeRasterizer())

    plan = service.plan(document, content, document_id="doc-digital")
    assert plan.input_probe.document_mode in (
        PdfInputMode.MACHINE_READABLE,
        PdfInputMode.MIXED,
    )

    _, ocr_result, sources = await service._apply_ocr(
        document,
        plan,
        _normalize_via(
            service, document, plan, _empty_response(plan.input_probe.page_count)
        ),
        content,
    )

    assert transcriber.calls == []
    assert ocr_result is None
    assert all(source is PdfTranscriptionSource.NONE for _, source in sources)


@pytest.mark.asyncio
async def test_image_only_page_gemini_already_read_is_not_sent_to_ocr() -> None:
    content = SCANNED.read_bytes()
    document = _document(content)
    transcriber = FakeTranscriber()
    service = _service(transcriber=transcriber, rasterizer=FakeRasterizer())

    plan = service.plan(document, content, document_id="doc-2")
    normalized, ocr_result, sources = await service._apply_ocr(
        document,
        plan,
        _normalize_via(service, document, plan, _populated_response(1)),
        content,
    )

    assert transcriber.calls == []
    assert ocr_result is None
    assert sources == ((1, PdfTranscriptionSource.GEMINI),)
    assert not any(
        is_ocr_method(block.extraction_method) for block in normalized.blocks
    )


# --------------------------------------------------------------------------
# Degrading without fabricating
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_ocr_leaves_the_scanned_page_empty() -> None:
    content = SCANNED.read_bytes()
    document = _document(content)
    transcriber = FakeTranscriber()
    service = _service(
        ocr_settings=OcrSettings(enabled=False),
        transcriber=transcriber,
        rasterizer=FakeRasterizer(),
    )

    plan = service.plan(document, content, document_id="doc-3")
    normalized, ocr_result, sources = await service._apply_ocr(
        document,
        plan,
        _normalize_via(service, document, plan, _empty_response(1)),
        content,
    )

    assert transcriber.calls == []
    assert ocr_result is None
    assert normalized.blocks == ()
    assert sources == ((1, PdfTranscriptionSource.NONE),)


@pytest.mark.asyncio
async def test_unavailable_engine_degrades_without_raising() -> None:
    content = SCANNED.read_bytes()
    document = _document(content)
    service = _service(
        transcriber=FakeTranscriber(available=False), rasterizer=FakeRasterizer()
    )

    plan = service.plan(document, content, document_id="doc-4")
    normalized, ocr_result, _ = await service._apply_ocr(
        document,
        plan,
        _normalize_via(service, document, plan, _empty_response(1)),
        content,
    )

    assert ocr_result is None
    assert normalized.blocks == ()


@pytest.mark.asyncio
async def test_no_transcriber_injected_behaves_as_before() -> None:
    content = SCANNED.read_bytes()
    document = _document(content)
    service = _service(transcriber=None, rasterizer=None)

    plan = service.plan(document, content, document_id="doc-5")
    normalized, ocr_result, _ = await service._apply_ocr(
        document,
        plan,
        _normalize_via(service, document, plan, _empty_response(1)),
        content,
    )

    assert ocr_result is None
    assert normalized.blocks == ()


@pytest.mark.asyncio
async def test_low_confidence_page_emits_no_blocks() -> None:
    """A misread digit must not be able to become an accepted interest rate."""
    content = SCANNED.read_bytes()
    document = _document(content)
    transcriber = FakeTranscriber(
        {
            1: OcrPageResult(
                page_number=1,
                outcome=OcrPageOutcome.LOW_CONFIDENCE,
                mean_confidence=31.4,
                word_count=8,
                detail="mean confidence 31.4 is below the floor 60.0",
            )
        }
    )
    service = _service(transcriber=transcriber, rasterizer=FakeRasterizer())

    plan = service.plan(document, content, document_id="doc-6")
    normalized, ocr_result, sources = await service._apply_ocr(
        document,
        plan,
        _normalize_via(service, document, plan, _empty_response(1)),
        content,
    )

    assert transcriber.calls == [1]
    assert ocr_result is not None
    assert ocr_result.transcribed_pages == ()
    assert normalized.blocks == ()
    assert sources == ((1, PdfTranscriptionSource.NONE),)


def test_a_non_transcribed_result_cannot_carry_text() -> None:
    with pytest.raises(ValueError, match="only a transcribed OCR page may carry text"):
        OcrPageResult(
            page_number=1,
            outcome=OcrPageOutcome.LOW_CONFIDENCE,
            text="13.5%",
            mean_confidence=20.0,
        )


# --------------------------------------------------------------------------
# Engine-unavailable fallback
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_models_failed_recovers_through_ocr() -> None:
    content = SCANNED.read_bytes()
    document = _document(content)
    transcriber = FakeTranscriber()
    service = _service(transcriber=transcriber, rasterizer=FakeRasterizer())

    plan = service.plan(document, content, document_id="doc-7")
    outcome = await service._ocr_only(document, plan, content)

    assert outcome is not None
    assert outcome.model_name is None
    assert is_ocr_method(outcome.normalized_document.extraction_method)
    assert len(outcome.normalized_document.blocks) == 1
    assert outcome.page_sources == ((1, PdfTranscriptionSource.OCR),)


@pytest.mark.asyncio
async def test_all_models_failed_with_no_ocr_yields_nothing() -> None:
    content = SCANNED.read_bytes()
    document = _document(content)
    service = _service(
        transcriber=FakeTranscriber(available=False), rasterizer=FakeRasterizer()
    )

    plan = service.plan(document, content, document_id="doc-8")
    assert await service._ocr_only(document, plan, content) is None


# --------------------------------------------------------------------------
# Bounds
# --------------------------------------------------------------------------


def test_rasterizer_reports_a_page_outside_the_document() -> None:
    rasterizer = PdfiumPageRasterizer()
    if not rasterizer.available:
        pytest.skip("pypdfium2 is not installed")
    result = rasterizer.rasterize_pages(
        SCANNED.read_bytes(), [9], dpi=150, max_pages=10, max_pixels=40_000_000
    )
    assert result.pages == ()
    assert "outside a 1-page PDF" in result.skipped[0].reason


def test_rasterizer_skips_a_page_over_the_pixel_budget() -> None:
    rasterizer = PdfiumPageRasterizer()
    if not rasterizer.available:
        pytest.skip("pypdfium2 is not installed")
    result = rasterizer.rasterize_pages(
        SCANNED.read_bytes(), [1], dpi=300, max_pages=10, max_pixels=1_000
    )
    assert result.pages == ()
    assert "skipped rather than downsampled" in result.skipped[0].reason


def test_rasterizer_reports_a_corrupt_pdf_instead_of_raising() -> None:
    rasterizer = PdfiumPageRasterizer()
    if not rasterizer.available:
        pytest.skip("pypdfium2 is not installed")
    result = rasterizer.rasterize_pages(
        b"not a pdf at all", [1], dpi=150, max_pages=10, max_pixels=40_000_000
    )
    assert result.pages == ()
    assert "could not be opened" in result.skipped[0].reason


def test_rasterizer_is_deterministic() -> None:
    rasterizer = PdfiumPageRasterizer()
    if not rasterizer.available:
        pytest.skip("pypdfium2 is not installed")
    content = SCANNED.read_bytes()
    first = rasterizer.rasterize_pages(
        content, [1], dpi=150, max_pages=10, max_pixels=40_000_000
    )
    second = rasterizer.rasterize_pages(
        content, [1], dpi=150, max_pages=10, max_pixels=40_000_000
    )
    assert first.pages[0].image_png == second.pages[0].image_png


@pytest.mark.asyncio
async def test_page_cap_skips_the_excess_pages() -> None:
    content = SCANNED.read_bytes()
    document = _document(content)
    transcriber = FakeTranscriber()
    rasterizer = FakeRasterizer()
    service = _service(
        ocr_settings=OcrSettings(max_pages=1),
        transcriber=transcriber,
        rasterizer=rasterizer,
    )
    plan = service.plan(document, content, document_id="doc-9")
    result = await service._transcribe_pages(content, plan, [1, 2, 3])

    assert transcriber.calls == [1]
    outcomes = {page.page_number: page.outcome for page in result.pages}
    assert outcomes[1] is OcrPageOutcome.TRANSCRIBED
    assert outcomes[2] is OcrPageOutcome.SKIPPED
    assert outcomes[3] is OcrPageOutcome.SKIPPED


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


def test_languages_accept_comma_and_plus_separators() -> None:
    assert OcrSettings(languages="hye,eng").languages == "hye+eng"
    assert OcrSettings(languages="hye+eng").languages == "hye+eng"
    assert OcrSettings(languages=" hye eng ").languages == "hye+eng"
    # A trailing separator is tolerated rather than failing startup.
    assert OcrSettings(languages="hye+").languages == "hye"


@pytest.mark.parametrize(
    "value",
    ["", "en", "HYE", "hye+eng+x", "+"],
)
def test_invalid_language_codes_are_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        OcrSettings(languages=value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("render_dpi", 71),
        ("render_dpi", 601),
        ("max_pages", 0),
        ("min_confidence", -1),
        ("min_confidence", 101),
        ("timeout_seconds", 0),
    ],
)
def test_out_of_range_settings_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        OcrSettings(**{field: value})


def test_blank_tesseract_command_is_unset() -> None:
    assert OcrSettings(tesseract_cmd="   ").tesseract_cmd is None


# --------------------------------------------------------------------------
# Engine-backed: skipped unless a real tesseract with the data is present
# --------------------------------------------------------------------------


def _engine_ready(settings: OcrSettings) -> bool:
    from app.services.ocr_transcriber import TesseractOcrTranscriber

    return (
        TesseractOcrTranscriber(settings).available and PdfiumPageRasterizer().available
    )


@pytest.mark.asyncio
async def test_real_engine_reads_a_rendered_page() -> None:
    from app.config import get_settings
    from app.services.ocr_transcriber import TesseractOcrTranscriber

    # Honour OCR_TESSERACT_CMD so a Windows install that is not on PATH still
    # exercises this test instead of silently skipping it.
    settings = OcrSettings(
        languages="eng",
        tesseract_cmd=get_settings().ocr.tesseract_cmd or shutil.which("tesseract"),
    )
    if not _engine_ready(settings):
        pytest.skip("no tesseract engine with the requested language data")

    from PIL import Image, ImageDraw, ImageFont

    from scripts.build_scanned_fixture import image_to_pdf

    font_path = next(
        (
            path
            for path in (
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            )
            if Path(path).exists()
        ),
        None,
    )
    if font_path is None:
        pytest.skip("no usable font for rendering the test page")

    image = Image.new("L", (1240, 400), color=255)
    draw = ImageDraw.Draw(image)
    draw.text(
        (90, 90), "Nominal rate: 13.5%", fill=20, font=ImageFont.truetype(font_path, 40)
    )
    pdf = image_to_pdf(image, 150)

    rasterizer = PdfiumPageRasterizer()
    page = rasterizer.rasterize_pages(
        pdf, [1], dpi=settings.render_dpi, max_pages=5, max_pixels=40_000_000
    ).pages[0]
    result = await TesseractOcrTranscriber(settings).transcribe(
        page,
        languages=settings.languages,
        timeout_seconds=settings.timeout_seconds,
        min_confidence=settings.min_confidence,
    )

    assert result.outcome is OcrPageOutcome.TRANSCRIBED
    assert "13.5" in result.text
    assert result.mean_confidence >= settings.min_confidence


def _normalize_via(
    service: GeminiPdfExtractionService,
    document: DocumentArtifact,
    plan,
    response: PdfExtractionResponse,
):
    from app.services.pdf_extraction import _normalize

    return _normalize(document, plan, response, "gemini-test")


# --------------------------------------------------------------------------
# Normalization fix plan: N28 (wider fill-in) and N15 (no key)
# --------------------------------------------------------------------------


def _blank_pdf() -> bytes:
    from io import BytesIO

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_an_empty_page_with_no_text_layer_and_no_image_is_sent_to_ocr() -> None:
    """Text drawn as vector shapes has neither a text layer nor an image."""
    content = _blank_pdf()
    document = _document(content)
    transcriber = FakeTranscriber()
    service = _service(transcriber=transcriber, rasterizer=FakeRasterizer())

    plan = service.plan(document, content, document_id="doc-vector")
    assert plan.input_probe.pages[0].input_mode is PdfInputMode.UNKNOWN
    _, _, sources = await service._apply_ocr(
        document,
        plan,
        _normalize_via(service, document, plan, _empty_response(1)),
        content,
    )

    assert transcriber.calls == [1]
    assert sources == ((1, PdfTranscriptionSource.OCR),)


@pytest.mark.asyncio
async def test_without_a_gemini_key_ocr_still_reads_a_scanned_pdf() -> None:
    content = SCANNED.read_bytes()
    service = GeminiPdfExtractionService(
        PdfExtractionSettings(),
        InMemoryPdfExtractionRepository(),
        api_key=None,
        ocr_settings=OcrSettings(),
        ocr_transcriber=FakeTranscriber(),
        rasterizer=FakeRasterizer(),
    )

    outcome = await service.extract(_document(content), content, document_id="doc-9")

    assert outcome.model_name is None
    assert is_ocr_method(outcome.normalized_document.extraction_method)


@pytest.mark.asyncio
async def test_without_a_gemini_key_or_ocr_the_model_is_reported_missing() -> None:
    from app.services.pdf_extraction import PdfModelUnavailable

    content = SCANNED.read_bytes()
    service = GeminiPdfExtractionService(
        PdfExtractionSettings(),
        InMemoryPdfExtractionRepository(),
        api_key=None,
        ocr_settings=OcrSettings(),
        ocr_transcriber=FakeTranscriber(available=False),
        rasterizer=FakeRasterizer(),
    )

    with pytest.raises(PdfModelUnavailable):
        await service.extract(_document(content), content, document_id="doc-10")
