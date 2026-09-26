"""Two acquisitions of unchanged content must produce the same identities.

Every content-addressed cache downstream -- source discovery, semantic
extraction, embeddings -- is keyed on identities derived here. When an identity
drifts between runs over content that did not change, each of those caches
misses and the run pays for a full re-extraction.
"""

import hashlib
from datetime import UTC, datetime

import pytest

from app.config import AcquisitionSettings
from app.domain.acquisition import NetworkPayload, SourceLocator, SourceType
from app.services.acquisition import AcquisitionService
from app.services.artifact_store import FileSystemArtifactStore
from app.services.browser_renderer import RenderedPage, order_network_payloads
from app.services.html_parser import HtmlArtifactParser
from app.services.html_retriever import RetrievedHtml
from app.services.normalization import StructuralNormalizationService
from app.services.pdf_downloader import DownloadedPdf, PdfProvenanceHeaders

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _payload(path: str, body: str) -> NetworkPayload:
    url = f"https://ameriabank.am/api/{path}"
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
    def __init__(self, payloads: tuple[NetworkPayload, ...], html: str) -> None:
        self._payloads = payloads
        self._html = html

    async def render(self, url: str) -> RenderedPage:
        return RenderedPage(
            final_url=url,
            html=self._html,
            title="Overdraft",
            visible_text="Expanded terms",
            interactions=1,
            network_payloads=self._payloads,
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


def test_capture_order_does_not_change_the_payload_list() -> None:
    first = _payload("terms", '{"rate": 13}')
    second = _payload("fees", '{"fee": 10}')
    third = _payload("limits", '{"max": 15}')

    arrived_one = order_network_payloads([first, second, third], limit=25)
    arrived_another = order_network_payloads([third, first, second], limit=25)

    assert arrived_one == arrived_another


def test_a_payload_captured_twice_becomes_one_document() -> None:
    once = _payload("terms", '{"rate": 13}')

    assert order_network_payloads([once, once], limit=25) == (once,)


@pytest.mark.asyncio
async def test_payload_arrival_order_does_not_rename_the_page(tmp_path) -> None:
    raw = """
    <html><body><button aria-expanded="false">See more</button>
    <p>Initial official content long enough.</p></body></html>
    """
    rendered = """
    <html><body><h1>Overdraft</h1>
    <p>Expanded terms: annual rate 13% and term up to 60 months.</p>
    </body></html>
    """
    payloads = (
        _payload("terms", '{"rate": 13}'),
        _payload("fees", '{"fee": 10}'),
    )
    normalizer = StructuralNormalizationService()

    forwards = await _service(
        tmp_path, raw, browser=_Browser(payloads, rendered)
    ).acquire("https://ameriabank.am/overdraft")
    backwards = await _service(
        tmp_path, raw, browser=_Browser(tuple(reversed(payloads)), rendered)
    ).acquire("https://ameriabank.am/overdraft")

    assert forwards.content_hash == backwards.content_hash
    assert forwards.page_content_hash == backwards.page_content_hash
    forwards_ids = [
        item.id for item in (await normalizer.normalize(forwards)).documents
    ]
    backwards_ids = [
        item.id for item in (await normalizer.normalize(backwards)).documents
    ]
    assert forwards_ids == backwards_ids


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
    normalizer = StructuralNormalizationService()

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
            await _service(tmp_path, html, browser=_Browser((), html)).acquire(
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
