from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError

from app.config import load_settings
from app.services.pdf_downloader import (
    PdfCandidate,
    PdfDownloader,
    PdfDownloadError,
    PdfDownloadFailure,
)
from app.services.snapshot_lifecycle import detect_large_rate_changes

URL = "https://ameriabank.am/tariff.pdf"
PDF = b"%PDF-1.7 tariff"


def _rate(value: str) -> dict:
    return {
        "interest_rate": {
            "status": "found",
            "value": [{"value": {"min": value, "max": value}, "conditions": []}],
        }
    }


def test_two_percentage_points_is_flagged() -> None:
    settings = load_settings(_env_file=None, hitl_large_rate_change_percentage_points=2)
    threshold = Decimal(str(settings.hitl.large_rate_change_percentage_points))
    assert detect_large_rate_changes(_rate("21"), _rate("23"), threshold=threshold)
    assert (
        detect_large_rate_changes(_rate("21"), _rate("22.9"), threshold=threshold) == ()
    )


def test_limits_are_settings_with_bounds() -> None:
    settings = load_settings(
        _env_file=None,
        download_timeout_seconds=10,
        http_max_attempts=2,
        max_download_bytes=5 * 1024 * 1024,
    )
    assert (settings.http.timeout_seconds, settings.http.max_attempts) == (10, 2)
    with pytest.raises(ValidationError):
        load_settings(_env_file=None, http_max_attempts=9)  # bound: 1..5


def _downloader(statuses, **http):
    calls = []

    def handler(request):
        status = statuses[min(len(calls), len(statuses) - 1)]
        calls.append(status)
        return httpx.Response(
            status, content=PDF, headers={"content-type": "application/pdf"}
        )

    settings = load_settings(_env_file=None, http_backoff_base_seconds=0, **http).http

    async def no_sleep(_):
        return None

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return PdfDownloader(client, settings, sleep=no_sleep), calls


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [408, 503])
async def test_transient_status_is_retried(status) -> None:
    downloader, calls = _downloader([status, 200])
    result = await downloader.download(PdfCandidate(URL))
    assert result.content == PDF and calls == [status, 200]


@pytest.mark.asyncio
async def test_forbidden_is_not_retried() -> None:
    downloader, calls = _downloader([403, 200])
    with pytest.raises(PdfDownloadError):
        await downloader.download(PdfCandidate(URL))
    assert calls == [403]


@pytest.mark.asyncio
async def test_download_limit_rejects_a_bigger_file() -> None:
    downloader, _ = _downloader([200], max_download_bytes=10)
    with pytest.raises(PdfDownloadError) as error:
        await downloader.download(PdfCandidate(URL))
    assert error.value.reason is PdfDownloadFailure.DOCUMENT_TOO_LARGE
