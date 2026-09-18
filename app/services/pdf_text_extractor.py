from __future__ import annotations

from io import BytesIO
from typing import Protocol

from pypdf import PdfReader

from app.config import OcrSettings
from app.domain.acquisition import DocumentArtifact, SourceLocator, SourceType
from app.domain.normalization import (
    NormalizationWarning,
    NormalizationWarningCode,
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    SourceReference,
    normalize_multiline_text,
    normalize_text,
)
from app.services.scalar_normalizer import extract_scalar_candidates


class OcrExtractor(Protocol):
    def extract_page(
        self,
        pdf_content: bytes,
        *,
        page_number: int,
        languages: tuple[str, ...],
        dpi: int,
        timeout_seconds: float,
    ) -> str: ...


class PdfTextExtractor:
    """Extract page-addressable PDF text and deterministically route weak pages to OCR."""

    def __init__(
        self, settings: OcrSettings, *, ocr_extractor: OcrExtractor | None = None
    ) -> None:
        self._settings = settings
        self._ocr_extractor = ocr_extractor

    def extract(
        self,
        document: DocumentArtifact,
        content: bytes,
        *,
        document_id: str,
    ) -> tuple[NormalizedDocument, tuple[NormalizationWarning, ...]]:
        warnings: list[NormalizationWarning] = []
        try:
            reader = PdfReader(BytesIO(content))
        except Exception as exc:  # pypdf exposes several parser exception types
            return self._empty_document(document, document_id), (
                NormalizationWarning(
                    code=NormalizationWarningCode.PDF_PARSE_FAILED,
                    source_id=document_id,
                    message=f"PDF could not be parsed: {exc}",
                ),
            )

        page_count = len(reader.pages)
        if page_count > self._settings.max_pages:
            warnings.append(
                NormalizationWarning(
                    code=NormalizationWarningCode.PAGE_LIMIT_REACHED,
                    source_id=document_id,
                    message=(
                        f"PDF has {page_count} pages; only the configured first "
                        f"{self._settings.max_pages} pages were normalized"
                    ),
                )
            )

        blocks: list[NormalizedBlock] = []
        strong_pages = 0
        methods: set[str] = set()
        for page_index, page in enumerate(reader.pages[: self._settings.max_pages]):
            page_number = page_index + 1
            try:
                raw_text = page.extract_text() or ""
            except Exception as exc:
                raw_text = ""
                warnings.append(
                    NormalizationWarning(
                        code=NormalizationWarningCode.PDF_PARSE_FAILED,
                        source_id=document_id,
                        message=f"PDF page {page_number} text extraction failed: {exc}",
                    )
                )

            method = "pdf_text"
            text = normalize_multiline_text(raw_text)
            if len(normalize_text(text)) < self._settings.min_text_chars_per_page:
                if self._ocr_extractor is None:
                    warnings.append(
                        NormalizationWarning(
                            code=NormalizationWarningCode.OCR_REQUIRED,
                            source_id=document_id,
                            message=(
                                f"PDF page {page_number} has insufficient embedded "
                                "text and no OCR adapter is configured"
                            ),
                        )
                    )
                else:
                    try:
                        ocr_text = normalize_multiline_text(
                            self._ocr_extractor.extract_page(
                                content,
                                page_number=page_number,
                                languages=self._settings.languages,
                                dpi=self._settings.dpi,
                                timeout_seconds=self._settings.timeout_seconds,
                            )
                        )
                    except Exception as exc:
                        warnings.append(
                            NormalizationWarning(
                                code=NormalizationWarningCode.OCR_FAILED,
                                source_id=document_id,
                                message=f"OCR failed for PDF page {page_number}: {exc}",
                            )
                        )
                    else:
                        if len(normalize_text(ocr_text)) > len(normalize_text(text)):
                            text = ocr_text
                            raw_text = ocr_text
                            method = "ocr"

            if len(normalize_text(text)) >= self._settings.min_text_chars_per_page:
                strong_pages += 1
            if not text:
                continue
            methods.add(method)
            locator = SourceLocator(
                source_url=document.final_url,
                source_type=SourceType.PDF,
                pdf_page=page_number,
            )
            for paragraph_index, (raw_paragraph, paragraph) in enumerate(
                _paragraphs(raw_text)
            ):
                block_id = f"{document_id}:page:{page_number}:block:{paragraph_index}"
                blocks.append(
                    NormalizedBlock(
                        id=block_id,
                        type=NormalizedBlockType.PARAGRAPH,
                        raw_text=raw_paragraph,
                        text=paragraph,
                        scalar_candidates=extract_scalar_candidates(paragraph),
                        source_refs=(
                            SourceReference(source_item_id=block_id, locator=locator),
                        ),
                        extraction_method=method,
                    )
                )

        processed_pages = min(page_count, self._settings.max_pages)
        quality = strong_pages / processed_pages if processed_pages else 0.0
        extraction_method = "+".join(sorted(methods)) if methods else "pdf_text"
        return (
            NormalizedDocument(
                id=document_id,
                name=document.document_name,
                source_url=document.final_url,
                source_type=SourceType.PDF,
                mime_type=document.mime_type,
                content_sha256=document.sha256,
                extraction_method=extraction_method,
                quality_score=quality,
                blocks=tuple(blocks),
            ),
            tuple(warnings),
        )

    @staticmethod
    def _empty_document(
        document: DocumentArtifact, document_id: str
    ) -> NormalizedDocument:
        return NormalizedDocument(
            id=document_id,
            name=document.document_name,
            source_url=document.final_url,
            source_type=SourceType.PDF,
            mime_type=document.mime_type,
            content_sha256=document.sha256,
            extraction_method="pdf_text",
            quality_score=0.0,
        )


def _paragraphs(text: str) -> tuple[tuple[str, str], ...]:
    # Preserve line structure within a page while bounding block size. Explicit
    # blank-line paragraphs survive when available; otherwise the page is one block.
    paragraphs = tuple(
        (value, normalized)
        for value in text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n")
        if (normalized := normalize_multiline_text(value))
    )
    normalized_text = normalize_multiline_text(text)
    return paragraphs or (((text, normalized_text),) if normalized_text else ())
