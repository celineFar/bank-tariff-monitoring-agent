import pytest

from app.domain.monitoring import SourceFailureCode
from app.services.failure_mapping import source_failure_code
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
    ],
)
def test_source_failures_have_stable_bounded_codes(error, expected) -> None:
    assert source_failure_code(error, stage="acquisition") is expected


def test_stage_fallbacks_do_not_expose_exception_text() -> None:
    assert (
        source_failure_code(RuntimeError("provider secret"), stage="semantic_extraction")
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
