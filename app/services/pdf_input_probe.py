from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.domain.pdf_extraction import PdfInputMode, PdfInputProbe, PdfPageProbe


def probe_pdf_input(content: bytes, *, text_threshold: int = 20) -> PdfInputProbe:
    reader = PdfReader(BytesIO(content))
    pages: list[PdfPageProbe] = []
    for index, page in enumerate(reader.pages):
        try:
            text_characters = len((page.extract_text() or "").strip())
        except Exception:
            text_characters = 0
        try:
            images_detected = bool(page.images)
        except Exception:
            images_detected = False
        if text_characters >= text_threshold and images_detected:
            mode = PdfInputMode.MIXED
        elif text_characters >= text_threshold:
            mode = PdfInputMode.MACHINE_READABLE
        elif images_detected:
            mode = PdfInputMode.IMAGE_ONLY
        else:
            mode = PdfInputMode.UNKNOWN
        pages.append(
            PdfPageProbe(
                page_number=index + 1,
                input_mode=mode,
                native_text_characters=text_characters,
                images_detected=images_detected,
            )
        )
    modes = {page.input_mode for page in pages}
    if len(modes) == 1:
        document_mode = next(iter(modes))
    elif not modes:
        document_mode = PdfInputMode.UNKNOWN
    else:
        document_mode = PdfInputMode.MIXED
    return PdfInputProbe(
        page_count=len(pages), document_mode=document_mode, pages=tuple(pages)
    )
