import os

import httpx
import pytest

from app.config import HttpSettings
from app.domain.web import HtmlCandidate
from app.services.html_retriever import HtmlRetriever

pytestmark = pytest.mark.live

PAGES = (
    (
        "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
        "en",
        "Consumer loan",
    ),
    (
        "https://ameriabank.am/personal/loans/consumer-loans/consumer-loans",
        "hy",
        "Սպառողական վարկ",
    ),
    (
        "https://ameriabank.am/en/personal/loans/mortgage/secondary-market",
        "en",
        "No loan service fees",
    ),
    (
        "https://ameriabank.am/personal/loans/mortgage/secondary-market",
        "hy",
        "Առանց վարկի սպասարկման վճարների",
    ),
)


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_HTTP") != "1",
    reason="set RUN_LIVE_HTTP=1 to call the official product pages",
)
@pytest.mark.asyncio
@pytest.mark.parametrize(("url", "language", "expected_phrase"), PAGES)
async def test_official_product_page_is_still_retrievable(
    url: str, language: str, expected_phrase: str
) -> None:
    settings = HttpSettings()
    async with httpx.AsyncClient(follow_redirects=False) as client:
        page = await HtmlRetriever(client, settings).retrieve(HtmlCandidate(url=url))

    assert page.language_hint == language
    assert expected_phrase in page.main_text
    assert page.title
    assert page.size_bytes > 0
    assert len(page.sha256) == 64
