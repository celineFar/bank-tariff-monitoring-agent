import hashlib
from datetime import UTC, datetime

import pytest

from app.config import AcquisitionSettings
from app.domain.acquisition import (
    AcquisitionMode,
    AcquisitionWarningCode,
    NetworkPayload,
    SourceLocator,
    SourceType,
)
from app.domain.monitoring import SourceFailureCode
from app.services.acquisition import (
    AcquisitionError,
    AcquisitionFailure,
    AcquisitionService,
)
from app.services.artifact_store import FileSystemArtifactStore
from app.services.browser_renderer import (
    BrowserRenderingError,
    BrowserRenderingFailure,
    RenderedPage,
)
from app.services.failure_mapping import source_failure_code
from app.services.html_parser import HtmlArtifactParser
from app.services.html_retriever import RetrievedHtml
from app.services.pdf_downloader import (
    DownloadedPdf,
    PdfDownloadError,
    PdfDownloadFailure,
    PdfProvenanceHeaders,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


class FakeHtmlRetriever:
    def __init__(self, html: str) -> None:
        self.html = html

    async def retrieve(self, url: str) -> RetrievedHtml:
        content = self.html.encode()
        return RetrievedHtml(
            source_url=url,
            final_url=url,
            mime_type="text/html",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            retrieval_started_at=NOW,
            retrieved_at=NOW,
            html=self.html,
        )


class FakePdfDownloader:
    def __init__(self, *, failing: frozenset[str] = frozenset()) -> None:
        self.urls: list[str] = []
        self.failing = failing

    async def download(self, candidate) -> DownloadedPdf:
        self.urls.append(candidate.url)
        if candidate.url in self.failing:
            raise PdfDownloadError(PdfDownloadFailure.TIMEOUT, "timed out")
        content = f"%PDF-1.7 official {candidate.url}".encode()
        return DownloadedPdf(
            source_url=candidate.url,
            final_url=candidate.url,
            mime_type="application/pdf",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            retrieval_started_at=NOW,
            retrieved_at=NOW,
            provenance_headers=PdfProvenanceHeaders(),
            content=content,
        )


class FakeBrowserRenderer:
    def __init__(
        self,
        rendered: RenderedPage | None = None,
        *,
        error: BrowserRenderingError | None = None,
    ) -> None:
        self.rendered = rendered
        self.error = error
        self.calls: list[str] = []

    async def render(self, url: str) -> RenderedPage:
        self.calls.append(url)
        if self.error is not None:
            raise self.error
        assert self.rendered is not None
        return self.rendered


STATIC = AcquisitionSettings(browser_enabled=False, min_main_content_chars=10)
BROWSER = AcquisitionSettings(browser_enabled=True, min_main_content_chars=10)

# ~9k characters of menus on every bank page: enough to pass the old
# "500 visible characters" check on its own.
SITE_CHROME = (
    "<header><nav>"
    + "".join(f"<a href='/menu/{index}'>Menu item {index}</a>" for index in range(400))
    + "</nav></header><footer><p>"
    + "Ameriabank footer text. " * 100
    + "</p></footer>"
)


def _service(tmp_path, html: str, *, settings=None, browser=None, pdf=None):
    return AcquisitionService(
        html_retriever=FakeHtmlRetriever(html),
        html_parser=HtmlArtifactParser(("ameriabank.am",)),
        pdf_downloader=pdf or FakePdfDownloader(),
        artifact_store=FileSystemArtifactStore(tmp_path),
        settings=settings or STATIC,
        browser_renderer=browser,
    )


def _rendered(html: str, *, payloads=(), **extra) -> RenderedPage:
    return RenderedPage(
        final_url="https://ameriabank.am/loan",
        html=html,
        title=None,
        visible_text="",
        interactions=extra.pop("interactions", 0),
        network_payloads=tuple(payloads),
        **extra,
    )


def _payload(url: str, body: str) -> NetworkPayload:
    return NetworkPayload(
        url=url,
        method="GET",
        status_code=200,
        mime_type="application/json",
        body_text=body,
        size_bytes=len(body.encode()),
        sha256=hashlib.sha256(body.encode()).hexdigest(),
        retrieved_at=NOW,
        locator=SourceLocator(
            source_url=url, source_type=SourceType.API, json_path="$"
        ),
    )


LOAN_PAGE = """
<html lang="en"><head><title>Consumer loan</title></head><body>
<h1>Consumer loan</h1><p>Amount up to 10,000,000 AMD.</p>
<a href="/terms.pdf">Official terms</a>
</body></html>
"""


@pytest.mark.asyncio
async def test_static_acquisition_preserves_content_and_downloads_pdf(tmp_path) -> None:
    pdf = FakePdfDownloader()

    artifact = await _service(tmp_path, LOAN_PAGE, pdf=pdf).acquire(
        "https://ameriabank.am/loan"
    )

    assert artifact.acquisition_mode is AcquisitionMode.STATIC
    assert artifact.raw_html == LOAN_PAGE
    assert artifact.rendered_html is None
    assert artifact.title == "Consumer loan"
    assert artifact.downloadable_documents[0].document_name == "Official terms"
    assert pdf.urls == ["https://ameriabank.am/terms.pdf"]
    assert {item.role for item in artifact.stored_artifacts} >= {
        "raw_html",
        "markdown",
        "linked_document_1",
    }
    assert artifact.inventory.pdf_links == 1
    assert artifact.warnings == ()
    assert len(artifact.content_hash) == 64


@pytest.mark.asyncio
async def test_rendered_page_supplies_the_dom_and_network_payload(tmp_path) -> None:
    payload = _payload("https://ameriabank.am/api/terms", '{"rate": 13}')
    rendered_html = """
    <html><body><h1>Consumer loan</h1>
    <p>Expanded terms: annual rate 13% and term up to 60 months.</p>
    </body></html>
    """
    browser = FakeBrowserRenderer(
        _rendered(rendered_html, payloads=(payload,), interactions=1)
    )

    artifact = await _service(
        tmp_path,
        "<html><body><p>Shell.</p></body></html>",
        settings=BROWSER,
        browser=browser,
    ).acquire("https://ameriabank.am/loan")

    assert artifact.acquisition_mode is AcquisitionMode.BROWSER
    assert artifact.rendered_html == rendered_html
    assert "Expanded terms" in artifact.markdown
    assert artifact.network_payloads[0].artifact is not None
    assert artifact.inventory.payloads == 1
    assert artifact.interactions == 1
    assert browser.calls == ["https://ameriabank.am/loan"]


@pytest.mark.asyncio
async def test_the_browser_renders_even_when_static_html_looks_complete(
    tmp_path,
) -> None:
    browser = FakeBrowserRenderer(_rendered(LOAN_PAGE))

    artifact = await _service(
        tmp_path, LOAN_PAGE, settings=BROWSER, browser=browser
    ).acquire("https://ameriabank.am/loan")

    assert artifact.acquisition_mode is AcquisitionMode.BROWSER
    assert browser.calls == ["https://ameriabank.am/loan"]


@pytest.mark.asyncio
async def test_an_empty_render_fails_instead_of_falling_back_to_static(
    tmp_path,
) -> None:
    # Static HTML that would have passed the old usefulness check on its own.
    raw = f"<html><body>{SITE_CHROME}{LOAN_PAGE}</body></html>"
    browser = FakeBrowserRenderer(_rendered("<html><body></body></html>"))

    with pytest.raises(AcquisitionError) as caught:
        await _service(tmp_path, raw, settings=BROWSER, browser=browser).acquire(
            "https://ameriabank.am/overdraft"
        )

    assert caught.value.reason is AcquisitionFailure.INCOMPLETE_CONTENT
    assert "no tables, PDF links or payloads" in caught.value.reasons
    assert (
        source_failure_code(caught.value, stage="acquisition")
        is SourceFailureCode.INCOMPLETE_CONTENT
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reason", "code"),
    [
        (BrowserRenderingFailure.INTERACTION, SourceFailureCode.BROWSER_FAILED),
        (BrowserRenderingFailure.NAVIGATION, SourceFailureCode.BROWSER_FAILED),
        (BrowserRenderingFailure.UNAVAILABLE, SourceFailureCode.BROWSER_UNAVAILABLE),
        (BrowserRenderingFailure.HTTP_STATUS, SourceFailureCode.HTTP_STATUS),
    ],
)
async def test_a_browser_failure_fails_with_a_typed_code_and_no_static_fallback(
    tmp_path, reason, code
) -> None:
    browser = FakeBrowserRenderer(error=BrowserRenderingError(reason, "failed"))

    with pytest.raises(AcquisitionError) as caught:
        await _service(tmp_path, LOAN_PAGE, settings=BROWSER, browser=browser).acquire(
            "https://ameriabank.am/loan"
        )

    assert caught.value.reason is AcquisitionFailure.BROWSER_FAILED
    assert source_failure_code(caught.value, stage="acquisition") is code


@pytest.mark.asyncio
async def test_an_enabled_browser_without_a_renderer_is_unavailable(tmp_path) -> None:
    with pytest.raises(AcquisitionError) as caught:
        await _service(tmp_path, LOAN_PAGE, settings=BROWSER).acquire(
            "https://ameriabank.am/loan"
        )

    assert caught.value.reason is AcquisitionFailure.BROWSER_UNAVAILABLE
    assert (
        source_failure_code(caught.value, stage="acquisition")
        is SourceFailureCode.BROWSER_UNAVAILABLE
    )


@pytest.mark.asyncio
async def test_site_chrome_does_not_count_as_main_content(tmp_path) -> None:
    settings = AcquisitionSettings(browser_enabled=False, min_main_content_chars=200)
    html = (
        f"<html><body>{SITE_CHROME}<main><h1>Loan</h1>"
        "<a href='/terms.pdf'>Terms</a></main></body></html>"
    )

    with pytest.raises(AcquisitionError) as caught:
        await _service(tmp_path, html, settings=settings).acquire(
            "https://ameriabank.am/loan"
        )

    assert caught.value.reason is AcquisitionFailure.INCOMPLETE_CONTENT
    assert caught.value.reasons[0].startswith("main_chars ")
    assert caught.value.reasons[0].endswith(" < 200")


@pytest.mark.asyncio
async def test_a_header_inside_the_content_is_not_site_chrome(tmp_path) -> None:
    settings = AcquisitionSettings(browser_enabled=False, min_main_content_chars=40)
    html = (
        "<html><body><main><article><header><p>"
        "Consumer loan up to AMD 15,000,000 at 16% a year."
        "</p></header><a href='/terms.pdf'>Terms</a></article></main></body></html>"
    )

    artifact = await _service(tmp_path, html, settings=settings).acquire(
        "https://ameriabank.am/loan"
    )

    assert artifact.inventory.main_chars >= 40


@pytest.mark.asyncio
async def test_text_without_any_tariff_structure_is_incomplete(tmp_path) -> None:
    html = "<html><body><main><p>" + "Long prose. " * 50 + "</p></main></body></html>"

    with pytest.raises(AcquisitionError) as caught:
        await _service(tmp_path, html).acquire("https://ameriabank.am/loan")

    assert caught.value.reasons == ("no tables, PDF links or payloads",)


@pytest.mark.asyncio
async def test_the_linked_document_cap_is_reported(tmp_path) -> None:
    links = "".join(f"<a href='/doc{index}.pdf'>Doc {index}</a>" for index in range(12))
    html = f"<html><body><main><p>Loan terms.</p>{links}</main></body></html>"
    settings = AcquisitionSettings(
        browser_enabled=False, min_main_content_chars=5, max_linked_documents=10
    )
    pdf = FakePdfDownloader()

    artifact = await _service(tmp_path, html, settings=settings, pdf=pdf).acquire(
        "https://ameriabank.am/loan"
    )

    assert len(pdf.urls) == 10
    assert artifact.inventory.pdf_links == 12
    (warning,) = artifact.warnings
    assert warning.code is AcquisitionWarningCode.LINKED_DOCUMENT_CAP_REACHED
    assert warning.detail.startswith("2 of 12")


@pytest.mark.asyncio
async def test_a_failed_linked_download_is_a_typed_warning(tmp_path) -> None:
    pdf = FakePdfDownloader(failing=frozenset({"https://ameriabank.am/terms.pdf"}))

    artifact = await _service(tmp_path, LOAN_PAGE, pdf=pdf).acquire(
        "https://ameriabank.am/loan"
    )

    (warning,) = artifact.warnings
    assert warning.code is AcquisitionWarningCode.LINKED_DOCUMENT_FAILED
    assert warning.detail.endswith("source.timeout")


@pytest.mark.asyncio
async def test_the_payload_cap_keeps_the_same_payloads_whatever_the_arrival_order(
    tmp_path,
) -> None:
    payloads = [
        _payload(f"https://ameriabank.am/api/{index:02d}", f'{{"n": {index}}}')
        for index in range(30)
    ]
    settings = AcquisitionSettings(
        browser_enabled=True, min_main_content_chars=5, max_network_payloads=25
    )
    page = "<html><body><main><p>Loan terms.</p></main></body></html>"

    kept = []
    for order in (payloads, list(reversed(payloads))):
        artifact = await _service(
            tmp_path,
            page,
            settings=settings,
            browser=FakeBrowserRenderer(_rendered(page, payloads=order)),
        ).acquire("https://ameriabank.am/loan")
        kept.append([payload.sha256 for payload in artifact.network_payloads])
        (warning,) = artifact.warnings
        assert warning.code is AcquisitionWarningCode.PAYLOAD_CAP_REACHED

    assert kept[0] == kept[1]
    assert len(kept[0]) == 25


@pytest.mark.asyncio
async def test_the_interaction_cap_is_reported(tmp_path) -> None:
    browser = FakeBrowserRenderer(
        _rendered(LOAN_PAGE, interactions=100, interaction_cap_reached=True)
    )

    artifact = await _service(
        tmp_path, LOAN_PAGE, settings=BROWSER, browser=browser
    ).acquire("https://ameriabank.am/loan")

    assert [warning.code for warning in artifact.warnings] == [
        AcquisitionWarningCode.INTERACTION_CAP_REACHED
    ]


@pytest.mark.asyncio
async def test_content_hash_is_stable_for_identical_source(tmp_path) -> None:
    service = _service(tmp_path, LOAN_PAGE)

    first = await service.acquire("https://ameriabank.am/loan")
    second = await service.acquire("https://ameriabank.am/loan")

    assert first.content_hash == second.content_hash
