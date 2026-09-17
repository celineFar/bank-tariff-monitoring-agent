from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.config import HttpSettings
from app.services.restricted_http import (
    Clock,
    RandomValue,
    RestrictedHttpError,
    RestrictedHttpFailure,
    RestrictedHttpTransport,
    Sleep,
)

DOCUMENT_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)
_OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


class DocumentDownloadError(RuntimeError):
    def __init__(
        self,
        reason: str,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class DocumentCandidate:
    url: str


@dataclass(frozen=True, slots=True)
class DownloadedDocument:
    source_url: str
    final_url: str
    mime_type: str
    size_bytes: int
    sha256: str
    retrieval_started_at: datetime
    retrieved_at: datetime
    retry_count: int
    content: bytes = field(repr=False)


class DocumentDownloader:
    """Download validated PDF or Office attachments discovered during crawling."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: HttpSettings,
        *,
        sleep: Sleep | None = None,
        clock: Clock | None = None,
        random_value: RandomValue | None = None,
    ) -> None:
        self._transport = RestrictedHttpTransport(
            client,
            settings,
            sleep=sleep or asyncio.sleep,
            clock=clock,
            random_value=random_value or random.random,
        )
        self._settings = settings

    async def download(self, candidate: DocumentCandidate) -> DownloadedDocument:
        accepted = DOCUMENT_MIME_TYPES.intersection(
            self._settings.allowed_download_mime_types
        )
        if not accepted:
            raise DocumentDownloadError(
                "UNSUPPORTED_MIME_TYPE",
                "No document MIME types are enabled by configuration",
            )
        try:
            response = await self._transport.fetch(
                candidate.url,
                accepted_mime_types=accepted,
                accept_header=", ".join(sorted(accepted)),
                max_bytes=self._settings.max_download_bytes,
            )
        except RestrictedHttpError as exc:
            reason = (
                "DOCUMENT_TOO_LARGE"
                if exc.reason is RestrictedHttpFailure.RESPONSE_TOO_LARGE
                else exc.reason.value
            )
            raise DocumentDownloadError(
                reason, str(exc), status_code=exc.status_code
            ) from exc

        if not _valid_signature(response.mime_type, response.content):
            raise DocumentDownloadError(
                "INVALID_DOCUMENT_SIGNATURE",
                "Document bytes do not match the declared supported content type",
            )
        return DownloadedDocument(
            source_url=response.source_url,
            final_url=response.final_url,
            mime_type=response.mime_type,
            size_bytes=response.size_bytes,
            sha256=response.sha256,
            retrieval_started_at=response.retrieval_started_at,
            retrieved_at=response.retrieved_at,
            retry_count=response.retry_count,
            content=response.content,
        )


def _valid_signature(mime_type: str, content: bytes) -> bool:
    if mime_type == "application/pdf":
        return content.startswith(b"%PDF-")
    if mime_type in {"application/msword", "application/vnd.ms-excel"}:
        return content.startswith(_OLE_SIGNATURE)
    return content.startswith(_ZIP_SIGNATURES)
