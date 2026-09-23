from __future__ import annotations

import asyncio
import hashlib
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urldefrag, urljoin

import httpx

from app.config import HttpSettings
from app.security.urls import DisallowedSourceUrl, validate_source_url

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], datetime]
RandomValue = Callable[[], float]


class HtmlRetrievalFailure(StrEnum):
    DISALLOWED_URL = "DISALLOWED_URL"
    HTTP_STATUS = "HTTP_STATUS"
    TIMEOUT = "TIMEOUT"
    TRANSPORT = "TRANSPORT"
    REDIRECT_WITHOUT_LOCATION = "REDIRECT_WITHOUT_LOCATION"
    REDIRECT_LIMIT_EXCEEDED = "REDIRECT_LIMIT_EXCEEDED"
    REDIRECT_LOOP = "REDIRECT_LOOP"
    INVALID_CONTENT_LENGTH = "INVALID_CONTENT_LENGTH"
    PAGE_TOO_LARGE = "PAGE_TOO_LARGE"
    UNSUPPORTED_MIME_TYPE = "UNSUPPORTED_MIME_TYPE"
    INVALID_ENCODING = "INVALID_ENCODING"


class HtmlRetrievalError(RuntimeError):
    def __init__(
        self,
        reason: HtmlRetrievalFailure,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class RetrievedHtml:
    source_url: str
    final_url: str
    mime_type: str
    size_bytes: int
    sha256: str
    retrieval_started_at: datetime
    retrieved_at: datetime
    html: str = field(repr=False)


class HtmlRetriever:
    """Retrieve allowlisted HTML with bounded redirects, retries, and bytes."""

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

    async def retrieve(self, url: str) -> RetrievedHtml:
        started_at = self._clock()
        source_url = self._validated_url(url)
        current_url = source_url
        visited: set[str] = set()
        redirects = 0

        while True:
            if current_url in visited:
                raise HtmlRetrievalError(
                    HtmlRetrievalFailure.REDIRECT_LOOP,
                    "HTML retrieval stopped because a redirect loop was detected",
                )
            visited.add(current_url)
            response = await self._request_with_retries(current_url)

            if response.status_code in _REDIRECT_STATUSES:
                location = response.headers.get("location")
                await response.aclose()
                if not location:
                    raise HtmlRetrievalError(
                        HtmlRetrievalFailure.REDIRECT_WITHOUT_LOCATION,
                        "HTML redirect did not include a Location header",
                    )
                redirects += 1
                if redirects > self._settings.max_redirects:
                    raise HtmlRetrievalError(
                        HtmlRetrievalFailure.REDIRECT_LIMIT_EXCEEDED,
                        "HTML retrieval exceeded the configured redirect limit",
                    )
                current_url = self._validated_url(urljoin(current_url, location))
                continue

            try:
                content, mime_type = await self._read_response(response)
            finally:
                await response.aclose()
            try:
                html = content.decode(response.encoding or "utf-8", errors="strict")
            except (LookupError, UnicodeDecodeError) as exc:
                raise HtmlRetrievalError(
                    HtmlRetrievalFailure.INVALID_ENCODING,
                    "HTML response could not be decoded safely",
                ) from exc
            return RetrievedHtml(
                source_url=source_url,
                final_url=current_url,
                mime_type=mime_type,
                size_bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                retrieval_started_at=started_at,
                retrieved_at=self._clock(),
                html=html,
            )

    async def _request_with_retries(self, url: str) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(1, self._settings.max_attempts + 1):
            request = self._client.build_request(
                "GET", url, headers={"User-Agent": self._settings.user_agent}
            )
            try:
                response = await self._client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt == self._settings.max_attempts:
                    raise HtmlRetrievalError(
                        HtmlRetrievalFailure.TIMEOUT,
                        "HTML retrieval timed out after bounded retries",
                    ) from exc
                await self._sleep(self._retry_delay(attempt))
                continue
            except httpx.TransportError as exc:
                last_error = exc
                if attempt == self._settings.max_attempts:
                    raise HtmlRetrievalError(
                        HtmlRetrievalFailure.TRANSPORT,
                        "HTML retrieval failed after bounded retries",
                    ) from exc
                await self._sleep(self._retry_delay(attempt))
                continue

            if response.status_code in _RETRYABLE_STATUSES:
                await response.aclose()
                if attempt < self._settings.max_attempts:
                    await self._sleep(self._retry_delay(attempt))
                    continue
            if response.status_code < 200 or response.status_code >= 400:
                status_code = response.status_code
                await response.aclose()
                raise HtmlRetrievalError(
                    HtmlRetrievalFailure.HTTP_STATUS,
                    f"HTML retrieval returned HTTP {status_code}",
                    status_code=status_code,
                )
            return response

        raise HtmlRetrievalError(
            HtmlRetrievalFailure.TRANSPORT,
            "HTML retrieval failed",
        ) from last_error

    async def _read_response(self, response: httpx.Response) -> tuple[bytes, str]:
        raw_length = response.headers.get("content-length")
        if raw_length:
            try:
                content_length = int(raw_length)
            except ValueError as exc:
                raise HtmlRetrievalError(
                    HtmlRetrievalFailure.INVALID_CONTENT_LENGTH,
                    "HTML response had an invalid Content-Length",
                ) from exc
            if content_length > self._settings.max_download_bytes:
                raise HtmlRetrievalError(
                    HtmlRetrievalFailure.PAGE_TOO_LARGE,
                    "HTML response exceeds the configured byte limit",
                )

        mime_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if mime_type != "text/html":
            raise HtmlRetrievalError(
                HtmlRetrievalFailure.UNSUPPORTED_MIME_TYPE,
                "HTML response did not use the text/html MIME type",
            )

        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > self._settings.max_download_bytes:
                raise HtmlRetrievalError(
                    HtmlRetrievalFailure.PAGE_TOO_LARGE,
                    "HTML response exceeds the configured byte limit",
                )
            chunks.append(chunk)
        return b"".join(chunks), mime_type

    def _validated_url(self, url: str) -> str:
        try:
            validated = validate_source_url(url, self._settings.allowed_source_hosts)
        except DisallowedSourceUrl as exc:
            raise HtmlRetrievalError(
                HtmlRetrievalFailure.DISALLOWED_URL,
                f"HTML retrieval rejected an unsafe source URL: {exc}",
            ) from exc
        return urldefrag(validated).url

    def _retry_delay(self, attempt: int) -> float:
        base = self._settings.backoff_base_seconds * (2 ** (attempt - 1))
        jitter = base * self._settings.retry_jitter_ratio * self._random_value()
        return min(base + jitter, self._settings.max_retry_delay_seconds)
