import hashlib
from collections import Counter
from datetime import UTC, datetime

import httpx
import pytest

from app.config import HttpSettings
from app.domain.crawl import CrawlStatus, ProductCategory, ProductSeed
from app.services.product_crawler import ProductCrawler
from app.services.restricted_http import HttpProvenanceHeaders, RestrictedHttpResponse

EN_URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
HY_URL = "https://ameriabank.am/personal/loans/consumer-loans/consumer-loans"
SUPPORT_URL = "https://ameriabank.am/en/special-offers/consumer-loan"
PDF_URL = "https://ameriabank.am/files/consumer-terms.pdf"
PDF_ALIAS_URL = "https://ameriabank.am/files/consumer-summary.pdf"
SECOND_LEVEL_URL = "https://ameriabank.am/en/special-offers/second-level"

PRODUCT = ProductSeed(
    product_id="consumer.unsecured",
    category=ProductCategory.CONSUMER,
    name="Consumer loan",
    url_en=EN_URL,
)
SIBLING = ProductSeed(
    product_id="consumer.overdraft",
    category=ProductCategory.CONSUMER,
    name="Overdraft",
    url_en="https://ameriabank.am/en/personal/loans/consumer-loans/overdraft",
)

EN_HTML = f"""<!doctype html><html lang="en"><head><title>Consumer loan</title></head>
<body><form id="Form"><div id="topbar"><div class="language-switcher">
<a href="{HY_URL}" hreflang="hy">hy</a></div></div>
<div id="wsc_main_content"><h1>Consumer loan</h1>
<p>Consumer lending product terms and rates.</p>
<a href="{PDF_URL}">Terms and conditions</a>
<a href="{SUPPORT_URL}">Special offer</a>
<a href="{SIBLING.url_en}">Overdraft</a>
<a href="https://partner.example/consumer">Partner information</a>
</div></form></body></html>""".encode()

HY_HTML = f"""<!doctype html><html lang="hy"><head><title>Սպառողական վարկ</title></head>
<body><form id="Form"><div id="wsc_main_content"><h1>Սպառողական վարկ</h1>
<p>Սպառողական վարկավորման պայմաններ և սակագներ:</p>
<a href="{PDF_URL}">Պայմաններ և սակագներ</a>
</div></form></body></html>""".encode()

SUPPORT_HTML = f"""<!doctype html><html lang="en"><head><title>Special offer</title></head>
<body><main><h1>Consumer loan special offer</h1><p>Offer details and rates.</p>
<a href="{PDF_ALIAS_URL}">Information summary</a>
<a href="{SECOND_LEVEL_URL}">Terms on another supporting page</a>
</main></body></html>""".encode()

PDF_BYTES = b"%PDF-1.7\nrecorded test document\n%%EOF"


async def _no_sleep(_: float) -> None:
    return None


class _FakeRenderer:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.calls: list[str] = []
        self.required_module_ids: list[tuple[str, ...]] = []
        self.closed = False

    async def render(
        self,
        url: str,
        *,
        required_module_ids: tuple[str, ...] = (),
    ) -> RestrictedHttpResponse:
        self.calls.append(url)
        self.required_module_ids.append(required_module_ids)
        now = datetime(2026, 9, 17, tzinfo=UTC)
        return RestrictedHttpResponse(
            source_url=url,
            final_url=url,
            mime_type="text/html",
            size_bytes=len(self.content),
            sha256=hashlib.sha256(self.content).hexdigest(),
            retrieval_started_at=now,
            retrieved_at=now,
            retry_count=0,
            provenance_headers=HttpProvenanceHeaders(),
            content=self.content,
        )

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_crawls_both_languages_supporting_page_and_deduplicates_documents() -> (
    None
):
    requests: Counter[str] = Counter()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requests[url] += 1
        if url == EN_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=EN_HTML
            )
        if url == HY_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=HY_HTML
            )
        if url == SUPPORT_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=SUPPORT_HTML
            )
        if url in {PDF_URL, PDF_ALIAS_URL}:
            return httpx.Response(
                200, headers={"Content-Type": "application/pdf"}, content=PDF_BYTES
            )
        raise AssertionError(f"crawler requested an unexpected URL: {url}")

    settings = HttpSettings(
        backoff_base_seconds=0,
        crawl_requests_per_second=20,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = ProductCrawler(
            client,
            settings,
            registry=(PRODUCT, SIBLING),
            sleep=_no_sleep,
            monotonic=lambda: 0,
        )
        result = await crawler.crawl_all((PRODUCT,))

    inventory = result.inventories[0]
    assert inventory.status is CrawlStatus.SUCCESS
    assert inventory.product_page_en is not None
    assert inventory.product_page_hy is not None
    assert inventory.product_page_hy.language == "hy"
    assert [page.final_url for page in inventory.supporting_pages] == [SUPPORT_URL]
    assert len(inventory.documents) == 1
    assert set(inventory.documents[0].urls) == {PDF_URL, PDF_ALIAS_URL}
    assert set(inventory.documents[0].original_urls) == {PDF_URL, PDF_ALIAS_URL}
    assert set(inventory.documents[0].referrer_urls) == {EN_URL, HY_URL, SUPPORT_URL}
    assert inventory.documents[0].content == PDF_BYTES
    assert inventory.supporting_pages[0].discovered_url == SUPPORT_URL
    assert [item.url for item in inventory.external_references] == [
        "https://partner.example/consumer"
    ]
    assert requests[PDF_URL] == 1
    assert requests[PDF_ALIAS_URL] == 1
    assert requests[SECOND_LEVEL_URL] == 0
    assert requests[str(SIBLING.url_en)] == 0


@pytest.mark.asyncio
async def test_one_product_failure_does_not_discard_other_inventory() -> None:
    broken = ProductSeed(
        product_id="consumer.broken",
        category=ProductCategory.CONSUMER,
        name="Broken",
        url_en="https://ameriabank.am/en/personal/loans/consumer-loans/broken",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == EN_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=EN_HTML
            )
        if str(request.url) == HY_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=HY_HTML
            )
        if str(request.url) == SUPPORT_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=SUPPORT_HTML
            )
        if str(request.url) in {PDF_URL, PDF_ALIAS_URL}:
            return httpx.Response(
                200, headers={"Content-Type": "application/pdf"}, content=PDF_BYTES
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = ProductCrawler(
            client,
            HttpSettings(backoff_base_seconds=0, crawl_requests_per_second=20),
            registry=(PRODUCT, broken, SIBLING),
            sleep=_no_sleep,
            monotonic=lambda: 0,
        )
        result = await crawler.crawl_all((broken, PRODUCT))

    by_id = {item.product_id: item for item in result.inventories}
    assert by_id["consumer.broken"].status is CrawlStatus.FAILED
    assert by_id["consumer.unsecured"].status is CrawlStatus.SUCCESS


@pytest.mark.asyncio
async def test_empty_static_page_uses_restricted_rendered_dom_fallback() -> None:
    empty_static_html = b"""<html lang="en"><head><title>Consumer loan</title></head>
    <body><form id="Form"><div id="wsc_main_content">
    <div class="wsc_content_manager_module_container"></div>
    <script>loadPublicContent()</script></div></form></body></html>"""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == EN_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=empty_static_html
            )
        if url == HY_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=HY_HTML
            )
        if url == SUPPORT_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=SUPPORT_HTML
            )
        if url in {PDF_URL, PDF_ALIAS_URL}:
            return httpx.Response(
                200, headers={"Content-Type": "application/pdf"}, content=PDF_BYTES
            )
        raise AssertionError(f"unexpected URL: {url}")

    renderer = _FakeRenderer(EN_HTML)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        async with ProductCrawler(
            client,
            HttpSettings(backoff_base_seconds=0, crawl_requests_per_second=20),
            registry=(PRODUCT, SIBLING),
            sleep=_no_sleep,
            monotonic=lambda: 0,
            renderer=renderer,
        ) as crawler:
            inventory = await crawler.crawl_product(PRODUCT)

    assert inventory.status is CrawlStatus.SUCCESS
    assert renderer.calls == [EN_URL]
    assert renderer.closed is True


@pytest.mark.asyncio
async def test_usable_static_page_with_busy_public_module_uses_rendered_dom() -> None:
    incomplete_static_html = b"""<html lang="en"><head><title>Consumer loan</title></head>
    <body><form id="Form"><div id="wsc_main_content">
    <h1>Consumer loan</h1><p>Public product description is present.</p>
    <div class="wsc_content_manager_module_container busy"></div>
    </div></form></body></html>"""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == EN_URL:
            return httpx.Response(
                200,
                headers={"Content-Type": "text/html"},
                content=incomplete_static_html,
            )
        if url == HY_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=HY_HTML
            )
        if url == SUPPORT_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=SUPPORT_HTML
            )
        if url in {PDF_URL, PDF_ALIAS_URL}:
            return httpx.Response(
                200, headers={"Content-Type": "application/pdf"}, content=PDF_BYTES
            )
        raise AssertionError(f"unexpected URL: {url}")

    renderer = _FakeRenderer(EN_HTML)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        async with ProductCrawler(
            client,
            HttpSettings(backoff_base_seconds=0, crawl_requests_per_second=20),
            registry=(PRODUCT, SIBLING),
            sleep=_no_sleep,
            monotonic=lambda: 0,
            renderer=renderer,
        ) as crawler:
            inventory = await crawler.crawl_product(PRODUCT)

    assert inventory.status is CrawlStatus.SUCCESS
    assert renderer.calls == [EN_URL]
    assert inventory.documents


@pytest.mark.asyncio
async def test_usable_banner_with_empty_dnn_module_waits_for_that_module() -> None:
    static_shell = b"""<html lang="en"><head><title>Loan information</title></head>
    <body><form id="Form"><div id="wsc_main_content">
    <div class="wsc_content_manager_module_container" id="Container28243">
      <h1>Be informed when taking a loan</h1>
    </div>
    <div class="wsc_content_manager_module_container" id="Container28245"></div>
    <script>initModule(28245, {hasViewContent: true})</script>
    <div id="dnn_WideFooter">
      <div class="wsc_content_manager_module_container" id="Container99999"></div>
    </div>
    </div></form></body></html>"""
    rendered_page = b"""<html lang="en"><head><title>Loan information</title></head>
    <body><form id="Form"><div id="wsc_main_content">
    <div class="wsc_content_manager_module_container" id="Container28243">
      <h1>Be informed when taking a loan</h1>
    </div>
    <div class="wsc_content_manager_module_container" id="Container28245">
      <h2>What should I know before becoming a guarantor?</h2>
      <p>If the borrower fails to pay, the guarantor bears responsibility.</p>
    </div>
    </div></form></body></html>"""
    complete_hy = """<html lang="hy"><head><title>Վարկային տեղեկություն</title></head>
    <body><main><h1>Վարկային տեղեկություն</h1>
    <p>Ամբողջական հրապարակային բովանդակություն.</p></main></body></html>""".encode()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == EN_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=static_shell
            )
        if url == HY_URL:
            return httpx.Response(
                200, headers={"Content-Type": "text/html"}, content=complete_hy
            )
        raise AssertionError(f"unexpected URL: {url}")

    renderer = _FakeRenderer(rendered_page)
    product = PRODUCT
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        async with ProductCrawler(
            client,
            HttpSettings(backoff_base_seconds=0, crawl_requests_per_second=20),
            registry=(product,),
            sleep=_no_sleep,
            monotonic=lambda: 0,
            renderer=renderer,
        ) as crawler:
            inventory = await crawler.crawl_product(product)

    assert inventory.status is CrawlStatus.SUCCESS
    assert renderer.calls == [EN_URL]
    assert renderer.required_module_ids == [("Container28245",)]
    assert inventory.product_page_en is not None
    assert b"guarantor bears responsibility" in inventory.product_page_en.content
