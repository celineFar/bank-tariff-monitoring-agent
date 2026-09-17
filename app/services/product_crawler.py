from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup, Tag

from app.config import HttpSettings
from app.domain.crawl import (
    CalculatorReference,
    CrawlIssue,
    CrawlLinkType,
    CrawlRunResult,
    CrawlStatus,
    DiscoveredLink,
    DocumentResource,
    ExternalReference,
    PageResource,
    PageSourceType,
    ProductSeed,
    ProductSourceInventory,
)
from app.domain.product_registry import PRODUCT_REGISTRY
from app.security.urls import DisallowedSourceUrl
from app.services.document_downloader import (
    DocumentCandidate,
    DocumentDownloader,
    DocumentDownloadError,
    DownloadedDocument,
)
from app.services.html_renderer import (
    HtmlRenderer,
    HtmlRenderError,
    PlaywrightHtmlRenderer,
)
from app.services.html_retriever import (
    HtmlCandidate,
    HtmlRetrievalError,
    HtmlRetrievalFailure,
    HtmlRetriever,
    RetrievedHtmlPage,
)
from app.services.rate_limiter import HostRateLimiter
from app.services.source_discovery import (
    classify_discovered_link,
    discover_armenian_candidates,
    extract_discovered_links,
    normalize_crawl_url,
)

logger = logging.getLogger(__name__)

AsyncSleep = Callable[[float], Awaitable[None]]
MonotonicClock = Callable[[], float]
DateTimeClock = Callable[[], datetime]
_ARMENIAN = re.compile(r"[\u0530-\u058f]")
_NON_CONTENT_PANE_MARKERS = frozenset(
    ("footer", "header", "navigation", "sidebar")
)


class ProductCrawler:
    """Bounded deterministic crawler for the configured product registry."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: HttpSettings,
        *,
        registry: Sequence[ProductSeed] = PRODUCT_REGISTRY,
        sleep: AsyncSleep = asyncio.sleep,
        monotonic: MonotonicClock = time.monotonic,
        clock: DateTimeClock | None = None,
        renderer: HtmlRenderer | None = None,
    ) -> None:
        self._settings = settings
        self._registry = tuple(registry)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._html_retriever = HtmlRetriever(client, settings)
        self._document_downloader = DocumentDownloader(client, settings)
        self._renderer = (
            renderer
            if renderer is not None
            else (
                PlaywrightHtmlRenderer(settings)
                if settings.crawl_render_dynamic_pages
                else None
            )
        )
        self._semaphore = asyncio.Semaphore(settings.crawl_max_concurrent_requests)
        self._rate_limiter = HostRateLimiter(
            settings.crawl_requests_per_second,
            sleep=sleep,
            clock=monotonic,
        )
        self._html_tasks: dict[str, asyncio.Task[RetrievedHtmlPage]] = {}
        self._document_tasks: dict[str, asyncio.Task[DownloadedDocument]] = {}
        self._cache_lock = asyncio.Lock()

    async def __aenter__(self) -> ProductCrawler:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._renderer is not None:
            await self._renderer.close()

    async def crawl_all(
        self, products: Sequence[ProductSeed] | None = None
    ) -> CrawlRunResult:
        started_at = self._clock()
        self._html_tasks.clear()
        self._document_tasks.clear()
        selected = tuple(products) if products is not None else self._registry
        inventories = await asyncio.gather(
            *(self.crawl_product(product) for product in selected)
        )
        return CrawlRunResult(
            started_at=started_at,
            completed_at=self._clock(),
            inventories=inventories,
        )

    async def crawl_product(self, product: ProductSeed) -> ProductSourceInventory:
        errors: list[CrawlIssue] = []
        warnings: list[CrawlIssue] = []
        try:
            en_page = await self._html(str(product.url_en), product.product_id)
        except (HtmlRetrievalError, DisallowedSourceUrl) as exc:
            errors.append(_html_or_url_issue(exc, str(product.url_en)))
            return ProductSourceInventory(
                product_id=product.product_id,
                product_name=product.name,
                category=product.category,
                status=CrawlStatus.FAILED,
                errors=tuple(errors),
            )

        page_en = _page_resource(en_page, PageSourceType.PRODUCT_PAGE)
        armenian_candidates = discover_armenian_candidates(
            en_page.raw_html,
            page_url=en_page.final_url,
            allowed_hosts=self._settings.allowed_source_hosts,
        )
        hy_page: RetrievedHtmlPage | None = None
        hy_url: str | None = None
        candidate_failures: list[CrawlIssue] = []
        for candidate in armenian_candidates:
            if candidate in {en_page.final_url, en_page.canonical_url}:
                continue
            try:
                fetched = await self._html(candidate, product.product_id)
            except (HtmlRetrievalError, DisallowedSourceUrl) as exc:
                candidate_failures.append(_html_or_url_issue(exc, candidate))
                continue
            if not _is_armenian_product_page(fetched):
                candidate_failures.append(
                    CrawlIssue(
                        reason="INVALID_LANGUAGE_VARIANT",
                        message="Candidate did not look like a valid Armenian product page",
                        url=candidate,
                    )
                )
                continue
            hy_page = fetched
            hy_url = candidate
            break

        if hy_page is None:
            errors.append(
                CrawlIssue(
                    reason="ARMENIAN_VARIANT_NOT_FOUND",
                    message="No verified Armenian product page was found",
                    url=en_page.final_url,
                )
            )
            warnings.extend(candidate_failures)
        elif candidate_failures:
            warnings.extend(candidate_failures)

        product_pages = [(en_page, "en")]
        if hy_page is not None:
            product_pages.append((hy_page, "hy"))
        language_urls = frozenset(
            (*armenian_candidates, *((hy_url,) if hy_url else ()))
        )

        document_links: dict[str, list[tuple[DiscoveredLink, str]]] = defaultdict(list)
        supporting_links: dict[str, DiscoveredLink] = {}
        external: dict[str, ExternalReference] = {}
        calculators: dict[str, CalculatorReference] = {}

        for page, language in product_pages:
            links = self._classified_links(page, product, language_urls)
            self._collect_links(
                links,
                language=language,
                document_links=document_links,
                supporting_links=supporting_links,
                external=external,
                calculators=calculators,
                allow_supporting=True,
            )

        supporting_pages: list[PageResource] = []
        seen_page_identities = {
            value
            for page, _ in product_pages
            for value in (page.final_url, page.canonical_url)
        }
        if self._settings.crawl_max_supporting_depth > 0:
            supporting_results = await asyncio.gather(
                *(
                    self._fetch_supporting_page(product, link)
                    for link in supporting_links.values()
                )
            )
            for source_link, page, issue in supporting_results:
                if issue is not None:
                    errors.append(issue)
                    continue
                if page is None:
                    continue
                identities = {page.final_url, page.canonical_url}
                if identities & seen_page_identities:
                    continue
                seen_page_identities.update(identities)
                supporting_pages.append(
                    _page_resource(
                        page,
                        PageSourceType.SUPPORTING_PAGE,
                        referrer_url=source_link.referrer_url,
                        discovered_url=source_link.original_url,
                    )
                )
                language = page.language_hint or "unknown"
                self._collect_links(
                    self._classified_links(page, product, language_urls),
                    language=language,
                    document_links=document_links,
                    supporting_links=supporting_links,
                    external=external,
                    calculators=calculators,
                    allow_supporting=False,
                )

        documents, document_errors = await self._download_documents(
            product.product_id, document_links
        )
        errors.extend(document_errors)
        status = CrawlStatus.PARTIAL if errors else CrawlStatus.SUCCESS
        return ProductSourceInventory(
            product_id=product.product_id,
            product_name=product.name,
            category=product.category,
            status=status,
            product_page_en=page_en,
            product_page_hy=(
                _page_resource(hy_page, PageSourceType.PRODUCT_PAGE)
                if hy_page is not None
                else None
            ),
            supporting_pages=tuple(supporting_pages),
            documents=documents,
            calculators=tuple(calculators.values()),
            external_references=tuple(external.values()),
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    def _classified_links(
        self,
        page: RetrievedHtmlPage,
        product: ProductSeed,
        language_urls: frozenset[str],
    ) -> tuple[DiscoveredLink, ...]:
        result: list[DiscoveredLink] = []
        for link in extract_discovered_links(
            page.raw_html,
            page_url=page.final_url,
            allowed_hosts=self._settings.allowed_source_hosts,
        ):
            classified = classify_discovered_link(
                link,
                product=product,
                registry=self._registry,
                language_variant_urls=language_urls,
                allowed_hosts=self._settings.allowed_source_hosts,
            )
            logger.info(
                "crawl_link_classified",
                extra={
                    "product_id": product.product_id,
                    "referrer": classified.referrer_url,
                    "candidate_url": classified.normalized_url,
                    "classification": classified.classification.value,
                    "reason": classified.classification_reason,
                },
            )
            result.append(classified)
        return tuple(result)

    @staticmethod
    def _collect_links(
        links: Sequence[DiscoveredLink],
        *,
        language: str,
        document_links: dict[str, list[tuple[DiscoveredLink, str]]],
        supporting_links: dict[str, DiscoveredLink],
        external: dict[str, ExternalReference],
        calculators: dict[str, CalculatorReference],
        allow_supporting: bool,
    ) -> None:
        for link in links:
            if link.classification is CrawlLinkType.DOCUMENT:
                document_links[link.normalized_url].append((link, language))
            elif (
                allow_supporting
                and link.classification is CrawlLinkType.SUPPORTING_PAGE
            ):
                supporting_links.setdefault(link.normalized_url, link)
            elif link.classification is CrawlLinkType.EXTERNAL and link.in_main_content:
                external.setdefault(
                    link.normalized_url,
                    ExternalReference(
                        url=link.normalized_url,
                        original_url=link.original_url,
                        referrer_url=link.referrer_url,
                        anchor_text=link.anchor_text,
                    ),
                )
            elif link.classification_reason == "calculator_reference":
                calculators.setdefault(
                    link.normalized_url,
                    CalculatorReference(
                        url=link.normalized_url,
                        original_url=link.original_url,
                        referrer_url=link.referrer_url,
                        anchor_text=link.anchor_text,
                    ),
                )

    async def _fetch_supporting_page(
        self, product: ProductSeed, link: DiscoveredLink
    ) -> tuple[DiscoveredLink, RetrievedHtmlPage | None, CrawlIssue | None]:
        try:
            page = await self._html(link.normalized_url, product.product_id)
        except (HtmlRetrievalError, DisallowedSourceUrl) as exc:
            return link, None, _html_or_url_issue(exc, link.normalized_url)
        return link, page, None

    async def _download_documents(
        self,
        product_id: str,
        links: dict[str, list[tuple[DiscoveredLink, str]]],
    ) -> tuple[tuple[DocumentResource, ...], list[CrawlIssue]]:
        if not links:
            return (), []
        results = await asyncio.gather(
            *(self._document(url, product_id) for url in links),
            return_exceptions=True,
        )
        by_checksum: dict[str, DocumentResource] = {}
        errors: list[CrawlIssue] = []
        for url, result in zip(links, results, strict=True):
            if isinstance(result, BaseException):
                if isinstance(result, DocumentDownloadError):
                    errors.append(_document_issue(result, url))
                else:
                    errors.append(
                        CrawlIssue(
                            reason="DOCUMENT_DOWNLOAD_FAILED",
                            message="Document download failed unexpectedly",
                            url=url,
                        )
                    )
                continue
            occurrences = links[url]
            referrers = tuple(
                dict.fromkeys(item.referrer_url for item, _ in occurrences)
            )
            original_urls = tuple(
                dict.fromkeys(item.original_url for item, _ in occurrences)
            )
            languages = tuple(dict.fromkeys(language for _, language in occurrences))
            anchor_texts = tuple(
                dict.fromkeys(
                    item.anchor_text for item, _ in occurrences if item.anchor_text
                )
            )
            contexts = tuple(
                dict.fromkeys(item.context for item, _ in occurrences if item.context)
            )
            existing = by_checksum.get(result.sha256)
            if existing is None:
                by_checksum[result.sha256] = DocumentResource(
                    sha256=result.sha256,
                    original_urls=original_urls,
                    urls=(url,),
                    final_url=result.final_url,
                    referrer_urls=referrers,
                    anchor_texts=anchor_texts,
                    contexts=contexts,
                    content_type=result.mime_type,
                    size_bytes=result.size_bytes,
                    retrieved_at=result.retrieved_at,
                    language_hints=languages,
                    content=result.content,
                )
            else:
                by_checksum[result.sha256] = existing.model_copy(
                    update={
                        "urls": tuple(dict.fromkeys((*existing.urls, url))),
                        "original_urls": tuple(
                            dict.fromkeys((*existing.original_urls, *original_urls))
                        ),
                        "referrer_urls": tuple(
                            dict.fromkeys((*existing.referrer_urls, *referrers))
                        ),
                        "language_hints": tuple(
                            dict.fromkeys((*existing.language_hints, *languages))
                        ),
                        "anchor_texts": tuple(
                            dict.fromkeys((*existing.anchor_texts, *anchor_texts))
                        ),
                        "contexts": tuple(
                            dict.fromkeys((*existing.contexts, *contexts))
                        ),
                    }
                )
        return tuple(by_checksum.values()), errors

    async def _html(self, url: str, product_id: str) -> RetrievedHtmlPage:
        normalized = normalize_crawl_url(
            url, base_url=url, allowed_hosts=self._settings.allowed_source_hosts
        )
        async with self._cache_lock:
            task = self._html_tasks.get(normalized)
            if task is None:
                task = asyncio.create_task(
                    self._fetch_html(normalized, product_id),
                    name=f"crawl-html:{normalized}",
                )
                self._html_tasks[normalized] = task
        return await task

    async def _document(self, url: str, product_id: str) -> DownloadedDocument:
        normalized = normalize_crawl_url(
            url, base_url=url, allowed_hosts=self._settings.allowed_source_hosts
        )
        async with self._cache_lock:
            task = self._document_tasks.get(normalized)
            if task is None:
                task = asyncio.create_task(
                    self._fetch_document(normalized, product_id),
                    name=f"crawl-document:{normalized}",
                )
                self._document_tasks[normalized] = task
        return await task

    async def _fetch_html(self, url: str, product_id: str) -> RetrievedHtmlPage:
        started = time.monotonic()
        try:
            async with self._semaphore:
                await self._rate_limiter.acquire()
                static_page: RetrievedHtmlPage | None = None
                try:
                    static_page = await self._html_retriever.retrieve(
                        HtmlCandidate(url)
                    )
                except HtmlRetrievalError as exc:
                    if (
                        exc.reason is not HtmlRetrievalFailure.NO_USABLE_CONTENT
                        or self._renderer is None
                    ):
                        raise
                required_module_ids = (
                    _unresolved_public_module_ids(static_page)
                    if static_page is not None
                    else ()
                )
                static_was_unresolved = static_page is not None and (
                    bool(required_module_ids)
                    or _has_busy_public_module(static_page)
                )
                should_render = self._renderer is not None and (
                    static_page is None or static_was_unresolved
                )
                if should_render:
                    try:
                        rendered = await self._renderer.render(
                            url,
                            required_module_ids=required_module_ids,
                        )
                        page = self._html_retriever.parse_response(rendered)
                    except HtmlRetrievalError:
                        if static_page is None or static_was_unresolved:
                            raise
                        page = static_page
                    except (HtmlRenderError, DisallowedSourceUrl) as render_exc:
                        if static_page is None or static_was_unresolved:
                            raise HtmlRetrievalError(
                                HtmlRetrievalFailure.RENDER_FAILED,
                                str(render_exc),
                            ) from render_exc
                        page = static_page
                elif static_page is not None:
                    page = static_page
                else:
                    raise AssertionError("HTML retrieval produced no result")
        except HtmlRetrievalError as exc:
            _log_http_failure(product_id, url, exc, started)
            raise
        _log_http_success(product_id, page, started)
        return page

    async def _fetch_document(self, url: str, product_id: str) -> DownloadedDocument:
        started = time.monotonic()
        try:
            async with self._semaphore:
                await self._rate_limiter.acquire()
                document = await self._document_downloader.download(
                    DocumentCandidate(url)
                )
        except DocumentDownloadError as exc:
            _log_http_failure(product_id, url, exc, started)
            raise
        logger.info(
            "crawl_http_success",
            extra={
                "product_id": product_id,
                "requested_url": url,
                "final_url": document.final_url,
                "status_code": 200,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "content_type": document.mime_type,
                "bytes": document.size_bytes,
                "retry_count": document.retry_count,
            },
        )
        return document


def _page_resource(
    page: RetrievedHtmlPage,
    source_type: PageSourceType,
    *,
    referrer_url: str | None = None,
    discovered_url: str | None = None,
) -> PageResource:
    return PageResource(
        source_type=source_type,
        source_url=page.source_url,
        final_url=page.final_url,
        canonical_url=page.canonical_url,
        title=page.title,
        language=page.language_hint,
        size_bytes=page.size_bytes,
        sha256=page.sha256,
        retrieved_at=page.retrieved_at,
        referrer_url=referrer_url,
        discovered_url=discovered_url,
        content=page.raw_html,
    )


def _is_armenian_product_page(page: RetrievedHtmlPage) -> bool:
    error_markers = ("404", "not found", "page not found", "էջը չի գտնվել")
    title = (page.title or "").casefold()
    if any(marker in title for marker in error_markers):
        return False
    return page.language_hint == "hy" or bool(_ARMENIAN.search(page.main_text))


def _unresolved_public_module_ids(page: RetrievedHtmlPage) -> tuple[str, ...]:
    soup = BeautifulSoup(page.raw_html, "html.parser")
    unresolved: list[str] = []
    for element in soup.select(".wsc_content_manager_module_container"):
        if not isinstance(element, Tag):
            continue
        if _is_in_non_content_pane(element):
            continue
        class_attribute = element.get("class")
        classes = (
            {str(item).casefold() for item in class_attribute}
            if isinstance(class_attribute, list)
            else {str(class_attribute).casefold()} if class_attribute else set()
        )
        for ignored in element.find_all(("script", "style", "noscript", "template")):
            ignored.decompose()
        has_public_text = bool(element.get_text(" ", strip=True))
        identifier = str(element.get("id", ""))
        if (
            ("busy" in classes or not has_public_text)
            and re.fullmatch(r"Container\d+", identifier)
            and identifier not in unresolved
        ):
            unresolved.append(identifier)
    return tuple(unresolved)


def _has_busy_public_module(page: RetrievedHtmlPage) -> bool:
    soup = BeautifulSoup(page.raw_html, "html.parser")
    return any(
        isinstance(element, Tag) and not _is_in_non_content_pane(element)
        for element in soup.select(".wsc_content_manager_module_container.busy")
    )


def _is_in_non_content_pane(element: Tag) -> bool:
    for ancestor in element.parents:
        if not isinstance(ancestor, Tag):
            continue
        class_attribute = ancestor.get("class")
        classes = (
            " ".join(str(item) for item in class_attribute)
            if isinstance(class_attribute, list)
            else str(class_attribute or "")
        )
        markers = f"{ancestor.get('id', '')} {classes} {ancestor.get('role', '')}"
        normalized = markers.casefold()
        if any(marker in normalized for marker in _NON_CONTENT_PANE_MARKERS):
            return True
    return False


def _html_or_url_issue(
    exc: HtmlRetrievalError | DisallowedSourceUrl, url: str
) -> CrawlIssue:
    if isinstance(exc, DisallowedSourceUrl):
        return CrawlIssue(
            reason="DISALLOWED_URL",
            message=str(exc),
            url=url,
        )
    return CrawlIssue(
        reason=exc.reason.value,
        message=str(exc),
        url=url,
        status_code=exc.status_code,
    )


def _document_issue(exc: DocumentDownloadError, url: str) -> CrawlIssue:
    return CrawlIssue(
        reason=exc.reason,
        message=str(exc),
        url=url,
        status_code=exc.status_code,
    )


def _log_http_success(product_id: str, page: RetrievedHtmlPage, started: float) -> None:
    logger.info(
        "crawl_http_success",
        extra={
            "product_id": product_id,
            "requested_url": page.source_url,
            "final_url": page.final_url,
            "status_code": 200,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "content_type": page.mime_type,
            "bytes": page.size_bytes,
            "retry_count": page.retry_count,
        },
    )


def _log_http_failure(
    product_id: str,
    url: str,
    exc: HtmlRetrievalError | DocumentDownloadError,
    started: float,
) -> None:
    logger.warning(
        "crawl_http_failure",
        extra={
            "product_id": product_id,
            "requested_url": url,
            "final_url": None,
            "status_code": exc.status_code,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "content_type": None,
            "bytes": 0,
            "retry_count": None,
            "reason": str(exc.reason),
        },
    )
