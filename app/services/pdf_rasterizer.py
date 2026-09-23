"""Deterministic PDF page rasterization for the OCR fallback.

No model call and no network. A page is rendered only when the OCR stage has
already decided it needs one, so an admitted-but-machine-readable document never
pays for rendering.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# PDF user space is 72 units per inch; rendering scale is dpi / 72.
_PDF_POINTS_PER_INCH = 72.0


class RasterizedPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    image_png: bytes
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    scale: float = Field(gt=0)


class SkippedPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    reason: str


class RasterizationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    pages: tuple[RasterizedPage, ...] = ()
    skipped: tuple[SkippedPage, ...] = ()


class PageRasterizer(Protocol):
    available: bool

    def rasterize_pages(
        self,
        content: bytes,
        page_numbers: Sequence[int],
        *,
        dpi: int,
        max_pages: int,
        max_pixels: int,
    ) -> RasterizationResult: ...


class PdfiumPageRasterizer:
    """`pypdfium2`-backed rasterizer.

    Availability is resolved once at construction so a missing optional
    dependency degrades the OCR stage instead of raising mid-pipeline.
    """

    def __init__(self) -> None:
        try:
            import pypdfium2  # noqa: F401
        except ImportError as exc:
            self.available = False
            self._unavailable_reason = f"pypdfium2 is not installed ({exc})"
            logger.info(
                "PDF rasterizer unavailable: %s; the OCR fallback is disabled",
                self._unavailable_reason,
            )
            return
        self.available = True
        self._unavailable_reason = ""

    def rasterize_pages(
        self,
        content: bytes,
        page_numbers: Sequence[int],
        *,
        dpi: int,
        max_pages: int,
        max_pixels: int,
    ) -> RasterizationResult:
        if not self.available:
            return RasterizationResult(
                skipped=tuple(
                    SkippedPage(page_number=number, reason=self._unavailable_reason)
                    for number in sorted(set(page_numbers))
                )
            )

        import pypdfium2

        requested = sorted(set(page_numbers))
        skipped: list[SkippedPage] = []
        if len(requested) > max_pages:
            for number in requested[max_pages:]:
                skipped.append(
                    SkippedPage(
                        page_number=number,
                        reason=f"page cap of {max_pages} reached",
                    )
                )
            requested = requested[:max_pages]

        rendered: list[RasterizedPage] = []
        scale = dpi / _PDF_POINTS_PER_INCH
        try:
            document = pypdfium2.PdfDocument(content)
        except Exception as exc:
            return RasterizationResult(
                skipped=tuple(
                    SkippedPage(
                        page_number=number,
                        reason=f"PDF could not be opened: {_summary(exc)}",
                    )
                    for number in sorted(set(page_numbers))
                )
            )
        try:
            page_count = len(document)
            for number in requested:
                if number < 1 or number > page_count:
                    skipped.append(
                        SkippedPage(
                            page_number=number,
                            reason=f"page {number} is outside a {page_count}-page PDF",
                        )
                    )
                    continue
                page = document[number - 1]
                width = max(1, int(page.get_width() * scale))
                height = max(1, int(page.get_height() * scale))
                if width * height > max_pixels:
                    skipped.append(
                        SkippedPage(
                            page_number=number,
                            reason=(
                                f"{width}x{height} exceeds the {max_pixels} pixel "
                                "budget; the page is skipped rather than downsampled"
                            ),
                        )
                    )
                    continue
                try:
                    bitmap = page.render(scale=scale)
                    image = bitmap.to_pil()
                    png = _to_png(image)
                except Exception as exc:
                    skipped.append(
                        SkippedPage(
                            page_number=number,
                            reason=f"render failed: {_summary(exc)}",
                        )
                    )
                    continue
                rendered.append(
                    RasterizedPage(
                        page_number=number,
                        image_png=png,
                        width=image.width,
                        height=image.height,
                        scale=scale,
                    )
                )
        finally:
            document.close()
        return RasterizationResult(pages=tuple(rendered), skipped=tuple(skipped))


def _to_png(image: object) -> bytes:
    """Encode deterministically: no timestamp chunk, fixed compression."""
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=False, compress_level=6)  # type: ignore[attr-defined]
    return buffer.getvalue()


def _summary(error: Exception) -> str:
    message = str(error).replace("\n", " ")[:300]
    return f"{type(error).__name__}: {message}"
