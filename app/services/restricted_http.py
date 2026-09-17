from __future__ import annotations

import asyncio
import hashlib
import random
from collections.abc import Awaitable, Callable, Collection
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from urllib.parse import urldefrag, urljoin

import httpx

from app.config import HttpSettings
from app.security.urls import DisallowedSourceUrl, validate_source_url

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_PROVENANCE_HEADER_LENGTH = 512

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], datetime]
RandomValue = Callable[[], float]


class RestrictedHttpFailure(StrEnum):
    DISALLOWED_URL = "DISALLOWED_URL"
    HTTP_STATUS = "HTTP_STATUS"
    TIMEOUT = "TIMEOUT"
    TRANSPORT = "TRANSPORT"
    REDIRECT_WITHOUT_LOCATION = "REDIRECT_WITHOUT_LOCATION"
    REDIRECT_LIMIT_EXCEEDED = "REDIRECT_LIMIT_EXCEEDED"
    REDIRECT_LOOP = "REDIRECT_LOOP"
    INVALID_CONTENT_LENGTH = "INVALID_CONTENT_LENGTH"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    UNSUPPORTED_MIME_TYPE = "UNSUPPORTED_MIME_TYPE"


class RestrictedHttpError(RuntimeError):
    """Controlled HTTP failure that never includes response content."""

    def __init__(
        self,
        reason: RestrictedHttpFailure,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class HttpProvenanceHeaders:
    etag: str | None = None
    last_modified: str | None = None
    content_disposition: str | None = None
    content_language: str | None = None


@dataclass(frozen=True, slots=True)
class RestrictedHttpResponse:
    source_url: str
    final_url: str
    mime_type: str
    size_bytes: int
    sha256: str
    retrieval_started_at: datetime
    retrieved_at: datetime
    retry_count: int
    provenance_headers: HttpProvenanceHeaders
    content: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class _Redirect:
    location: str


@dataclass(frozen=True, slots=True)
class _RetryableStatus:
    status_code: int
    retry_after: str | None


@dataclass(frozen=True, slots=True)
class _Payload:
    content: bytes
    mime_type: str
    sha256: str
    provenance_headers: HttpProvenanceHeaders


class RestrictedHttpTransport:
    """Allowlisted, bounded transport shared by deterministic retrievers."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: HttpSettings,
        *,
        sleep: Sleep = asyncio.sleep,
        clock: Clock | None = None,
        random_value: RandomValue = random.random,
    ) -> None:
        self._client = client
        self._settings = settings
        self._sleep = sleep
        self._clock = clock or (lambda: datetime.now(UTC))
        self._random_value = random_value

    async def fetch(
        self,
        url: str,
        *,
        accepted_mime_types: Collection[str],
        accept_header: str,
        max_bytes: int,
    ) -> RestrictedHttpResponse:
        allowed_mime_types = frozenset(
            value.strip().lower() for value in accepted_mime_types
        )
        if not allowed_mime_types:
            raise ValueError("at least one accepted MIME type is required")

        started_at = self._clock()
        source_url = self._validated_url(url)
        current_url = source_url
        visited: set[str] = set()
        redirect_count = 0
        retry_count = 0

        while True:
            if current_url in visited:
                raise RestrictedHttpError(
                    RestrictedHttpFailure.REDIRECT_LOOP,
                    "HTTP retrieval stopped because a redirect loop was detected",
                )
            visited.add(current_url)

            result, attempts = await self._request_with_retries(
                current_url,
                accepted_mime_types=allowed_mime_types,
                accept_header=accept_header,
                max_bytes=max_bytes,
            )
            retry_count += attempts - 1
            if isinstance(result, _Redirect):
                target_url = self._validated_url(urljoin(current_url, result.location))
                redirect_count += 1
                if redirect_count > self._settings.max_redirects:
                    raise RestrictedHttpError(
                        RestrictedHttpFailure.REDIRECT_LIMIT_EXCEEDED,
                        "HTTP retrieval exceeded the configured redirect limit",
                    )
                current_url = target_url
                continue

            return RestrictedHttpResponse(
                source_url=source_url,
                final_url=current_url,
                mime_type=result.mime_type,
                size_bytes=len(result.content),
                sha256=result.sha256,
                retrieval_started_at=started_at,
                retrieved_at=self._clock(),
                retry_count=retry_count,
                provenance_headers=result.provenance_headers,
                content=result.content,
            )

    def _validated_url(self, url: str) -> str:
        try:
            validated = validate_source_url(url, self._settings.allowed_source_hosts)
        except DisallowedSourceUrl as exc:
            raise RestrictedHttpError(
                RestrictedHttpFailure.DISALLOWED_URL,
                f"HTTP retrieval rejected an unsafe source URL: {exc}",
            ) from exc
        return urldefrag(validated).url

    async def _request_with_retries(
        self,
        url: str,
        *,
        accepted_mime_types: frozenset[str],
        accept_header: str,
        max_bytes: int,
    ) -> tuple[_Redirect | _Payload, int]:
        for attempt in range(1, self._settings.max_attempts + 1):
            try:
                result = await self._request_once(
                    url,
                    accepted_mime_types=accepted_mime_types,
                    accept_header=accept_header,
                    max_bytes=max_bytes,
                )
            except httpx.TimeoutException as exc:
                if attempt == self._settings.max_attempts:
                    raise RestrictedHttpError(
                        RestrictedHttpFailure.TIMEOUT,
                        "HTTP retrieval exhausted its timeout retries",
                    ) from exc
                await self._backoff(attempt)
                continue
            except httpx.TransportError as exc:
                if attempt == self._settings.max_attempts:
                    raise RestrictedHttpError(
                        RestrictedHttpFailure.TRANSPORT,
                        "HTTP retrieval exhausted its transport retries",
                    ) from exc
                await self._backoff(attempt)
                continue

            if isinstance(result, _RetryableStatus):
                if attempt == self._settings.max_attempts:
                    raise RestrictedHttpError(
                        RestrictedHttpFailure.HTTP_STATUS,
                        "HTTP retrieval exhausted retries for a transient status",
                        status_code=result.status_code,
                    )
                await self._backoff(attempt, retry_after=result.retry_after)
                continue
            return result, attempt

        raise AssertionError("retry loop exited unexpectedly")

    async def _request_once(
        self,
        url: str,
        *,
        accepted_mime_types: frozenset[str],
        accept_header: str,
        max_bytes: int,
    ) -> _Redirect | _RetryableStatus | _Payload:
        async with self._client.stream(
            "GET",
            url,
            headers={
                "Accept": accept_header,
                "User-Agent": self._settings.user_agent,
            },
            follow_redirects=False,
            timeout=self._settings.timeout_seconds,
        ) as response:
            if response.status_code in _REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    raise RestrictedHttpError(
                        RestrictedHttpFailure.REDIRECT_WITHOUT_LOCATION,
                        "HTTP redirect did not provide a Location header",
                        status_code=response.status_code,
                    )
                return _Redirect(location=location)

            if response.status_code == 429 or 500 <= response.status_code <= 599:
                return _RetryableStatus(
                    status_code=response.status_code,
                    retry_after=response.headers.get("retry-after"),
                )
            if response.status_code != 200:
                raise RestrictedHttpError(
                    RestrictedHttpFailure.HTTP_STATUS,
                    "HTTP retrieval returned a non-success status",
                    status_code=response.status_code,
                )

            mime_type = response.headers.get("content-type", "").partition(";")[0]
            mime_type = mime_type.strip().lower()
            configured_mime_types = set(self._settings.allowed_download_mime_types)
            if (
                mime_type not in accepted_mime_types
                or mime_type not in configured_mime_types
            ):
                raise RestrictedHttpError(
                    RestrictedHttpFailure.UNSUPPORTED_MIME_TYPE,
                    "HTTP retrieval returned an unsupported content type",
                )

            self._validate_content_length(
                response.headers.get("content-length"), max_bytes=max_bytes
            )
            return await self._read_body(response, mime_type, max_bytes=max_bytes)

    @staticmethod
    def _validate_content_length(raw_value: str | None, *, max_bytes: int) -> None:
        if raw_value is None:
            return
        try:
            content_length = int(raw_value)
        except ValueError as exc:
            raise RestrictedHttpError(
                RestrictedHttpFailure.INVALID_CONTENT_LENGTH,
                "HTTP response contained an invalid Content-Length header",
            ) from exc
        if content_length < 0:
            raise RestrictedHttpError(
                RestrictedHttpFailure.INVALID_CONTENT_LENGTH,
                "HTTP response contained a negative Content-Length header",
            )
        if content_length > max_bytes:
            raise RestrictedHttpError(
                RestrictedHttpFailure.RESPONSE_TOO_LARGE,
                "HTTP response exceeded the configured byte limit",
            )

    @staticmethod
    async def _read_body(
        response: httpx.Response, mime_type: str, *, max_bytes: int
    ) -> _Payload:
        content = bytearray()
        checksum = hashlib.sha256()

        async for chunk in response.aiter_bytes():
            if not chunk:
                continue
            if len(content) + len(chunk) > max_bytes:
                raise RestrictedHttpError(
                    RestrictedHttpFailure.RESPONSE_TOO_LARGE,
                    "HTTP response exceeded the configured byte limit while streaming",
                )
            content.extend(chunk)
            checksum.update(chunk)

        return _Payload(
            content=bytes(content),
            mime_type=mime_type,
            sha256=checksum.hexdigest(),
            provenance_headers=_safe_provenance_headers(response.headers),
        )

    async def _backoff(
        self, failed_attempt: int, *, retry_after: str | None = None
    ) -> None:
        exponential_delay = self._settings.backoff_base_seconds * (
            2 ** (failed_attempt - 1)
        )
        random_fraction = min(max(self._random_value(), 0.0), 1.0)
        jitter = exponential_delay * self._settings.retry_jitter_ratio * random_fraction
        client_delay = exponential_delay + jitter
        server_delay = (
            _parse_retry_after(retry_after, now=self._clock())
            if retry_after is not None
            else None
        )
        delay = min(
            max(client_delay, server_delay or 0),
            self._settings.max_retry_delay_seconds,
        )
        await self._sleep(delay)


def _safe_provenance_headers(headers: httpx.Headers) -> HttpProvenanceHeaders:
    return HttpProvenanceHeaders(
        etag=_safe_header(headers.get("etag")),
        last_modified=_safe_header(headers.get("last-modified")),
        content_disposition=_safe_header(headers.get("content-disposition")),
        content_language=_safe_header(headers.get("content-language")),
    )


def _safe_header(value: str | None) -> str | None:
    if value is None or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        return None
    return value.strip()[:_MAX_PROVENANCE_HEADER_LENGTH] or None


def _parse_retry_after(value: str | None, *, now: datetime) -> float | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized.isascii() and normalized.isdigit():
        try:
            return float(int(normalized))
        except (ValueError, OverflowError):
            return None
    try:
        retry_at = parsedate_to_datetime(normalized)
    except (TypeError, ValueError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return max((retry_at.astimezone(UTC) - now.astimezone(UTC)).total_seconds(), 0)
