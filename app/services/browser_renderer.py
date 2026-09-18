from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from app.config import AcquisitionSettings, HttpSettings
from app.domain.acquisition import NetworkPayload, SourceLocator, SourceType
from app.security.urls import DisallowedSourceUrl, validate_source_url


class BrowserRenderingFailure(StrEnum):
    UNAVAILABLE = "UNAVAILABLE"
    NAVIGATION = "NAVIGATION"
    DISALLOWED_REDIRECT = "DISALLOWED_REDIRECT"
    HTTP_STATUS = "HTTP_STATUS"
    REDIRECT_LIMIT_EXCEEDED = "REDIRECT_LIMIT_EXCEEDED"
    UNSUPPORTED_MIME_TYPE = "UNSUPPORTED_MIME_TYPE"
    PAGE_TOO_LARGE = "PAGE_TOO_LARGE"


class BrowserRenderingError(RuntimeError):
    def __init__(self, reason: BrowserRenderingFailure, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class RenderedPage:
    final_url: str
    html: str
    title: str | None
    visible_text: str
    interactions: int
    network_payloads: tuple[NetworkPayload, ...]


class BrowserRenderer(Protocol):
    async def render(self, url: str) -> RenderedPage: ...


class PlaywrightBrowserRenderer:
    """Bounded, read-only browser rendering for allowlisted public pages."""

    def __init__(
        self, http_settings: HttpSettings, acquisition_settings: AcquisitionSettings
    ) -> None:
        self._http = http_settings
        self._settings = acquisition_settings

    async def render(self, url: str) -> RenderedPage:
        try:
            from playwright.async_api import Error as PlaywrightError
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise BrowserRenderingError(
                BrowserRenderingFailure.UNAVAILABLE,
                "Playwright is not installed",
            ) from exc

        validate_source_url(url, self._http.allowed_source_hosts)
        captured: list[NetworkPayload] = []
        capture_tasks: set[asyncio.Task[None]] = set()

        async def capture_response(response: object) -> None:
            if len(captured) >= self._settings.max_network_payloads:
                return
            request = response.request
            if request.resource_type not in {"xhr", "fetch"} or request.method != "GET":
                return
            if response.status < 200 or response.status >= 300:
                return
            try:
                payload_url = validate_source_url(
                    response.url, self._http.allowed_source_hosts
                )
            except DisallowedSourceUrl:
                return
            mime_type = (
                response.headers.get("content-type", "").split(";", 1)[0].lower()
            )
            if not (
                mime_type == "application/json"
                or mime_type.endswith("+json")
                or mime_type.startswith("text/")
            ):
                return
            try:
                body = await response.body()
            except PlaywrightError:
                return
            if len(body) > self._settings.max_network_payload_bytes:
                return
            body_text = body.decode("utf-8", errors="replace")
            checksum = hashlib.sha256(body).hexdigest()
            captured.append(
                NetworkPayload(
                    url=payload_url,
                    method=request.method,
                    status_code=response.status,
                    mime_type=mime_type,
                    body_text=body_text,
                    size_bytes=len(body),
                    sha256=checksum,
                    retrieved_at=datetime.now(UTC),
                    locator=SourceLocator(
                        source_url=payload_url,
                        source_type=SourceType.API,
                        json_path="$" if "json" in mime_type else None,
                    ),
                )
            )

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True, args=["--disable-dev-shm-usage"]
            )
            try:
                context = await browser.new_context(
                    user_agent=self._http.user_agent,
                    accept_downloads=False,
                    service_workers="block",
                )
                page = await context.new_page()
                page.set_default_timeout(
                    self._settings.browser_navigation_timeout_seconds * 1000
                )

                async def route_request(route: object, request: object) -> None:
                    if request.method not in {"GET", "HEAD"}:
                        await route.abort("blockedbyclient")
                        return
                    if request.resource_type in {"image", "media", "font"}:
                        await route.abort("blockedbyclient")
                        return
                    try:
                        validate_source_url(
                            request.url, self._http.allowed_source_hosts
                        )
                    except DisallowedSourceUrl:
                        await route.abort("blockedbyclient")
                        return
                    await route.continue_()

                await page.route("**/*", route_request)

                def schedule_capture(response: object) -> None:
                    task = asyncio.create_task(capture_response(response))
                    capture_tasks.add(task)
                    task.add_done_callback(capture_tasks.discard)

                page.on("response", schedule_capture)
                try:
                    response = await page.goto(url, wait_until="domcontentloaded")
                except PlaywrightTimeoutError as exc:
                    raise BrowserRenderingError(
                        BrowserRenderingFailure.NAVIGATION,
                        "Browser navigation timed out",
                    ) from exc
                except PlaywrightError as exc:
                    raise BrowserRenderingError(
                        BrowserRenderingFailure.NAVIGATION,
                        "Browser navigation failed",
                    ) from exc
                if response is None or response.status < 200 or response.status >= 400:
                    status = response.status if response else "unknown"
                    raise BrowserRenderingError(
                        BrowserRenderingFailure.HTTP_STATUS,
                        f"Browser navigation returned HTTP {status}",
                    )
                redirect_count = 0
                redirected_from = response.request.redirected_from
                while redirected_from is not None:
                    redirect_count += 1
                    redirected_from = redirected_from.redirected_from
                if redirect_count > self._http.max_redirects:
                    raise BrowserRenderingError(
                        BrowserRenderingFailure.REDIRECT_LIMIT_EXCEEDED,
                        "Browser navigation exceeded the configured redirect limit",
                    )
                mime_type = (
                    response.headers.get("content-type", "").split(";", 1)[0].lower()
                )
                if mime_type != "text/html":
                    raise BrowserRenderingError(
                        BrowserRenderingFailure.UNSUPPORTED_MIME_TYPE,
                        "Browser navigation did not return text/html",
                    )
                try:
                    final_url = validate_source_url(
                        page.url, self._http.allowed_source_hosts
                    )
                except DisallowedSourceUrl as exc:
                    raise BrowserRenderingError(
                        BrowserRenderingFailure.DISALLOWED_REDIRECT,
                        "Browser navigation left the source allowlist",
                    ) from exc

                interactions = await page.evaluate(
                    """
                    ({maxInteractions, labels}) => {
                      let count = 0;
                      for (const details of document.querySelectorAll('details:not([open])')) {
                        if (count >= maxInteractions) break;
                        details.open = true;
                        count += 1;
                      }
                      const candidates = document.querySelectorAll(
                        'button, [role="button"], [role="tab"], [aria-expanded="false"]'
                      );
                      for (const element of candidates) {
                        if (count >= maxInteractions) break;
                        if (element.closest('form') || element.disabled) continue;
                        const style = window.getComputedStyle(element);
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        const text = (element.innerText || element.textContent || '')
                          .trim().toLocaleLowerCase();
                        const expandable = element.getAttribute('aria-expanded') === 'false';
                        const isTab = element.getAttribute('role') === 'tab';
                        if (!expandable && !isTab && !labels.some(label => text.includes(label))) {
                          continue;
                        }
                        element.click();
                        count += 1;
                      }
                      return count;
                    }
                    """,
                    {
                        "maxInteractions": self._settings.max_interactions,
                        "labels": [
                            "terms and conditions",
                            "see more",
                            "show more",
                            "learn more",
                            "details",
                            "պայմաններ",
                            "տեսնել ավելին",
                        ],
                    },
                )
                if self._settings.browser_settle_milliseconds:
                    await page.wait_for_timeout(
                        self._settings.browser_settle_milliseconds
                    )
                if capture_tasks:
                    await asyncio.gather(*tuple(capture_tasks), return_exceptions=True)
                html = await page.content()
                if len(html.encode("utf-8")) > self._http.max_download_bytes:
                    raise BrowserRenderingError(
                        BrowserRenderingFailure.PAGE_TOO_LARGE,
                        "Rendered HTML exceeds the configured byte limit",
                    )
                visible_text = await page.locator("body").inner_text()
                title = (await page.title()).strip() or None
                return RenderedPage(
                    final_url=final_url,
                    html=html,
                    title=title,
                    visible_text=visible_text,
                    interactions=interactions,
                    network_payloads=tuple(
                        captured[: self._settings.max_network_payloads]
                    ),
                )
            finally:
                await browser.close()
