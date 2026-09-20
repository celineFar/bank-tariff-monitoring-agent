from __future__ import annotations

from pydantic import ValidationError

from app.domain.monitoring import SourceFailureCode
from app.services.browser_renderer import BrowserRenderingError
from app.services.html_retriever import (
    HtmlRetrievalError,
    HtmlRetrievalFailure,
)
from app.services.pdf_downloader import PdfDownloadError, PdfDownloadFailure

_REDIRECT_FAILURES = {
    HtmlRetrievalFailure.REDIRECT_WITHOUT_LOCATION,
    HtmlRetrievalFailure.REDIRECT_LIMIT_EXCEEDED,
    HtmlRetrievalFailure.REDIRECT_LOOP,
    PdfDownloadFailure.REDIRECT_WITHOUT_LOCATION,
    PdfDownloadFailure.REDIRECT_LIMIT_EXCEEDED,
    PdfDownloadFailure.REDIRECT_LOOP,
}


def source_failure_code(exc: Exception, *, stage: str) -> SourceFailureCode:
    """Return a stable, bounded code while retaining the exception chain for audit."""
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, (HtmlRetrievalError, PdfDownloadError)):
            reason = current.reason
            if reason in {
                HtmlRetrievalFailure.DISALLOWED_URL,
                PdfDownloadFailure.DISALLOWED_URL,
            }:
                return SourceFailureCode.URL_REJECTED
            if reason in {
                HtmlRetrievalFailure.TIMEOUT,
                PdfDownloadFailure.TIMEOUT,
            }:
                return SourceFailureCode.TIMEOUT
            if reason in {
                HtmlRetrievalFailure.TRANSPORT,
                PdfDownloadFailure.TRANSPORT,
            }:
                return SourceFailureCode.TRANSPORT
            if reason in _REDIRECT_FAILURES:
                return SourceFailureCode.REDIRECT_REJECTED
            if reason in {
                HtmlRetrievalFailure.UNSUPPORTED_MIME_TYPE,
                PdfDownloadFailure.UNSUPPORTED_MIME_TYPE,
            }:
                return SourceFailureCode.MIME_REJECTED
            if reason in {
                HtmlRetrievalFailure.PAGE_TOO_LARGE,
                HtmlRetrievalFailure.INVALID_CONTENT_LENGTH,
                PdfDownloadFailure.DOCUMENT_TOO_LARGE,
                PdfDownloadFailure.INVALID_CONTENT_LENGTH,
            }:
                return SourceFailureCode.SIZE_REJECTED
            if reason is PdfDownloadFailure.INVALID_PDF_SIGNATURE:
                return SourceFailureCode.SIGNATURE_REJECTED
            if reason in {
                HtmlRetrievalFailure.HTTP_STATUS,
                PdfDownloadFailure.HTTP_STATUS,
            }:
                return (
                    SourceFailureCode.NOT_FOUND
                    if current.status_code == 404
                    else SourceFailureCode.HTTP_STATUS
                )
        if isinstance(current, BrowserRenderingError) or type(current).__name__ == "AcquisitionError":
            return SourceFailureCode.PARSING_FAILED
        if isinstance(current, ValidationError):
            return SourceFailureCode.MALFORMED_STRUCTURED_OUTPUT
        current = current.__cause__ or current.__context__

    if stage == "pdf_extraction":
        return SourceFailureCode.PDF_EXTRACTION_FAILED
    if stage == "normalization":
        return SourceFailureCode.PARSING_FAILED
    if stage == "semantic_extraction":
        return SourceFailureCode.MODEL_FAILED
    if stage == "source_discovery":
        return SourceFailureCode.MODEL_FAILED
    return SourceFailureCode.VALIDATION_FAILED
