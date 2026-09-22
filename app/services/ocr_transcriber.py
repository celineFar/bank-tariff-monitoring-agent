"""OCR transcription of rendered PDF pages.

This is the fallback path of `System Description.md` §5.4: a page with no text
layer cannot be parsed directly, so it is rendered and read by a local OCR
engine. The stage is deterministic application code, never a model tool, and it
never fabricates text — a page that does not clear the confidence floor produces
no blocks at all.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Protocol

from app.config import OcrSettings
from app.domain.normalization import normalize_multiline_text
from app.domain.pdf_extraction import OcrPageOutcome, OcrPageResult
from app.services.pdf_rasterizer import RasterizedPage

logger = logging.getLogger(__name__)


class OcrTranscriber(Protocol):
    available: bool
    engine_version: str

    async def transcribe(
        self,
        page: RasterizedPage,
        *,
        languages: str,
        timeout_seconds: float,
        min_confidence: float,
    ) -> OcrPageResult: ...


class TesseractOcrTranscriber:
    """Tesseract adapter.

    Tesseract is the only maintained open engine shipping usable Armenian
    (`hye`) language data, which the bank's «տեղեկատվական ամփոփագիր» documents
    require. Availability — import, binary, and each requested traineddata — is
    resolved once here so the pipeline never discovers a missing engine halfway
    through a run.
    """

    def __init__(self, settings: OcrSettings) -> None:
        self._settings = settings
        self.available = False
        self.engine_version = "unavailable"
        self._unavailable_reason = ""

        if not settings.enabled:
            self._unavailable_reason = "OCR_ENABLED is false"
            return
        try:
            import pytesseract
        except ImportError as exc:
            self._unavailable_reason = (
                f"pytesseract is not installed ({exc}); "
                "install the optional 'ocr' extra"
            )
            logger.info("OCR unavailable: %s", self._unavailable_reason)
            return

        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        elif shutil.which("tesseract") is None:
            self._unavailable_reason = (
                "the tesseract binary is not on PATH; set OCR_TESSERACT_CMD"
            )
            logger.info("OCR unavailable: %s", self._unavailable_reason)
            return

        try:
            version = str(pytesseract.get_tesseract_version())
            installed = set(pytesseract.get_languages(config=""))
        except Exception as exc:
            self._unavailable_reason = (
                f"tesseract could not be queried: {_summary(exc)}"
            )
            logger.info("OCR unavailable: %s", self._unavailable_reason)
            return

        missing = [
            code for code in settings.languages.split("+") if code not in installed
        ]
        if missing:
            self._unavailable_reason = (
                f"tesseract {version} is missing traineddata for {', '.join(missing)}"
            )
            logger.warning("OCR unavailable: %s", self._unavailable_reason)
            return

        self.available = True
        self.engine_version = version
        logger.info(
            "OCR available: tesseract %s with languages %s",
            version,
            settings.languages,
        )

    @property
    def unavailable_reason(self) -> str:
        return self._unavailable_reason

    async def transcribe(
        self,
        page: RasterizedPage,
        *,
        languages: str,
        timeout_seconds: float,
        min_confidence: float,
    ) -> OcrPageResult:
        if not self.available:
            return OcrPageResult(
                page_number=page.page_number,
                outcome=OcrPageOutcome.SKIPPED,
                detail=self._unavailable_reason or "OCR engine unavailable",
            )
        try:
            text, confidence, words = await asyncio.wait_for(
                asyncio.to_thread(
                    _run_tesseract, page.image_png, languages, timeout_seconds
                ),
                timeout=timeout_seconds + 5,
            )
        except TimeoutError:
            return OcrPageResult(
                page_number=page.page_number,
                outcome=OcrPageOutcome.FAILED,
                detail=f"OCR timed out after {timeout_seconds:g}s",
            )
        except Exception as exc:
            return OcrPageResult(
                page_number=page.page_number,
                outcome=OcrPageOutcome.FAILED,
                detail=f"OCR engine error: {_summary(exc)}",
            )

        normalized = normalize_multiline_text(text)
        if not normalized or words == 0:
            return OcrPageResult(
                page_number=page.page_number,
                outcome=OcrPageOutcome.LOW_CONFIDENCE,
                mean_confidence=confidence,
                word_count=words,
                detail="OCR recognized no words on this page",
            )
        if confidence < min_confidence:
            # Emit nothing rather than a misread digit that could become an
            # accepted interest rate.
            return OcrPageResult(
                page_number=page.page_number,
                outcome=OcrPageOutcome.LOW_CONFIDENCE,
                mean_confidence=confidence,
                word_count=words,
                detail=(
                    f"mean confidence {confidence:.1f} is below the floor "
                    f"{min_confidence:.1f}"
                ),
            )
        return OcrPageResult(
            page_number=page.page_number,
            outcome=OcrPageOutcome.TRANSCRIBED,
            text=normalized,
            mean_confidence=confidence,
            word_count=words,
        )


def _run_tesseract(
    image_png: bytes, languages: str, timeout_seconds: float
) -> tuple[str, float, int]:
    """Return recognized text, mean word confidence, and word count."""
    from io import BytesIO

    import pytesseract
    from PIL import Image

    with Image.open(BytesIO(image_png)) as image:
        data = pytesseract.image_to_data(
            image,
            lang=languages,
            output_type=pytesseract.Output.DICT,
            timeout=timeout_seconds,
        )

    words: list[str] = []
    confidences: list[float] = []
    for text, confidence in zip(
        data.get("text", []), data.get("conf", []), strict=False
    ):
        token = (text or "").strip()
        if not token:
            continue
        try:
            value = float(confidence)
        except (TypeError, ValueError):
            continue
        if value < 0:  # tesseract reports -1 for non-text regions
            continue
        words.append(token)
        confidences.append(value)

    if not confidences:
        return "", 0.0, 0
    mean = sum(confidences) / len(confidences)
    return _reflow(data, words), mean, len(words)


def _reflow(data: dict[str, list[object]], words: list[str]) -> str:
    """Rebuild line breaks from tesseract's block/paragraph/line indices."""
    lines: dict[tuple[object, object, object], list[str]] = {}
    order: list[tuple[object, object, object]] = []
    texts = data.get("text", [])
    confs = data.get("conf", [])
    for index, raw in enumerate(texts):
        token = (str(raw) or "").strip()
        if not token:
            continue
        try:
            if float(confs[index]) < 0:
                continue
        except (TypeError, ValueError, IndexError):
            continue
        key = (
            data.get("block_num", [0] * len(texts))[index],
            data.get("par_num", [0] * len(texts))[index],
            data.get("line_num", [0] * len(texts))[index],
        )
        if key not in lines:
            lines[key] = []
            order.append(key)
        lines[key].append(token)
    if not order:
        return " ".join(words)
    return "\n".join(" ".join(lines[key]) for key in order)


def _summary(error: Exception) -> str:
    message = str(error).replace("\n", " ")[:300]
    return f"{type(error).__name__}: {message}"
