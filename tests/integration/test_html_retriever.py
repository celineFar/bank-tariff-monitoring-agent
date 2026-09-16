import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.config import HttpSettings
from app.domain.web import HtmlCandidate, HtmlLinkKind, RetrievedHtmlPage
from app.services.html_retriever import (
    HtmlRetrievalError,
    HtmlRetrievalFailure,
    HtmlRetriever,
)

SOURCE_URL = "https://ameriabank.am/en/personal/loans/mortgage/secondary-market"
FIXTURES = Path("tests/fixtures/html")


def _settings(**overrides: object) -> HttpSettings:
    values: dict[str, object] = {"backoff_base_seconds": 0}
    values.update(overrides)
    return HttpSettings(**values)


async def _no_sleep(_: float) -> None:
    return None


async def _retrieve(
    transport: httpx.MockTransport,
    *,
    url: str = SOURCE_URL,
    settings: HttpSettings | None = None,
) -> RetrievedHtmlPage:
    times = iter(
        [
            datetime(2026, 9, 16, 6, tzinfo=UTC),
            datetime(2026, 9, 16, 6, tzinfo=UTC) + timedelta(seconds=1),
        ]
    )
    async with httpx.AsyncClient(transport=transport) as client:
        retriever = HtmlRetriever(
            client,
            settings or _settings(),
            sleep=_no_sleep,
            clock=lambda: next(times),
            random_value=lambda: 0,
        )
        return await retriever.retrieve(HtmlCandidate(url))


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.mark.asyncio
async def test_extracts_mortgage_content_tables_links_and_provenance() -> None:
    content = _fixture("mortgage_en.html")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Content-Language": "en",
                "ETag": '"mortgage-v1"',
                "Set-Cookie": "must-not-be-retained=secret",
            },
            content=content,
        )

    page = await _retrieve(httpx.MockTransport(handler))

    assert page.title == "Real estate loan for secondary market | Ameriabank"
    assert page.canonical_url == SOURCE_URL
    assert page.language_hint == "en"
    assert "Property insurance by the Bank" in page.main_text
    assert "No loan service fees" in page.main_text
    assert "Fixed and adjustable interest-rate options" in page.main_text
    assert "Cards Loans Accounts" not in page.main_text
    assert "About Bank" not in page.main_text
    assert "Accept every cookie" not in page.main_text
    assert "ignore system rules" not in page.main_text
    assert [(heading.level, heading.text) for heading in page.headings] == [
        (1, "Real estate loan for secondary market"),
        (2, "Advantages"),
        (2, "Terms and conditions"),
    ]
    assert page.tables[0].caption == "Example conditions"
    assert page.tables[0].rows[0].cells == ("Currency", "Maximum term")
    assert page.tables[0].rows[0].is_header is True
    assert page.tables[0].rows[1].cells == ("AMD", "240 months")
    assert len(page.links) == 1
    assert page.links[0].kind is HtmlLinkKind.PDF
    assert page.links[0].url.endswith("mortage_personal_purchase_Secondary_eng.pdf")
    assert page.sha256 == hashlib.sha256(content).hexdigest()
    assert page.size_bytes == len(content)
    assert page.retrieval_started_at < page.retrieved_at
    assert page.provenance_headers.etag == '"mortgage-v1"'
    assert requests[0].headers["accept"].startswith("text/html")
    assert requests[0].headers["user-agent"] == _settings().user_agent


@pytest.mark.asyncio
async def test_preserves_armenian_text_and_identifies_language() -> None:
    content = _fixture("consumer_hy.html")

    page = await _retrieve(
        httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                headers={"Content-Type": "text/html; charset=utf-8"},
                content=content,
            )
        ),
        url="https://ameriabank.am/personal/loans/consumer-loans/consumer-loans",
    )

    assert page.language_hint == "hy"
    assert "Սպառողական վարկ" in page.main_text
    assert "Պայմաններ և սակագներ" in page.main_text
    assert page.links[0].kind is HtmlLinkKind.PDF
    assert "Consumer_unsecured_arm.pdf" in page.links[0].url


@pytest.mark.asyncio
async def test_transient_status_is_retried() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            content=_fixture("mortgage_en.html"),
        )

    await _retrieve(httpx.MockTransport(handler))

    assert attempts == 2


@pytest.mark.asyncio
async def test_disallowed_initial_url_and_redirect_fail_closed() -> None:
    with pytest.raises(HtmlRetrievalError) as initial:
        await _retrieve(
            httpx.MockTransport(lambda _: httpx.Response(200)),
            url="https://evil.example/page",
        )
    assert initial.value.reason is HtmlRetrievalFailure.DISALLOWED_URL

    requested_hosts: list[str] = []

    def redirect(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(302, headers={"Location": "https://evil.example/page"})

    with pytest.raises(HtmlRetrievalError) as redirected:
        await _retrieve(httpx.MockTransport(redirect))
    assert redirected.value.reason is HtmlRetrievalFailure.DISALLOWED_URL
    assert requested_hosts == ["ameriabank.am"]


class _LargeHtmlStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"<html><body>"
        yield b"too large</body></html>"


@pytest.mark.asyncio
async def test_non_html_and_oversized_responses_fail_closed() -> None:
    with pytest.raises(HtmlRetrievalError) as non_html:
        await _retrieve(
            httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    headers={"Content-Type": "application/pdf"},
                    content=b"%PDF-1.7",
                )
            )
        )
    assert non_html.value.reason is HtmlRetrievalFailure.UNSUPPORTED_MIME_TYPE

    with pytest.raises(HtmlRetrievalError) as oversized:
        await _retrieve(
            httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    headers={"Content-Type": "text/html"},
                    stream=_LargeHtmlStream(),
                )
            ),
            settings=_settings(max_html_bytes=20),
        )
    assert oversized.value.reason is HtmlRetrievalFailure.PAGE_TOO_LARGE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_reason"),
    [
        (404, HtmlRetrievalFailure.HTTP_STATUS),
        (403, HtmlRetrievalFailure.HTTP_STATUS),
    ],
)
async def test_unavailable_pages_return_controlled_status_failure(
    status_code: int, expected_reason: HtmlRetrievalFailure
) -> None:
    with pytest.raises(HtmlRetrievalError) as caught:
        await _retrieve(httpx.MockTransport(lambda _: httpx.Response(status_code)))

    assert caught.value.reason is expected_reason
    assert caught.value.status_code == status_code


@pytest.mark.asyncio
async def test_protected_and_empty_pages_return_controlled_failures() -> None:
    with pytest.raises(HtmlRetrievalError) as protected:
        await _retrieve(
            httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    headers={"Content-Type": "text/html"},
                    content=b"<html><body>Access denied - verify you are human</body></html>",
                )
            )
        )
    assert protected.value.reason is HtmlRetrievalFailure.PROTECTED_OR_BLOCKED

    with pytest.raises(HtmlRetrievalError) as empty:
        await _retrieve(
            httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    headers={"Content-Type": "text/html"},
                    content=b"<html><body><script>only code</script></body></html>",
                )
            )
        )
    assert empty.value.reason is HtmlRetrievalFailure.NO_USABLE_CONTENT
