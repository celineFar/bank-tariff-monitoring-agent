import hashlib
from datetime import UTC, datetime

import pytest

from app.config import AcquisitionSettings
from app.domain.acquisition import (
    AcquisitionMode,
    NetworkPayload,
    SourceLocator,
    SourceType,
)
from app.services.acquisition import AcquisitionError, AcquisitionService
from app.services.artifact_store import FileSystemArtifactStore
from app.services.browser_renderer import RenderedPage
from app.services.html_parser import HtmlArtifactParser
from app.services.html_retriever import RetrievedHtml
from app.services.pdf_downloader import DownloadedPdf, PdfProvenanceHeaders

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
    def __init__(self) -> None:
        self.urls: list[str] = []

    async def download(self, candidate) -> DownloadedPdf:
        self.urls.append(candidate.url)
        content = b"%PDF-1.7 official"
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
    def __init__(self, rendered: RenderedPage) -> None:
        self.rendered = rendered
        self.calls: list[str] = []

    async def render(self, url: str) -> RenderedPage:
        self.calls.append(url)
        return self.rendered


def _service(tmp_path, html: str, *, settings=None, browser=None, pdf=None):
    return AcquisitionService(
        html_retriever=FakeHtmlRetriever(html),
        html_parser=HtmlArtifactParser(("ameriabank.am",)),
        pdf_downloader=pdf or FakePdfDownloader(),
        artifact_store=FileSystemArtifactStore(tmp_path),
        settings=settings or AcquisitionSettings(min_static_text_chars=10),
        browser_renderer=browser,
    )


@pytest.mark.asyncio
async def test_static_acquisition_preserves_content_and_downloads_pdf(tmp_path) -> None:
    html = """
    <html lang="en"><head><title>Consumer loan</title></head><body>
    <h1>Consumer loan</h1><p>Amount up to 10,000,000 AMD.</p>
    <a href="/terms.pdf">Official terms</a>
    </body></html>
    """
    pdf = FakePdfDownloader()

    artifact = await _service(tmp_path, html, pdf=pdf).acquire(
        "https://ameriabank.am/loan"
    )

    assert artifact.acquisition_mode is AcquisitionMode.STATIC
    assert artifact.raw_html == html
    assert artifact.rendered_html is None
    assert artifact.title == "Consumer loan"
    assert artifact.downloadable_documents[0].document_name == "Official terms"
    assert pdf.urls == ["https://ameriabank.am/terms.pdf"]
    assert {item.role for item in artifact.stored_artifacts} >= {
        "raw_html",
        "markdown",
        "linked_document_1",
    }
    assert len(artifact.content_hash) == 64


@pytest.mark.asyncio
async def test_interactive_page_uses_rendered_dom_and_network_payload(tmp_path) -> None:
    raw = """
    <html><body><button aria-expanded="false">See more</button>
    <p>Initial official content long enough.</p></body></html>
    """
    payload_body = '{"rate": 13}'
    payload = NetworkPayload(
        url="https://ameriabank.am/api/terms",
        method="GET",
        status_code=200,
        mime_type="application/json",
        body_text=payload_body,
        size_bytes=len(payload_body.encode()),
        sha256=hashlib.sha256(payload_body.encode()).hexdigest(),
        retrieved_at=NOW,
        locator=SourceLocator(
            source_url="https://ameriabank.am/api/terms",
            source_type=SourceType.API,
            json_path="$",
        ),
    )
    rendered_html = """
    <html><body><h1>Consumer loan</h1>
    <p>Expanded terms: annual rate 13% and term up to 60 months.</p>
    </body></html>
    """
    browser = FakeBrowserRenderer(
        RenderedPage(
            final_url="https://ameriabank.am/loan",
            html=rendered_html,
            title="Consumer loan",
            visible_text="Expanded terms",
            interactions=1,
            network_payloads=(payload,),
        )
    )

    artifact = await _service(tmp_path, raw, browser=browser).acquire(
        "https://ameriabank.am/loan"
    )

    assert artifact.acquisition_mode is AcquisitionMode.BROWSER
    assert artifact.rendered_html == rendered_html
    assert "Expanded terms" in artifact.markdown
    assert artifact.network_payloads[0].artifact is not None
    assert browser.calls == ["https://ameriabank.am/loan"]


@pytest.mark.asyncio
async def test_empty_browser_render_uses_useful_static_page(tmp_path) -> None:
    raw = """<html><body><button aria-expanded="false">Terms</button>
    <h1>Overdraft</h1><p>Official overdraft terms and rates are listed here.</p>
    </body></html>"""
    browser = FakeBrowserRenderer(
        RenderedPage(
            final_url="https://ameriabank.am/overdraft",
            html="<html><body></body></html>",
            title=None,
            visible_text="",
            interactions=0,
            network_payloads=(),
        )
    )

    artifact = await _service(tmp_path, raw, browser=browser).acquire(
        "https://ameriabank.am/overdraft"
    )

    assert artifact.acquisition_mode is AcquisitionMode.STATIC
    assert artifact.rendered_html is None
    assert "Official overdraft terms" in artifact.markdown
    assert "using static HTML" in artifact.warnings[0]
    assert browser.calls == ["https://ameriabank.am/overdraft"]


@pytest.mark.asyncio
async def test_insufficient_static_content_requires_browser(tmp_path) -> None:
    settings = AcquisitionSettings(
        browser_enabled=False,
        min_static_text_chars=100,
    )

    with pytest.raises(AcquisitionError, match="browser acquisition is disabled"):
        await _service(
            tmp_path,
            "<html><body><div id='root'></div></body></html>",
            settings=settings,
        ).acquire("https://ameriabank.am/loan")


@pytest.mark.asyncio
async def test_content_hash_is_stable_for_identical_source(tmp_path) -> None:
    html = "<html><body><h1>Loan</h1><p>Official amount 100 AMD.</p></body></html>"
    service = _service(tmp_path, html)

    first = await service.acquire("https://ameriabank.am/loan")
    second = await service.acquire("https://ameriabank.am/loan")

    assert first.content_hash == second.content_hash
