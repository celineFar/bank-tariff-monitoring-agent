import hashlib
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.config import HttpSettings
from app.services.pdf_downloader import (
    DownloadedPdf,
    PdfCandidate,
    PdfDownloader,
    PdfDownloadError,
    PdfDownloadFailure,
)

SOURCE_URL = "https://ameriabank.am/documents/tariff.pdf"
PDF_BYTES = b"%PDF-1.7\ncontrolled fixture\n%%EOF"


def _settings(**overrides: object) -> HttpSettings:
    return HttpSettings(backoff_base_seconds=0, **overrides)


async def _no_sleep(_: float) -> None:
    return None


async def _download(
    handler: httpx.MockTransport,
    *,
    settings: HttpSettings | None = None,
    clock: Callable[[], datetime] | None = None,
) -> DownloadedPdf:
    async with httpx.AsyncClient(transport=handler) as client:
        downloader = PdfDownloader(
            client,
            settings or _settings(),
            sleep=_no_sleep,
            clock=clock,
        )
        return await downloader.download(PdfCandidate(SOURCE_URL))


@pytest.mark.asyncio
async def test_downloads_valid_pdf_with_hash_and_safe_provenance() -> None:
    requests: list[httpx.Request] = []
    times = iter(
        [
            datetime(2026, 9, 16, 6, tzinfo=UTC),
            datetime(2026, 9, 16, 6, tzinfo=UTC) + timedelta(seconds=1),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/pdf; charset=binary",
                "ETag": '"version-1"',
                "Last-Modified": "Wed, 16 Sep 2026 02:00:00 GMT",
                "Content-Disposition": 'attachment; filename="tariff.pdf"',
                "Set-Cookie": "must-not-be-retained=secret",
            },
            content=PDF_BYTES,
        )

    document = await _download(httpx.MockTransport(handler), clock=lambda: next(times))

    assert document.source_url == SOURCE_URL
    assert document.final_url == SOURCE_URL
    assert document.content == PDF_BYTES
    assert document.mime_type == "application/pdf"
    assert document.size_bytes == len(PDF_BYTES)
    assert document.sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
    assert document.retrieval_started_at < document.retrieved_at
    assert document.provenance_headers.etag == '"version-1"'
    assert document.provenance_headers.last_modified is not None
    assert document.provenance_headers.content_disposition is not None
    assert requests[0].headers["accept"] == "application/pdf"
    assert requests[0].headers["user-agent"] == _settings().user_agent


@pytest.mark.asyncio
async def test_timeout_retries_then_returns_controlled_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("fixture timeout", request=request)

    with pytest.raises(PdfDownloadError) as caught:
        await _download(httpx.MockTransport(handler))

    assert caught.value.reason is PdfDownloadFailure.TIMEOUT
    assert attempts == _settings().max_attempts


@pytest.mark.asyncio
async def test_404_is_not_retried() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404)

    with pytest.raises(PdfDownloadError) as caught:
        await _download(httpx.MockTransport(handler))

    assert caught.value.reason is PdfDownloadFailure.HTTP_STATUS
    assert caught.value.status_code == 404
    assert attempts == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("transient_status", [429, 500, 503])
async def test_transient_status_is_retried(transient_status: int) -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(transient_status)
        return httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            content=PDF_BYTES,
        )

    document = await _download(httpx.MockTransport(handler))

    assert document.content == PDF_BYTES
    assert attempts == 2


@pytest.mark.asyncio
async def test_follows_allowlisted_redirect_and_records_final_url() -> None:
    final_url = "https://www.ameriabank.am/documents/current.pdf"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == SOURCE_URL:
            return httpx.Response(302, headers={"Location": final_url})
        return httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            content=PDF_BYTES,
        )

    document = await _download(httpx.MockTransport(handler))

    assert document.source_url == SOURCE_URL
    assert document.final_url == final_url


class _StaticStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield PDF_BYTES[:8]
        yield PDF_BYTES[8:]


@pytest.mark.asyncio
async def test_streamed_content_over_limit_is_rejected() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            stream=_StaticStream(),
        )

    with pytest.raises(PdfDownloadError) as caught:
        await _download(
            httpx.MockTransport(handler),
            settings=_settings(max_download_bytes=len(PDF_BYTES) - 1),
        )

    assert caught.value.reason is PdfDownloadFailure.DOCUMENT_TOO_LARGE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content_type", "content", "reason"),
    [
        ("text/html", PDF_BYTES, PdfDownloadFailure.UNSUPPORTED_MIME_TYPE),
        (
            "application/pdf",
            b"<html>not a PDF</html>",
            PdfDownloadFailure.INVALID_PDF_SIGNATURE,
        ),
    ],
)
async def test_spoofed_mime_or_signature_is_rejected(
    content_type: str, content: bytes, reason: PdfDownloadFailure
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": content_type},
            content=content,
        )

    with pytest.raises(PdfDownloadError) as caught:
        await _download(httpx.MockTransport(handler))

    assert caught.value.reason is reason


@pytest.mark.asyncio
async def test_disallowed_redirect_fails_before_following_it() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(302, headers={"Location": "https://evil.example/a.pdf"})

    with pytest.raises(PdfDownloadError) as caught:
        await _download(httpx.MockTransport(handler))

    assert caught.value.reason is PdfDownloadFailure.DISALLOWED_URL
    assert requested_hosts == ["ameriabank.am"]


@pytest.mark.asyncio
async def test_redirect_loop_is_detected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("tariff.pdf"):
            return httpx.Response(302, headers={"Location": "/documents/other.pdf"})
        return httpx.Response(302, headers={"Location": SOURCE_URL})

    with pytest.raises(PdfDownloadError) as caught:
        await _download(httpx.MockTransport(handler))

    assert caught.value.reason is PdfDownloadFailure.REDIRECT_LOOP


@pytest.mark.asyncio
async def test_redirect_limit_is_enforced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        redirect_number = int(request.url.params.get("redirect", "0"))
        return httpx.Response(
            302,
            headers={"Location": f"{SOURCE_URL}?redirect={redirect_number + 1}"},
        )

    with pytest.raises(PdfDownloadError) as caught:
        await _download(
            httpx.MockTransport(handler), settings=_settings(max_redirects=1)
        )

    assert caught.value.reason is PdfDownloadFailure.REDIRECT_LIMIT_EXCEEDED


class _InterruptedStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"%PDF-1.7 partial"
        raise httpx.ReadError("fixture stream interrupted")


@pytest.mark.asyncio
async def test_interrupted_stream_returns_no_partial_document() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            stream=_InterruptedStream(),
        )

    with pytest.raises(PdfDownloadError) as caught:
        await _download(
            httpx.MockTransport(handler), settings=_settings(max_attempts=1)
        )

    assert caught.value.reason is PdfDownloadFailure.TRANSPORT
