import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from bs4 import BeautifulSoup

from app.config import HttpSettings
from app.domain.web import HtmlCandidate
from app.services.html_retriever import HtmlRetriever

FIXTURE_DIR = Path("tests/fixtures/html/recorded")
MANIFEST = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
PAGES = MANIFEST["pages"]


async def _no_sleep(_: float) -> None:
    return None


@pytest.mark.parametrize("entry", PAGES, ids=lambda entry: entry["filename"])
def test_recorded_page_is_an_integral_sanitized_download(
    entry: dict[str, Any],
) -> None:
    content = (FIXTURE_DIR / str(entry["filename"])).read_bytes()
    soup = BeautifulSoup(content, "html.parser")

    assert len(content) == entry["snapshot_size_bytes"]
    assert hashlib.sha256(content).hexdigest() == entry["snapshot_sha256"]
    assert int(entry["source_size_bytes"]) > len(content)
    assert soup.select_one("form#Form") is not None
    assert soup.select_one("#wsc_main_content") is not None
    assert soup.select_one("#topbar") is not None
    assert soup.find("script") is None
    assert soup.find("header") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", PAGES, ids=lambda entry: entry["filename"])
async def test_retrieves_product_evidence_from_recorded_page(
    entry: dict[str, Any],
) -> None:
    content = (FIXTURE_DIR / str(entry["filename"])).read_bytes()
    times = iter(
        (
            datetime(2026, 9, 16, 6, tzinfo=UTC),
            datetime(2026, 9, 16, 6, tzinfo=UTC) + timedelta(seconds=1),
        )
    )
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Content-Language": str(entry["language"]),
            },
            content=content,
        )
    )

    async with httpx.AsyncClient(transport=transport) as client:
        retriever = HtmlRetriever(
            client,
            HttpSettings(backoff_base_seconds=0),
            sleep=_no_sleep,
            clock=lambda: next(times),
            random_value=lambda: 0,
        )
        page = await retriever.retrieve(HtmlCandidate(url=str(entry["source_url"])))

    assert page.source_url == entry["source_url"]
    assert page.canonical_url == entry["source_url"]
    assert page.language_hint == entry["language"]
    assert page.title
    assert page.headings
    assert page.sha256 == hashlib.sha256(content).hexdigest()
    for phrase in entry["expected_phrases"]:
        assert phrase in page.main_text
    assert "About Bank" not in page.main_text
    assert "Բանկի մասին" not in page.main_text
    assert "Cards Types of cards" not in page.main_text
    assert "Քարտեր Քարտերի տեսակներ" not in page.main_text
