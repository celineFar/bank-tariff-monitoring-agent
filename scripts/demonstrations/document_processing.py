"""Deliverable 11 — digital PDF path and the scanned-page OCR fallback."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.domain.pdf_extraction import OcrPageOutcome, PdfInputMode
from app.services.ocr_transcriber import TesseractOcrTranscriber
from app.services.pdf_input_probe import probe_pdf_input
from app.services.pdf_rasterizer import PdfiumPageRasterizer
from scripts.demonstrations import ScenarioResult

FIXTURES = Path("tests/fixtures/pdfs")
DIGITAL = FIXTURES / "digital_sample.pdf"
SCANNED = FIXTURES / "scanned_armenian_sample.pdf"

# Tokens rendered into the scanned fixture by scripts/build_scanned_fixture.py.
# Recovering any of them proves OCR read the page image, not a text layer.
EXPECTED_TOKENS = ("13.5", "14.2", "AMD", "300,000")


async def run() -> ScenarioResult:
    result = ScenarioResult(
        deliverable="Deliverable 11",
        title="Document processing: digital PDF path and scanned-page OCR fallback",
    )

    digital_bytes = DIGITAL.read_bytes() if DIGITAL.exists() else b""
    digital_probe = probe_pdf_input(digital_bytes) if digital_bytes else None
    if digital_probe is not None:
        result.step(
            f"Probed the committed real bank PDF {DIGITAL.name}: "
            f"{digital_probe.page_count} page(s), "
            f"mode={digital_probe.document_mode.value}, "
            f"native text on page 1 = "
            f"{digital_probe.pages[0].native_text_characters} chars."
        )
        result.step(
            "    It has a text layer, so it takes the direct path and never "
            "reaches the OCR stage."
        )

    scanned_bytes = SCANNED.read_bytes() if SCANNED.exists() else b""
    scanned_probe = probe_pdf_input(scanned_bytes) if scanned_bytes else None
    if scanned_probe is not None:
        result.step(
            f"Probed the committed rendered page {SCANNED.name} "
            f"({len(scanned_bytes):,} bytes): "
            f"mode={scanned_probe.document_mode.value}, "
            f"native text = {scanned_probe.pages[0].native_text_characters} chars, "
            f"images detected = {scanned_probe.pages[0].images_detected}."
        )
        result.step(
            "    The page carries Armenian tariff text as a raster image only, "
            "so nothing can be parsed from it directly."
        )

    # Use the configured settings, so OCR_TESSERACT_CMD and OCR_LANGUAGES
    # from the environment apply here exactly as they do in the pipeline.
    settings = get_settings().ocr
    rasterizer = PdfiumPageRasterizer()
    transcriber = TesseractOcrTranscriber(settings)
    engine_ready = rasterizer.available and transcriber.available

    recovered_text = ""
    confidence = 0.0
    outcome: OcrPageOutcome | None = None
    if engine_ready and scanned_bytes:
        result.step(
            f"OCR engine available: tesseract {transcriber.engine_version} "
            f"with languages {settings.languages}."
        )
        rendered = rasterizer.rasterize_pages(
            scanned_bytes,
            [1],
            dpi=settings.render_dpi,
            max_pages=settings.max_pages,
            max_pixels=settings.max_pixels_per_page,
        )
        result.step(
            f"Rasterized page 1 at {settings.render_dpi} dpi "
            f"({rendered.pages[0].width}x{rendered.pages[0].height} px)."
            if rendered.pages
            else f"Rasterization skipped: {rendered.skipped[0].reason}"
        )
        if rendered.pages:
            page_result = await transcriber.transcribe(
                rendered.pages[0],
                languages=settings.languages,
                timeout_seconds=settings.timeout_seconds,
                min_confidence=settings.min_confidence,
            )
            outcome = page_result.outcome
            confidence = page_result.mean_confidence
            recovered_text = page_result.text
            result.step(
                f"OCR outcome={outcome.value}, mean confidence="
                f"{confidence:.1f}, words={page_result.word_count}."
            )
            if recovered_text:
                preview = recovered_text.replace("\n", " / ")[:160]
                result.step(f"    recovered: {preview}")
    else:
        reason = (
            "pypdfium2 is not installed"
            if not rasterizer.available
            else transcriber.unavailable_reason
        )
        result.step(f"OCR engine not available in this environment: {reason}")
        result.note(
            "Install the optional extra and the engine to run the OCR leg:\n"
            "      uv sync --extra ocr\n"
            "      Linux:   apt-get install tesseract-ocr tesseract-ocr-hye\n"
            "      Windows: install Tesseract with the Armenian language data "
            "and set OCR_TESSERACT_CMD"
        )

    result.check(
        "digital sample is committed",
        "a real bank PDF ships in the repository, not an ignored data directory",
        bool(digital_bytes),
        f"{DIGITAL} ({len(digital_bytes):,} bytes)",
    )
    result.check(
        "digital PDFs take the direct path",
        "a PDF with a text layer is classified machine_readable or mixed",
        digital_probe is not None
        and digital_probe.document_mode
        in (PdfInputMode.MACHINE_READABLE, PdfInputMode.MIXED),
        f"mode={digital_probe.document_mode.value}" if digital_probe else "no sample",
    )
    result.check(
        "scanned page is detected",
        "a page with no text layer is classified image_only, not machine_readable",
        scanned_probe is not None
        and scanned_probe.document_mode is PdfInputMode.IMAGE_ONLY,
        f"mode={scanned_probe.document_mode.value}" if scanned_probe else "no sample",
    )
    result.check(
        "no text is invented for a scanned page",
        "the prober reports zero native characters rather than guessing",
        scanned_probe is not None
        and scanned_probe.pages[0].native_text_characters == 0
        and scanned_probe.pages[0].images_detected,
        (
            f"chars={scanned_probe.pages[0].native_text_characters}, "
            f"images={scanned_probe.pages[0].images_detected}"
        )
        if scanned_probe
        else "no sample",
    )

    if not engine_ready:
        result.note(
            "SKIPPED: the OCR fallback criteria below were not evaluated because "
            "no OCR engine is installed. This is reported as a skip, not a pass."
        )
        return result

    found = [token for token in EXPECTED_TOKENS if token in recovered_text]
    result.check(
        "OCR reads the scanned page",
        "the OCR stage transcribes the image-only page",
        outcome is OcrPageOutcome.TRANSCRIBED and bool(recovered_text),
        f"outcome={outcome.value if outcome else 'none'}, "
        f"{len(recovered_text)} chars recovered",
    )
    result.check(
        "recovered text contains the rendered tariff values",
        "OCR output matches values rendered into the page image",
        bool(found),
        f"recovered tokens: {found}",
    )
    result.check(
        "confidence is reported",
        "the stage reports a mean confidence rather than an opaque success",
        confidence > 0,
        f"mean confidence={confidence:.1f}, floor={settings.min_confidence:.1f}",
    )
    return result
