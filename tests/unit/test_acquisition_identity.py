"""Two acquisitions of unchanged content must produce the same identities.

Every content-addressed cache downstream -- source discovery, semantic
extraction, embeddings -- is keyed on identities derived here. When an identity
drifts between runs over content that did not change, each of those caches
misses and the run pays for a full re-extraction.
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import AcquisitionSettings
from app.services.acquisition import AcquisitionService
from app.services.artifact_store import FileSystemArtifactStore
from app.services.browser_renderer import RenderedPage
from app.services.html_parser import HtmlArtifactParser
from app.services.html_retriever import RetrievedHtml
from app.services.normalization import (
    NoPdfExtractor,
    StructuralNormalizationService,
)
from app.services.pdf_downloader import DownloadedPdf, PdfProvenanceHeaders

NOW = datetime(2026, 9, 18, tzinfo=UTC)


class _Retriever:
    def __init__(self, html: str) -> None:
        self._html = html

    async def retrieve(self, url: str) -> RetrievedHtml:
        content = self._html.encode()
        return RetrievedHtml(
            source_url=url,
            final_url=url,
            mime_type="text/html",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            retrieval_started_at=NOW,
            retrieved_at=NOW,
            html=self._html,
        )


class _PdfDownloader:
    def __init__(self, content: bytes = b"%PDF-1.7 official") -> None:
        self.content = content

    async def download(self, candidate) -> DownloadedPdf:
        return DownloadedPdf(
            source_url=candidate.url,
            final_url=candidate.url,
            mime_type="application/pdf",
            size_bytes=len(self.content),
            sha256=hashlib.sha256(self.content).hexdigest(),
            retrieval_started_at=NOW,
            retrieved_at=NOW,
            provenance_headers=PdfProvenanceHeaders(),
            content=self.content,
        )


class _Browser:
    def __init__(self, html: str) -> None:
        self._html = html

    async def render(self, url: str) -> RenderedPage:
        return RenderedPage(
            final_url=url,
            html=self._html,
            title="Overdraft",
            visible_text="Expanded terms",
            interactions=1,
        )


def _service(tmp_path, html: str, *, browser=None, pdf=None) -> AcquisitionService:
    return AcquisitionService(
        html_retriever=_Retriever(html),
        html_parser=HtmlArtifactParser(("ameriabank.am",)),
        pdf_downloader=pdf or _PdfDownloader(),
        artifact_store=FileSystemArtifactStore(tmp_path),
        settings=AcquisitionSettings(
            browser_enabled=browser is not None, min_main_content_chars=10
        ),
        browser_renderer=browser,
    )


@pytest.mark.asyncio
async def test_a_revised_linked_document_does_not_rename_the_page(tmp_path) -> None:
    html = """
    <html lang="en"><head><title>Overdraft</title></head><body>
    <h1>Overdraft</h1><p>Amount up to 10,000,000 AMD.</p>
    <a href="/terms.pdf">Official terms</a>
    </body></html>
    """

    original = await _service(tmp_path, html).acquire("https://ameriabank.am/overdraft")
    revised = await _service(
        tmp_path, html, pdf=_PdfDownloader(b"%PDF-1.7 revised")
    ).acquire("https://ameriabank.am/overdraft")

    # The acquisition as a whole changed, and its content hash says so...
    assert original.content_hash != revised.content_hash
    # ...but the page's own markup did not, so the page document keeps its name
    # and the evidence quoted from it keeps its cached extraction.
    assert original.page_content_hash == revised.page_content_hash


@pytest.mark.asyncio
async def test_document_ids_are_addressed_by_content_not_position(tmp_path) -> None:
    without = """
    <html lang="en"><head><title>Overdraft</title></head><body>
    <h1>Overdraft</h1><p>Amount up to 10,000,000 AMD.</p>
    <a href="/terms.pdf">Official terms</a>
    </body></html>
    """
    # The same terms PDF, now preceded on the page by an unrelated leaflet.
    with_leaflet = without.replace(
        '<a href="/terms.pdf">Official terms</a>',
        '<a href="/leaflet.pdf">Leaflet</a><a href="/terms.pdf">Official terms</a>',
    )
    normalizer = StructuralNormalizationService(
        artifact_reader=FileSystemArtifactStore(Path(".")),
        pdf_extractor=NoPdfExtractor(),
    )

    before = await normalizer.normalize(
        await _service(tmp_path, without).acquire("https://ameriabank.am/overdraft")
    )
    after = await normalizer.normalize(
        await _service(tmp_path, with_leaflet).acquire(
            "https://ameriabank.am/overdraft"
        )
    )

    terms_id = next(
        item.id for item in before.documents if item.id.startswith("document:")
    )
    assert terms_id in {item.id for item in after.documents}


def _aspnet_page(view_state: str, token: str, *, amount: str = "10,000,000") -> str:
    """The bank's pages carry three hidden fields that change on every request."""
    return f"""
    <html lang="en"><head><title>Overdraft</title></head><body>
    <form id="Form">
      <input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="{view_state}" />
      <input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION"
             value="{view_state[::-1]}" />
      <h1>Overdraft</h1><p>Amount up to {amount} AMD.</p>
      <a href="/terms.pdf">Official terms</a>
      <input name="__RequestVerificationToken" type="hidden" value="{token}" />
    </form>
    </body></html>
    """


@pytest.mark.asyncio
async def test_per_request_form_tokens_do_not_rename_the_page(tmp_path) -> None:
    # Measured live on 2026-09-26: two fetches of the Overdraft page, seconds
    # apart, differed only in these three fields -- and got two page ids, so
    # every extraction cache missed.
    first = await _service(
        tmp_path, _aspnet_page("BwyBTnZQdPsd", "DnwM91GA9DJX")
    ).acquire("https://ameriabank.am/overdraft")
    second = await _service(
        tmp_path, _aspnet_page("4YXJM+soRSFc", "8Keo3O5yhFjL")
    ).acquire("https://ameriabank.am/overdraft")

    assert first.raw_html != second.raw_html
    assert first.page_content_hash == second.page_content_hash
    assert first.content_hash == second.content_hash


@pytest.mark.asyncio
async def test_per_request_tokens_in_the_rendered_page_do_not_rename_it(
    tmp_path,
) -> None:
    pages = []
    for view_state, token in (("BwyBTnZQdPsd", "DnwM91"), ("4YXJM+soRSFc", "8Keo3O")):
        html = _aspnet_page(view_state, token)
        pages.append(
            await _service(tmp_path, html, browser=_Browser(html)).acquire(
                "https://ameriabank.am/overdraft"
            )
        )

    assert pages[0].rendered_html != pages[1].rendered_html
    assert pages[0].page_content_hash == pages[1].page_content_hash


@pytest.mark.asyncio
async def test_a_changed_visible_value_renames_the_page(tmp_path) -> None:
    before = await _service(
        tmp_path, _aspnet_page("BwyBTnZQdPsd", "DnwM91GA9DJX")
    ).acquire("https://ameriabank.am/overdraft")
    after = await _service(
        tmp_path,
        _aspnet_page("BwyBTnZQdPsd", "DnwM91GA9DJX", amount="12,000,000"),
    ).acquire("https://ameriabank.am/overdraft")

    assert before.page_content_hash != after.page_content_hash


PAGE_WITH_CHROME = """
<html><body>
<header><nav><a href="/en/about">About Bank</a></nav></header>
<main><h1>Consumer loan</h1>
<table><tr><td>Annual interest rate</td><td>Fixed 20%</td></tr></table>
<a href="/terms.pdf">Terms</a></main>
<footer><div class="footer-content">{notice}<a href="/en/contacts">Contacts</a></div></footer>
</body></html>
"""


@pytest.mark.asyncio
async def test_a_late_footer_module_does_not_rename_the_page(tmp_path) -> None:
    # Finding F1 of the normalization scenarios: the consumer-loan page's footer
    # notice sometimes arrives after the render has finished.
    without = PAGE_WITH_CHROME.format(notice="")
    with_notice = PAGE_WITH_CHROME.format(
        notice="<p>Dear User,</p><p>If you find any discrepancies, consider the "
        "Armenian version as prevailing.</p>"
    )

    first = await _service(tmp_path, without, browser=_Browser(without)).acquire(
        "https://ameriabank.am/loan"
    )
    second = await _service(
        tmp_path, with_notice, browser=_Browser(with_notice)
    ).acquire("https://ameriabank.am/loan")

    assert first.page_content_hash == second.page_content_hash


@pytest.mark.asyncio
async def test_a_changed_menu_link_does_not_rename_the_page(tmp_path) -> None:
    before = PAGE_WITH_CHROME.format(notice="")
    after = before.replace('href="/en/about">About Bank', 'href="/en/bank">The Bank')

    first = await _service(tmp_path, before, browser=_Browser(before)).acquire(
        "https://ameriabank.am/loan"
    )
    second = await _service(tmp_path, after, browser=_Browser(after)).acquire(
        "https://ameriabank.am/loan"
    )

    assert first.page_content_hash == second.page_content_hash


@pytest.mark.asyncio
async def test_a_changed_tariff_still_renames_the_page(tmp_path) -> None:
    before = PAGE_WITH_CHROME.format(notice="")
    after = before.replace("Fixed 20%", "Fixed 21%")

    first = await _service(tmp_path, before, browser=_Browser(before)).acquire(
        "https://ameriabank.am/loan"
    )
    second = await _service(tmp_path, after, browser=_Browser(after)).acquire(
        "https://ameriabank.am/loan"
    )

    assert first.page_content_hash != second.page_content_hash
