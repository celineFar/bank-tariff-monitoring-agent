"""The renderer's DOM steps, run in a real local Chromium against fixture pages.

No network: each fixture is loaded with `page.set_content`, then the exact
settle / expand / mark sequence `render` uses runs on it, and the parser reads
the result the way acquisition does.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from app.config import AcquisitionSettings, HttpSettings
from app.services.browser_renderer import PlaywrightBrowserRenderer
from app.services.html_parser import HtmlArtifactParser

pytestmark = [pytest.mark.browser, pytest.mark.asyncio]

playwright_api = pytest.importorskip("playwright.async_api")

SOURCE_URL = "https://ameriabank.am/en/personal/loans/test"


@asynccontextmanager
async def _browser_page():
    """A fresh page in a local Chromium; skips the test only if it cannot start."""
    async with playwright_api.async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True)
        except playwright_api.Error as exc:  # pragma: no cover - environment
            pytest.skip(f"local Chromium is unavailable: {exc}")
        try:
            yield await browser.new_page()
        finally:
            await browser.close()


# Shaped like the six seed pages that used to parse as empty: an ASP.NET form
# wrapping the whole page, faded in from opacity 0 by a page-transition script,
# and no <h1>.
FADE_IN_WITHOUT_H1 = """
<html><body>
  <div class="animsition-loading"></div>
  <form id="Form" style="opacity: 0; transition: opacity 200ms">
    <h2>Consumer loan</h2>
    <p>Loan amount from AMD 100,000 to AMD 15,000,000 for a term of up to 60 months.</p>
    <table>
      <tr><th>Currency</th><th>Interest rate</th></tr>
      <tr><td>AMD</td><td>16%</td></tr>
    </table>
  </form>
  <script>
    setTimeout(() => { document.getElementById('Form').style.opacity = '1'; }, 300);
  </script>
</body></html>
"""


async def _expand_and_parse(html: str, settings: AcquisitionSettings):
    renderer = PlaywrightBrowserRenderer(HttpSettings(), settings)
    async with _browser_page() as page:
        await page.set_content(html)
        await renderer.expand_and_mark(page)
        rendered = await page.content()
    return HtmlArtifactParser(("ameriabank.am",)).parse(rendered, source_url=SOURCE_URL)


async def test_a_faded_in_page_without_h1_is_not_hidden() -> None:
    parsed = await _expand_and_parse(
        FADE_IN_WITHOUT_H1, AcquisitionSettings(browser_settle_milliseconds=0)
    )

    assert "Loan amount from AMD 100,000" in parsed.visible_text
    assert len(parsed.tables) == 1


async def test_a_panel_hidden_with_display_none_stays_hidden() -> None:
    parsed = await _expand_and_parse(
        """
        <html><body><main>
          <h1>Mortgage</h1>
          <p>Visible terms of the mortgage offer, shown to every visitor.</p>
          <div style="display: none"><p>Archived terms nobody can open.</p></div>
        </main></body></html>
        """,
        AcquisitionSettings(browser_settle_milliseconds=0),
    )

    assert "Visible terms of the mortgage offer" in parsed.visible_text
    assert "Archived terms" not in parsed.visible_text


async def test_content_that_never_becomes_visible_still_parses_empty() -> None:
    # The completeness gate, not the renderer, must reject such a page, so the
    # renderer must not invent visibility for it.
    parsed = await _expand_and_parse(
        """
        <html><body>
          <form style="visibility: hidden">
            <p>Terms that are never shown to a visitor.</p>
          </form>
        </body></html>
        """,
        AcquisitionSettings(browser_settle_milliseconds=0),
    )

    assert "never shown" not in parsed.visible_text
    assert not parsed.tables


async def test_the_interaction_cap_is_reported() -> None:
    renderer = PlaywrightBrowserRenderer(
        HttpSettings(),
        AcquisitionSettings(browser_settle_milliseconds=0, max_interactions=1),
    )
    async with _browser_page() as page:
        await page.set_content(
            """
            <html><body><main>
              <button aria-expanded="false">Rates</button>
              <button aria-expanded="false">Fees</button>
            </main></body></html>
            """
        )
        interactions, cap_reached = await renderer.expand_and_mark(page)

    assert interactions == 1
    assert cap_reached is True


async def test_a_button_that_navigates_away_is_stopped() -> None:
    renderer = PlaywrightBrowserRenderer(
        HttpSettings(), AcquisitionSettings(browser_settle_milliseconds=0)
    )
    async with _browser_page() as page:
        await page.set_content(
            """
            <html><body><main>
              <p>Overdraft terms.</p>
              <button aria-expanded="false"
                onclick="location.href='https://ameriabank.am/other'">
                Learn more
              </button>
            </main></body></html>
            """
        )
        start = page.url

        async def route(route, request):
            await renderer.route(route, request, page=page, loaded=True)

        await page.route("**/*", route)
        interactions, _ = await renderer.expand_and_mark(page)
        end = page.url
        content = await page.content()

    assert interactions == 1
    assert end == start
    assert "Overdraft terms." in content
