from __future__ import annotations

import asyncio
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

import httpx

from app.config import HttpSettings
from app.domain.crawl import CrawlIssue, PageResource, ProductSeed
from app.domain.discovery import (
    CandidateRetrievalStatus,
    DiscoveryOrigin,
    OfficialSourceDiscoveryRun,
    ProductDiscoveryResult,
    SourceCandidate,
    SourceCandidateType,
)
from app.domain.product_registry import PRODUCT_REGISTRY
from app.security.urls import DisallowedSourceUrl
from app.services.product_crawler import ProductCrawler
from app.services.rate_limiter import HostRateLimiter
from app.services.restricted_http import RestrictedHttpError, RestrictedHttpTransport
from app.services.source_discovery import normalize_crawl_url

_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xls", ".xlsx"})
_OFFICIAL_DOCUMENT_TERMS = (
    "terms",
    "tariff",
    "rates",
    "fees",
    "information guide",
    "information summary",
    "lending terms",
    "loan terms",
    "պայմաններ",
    "սակագներ",
    "տեղեկատվական ամփոփագիր",
    "ամփոփաթերթիկ",
    "վարկավորման պայմաններ",
    "տոկոսադրույք",
)
_SPACE = re.compile(r"[^\w\u0530-\u058f]+", re.UNICODE)
AsyncSleep = Callable[[float], Awaitable[None]]
MonotonicClock = Callable[[], float]


class OfficialSourceDiscovery:
    """Discover official candidates without declaring that candidates are authoritative."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: HttpSettings,
        *,
        crawler: ProductCrawler | None = None,
        registry: Sequence[ProductSeed] = PRODUCT_REGISTRY,
        sleep: AsyncSleep | None = None,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        self._settings = settings
        self._registry = tuple(registry)
        self._crawler = crawler or ProductCrawler(client, settings, registry=registry)
        self._owns_crawler = crawler is None
        self._transport = RestrictedHttpTransport(client, settings)
        self._sitemap_rate_limiter = HostRateLimiter(
            settings.crawl_requests_per_second,
            sleep=sleep or asyncio.sleep,
            clock=monotonic,
        )

    async def __aenter__(self) -> OfficialSourceDiscovery:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_crawler:
            await self._crawler.close()

    async def discover(
        self, products: Sequence[ProductSeed] | None = None
    ) -> OfficialSourceDiscoveryRun:
        started_at = datetime.now(UTC)
        selected = tuple(products) if products is not None else self._registry
        crawl = await self._crawler.crawl_all(selected)
        sitemap_entries, sitemap_urls, sitemap_warnings = await self._sitemap_entries()

        results: list[ProductDiscoveryResult] = []
        for product, inventory in zip(selected, crawl.inventories, strict=True):
            candidates = self._inventory_candidates(product, inventory)
            known_urls = {item.normalized_url for item in candidates}
            sibling_urls = self._sibling_seed_urls(product)
            remaining = max(
                self._settings.discovery_max_candidates_per_product - len(candidates),
                0,
            )
            for url in sitemap_entries:
                if (
                    not remaining
                    or url in known_urls
                    or url in sibling_urls
                    or urlsplit(url).path.casefold().startswith("/ru/")
                ):
                    continue
                signals = match_product_signals(url, product)
                if not signals:
                    continue
                candidates.append(
                    SourceCandidate(
                        product_id=product.product_id,
                        candidate_type=_candidate_type_from_url(url),
                        origin=DiscoveryOrigin.SITEMAP,
                        original_url=url,
                        normalized_url=url,
                        discovery_path=(*sitemap_urls[:1], url),
                        match_signals=signals,
                        retrieval_status=CandidateRetrievalStatus.NOT_RETRIEVED,
                    )
                )
                known_urls.add(url)
                remaining -= 1

            errors = inventory.errors
            if not candidates:
                errors = (
                    *errors,
                    CrawlIssue(
                        reason="PRODUCT_SOURCE_NOT_FOUND",
                        message="Discovery produced no official source candidates",
                        url=str(product.url_en),
                    ),
                )
            results.append(
                ProductDiscoveryResult(
                    product_id=product.product_id,
                    product_name=product.name,
                    category=product.category,
                    candidates=tuple(candidates),
                    inventory=inventory,
                    warnings=inventory.warnings,
                    errors=errors,
                )
            )

        return OfficialSourceDiscoveryRun(
            started_at=started_at,
            completed_at=datetime.now(UTC),
            products=tuple(results),
            sitemap_urls_retrieved=sitemap_urls,
            warnings=sitemap_warnings,
        )

    def _sibling_seed_urls(self, product: ProductSeed) -> frozenset[str]:
        sibling_urls: set[str] = set()
        for sibling in self._registry:
            if sibling.product_id == product.product_id:
                continue
            url = normalize_crawl_url(
                str(sibling.url_en),
                base_url=str(sibling.url_en),
                allowed_hosts=self._settings.allowed_source_hosts,
            )
            sibling_urls.add(url)
            parsed = urlsplit(url)
            if parsed.path.casefold().startswith("/en/"):
                sibling_urls.add(parsed._replace(path=parsed.path[3:]).geturl())
        return frozenset(sibling_urls)

    async def _sitemap_entries(
        self,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[CrawlIssue, ...]]:
        if self._settings.discovery_max_sitemaps == 0:
            return (), (), ()
        pending = deque(self._settings.discovery_sitemap_urls)
        visited: set[str] = set()
        visited_order: list[str] = []
        entries: list[str] = []
        warnings: list[CrawlIssue] = []

        while pending and len(visited) < self._settings.discovery_max_sitemaps:
            requested = pending.popleft()
            try:
                normalized = normalize_crawl_url(
                    requested,
                    base_url=requested,
                    allowed_hosts=self._settings.allowed_source_hosts,
                )
            except DisallowedSourceUrl as exc:
                warnings.append(
                    CrawlIssue(
                        reason="INVALID_SITEMAP_URL",
                        message=str(exc),
                        url=requested,
                    )
                )
                continue
            if normalized in visited:
                continue
            visited.add(normalized)
            visited_order.append(normalized)
            try:
                await self._sitemap_rate_limiter.acquire()
                response = await self._transport.fetch(
                    normalized,
                    accepted_mime_types=("application/xml", "text/xml"),
                    accept_header="application/xml, text/xml;q=0.9",
                    max_bytes=self._settings.max_html_bytes,
                    require_configured_mime_type=False,
                )
                locations, is_index = _parse_sitemap(response.content)
            except (RestrictedHttpError, ValueError) as exc:
                warnings.append(
                    CrawlIssue(
                        reason="SITEMAP_RETRIEVAL_FAILED",
                        message=str(exc),
                        url=normalized,
                        status_code=getattr(exc, "status_code", None),
                    )
                )
                continue

            for location in locations:
                try:
                    safe_url = normalize_crawl_url(
                        location,
                        base_url=response.final_url,
                        allowed_hosts=self._settings.allowed_source_hosts,
                    )
                except DisallowedSourceUrl:
                    continue
                if is_index:
                    if (
                        safe_url not in visited
                        and len(visited) + len(pending)
                        < self._settings.discovery_max_sitemaps
                    ):
                        pending.append(safe_url)
                elif (
                    safe_url not in entries
                    and len(entries) < self._settings.discovery_max_sitemap_entries
                ):
                    entries.append(safe_url)

        return tuple(entries), tuple(visited_order), tuple(warnings)

    def _inventory_candidates(
        self, product: ProductSeed, inventory
    ) -> list[SourceCandidate]:
        result: list[SourceCandidate] = []
        pages = (
            *((inventory.product_page_en,) if inventory.product_page_en else ()),
            *((inventory.product_page_hy,) if inventory.product_page_hy else ()),
            *inventory.supporting_pages,
        )
        for page in pages:
            result.append(_page_candidate(product, page))
        for document in inventory.documents:
            for index, url in enumerate(document.urls):
                original_url = (
                    document.original_urls[index]
                    if index < len(document.original_urls)
                    else url
                )
                result.append(
                    SourceCandidate(
                        product_id=product.product_id,
                        candidate_type=SourceCandidateType.DOCUMENT,
                        origin=DiscoveryOrigin.PAGE_LINK,
                        original_url=original_url,
                        normalized_url=url,
                        discovery_path=(*document.referrer_urls, url),
                        anchor_text=(
                            document.anchor_texts[0] if document.anchor_texts else None
                        ),
                        context=document.contexts[0] if document.contexts else None,
                        match_signals=("validated_page_document_link",),
                        retrieval_status=CandidateRetrievalStatus.RETRIEVED,
                        status_code=200,
                        content_sha256=document.sha256,
                        mime_type=document.content_type,
                    )
                )
        return result[: self._settings.discovery_max_candidates_per_product]


def match_product_signals(url: str, product: ProductSeed) -> tuple[str, ...]:
    """Return deterministic URL signals; an empty tuple means no product match."""

    haystack = _normalized_search_text(unquote(urlsplit(url).path))
    aliases = tuple(dict.fromkeys((product.name, *product.aliases)))
    product_matches: list[str] = []
    for alias in aliases:
        normalized_alias = _normalized_search_text(alias)
        if not normalized_alias:
            continue
        alias_tokens = normalized_alias.split()
        haystack_tokens = set(haystack.split())
        if normalized_alias in haystack or (
            len(alias_tokens) >= 2 and set(alias_tokens).issubset(haystack_tokens)
        ):
            product_matches.append(f"product_alias:{alias}")
    if not product_matches:
        return ()

    document_matches = [
        f"official_document_term:{term}"
        for term in _OFFICIAL_DOCUMENT_TERMS
        if _normalized_search_text(term) in haystack
    ]
    return tuple(dict.fromkeys((*product_matches, *document_matches)))


def _page_candidate(product: ProductSeed, page: PageResource) -> SourceCandidate:
    is_product_page = page.source_type.value == SourceCandidateType.PRODUCT_PAGE.value
    return SourceCandidate(
        product_id=product.product_id,
        candidate_type=(
            SourceCandidateType.PRODUCT_PAGE
            if is_product_page
            else SourceCandidateType.SUPPORTING_PAGE
        ),
        origin=(
            DiscoveryOrigin.REGISTRY if is_product_page else DiscoveryOrigin.PAGE_LINK
        ),
        original_url=page.discovered_url or page.source_url,
        normalized_url=page.final_url,
        discovery_path=tuple(
            dict.fromkeys(
                value
                for value in (str(product.url_en), page.referrer_url, page.final_url)
                if value
            )
        ),
        title=page.title,
        match_signals=(
            "configured_product_seed"
            if is_product_page
            else "relevant_direct_page_link",
        ),
        retrieval_status=CandidateRetrievalStatus.RETRIEVED,
        status_code=page.status_code,
        content_sha256=page.sha256,
        mime_type="text/html",
    )


def _candidate_type_from_url(url: str) -> SourceCandidateType:
    suffix = PurePosixPath(urlsplit(url).path).suffix.casefold()
    return (
        SourceCandidateType.DOCUMENT
        if suffix in _DOCUMENT_EXTENSIONS
        else SourceCandidateType.PAGE
    )


def _normalized_search_text(value: str) -> str:
    return " ".join(_SPACE.sub(" ", value.casefold()).split())


def _parse_sitemap(content: bytes) -> tuple[tuple[str, ...], bool]:
    prefix = content[:4096].upper()
    if b"<!DOCTYPE" in prefix or b"<!ENTITY" in prefix:
        raise ValueError("sitemap XML declarations and entities are not allowed")
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise ValueError("sitemap response was not valid XML") from exc
    local_name = root.tag.rsplit("}", 1)[-1].casefold()
    if local_name not in {"urlset", "sitemapindex"}:
        raise ValueError("XML response was not a sitemap")
    locations = tuple(
        text.strip()
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1].casefold() == "loc"
        and (text := element.text)
        and text.strip()
    )
    return locations, local_name == "sitemapindex"
