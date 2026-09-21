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


_PREPARE_ACQUISITION_DOM = """
() => {
  const isVisible = (element) => {
    if (!(element instanceof HTMLElement) && !(element instanceof SVGElement)) {
      return false;
    }
    const style = window.getComputedStyle(element);
    if (
      style.display === 'none'
      || style.visibility === 'hidden'
      || style.visibility === 'collapse'
      || style.opacity === '0'
    ) {
      return false;
    }
    return element.getClientRects().length > 0;
  };

  for (const anchor of document.querySelectorAll('a[href^="#"]')) {
    const fragment = anchor.getAttribute('href')?.slice(1);
    if (!fragment) continue;
    const panel = document.getElementById(fragment);
    const label = (anchor.innerText || anchor.textContent || '').trim();
    if (panel && label) {
      panel.setAttribute('data-acquisition-context-title', label);
      anchor.setAttribute('data-acquisition-tab-control', 'true');
      anchor.setAttribute('aria-controls', fragment);
    }
  }

  for (const element of document.body.querySelectorAll('*')) {
    if (isVisible(element)) {
      element.setAttribute('data-acquisition-visible', 'true');
    }
  }
}
"""

_PERFORM_ONE_INTERACTION = """
({labels}) => {
  const isVisible = (element) => {
    const style = window.getComputedStyle(element);
    return (
      style.display !== 'none'
      && style.visibility !== 'hidden'
      && style.visibility !== 'collapse'
      && style.opacity !== '0'
      && element.getClientRects().length > 0
    );
  };

  for (const element of document.querySelectorAll(
    '[data-acquisition-current-interaction="true"]'
  )) {
    element.removeAttribute('data-acquisition-current-interaction');
  }

  const selector = [
    'button',
    '[role="button"]',
    '[role="tab"]',
    '[aria-expanded="false"]',
    '[data-acquisition-tab-control="true"]',
    '[id*="show-more" i]',
    '[class*="show-more" i]'
  ].join(', ');
  let repeatableCandidate = null;
  for (const element of document.querySelectorAll(selector)) {
    if (!isVisible(element) || element.disabled) continue;
    if (element.dataset.acquisitionExhausted === 'true') continue;
    if (
      element.tagName === 'A'
      && !String(element.getAttribute('href') || '').startsWith('#')
    ) {
      continue;
    }
    const text = (element.innerText || element.textContent || '')
      .trim()
      .toLocaleLowerCase();
    const expandable = element.getAttribute('aria-expanded') === 'false';
    const isTab = (
      element.getAttribute('role') === 'tab'
      || element.getAttribute('data-acquisition-tab-control') === 'true'
    );
    const matchedLabel = labels.find((label) => text.includes(label));
    if (!expandable && !isTab && !matchedLabel) continue;

    const repeatable = matchedLabel === 'show more' || matchedLabel === 'see more';
    if (!repeatable && element.dataset.acquisitionInteracted === 'true') continue;
    if (repeatable) {
      repeatableCandidate ||= element;
      continue;
    }
    element.dataset.acquisitionInteracted = 'true';
    element.dataset.acquisitionCurrentInteraction = 'true';
    element.click();
    return {interacted: true, repeatable: false};
  }

  const closedDetails = Array.from(
    document.querySelectorAll('details:not([open])')
  ).find(isVisible);
  if (closedDetails) {
    closedDetails.open = true;
    closedDetails.setAttribute('data-acquisition-interacted', 'true');
    return {interacted: true, repeatable: false};
  }

  if (repeatableCandidate) {
    repeatableCandidate.dataset.acquisitionInteracted = 'true';
    repeatableCandidate.dataset.acquisitionCurrentInteraction = 'true';
    repeatableCandidate.click();
    return {interacted: true, repeatable: true};
  }
  return {interacted: false, repeatable: false};
}
"""

_ACQUISITION_DOM_SIGNATURE = """
() => [
  document.body.innerText.length,
  document.body.innerHTML.length,
  document.body.querySelectorAll('*').length
].join(':')
"""

_MARK_CURRENT_INTERACTION_EXHAUSTED = """
() => {
  const element = document.querySelector(
    '[data-acquisition-current-interaction="true"]'
  );
  if (element) element.dataset.acquisitionExhausted = 'true';
}
"""

_FINALIZE_ACQUISITION_DOM = """
() => {
  const isVisible = (element) => {
    const style = window.getComputedStyle(element);
    return (
      style.display !== 'none'
      && style.visibility !== 'hidden'
      && style.visibility !== 'collapse'
      && style.opacity !== '0'
      && element.getClientRects().length > 0
    );
  };
  for (const element of document.body.querySelectorAll('*')) {
    if (isVisible(element)) {
      element.setAttribute('data-acquisition-visible', 'true');
    } else if (
      element.getAttribute('data-acquisition-interacted') === 'true'
      || element.closest('[data-acquisition-interacted="true"]')
    ) {
      element.setAttribute('data-acquisition-visible', 'false');
    } else if (element.getAttribute('data-acquisition-visible') !== 'true') {
      element.setAttribute('data-acquisition-visible', 'false');
    }
  }
}
"""


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

                if self._settings.browser_settle_milliseconds:
                    await page.wait_for_timeout(
                        self._settings.browser_settle_milliseconds
                    )
                await page.evaluate(_PREPARE_ACQUISITION_DOM)
                interaction_labels = [
                    "terms and conditions",
                    "see more",
                    "show more",
                    "learn more",
                    "details",
                    "պայմաններ",
                    "տեսնել ավելին",
                ]
                interactions = 0
                while interactions < self._settings.max_interactions:
                    before_signature = await page.evaluate(_ACQUISITION_DOM_SIGNATURE)
                    interaction = await page.evaluate(
                        _PERFORM_ONE_INTERACTION,
                        {"labels": interaction_labels},
                    )
                    if not interaction["interacted"]:
                        break
                    interactions += 1
                    if self._settings.browser_settle_milliseconds:
                        await page.wait_for_timeout(
                            self._settings.browser_settle_milliseconds
                        )
                    after_signature = await page.evaluate(_ACQUISITION_DOM_SIGNATURE)
                    if interaction["repeatable"] and (
                        before_signature == after_signature
                    ):
                        await page.evaluate(_MARK_CURRENT_INTERACTION_EXHAUSTED)
                    await page.evaluate(_PREPARE_ACQUISITION_DOM)
                await page.evaluate(_FINALIZE_ACQUISITION_DOM)
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
