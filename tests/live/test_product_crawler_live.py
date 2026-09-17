import os

import httpx
import pytest

from app.config import HttpSettings
from app.domain.crawl import CrawlStatus
from app.domain.product_registry import PRODUCT_REGISTRY
from app.services.product_crawler import ProductCrawler

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_CRAWLER") != "1",
    reason="set RUN_LIVE_CRAWLER=1 to crawl all official product sources",
)
@pytest.mark.asyncio
async def test_all_registered_products_have_bilingual_source_inventories() -> None:
    async with httpx.AsyncClient(follow_redirects=False) as client:
        async with ProductCrawler(client, HttpSettings()) as crawler:
            result = await crawler.crawl_all()

    assert len(result.inventories) == len(PRODUCT_REGISTRY) == 14
    failures = {
        inventory.product_id: [error.reason for error in inventory.errors]
        for inventory in result.inventories
        if inventory.status is not CrawlStatus.SUCCESS
    }
    assert failures == {}
    assert all(item.product_page_en is not None for item in result.inventories)
    assert all(item.product_page_hy is not None for item in result.inventories)
