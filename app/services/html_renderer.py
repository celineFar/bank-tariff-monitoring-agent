from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import (
    Browser,
    Playwright,
    Route,
    WebSocketRoute,
    async_playwright,
)
from playwright.async_api import (
    Error as PlaywrightError,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from app.config import HttpSettings
from app.security.urls import DisallowedSourceUrl, validate_source_url
from app.services.restricted_http import HttpProvenanceHeaders, RestrictedHttpResponse


class HtmlRenderError(RuntimeError):
    pass


class HtmlRenderer(Protocol):
    async def render(self, url: str) -> RestrictedHttpResponse: ...

    async def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class _BrowserState:
    playwright: Playwright
    browser: Browser


class PlaywrightHtmlRenderer:
    """Restricted rendered-DOM fallback for official dynamic product pages."""

    def __init__(self, settings: HttpSettings) -> None:
        self._settings = settings
        self._state: _BrowserState | None = None
        self._start_lock = asyncio.Lock()
        self._render_semaphore = asyncio.Semaphore(
            settings.crawl_max_concurrent_renders
        )

    async def render(self, url: str) -> RestrictedHttpResponse:
        async with self._render_semaphore:
            return await self._render(url)

    async def _render(self, url: str) -> RestrictedHttpResponse:
        source_url = validate_source_url(url, self._settings.allowed_source_hosts)
        started_at = datetime.now(UTC)
        state = await self._browser_state()
        context = await state.browser.new_context(
            accept_downloads=False,
            ignore_https_errors=False,
            java_script_enabled=True,
            service_workers="block",
            user_agent=self._settings.user_agent,
        )
        page = await context.new_page()
        await page.route("**/*", self._route_request)
        await page.route_web_socket("**/*", self._route_web_socket)
        timeout_ms = self._settings.crawl_render_timeout_seconds * 1000
        try:
            response = await page.goto(
                source_url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            if response is None or response.status != 200:
                status = response.status if response is not None else "unknown"
                raise HtmlRenderError(
                    f"Rendered HTML navigation returned non-success status {status}"
                )
            try:
                await page.wait_for_function(
                    """() => Array.from(document.querySelectorAll(
                        '.wsc_content_manager_module_container'
                    )).some(element => element.children.length > 0 ||
                        element.innerText.trim().length > 0)""",
                    timeout=timeout_ms,
                )
            except PlaywrightTimeoutError:
                # Parsing below remains authoritative and returns NO_USABLE_CONTENT
                # if the official page never populated its public modules.
                pass
            final_url = validate_source_url(
                page.url, self._settings.allowed_source_hosts
            )
            content = (await page.content()).encode("utf-8")
        except DisallowedSourceUrl:
            raise
        except PlaywrightError as exc:
            raise HtmlRenderError("Rendered HTML navigation failed") from exc
        finally:
            await context.close()

        if len(content) > self._settings.max_html_bytes:
            raise HtmlRenderError("Rendered HTML exceeded the configured byte limit")
        retrieved_at = datetime.now(UTC)
        return RestrictedHttpResponse(
            source_url=source_url,
            final_url=final_url,
            mime_type="text/html",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            retrieval_started_at=started_at,
            retrieved_at=retrieved_at,
            retry_count=0,
            provenance_headers=HttpProvenanceHeaders(),
            content=content,
        )

    async def close(self) -> None:
        async with self._start_lock:
            state = self._state
            self._state = None
        if state is not None:
            await state.browser.close()
            await state.playwright.stop()

    async def _browser_state(self) -> _BrowserState:
        async with self._start_lock:
            if self._state is not None:
                return self._state
            playwright = await async_playwright().start()
            try:
                browser = await playwright.chromium.launch(headless=True)
            except PlaywrightError:
                try:
                    browser = await playwright.chromium.launch(
                        channel="msedge", headless=True
                    )
                except PlaywrightError as exc:
                    await playwright.stop()
                    raise HtmlRenderError(
                        "No usable Chromium browser is installed for rendered HTML"
                    ) from exc
            self._state = _BrowserState(playwright=playwright, browser=browser)
            return self._state

    async def _route_request(self, route: Route) -> None:
        request = route.request
        if request.resource_type in {"font", "image", "media", "stylesheet"}:
            await route.abort()
            return
        try:
            validate_source_url(request.url, self._settings.allowed_source_hosts)
        except DisallowedSourceUrl:
            await route.abort()
            return
        await route.continue_()

    async def _route_web_socket(self, route: WebSocketRoute) -> None:
        parsed = urlsplit(route.url)
        if parsed.scheme.lower() != "wss":
            await route.close(code=1008, reason="WebSocket URL is not allowed")
            return
        comparable = urlunsplit(
            ("https", parsed.netloc, parsed.path, parsed.query, parsed.fragment)
        )
        try:
            validate_source_url(comparable, self._settings.allowed_source_hosts)
        except DisallowedSourceUrl:
            await route.close(code=1008, reason="WebSocket host is not allowlisted")
            return
        route.connect_to_server()
