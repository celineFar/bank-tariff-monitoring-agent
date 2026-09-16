from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urldefrag, urljoin

import httpx

from app.config import HttpSettings
from app.security.urls import DisallowedSourceUrl, validate_source_url

_PDF_MIME_TYPE = "application/pdf"
_PDF_SIGNATURE = b"%PDF-"
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_PROVENANCE_HEADER_LENGTH = 512

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], datetime]


class PdfDownloadFailure(StrEnum):
    DISALLOWED_URL = "DISALLOWED_URL"
    HTTP_STATUS = "HTTP_STATUS"
    TIMEOUT = "TIMEOUT"
    TRANSPORT = "TRANSPORT"
    REDIRECT_WITHOUT_LOCATION = "REDIRECT_WITHOUT_LOCATION"
    REDIRECT_LIMIT_EXCEEDED = "REDIRECT_LIMIT_EXCEEDED"
    REDIRECT_LOOP = "REDIRECT_LOOP"
    INVALID_CONTENT_LENGTH = "INVALID_CONTENT_LENGTH"
    DOCUMENT_TOO_LARGE = "DOCUMENT_TOO_LARGE"
    UNSUPPORTED_MIME_TYPE = "UNSUPPORTED_MIME_TYPE"
    INVALID_PDF_SIGNATURE = "INVALID_PDF_SIGNATURE"


class PdfDownloadError(RuntimeError):
    """Controlled downloader failure without response-body or credential leakage."""

    def __init__(
        self,
        reason: PdfDownloadFailure,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class PdfCandidate:
    """A PDF URL emitted by the official-source discovery boundary."""

    url: str


@dataclass(frozen=True, slots=True)
class PdfProvenanceHeaders:
    etag: str | None = None
    last_modified: str | None = None
    content_disposition: str | None = None


@dataclass(frozen=True, slots=True)
class DownloadedPdf:
    source_url: str
    final_url: str
    mime_type: str
    size_bytes: int
    sha256: str
    retrieval_started_at: datetime
    retrieved_at: datetime
    provenance_headers: PdfProvenanceHeaders
    content: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class _Redirect:
    location: str


@dataclass(frozen=True, slots=True)
class _RetryableStatus:
    status_code: int


@dataclass(frozen=True, slots=True)
class _PdfPayload:
    content: bytes
    mime_type: str
    sha256: str
    provenance_headers: PdfProvenanceHeaders


class PdfDownloader:
    """Download allowlisted PDFs through a caller-owned async HTTP client."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: HttpSettings,
        *,
        sleep: Sleep = asyncio.sleep,
        clock: Clock | None = None,
    ) -> None:
        self._client = client
        self._settings = settings
        self._sleep = sleep
        self._clock = clock or (lambda: datetime.now(UTC))

    async def download(self, candidate: PdfCandidate) -> DownloadedPdf:
        started_at = self._clock()
        source_url = self._validated_url(candidate.url)
        current_url = source_url
        visited: set[str] = set()
        redirect_count = 0

        while True:
            if current_url in visited:
                raise PdfDownloadError(
                    PdfDownloadFailure.REDIRECT_LOOP,
                    "PDF download stopped because a redirect loop was detected",
                )
            visited.add(current_url)

            result = await self._request_with_retries(current_url)
            if isinstance(result, _Redirect):
                target_url = self._validated_url(urljoin(current_url, result.location))
                redirect_count += 1
                if redirect_count > self._settings.max_redirects:
                    raise PdfDownloadError(
                        PdfDownloadFailure.REDIRECT_LIMIT_EXCEEDED,
                        "PDF download exceeded the configured redirect limit",
                    )
                current_url = target_url
                continue

            return DownloadedPdf(
                source_url=source_url,
                final_url=current_url,
                mime_type=result.mime_type,
                size_bytes=len(result.content),
                sha256=result.sha256,
                retrieval_started_at=started_at,
                retrieved_at=self._clock(),
                provenance_headers=result.provenance_headers,
                content=result.content,
            )

    def _validated_url(self, url: str) -> str:
        try:
            validated = validate_source_url(url, self._settings.allowed_source_hosts)
        except DisallowedSourceUrl as exc:
            raise PdfDownloadError(
                PdfDownloadFailure.DISALLOWED_URL,
                f"PDF download rejected an unsafe source URL: {exc}",
            ) from exc
        return urldefrag(validated).url

    async def _request_with_retries(self, url: str) -> _Redirect | _PdfPayload:
        for attempt in range(1, self._settings.max_attempts + 1):
            try:
                result = await self._request_once(url)
            except httpx.TimeoutException as exc:
                if attempt == self._settings.max_attempts:
                    raise PdfDownloadError(
                        PdfDownloadFailure.TIMEOUT,
                        "PDF download exhausted its timeout retries",
                    ) from exc
                await self._backoff(attempt)
                continue
            except httpx.TransportError as exc:
                if attempt == self._settings.max_attempts:
                    raise PdfDownloadError(
                        PdfDownloadFailure.TRANSPORT,
                        "PDF download exhausted its transport retries",
                    ) from exc
                await self._backoff(attempt)
                continue

            if isinstance(result, _RetryableStatus):
                if attempt == self._settings.max_attempts:
                    raise PdfDownloadError(
                        PdfDownloadFailure.HTTP_STATUS,
                        "PDF download exhausted retries for a transient HTTP status",
                        status_code=result.status_code,
                    )
                await self._backoff(attempt)
                continue
            return result

        raise AssertionError("retry loop exited unexpectedly")

    async def _request_once(
        self, url: str
    ) -> _Redirect | _RetryableStatus | _PdfPayload:
        async with self._client.stream(
            "GET",
            url,
            headers={
                "Accept": _PDF_MIME_TYPE,
                "User-Agent": self._settings.user_agent,
            },
            follow_redirects=False,
            timeout=self._settings.timeout_seconds,
        ) as response:
            if response.status_code in _REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    raise PdfDownloadError(
                        PdfDownloadFailure.REDIRECT_WITHOUT_LOCATION,
                        "PDF redirect did not provide a Location header",
                        status_code=response.status_code,
                    )
                return _Redirect(location=location)

            if response.status_code == 429 or 500 <= response.status_code <= 599:
                return _RetryableStatus(status_code=response.status_code)
            if response.status_code != 200:
                raise PdfDownloadError(
                    PdfDownloadFailure.HTTP_STATUS,
                    "PDF download returned a non-success HTTP status",
                    status_code=response.status_code,
                )

            mime_type = response.headers.get("content-type", "").partition(";")[0]
            mime_type = mime_type.strip().lower()
            if (
                mime_type != _PDF_MIME_TYPE
                or mime_type not in self._settings.allowed_download_mime_types
            ):
                raise PdfDownloadError(
                    PdfDownloadFailure.UNSUPPORTED_MIME_TYPE,
                    "PDF download returned an unsupported content type",
                )

            self._validate_content_length(response.headers.get("content-length"))
            return await self._read_pdf(response, mime_type)

    def _validate_content_length(self, raw_value: str | None) -> None:
        if raw_value is None:
            return
        try:
            content_length = int(raw_value)
        except ValueError as exc:
            raise PdfDownloadError(
                PdfDownloadFailure.INVALID_CONTENT_LENGTH,
                "PDF response contained an invalid Content-Length header",
            ) from exc
        if content_length < 0:
            raise PdfDownloadError(
                PdfDownloadFailure.INVALID_CONTENT_LENGTH,
                "PDF response contained a negative Content-Length header",
            )
        if content_length > self._settings.max_download_bytes:
            raise PdfDownloadError(
                PdfDownloadFailure.DOCUMENT_TOO_LARGE,
                "PDF response exceeded the configured byte limit",
            )

    async def _read_pdf(self, response: httpx.Response, mime_type: str) -> _PdfPayload:
        content = bytearray()
        checksum = hashlib.sha256()

        async for chunk in response.aiter_bytes():
            if not chunk:
                continue
            if len(content) + len(chunk) > self._settings.max_download_bytes:
                raise PdfDownloadError(
                    PdfDownloadFailure.DOCUMENT_TOO_LARGE,
                    "PDF response exceeded the configured byte limit while streaming",
                )
            content.extend(chunk)
            checksum.update(chunk)
            if len(content) >= len(_PDF_SIGNATURE) and not content.startswith(
                _PDF_SIGNATURE
            ):
                raise PdfDownloadError(
                    PdfDownloadFailure.INVALID_PDF_SIGNATURE,
                    "PDF response content did not match the declared file type",
                )

        if not content.startswith(_PDF_SIGNATURE):
            raise PdfDownloadError(
                PdfDownloadFailure.INVALID_PDF_SIGNATURE,
                "PDF response was empty or had an invalid signature",
            )

        return _PdfPayload(
            content=bytes(content),
            mime_type=mime_type,
            sha256=checksum.hexdigest(),
            provenance_headers=_safe_provenance_headers(response.headers),
        )

    async def _backoff(self, failed_attempt: int) -> None:
        delay = min(
            self._settings.backoff_base_seconds * (2 ** (failed_attempt - 1)),
            self._settings.timeout_seconds,
        )
        await self._sleep(delay)


def _safe_provenance_headers(headers: httpx.Headers) -> PdfProvenanceHeaders:
    return PdfProvenanceHeaders(
        etag=_safe_header(headers.get("etag")),
        last_modified=_safe_header(headers.get("last-modified")),
        content_disposition=_safe_header(headers.get("content-disposition")),
    )


def _safe_header(value: str | None) -> str | None:
    if value is None or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        return None
    return value.strip()[:_MAX_PROVENANCE_HEADER_LENGTH] or None
