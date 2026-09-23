import httpx
import pytest

from app.config import HttpSettings
from app.services.html_retriever import (
    HtmlRetrievalError,
    HtmlRetrievalFailure,
    HtmlRetriever,
)


async def _no_sleep(_: float) -> None:
    return None


def _settings(**overrides: object) -> HttpSettings:
    return HttpSettings(
        allowed_source_hosts=("ameriabank.am",),
        max_download_bytes=100,
        backoff_base_seconds=0,
        retry_jitter_ratio=0,
        **overrides,
    )


@pytest.mark.asyncio
async def test_retrieves_html_and_follows_only_allowlisted_redirects() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/loan"})
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content="<p>Վարկ 13%</p>".encode(),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await HtmlRetriever(client, _settings(), sleep=_no_sleep).retrieve(
            "https://ameriabank.am/start#fragment"
        )

    assert calls == [
        "https://ameriabank.am/start",
        "https://ameriabank.am/loan",
    ]
    assert result.final_url == "https://ameriabank.am/loan"
    assert result.html == "<p>Վարկ 13%</p>"
    assert len(result.sha256) == 64


@pytest.mark.asyncio
async def test_rejects_disallowed_redirect_before_requesting_target() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(302, headers={"location": "https://evil.example/x"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(HtmlRetrievalError) as error:
            await HtmlRetriever(client, _settings(), sleep=_no_sleep).retrieve(
                "https://ameriabank.am/start"
            )

    assert error.value.reason is HtmlRetrievalFailure.DISALLOWED_URL
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("headers", "body", "reason"),
    [
        (
            {"content-type": "application/json"},
            b"{}",
            HtmlRetrievalFailure.UNSUPPORTED_MIME_TYPE,
        ),
        (
            {"content-type": "text/html", "content-length": "101"},
            b"",
            HtmlRetrievalFailure.PAGE_TOO_LARGE,
        ),
        (
            {"content-type": "text/html"},
            b"x" * 101,
            HtmlRetrievalFailure.PAGE_TOO_LARGE,
        ),
    ],
)
async def test_rejects_unsupported_or_oversized_content(
    headers: dict[str, str], body: bytes, reason: HtmlRetrievalFailure
) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers=headers, content=body)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(HtmlRetrievalError) as error:
            await HtmlRetriever(client, _settings(), sleep=_no_sleep).retrieve(
                "https://ameriabank.am/loan"
            )

    assert error.value.reason is reason


@pytest.mark.asyncio
async def test_retries_transient_status_with_bound() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=b"<p>ok</p>"
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await HtmlRetriever(client, _settings(), sleep=_no_sleep).retrieve(
            "https://ameriabank.am/loan"
        )

    assert result.html == "<p>ok</p>"
    assert calls == 2
