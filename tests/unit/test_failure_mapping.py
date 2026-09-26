import pytest
from google.genai.errors import ClientError

from app.domain.monitoring import SourceFailureCode
from app.services.failure_mapping import (
    bounded_failure_detail,
    describe_failure,
    source_failure_code,
)
from app.services.html_retriever import HtmlRetrievalError, HtmlRetrievalFailure
from app.services.monitoring_pipeline import IndexingPipeline, OfferingPipelineError
from app.services.pdf_downloader import PdfDownloadError, PdfDownloadFailure


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            HtmlRetrievalError(HtmlRetrievalFailure.TIMEOUT, "secret detail"),
            SourceFailureCode.TIMEOUT,
        ),
        (
            HtmlRetrievalError(
                HtmlRetrievalFailure.HTTP_STATUS,
                "not found",
                status_code=404,
            ),
            SourceFailureCode.NOT_FOUND,
        ),
        (
            PdfDownloadError(
                PdfDownloadFailure.UNSUPPORTED_MIME_TYPE,
                "wrong type",
            ),
            SourceFailureCode.MIME_REJECTED,
        ),
        (
            PdfDownloadError(
                PdfDownloadFailure.DOCUMENT_TOO_LARGE,
                "large",
            ),
            SourceFailureCode.SIZE_REJECTED,
        ),
        (
            PdfDownloadError(
                PdfDownloadFailure.REDIRECT_LOOP,
                "loop",
            ),
            SourceFailureCode.REDIRECT_REJECTED,
        ),
        (
            PdfDownloadError(
                PdfDownloadFailure.INVALID_PDF_SIGNATURE,
                "signature",
            ),
            SourceFailureCode.SIGNATURE_REJECTED,
        ),
        (
            HtmlRetrievalError(
                HtmlRetrievalFailure.DISALLOWED_URL,
                "unsafe",
            ),
            SourceFailureCode.URL_REJECTED,
        ),
        (
            HtmlRetrievalError(
                HtmlRetrievalFailure.TRANSPORT,
                "transport",
            ),
            SourceFailureCode.TRANSPORT,
        ),
        (
            HtmlRetrievalError(
                HtmlRetrievalFailure.HTTP_STATUS,
                "status",
                status_code=403,
            ),
            SourceFailureCode.HTTP_STATUS,
        ),
    ],
)
def test_source_failures_have_stable_bounded_codes(error, expected) -> None:
    assert source_failure_code(error, stage="acquisition") is expected


def test_stage_fallbacks_do_not_expose_exception_text() -> None:
    assert (
        source_failure_code(
            RuntimeError("provider secret"), stage="semantic_extraction"
        )
        is SourceFailureCode.MODEL_FAILED
    )


@pytest.mark.asyncio
async def test_pipeline_preserves_precise_failure_code_without_source_body() -> None:
    async def fail():
        raise HtmlRetrievalError(
            HtmlRetrievalFailure.HTTP_STATUS,
            "private response body",
            status_code=404,
        )

    with pytest.raises(OfferingPipelineError) as captured:
        await IndexingPipeline._stage(
            "acquisition",
            "offering.acquisition_failed",
            fail(),
            [],
        )

    assert captured.value.failure_code == "source.not_found"
    assert captured.value.cause_type == "HtmlRetrievalError"
    assert "private response body" not in str(captured.value)
    assert (
        source_failure_code(RuntimeError("document body"), stage="normalization")
        is SourceFailureCode.PARSING_FAILED
    )


def test_stored_detail_keeps_the_provider_status_without_its_message() -> None:
    error = ClientError(
        404,
        {
            "error": {
                "status": "NOT_FOUND",
                "message": "This model is no longer available to new users.",
            }
        },
    )

    detail = bounded_failure_detail(error)

    assert detail == "ClientError:http_404_NOT_FOUND"
    assert "no longer available" not in detail


def test_stored_detail_of_an_ordinary_error_is_its_type() -> None:
    assert bounded_failure_detail(RuntimeError("fixture failure")) == "RuntimeError"


def test_log_description_keeps_the_provider_message_for_operators() -> None:
    error = ClientError(
        404,
        {"error": {"status": "NOT_FOUND", "message": "model retired"}},
    )

    assert describe_failure(error) == "HTTP 404 / NOT_FOUND: model retired"


def _browser_failure(reason):
    from app.services.acquisition_errors import AcquisitionError, AcquisitionFailure
    from app.services.browser_renderer import BrowserRenderingError

    try:
        try:
            raise BrowserRenderingError(reason, "render failed")
        except BrowserRenderingError as exc:
            raise AcquisitionError(
                AcquisitionFailure.BROWSER_FAILED, "browser failed"
            ) from exc
    except AcquisitionError as wrapped:
        return wrapped


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("UNAVAILABLE", SourceFailureCode.BROWSER_UNAVAILABLE),
        ("NAVIGATION", SourceFailureCode.BROWSER_FAILED),
        ("INTERACTION", SourceFailureCode.BROWSER_FAILED),
        ("DISALLOWED_REDIRECT", SourceFailureCode.REDIRECT_REJECTED),
        ("REDIRECT_LIMIT_EXCEEDED", SourceFailureCode.REDIRECT_REJECTED),
        ("HTTP_STATUS", SourceFailureCode.HTTP_STATUS),
        ("UNSUPPORTED_MIME_TYPE", SourceFailureCode.MIME_REJECTED),
        ("PAGE_TOO_LARGE", SourceFailureCode.SIZE_REJECTED),
    ],
)
def test_each_browser_failure_keeps_its_own_code(reason, expected) -> None:
    from app.services.browser_renderer import BrowserRenderingFailure

    error = _browser_failure(BrowserRenderingFailure(reason))

    assert source_failure_code(error, stage="acquisition") is expected


def test_every_browser_failure_reason_is_mapped() -> None:
    from app.services.browser_renderer import BrowserRenderingFailure
    from app.services.failure_mapping import _BROWSER_FAILURES

    assert set(_BROWSER_FAILURES) == set(BrowserRenderingFailure)


def test_acquisition_failures_have_their_own_codes() -> None:
    from app.services.acquisition_errors import AcquisitionError, AcquisitionFailure

    incomplete = AcquisitionError(
        AcquisitionFailure.INCOMPLETE_CONTENT, "thin", reasons=("tables 3 -> 0",)
    )
    unavailable = AcquisitionError(AcquisitionFailure.BROWSER_UNAVAILABLE, "none")
    unexplained = AcquisitionError(AcquisitionFailure.BROWSER_FAILED, "failed")

    assert (
        source_failure_code(incomplete, stage="acquisition")
        is SourceFailureCode.INCOMPLETE_CONTENT
    )
    assert (
        source_failure_code(unavailable, stage="acquisition")
        is SourceFailureCode.BROWSER_UNAVAILABLE
    )
    assert (
        source_failure_code(unexplained, stage="acquisition")
        is SourceFailureCode.BROWSER_FAILED
    )


def test_a_playwright_error_is_never_reported_as_validation_failure() -> None:
    # A raw Playwright error escaping the renderer used to fall through every
    # branch and read as `source.validation_failed`. The renderer now wraps it;
    # this pins the wrapped form.
    from app.services.browser_renderer import BrowserRenderingFailure

    error = _browser_failure(BrowserRenderingFailure.INTERACTION)

    assert (
        source_failure_code(error, stage="acquisition")
        is not SourceFailureCode.VALIDATION_FAILED
    )


def test_incomplete_content_reasons_reach_the_pipeline_error() -> None:
    from app.services.acquisition_errors import AcquisitionError, AcquisitionFailure

    error = OfferingPipelineError(
        "acquisition",
        SourceFailureCode.INCOMPLETE_CONTENT.value,
        AcquisitionError(
            AcquisitionFailure.INCOMPLETE_CONTENT,
            "thin",
            reasons=("tables 3 -> 0", "pdf_links 10 -> 0"),
        ),
    )

    assert error.cause_reason == "INCOMPLETE_CONTENT"
    assert error.cause_reasons == ("tables 3 -> 0", "pdf_links 10 -> 0")


def test_every_source_failure_code_has_an_explanation() -> None:
    from app.services.failure_mapping import explain_failure_code

    for code in SourceFailureCode.__members__.values():
        explanation = explain_failure_code(code.value)
        assert not explanation.startswith("Monitoring stopped with failure code"), code
