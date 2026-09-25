from __future__ import annotations

from google.genai.errors import APIError
from pydantic import ValidationError

from app.domain.monitoring import (
    IndexingFailureCode,
    OfferingFailureCode,
    RunFailureCode,
    SourceFailureCode,
)
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
        if (
            isinstance(current, BrowserRenderingError)
            or type(current).__name__ == "AcquisitionError"
        ):
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


def describe_failure(error: Exception) -> str:
    """One bounded log line carrying what the provider actually reported.

    For logs only. `docs/failure-behavior.md` keeps provider text out of stored
    details and user-visible messages; use `bounded_failure_detail` for those.
    """
    if isinstance(error, APIError):
        message = (error.message or "no provider message").replace("\n", " ")[:500]
        return f"HTTP {error.code} / {error.status or 'UNKNOWN'}: {message}"
    message = str(error).replace("\n", " ")[:500]
    return f"{type(error).__name__}: {message}"


def bounded_failure_detail(error: Exception) -> str:
    """The stored detail: exception type plus, for a provider error, its status.

    `ClientError` alone cannot separate a retired model from a rate limit, and
    a run's audit trail has to survive that question months later. The status
    token comes from the transport, never from the response body, so no
    provider message, source content, or address is persisted.
    """
    if isinstance(error, APIError):
        status = (error.status or "unknown").replace(" ", "_")[:40]
        return f"{type(error).__name__}:http_{error.code}_{status}"
    return type(error).__name__


_FAILURE_EXPLANATIONS = {
    SourceFailureCode.URL_REJECTED: (
        "a source link fell outside the allowed official hosts, so it was not fetched"
    ),
    SourceFailureCode.TIMEOUT: "the bank's site did not respond in time",
    SourceFailureCode.TRANSPORT: "the connection to the bank's site failed",
    SourceFailureCode.HTTP_STATUS: "the bank's site returned an error status",
    SourceFailureCode.NOT_FOUND: "a published tariff document is no longer there",
    SourceFailureCode.MIME_REJECTED: (
        "a source was served in a format this pipeline does not accept"
    ),
    SourceFailureCode.SIZE_REJECTED: "a source was larger than the configured limit",
    SourceFailureCode.REDIRECT_REJECTED: (
        "a source redirect chain was not safe to follow"
    ),
    SourceFailureCode.SIGNATURE_REJECTED: "a downloaded file was not a valid PDF",
    SourceFailureCode.PARSING_FAILED: "a source page could not be parsed",
    SourceFailureCode.PDF_EXTRACTION_FAILED: (
        "a tariff PDF could not be transcribed by any configured model"
    ),
    SourceFailureCode.MODEL_FAILED: (
        "no configured model was available to read the sources"
    ),
    SourceFailureCode.MALFORMED_STRUCTURED_OUTPUT: (
        "a model returned output the validator rejected"
    ),
    SourceFailureCode.VALIDATION_FAILED: (
        "the extracted values did not pass validation, so nothing was published"
    ),
    IndexingFailureCode.INVALID_DOCUMENT: "a source document failed its index checks",
    IndexingFailureCode.EMBEDDING_FAILED: "the evidence index could not be built",
    IndexingFailureCode.PUBLICATION_FAILED: "the snapshot could not be published",
    OfferingFailureCode.NOT_CONFIGURED: (
        "the offering is not configured in the seed catalog"
    ),
    OfferingFailureCode.ACQUISITION_FAILED: (
        "the bank's page for this offering could not be fetched"
    ),
    OfferingFailureCode.NORMALIZATION_FAILED: (
        "the fetched sources could not be turned into readable documents"
    ),
    OfferingFailureCode.SOURCE_DISCOVERY_FAILED: (
        "the pipeline could not decide which sources carry current tariffs"
    ),
    OfferingFailureCode.SEMANTIC_EXTRACTION_FAILED: (
        "the tariff fields could not be extracted from the selected sources"
    ),
    OfferingFailureCode.VALIDATION_FAILED: (
        "the extracted values did not pass validation, so nothing was published"
    ),
    RunFailureCode.INTERNAL_ERROR: "the run hit an unexpected internal error",
    RunFailureCode.PERSISTENCE_FAILED: "the run could not be saved",
    RunFailureCode.CLAIM_CONFLICT: "another worker already claimed this run",
    RunFailureCode.INVALID_TRANSITION: "the run was in an unexpected state",
    RunFailureCode.CANCELLED: "it was cancelled before it finished",
    RunFailureCode.INTERRUPTED: (
        "the chat session running it closed before it finished"
    ),
}


def explain_failure_code(code: str | None) -> str:
    """A sentence an operator can act on, for a code that stays the record.

    The code alone is the audit trail; this is what makes it readable in chat
    without inventing a cause the run did not record.
    """
    if not code:
        return "The monitoring run failed and recorded no failure code."
    for failure, explanation in _FAILURE_EXPLANATIONS.items():
        if failure.value == code:
            return (
                f"Monitoring stopped because {explanation}. "
                "No tariff values were saved; the run can be retried."
            )
    return (
        f"Monitoring stopped with failure code {code}. "
        "No tariff values were saved; the run can be retried."
    )
