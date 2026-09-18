from datetime import UTC, datetime
from io import BytesIO

from pypdf import PdfWriter

from app.config import OcrSettings
from app.domain.acquisition import DocumentArtifact, StoredArtifact
from app.domain.normalization import NormalizationWarningCode
from app.services.pdf_text_extractor import PdfTextExtractor


class StubOcr:
    def extract_page(
        self,
        pdf_content: bytes,
        *,
        page_number: int,
        languages: tuple[str, ...],
        dpi: int,
        timeout_seconds: float,
    ) -> str:
        return "OCR loan term is up to 240 months."


def _blank_pdf() -> bytes:
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(stream)
    return stream.getvalue()


def _document(content: bytes) -> DocumentArtifact:
    import hashlib

    checksum = hashlib.sha256(content).hexdigest()
    stored = StoredArtifact(
        role="linked_document",
        sha256=checksum,
        size_bytes=len(content),
        media_type="application/pdf",
        relative_path=f"{checksum[:2]}/{checksum}.pdf",
    )
    return DocumentArtifact(
        source_url="https://ameriabank.am/terms.pdf",
        final_url="https://ameriabank.am/terms.pdf",
        document_name="Terms",
        mime_type="application/pdf",
        size_bytes=len(content),
        sha256=checksum,
        retrieved_at=datetime.now(UTC),
        artifact=stored,
    )


def test_weak_pdf_page_is_routed_to_injected_ocr() -> None:
    content = _blank_pdf()
    extractor = PdfTextExtractor(
        OcrSettings(min_text_chars_per_page=20), ocr_extractor=StubOcr()
    )

    document, warnings = extractor.extract(
        _document(content), content, document_id="document:1"
    )

    assert warnings == ()
    assert document.extraction_method == "ocr"
    assert document.blocks[0].source_refs[0].locator.pdf_page == 1
    assert document.blocks[0].scalar_candidates[0].value == 240


def test_weak_pdf_page_without_ocr_emits_explicit_warning() -> None:
    content = _blank_pdf()
    extractor = PdfTextExtractor(OcrSettings(min_text_chars_per_page=20))

    document, warnings = extractor.extract(
        _document(content), content, document_id="document:1"
    )

    assert document.quality_score == 0
    assert warnings[0].code is NormalizationWarningCode.OCR_REQUIRED
