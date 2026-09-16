from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

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

_PDF_MIME_TYPE = "application/pdf"
_PDF_SIGNATURE = b"%PDF-"


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


class PdfDownloader:
    """Download allowlisted PDFs through the shared restricted transport."""

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

    async def download(self, candidate: PdfCandidate) -> DownloadedPdf:
        try:
            response = await self._transport.fetch(
                candidate.url,
                accepted_mime_types={_PDF_MIME_TYPE},
                accept_header=_PDF_MIME_TYPE,
                max_bytes=self._settings.max_download_bytes,
            )
        except RestrictedHttpError as exc:
            raise PdfDownloadError(
                _pdf_failure(exc.reason),
                str(exc),
                status_code=exc.status_code,
            ) from exc

        if not response.content.startswith(_PDF_SIGNATURE):
            raise PdfDownloadError(
                PdfDownloadFailure.INVALID_PDF_SIGNATURE,
                "PDF response was empty or had an invalid signature",
            )

        return DownloadedPdf(
            source_url=response.source_url,
            final_url=response.final_url,
            mime_type=response.mime_type,
            size_bytes=response.size_bytes,
            sha256=response.sha256,
            retrieval_started_at=response.retrieval_started_at,
            retrieved_at=response.retrieved_at,
            provenance_headers=PdfProvenanceHeaders(
                etag=response.provenance_headers.etag,
                last_modified=response.provenance_headers.last_modified,
                content_disposition=response.provenance_headers.content_disposition,
            ),
            content=response.content,
        )


def _pdf_failure(reason: RestrictedHttpFailure) -> PdfDownloadFailure:
    if reason is RestrictedHttpFailure.RESPONSE_TOO_LARGE:
        return PdfDownloadFailure.DOCUMENT_TOO_LARGE
    return PdfDownloadFailure(reason.value)
