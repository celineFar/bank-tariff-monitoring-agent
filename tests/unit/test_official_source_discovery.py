import hashlib
from datetime import UTC, datetime

import httpx
import pytest

from app.config import HttpSettings
from app.domain.crawl import (
    CrawlRunResult,
    CrawlStatus,
    PageResource,
    PageSourceType,
    ProductCategory,
    ProductSeed,
    ProductSourceInventory,
)
from app.domain.discovery import CandidateRetrievalStatus, DiscoveryOrigin
from app.services.official_source_discovery import (
    OfficialSourceDiscovery,
    _parse_sitemap,
    match_product_signals,
)

SEED_URL = "https://ameriabank.am/en/personal/loans/mortgage/express-loan"
SITEMAP_URL = "https://ameriabank.am/sitemap.xml"
HTML = b"<html><main><h1>Quick mortgage</h1></main></html>"
NOW = datetime(2026, 9, 17, tzinfo=UTC)
PRODUCT = ProductSeed(
    product_id="mortgage.quick",
    category=ProductCategory.MORTGAGE,
    name="Quick mortgage loan",
    aliases=("quick mortgage", "express mortgage"),
    url_en=SEED_URL,
)


class _FakeCrawler:
    def __init__(self, inventory: ProductSourceInventory) -> None:
        self.inventory = inventory

    async def crawl_all(self, products):
        return CrawlRunResult(
            started_at=NOW,
            completed_at=NOW,
            inventories=(self.inventory,),
        )


def _inventory() -> ProductSourceInventory:
    return ProductSourceInventory(
        product_id=PRODUCT.product_id,
        product_name=PRODUCT.name,
        category=PRODUCT.category,
        status=CrawlStatus.SUCCESS,
        product_page_en=PageResource(
            source_type=PageSourceType.PRODUCT_PAGE,
            source_url=SEED_URL,
            final_url=SEED_URL,
            canonical_url=SEED_URL,
            title="Quick mortgage",
            language="en",
            size_bytes=len(HTML),
            sha256=hashlib.sha256(HTML).hexdigest(),
            retrieved_at=NOW,
            content=HTML,
        ),
    )


@pytest.mark.asyncio
async def test_combines_retrieved_seed_with_relevant_sitemap_candidates() -> None:
    sitemap = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://ameriabank.am/en/files/quick-mortgage-terms.pdf</loc></url>
      <url><loc>https://ameriabank.am/en/personal/cards</loc></url>
      <url><loc>https://evil.example/quick-mortgage-terms.pdf</loc></url>
    </urlset>"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == SITEMAP_URL
        return httpx.Response(
            200,
            headers={"Content-Type": "application/xml"},
            content=sitemap,
        )

    settings = HttpSettings(
        discovery_sitemap_urls=(SITEMAP_URL,),
        discovery_max_candidates_per_product=5,
        backoff_base_seconds=0,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = OfficialSourceDiscovery(
            client,
            settings,
            crawler=_FakeCrawler(_inventory()),  # type: ignore[arg-type]
            registry=(PRODUCT,),
        )
        result = await service.discover((PRODUCT,))

    candidates = result.products[0].candidates
    assert candidates[0].origin is DiscoveryOrigin.REGISTRY
    assert candidates[0].retrieval_status is CandidateRetrievalStatus.RETRIEVED
    assert candidates[1].origin is DiscoveryOrigin.SITEMAP
    assert candidates[1].retrieval_status is CandidateRetrievalStatus.NOT_RETRIEVED
    assert candidates[1].normalized_url.endswith("quick-mortgage-terms.pdf")
    assert all("evil.example" not in item.normalized_url for item in candidates)
    assert result.sitemap_urls_retrieved == (SITEMAP_URL,)


def test_product_signal_matching_requires_a_product_alias() -> None:
    assert match_product_signals(
        "https://ameriabank.am/files/quick-mortgage-terms.pdf", PRODUCT
    ) == (
        "product_alias:quick mortgage",
        "official_document_term:terms",
    )
    assert (
        match_product_signals(
            "https://ameriabank.am/files/generic-loan-terms.pdf", PRODUCT
        )
        == ()
    )


def test_sitemap_parser_rejects_document_type_declarations() -> None:
    with pytest.raises(ValueError, match="declarations and entities"):
        _parse_sitemap(b"<!DOCTYPE foo><urlset></urlset>")
