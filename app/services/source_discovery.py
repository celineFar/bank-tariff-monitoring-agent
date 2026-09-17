from __future__ import annotations

import html
import ipaddress
import re
from collections.abc import Iterable, Sequence
from urllib.parse import (
    parse_qsl,
    urldefrag,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.domain.crawl import (
    CrawlLinkType,
    DiscoveredLink,
    LinkOrigin,
    ProductSeed,
)
from app.security.urls import DisallowedSourceUrl, validate_source_url

_ATTRIBUTE_SELECTORS = (
    ("a[href]", "href"),
    ("link[href]", "href"),
    ("iframe[src]", "src"),
    ("embed[src]", "src"),
    ("object[data]", "data"),
    ("source[src]", "src"),
)
_DATA_ATTRIBUTES = ("data-href", "data-url", "data-src", "data-file", "data-download")
_DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx")
_DOCUMENT_PATH_MARKERS = ("/portals/0/files/", "/userfiles/file/")
_DOCUMENT_KEYWORDS = (
    "terms",
    "tariff",
    "rates",
    "fees",
    "commission",
    "lending terms",
    "loan terms",
    "information guide",
    "information summary",
    "download",
    "details",
    "պայմաններ",
    "սակագներ",
    "տեղեկատվական ամփոփագիր",
    "ամփոփաթերթիկ",
    "վարկավորման պայմաններ",
    "տոկոսադրույք",
    "միջնորդավճար",
    "վճար",
    "ներբեռնել",
)
_SUPPORTING_KEYWORDS = (
    *_DOCUMENT_KEYWORDS,
    "special offer",
    "information",
    "campaign",
    "learn more",
    "հատուկ առաջարկ",
    "տեղեկություն",
    "իմացիր ավելին",
)
_IGNORE_KEYWORDS = (
    "apply now",
    "apply online",
    "contact",
    "branch",
    "login",
    "myameria",
    "facebook",
    "instagram",
    "linkedin",
    "youtube",
    "privacy",
    "terms of use",
    "դիմել հիմա",
    "մասնաճյուղ",
    "գաղտնիություն",
)
_TRACKING_PARAMETERS = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid", "yclid"})
_SCRIPT_LITERAL = re.compile(r"(?P<quote>['\"])(?P<url>https?://.+?|/.+?)(?P=quote)")
_SPACE = re.compile(r"\s+")
_BOILERPLATE_MARKERS = frozenset(
    {
        "breadcrumb",
        "cookie",
        "footer",
        "header",
        "menu",
        "navbar",
        "navigation",
        "sidebar",
        "social",
        "topbar",
    }
)


def normalize_crawl_url(
    value: str,
    *,
    base_url: str,
    allowed_hosts: tuple[str, ...] | None = None,
) -> str:
    """Resolve and conservatively normalize a crawl URL without changing path case."""

    resolved = html.unescape(value.strip()).replace("\\/", "/")
    resolved = urldefrag(urljoin(base_url, resolved)).url
    parsed = urlsplit(resolved)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise DisallowedSourceUrl("Discovered URL must use HTTPS and include a host")
    if parsed.username or parsed.password:
        raise DisallowedSourceUrl("Discovered URL credentials are not allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise DisallowedSourceUrl("Discovered URL contains an invalid port") from exc
    if port not in {None, 443}:
        raise DisallowedSourceUrl("Discovered URL must use the standard HTTPS port")

    host = parsed.hostname.lower().rstrip(".")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise DisallowedSourceUrl("IP-literal discovered URLs are not allowed")
    netloc = host
    query = urlencode(
        [
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in _TRACKING_PARAMETERS
        ],
        doseq=True,
    )
    normalized = urlunsplit(("https", netloc, parsed.path or "/", query, ""))
    if allowed_hosts is not None:
        return validate_source_url(normalized, allowed_hosts)
    return normalized


def discover_armenian_candidates(
    raw_html: bytes,
    *,
    page_url: str,
    allowed_hosts: tuple[str, ...],
) -> tuple[str, ...]:
    soup = BeautifulSoup(raw_html, "html.parser")
    candidates: list[str] = []

    for element in soup.select("a[href], link[href]"):
        href = element.get("href")
        if not isinstance(href, str):
            continue
        hreflang = str(element.get("hreflang", "")).lower()
        language = str(element.get("lang", "")).lower()
        text = _clean_text(element.get_text(" ", strip=True)).casefold()
        parent = element.parent if isinstance(element.parent, Tag) else None
        parent_markers = _element_markers(parent) if parent else ""
        is_language_ui = "lang" in parent_markers or "language" in parent_markers
        if not (
            hreflang == "hy"
            or language == "hy"
            or text in {"hy", "հայ", "հայերեն"}
            or (is_language_ui and text.startswith("hy"))
        ):
            continue
        try:
            normalized = normalize_crawl_url(
                href, base_url=page_url, allowed_hosts=allowed_hosts
            )
        except DisallowedSourceUrl:
            continue
        if normalized not in candidates:
            candidates.append(normalized)

    parsed = urlsplit(page_url)
    if parsed.path.lower().startswith("/en/"):
        fallback = urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path[3:], parsed.query, "")
        )
        try:
            fallback = normalize_crawl_url(
                fallback, base_url=page_url, allowed_hosts=allowed_hosts
            )
        except DisallowedSourceUrl:
            pass
        else:
            if fallback not in candidates:
                candidates.append(fallback)
    return tuple(candidates)


def extract_discovered_links(
    raw_html: bytes,
    *,
    page_url: str,
    allowed_hosts: tuple[str, ...],
) -> tuple[DiscoveredLink, ...]:
    """Extract literal URLs without executing page scripts."""

    soup = BeautifulSoup(raw_html, "html.parser")
    root = _content_root(soup)
    extracted: list[DiscoveredLink] = []

    for selector, attribute in _ATTRIBUTE_SELECTORS:
        elements: Iterable[Tag]
        if selector.startswith("link"):
            elements = soup.select(selector)
        else:
            elements = root.select(selector)
        for element in elements:
            value = element.get(attribute)
            if isinstance(value, str):
                _append_link(
                    extracted,
                    value=value,
                    element=element,
                    attribute=attribute,
                    origin=LinkOrigin.ATTRIBUTE,
                    root=root,
                    page_url=page_url,
                    allowed_hosts=allowed_hosts,
                )

    for element in root.find_all(True):
        for attribute in _DATA_ATTRIBUTES:
            value = element.get(attribute)
            if isinstance(value, str):
                _append_link(
                    extracted,
                    value=value,
                    element=element,
                    attribute=attribute,
                    origin=LinkOrigin.DATA_ATTRIBUTE,
                    root=root,
                    page_url=page_url,
                    allowed_hosts=allowed_hosts,
                )

        onclick = element.get("onclick")
        if isinstance(onclick, str):
            for literal in _script_literals(onclick):
                _append_link(
                    extracted,
                    value=literal,
                    element=element,
                    attribute="onclick",
                    origin=LinkOrigin.INLINE_SCRIPT,
                    root=root,
                    page_url=page_url,
                    allowed_hosts=allowed_hosts,
                )

    for script in root.find_all("script"):
        for literal in _script_literals(script.string or script.get_text(" ")):
            _append_link(
                extracted,
                value=literal,
                element=script,
                attribute="script",
                origin=LinkOrigin.INLINE_SCRIPT,
                root=root,
                page_url=page_url,
                allowed_hosts=allowed_hosts,
            )

    deduplicated: dict[str, DiscoveredLink] = {}
    for link in extracted:
        existing = deduplicated.get(link.normalized_url)
        if (
            existing is None
            or (not existing.anchor_text and link.anchor_text)
            or (not existing.in_main_content and link.in_main_content)
        ):
            deduplicated[link.normalized_url] = link
    return tuple(deduplicated.values())


def classify_discovered_link(
    link: DiscoveredLink,
    *,
    product: ProductSeed,
    registry: Sequence[ProductSeed],
    language_variant_urls: frozenset[str] = frozenset(),
    allowed_hosts: tuple[str, ...],
) -> DiscoveredLink:
    parsed = urlsplit(link.normalized_url)
    allowed = {host.lower().rstrip(".") for host in allowed_hosts}
    if (parsed.hostname or "").lower().rstrip(".") not in allowed:
        return link.model_copy(
            update={
                "classification": CrawlLinkType.EXTERNAL,
                "classification_reason": "host_not_allowlisted",
            }
        )
    if link.normalized_url in language_variant_urls:
        return link.model_copy(
            update={
                "classification": CrawlLinkType.LANGUAGE_VARIANT,
                "classification_reason": "armenian_language_variant",
            }
        )

    sibling_urls = {
        normalize_crawl_url(
            str(item.url_en), base_url=str(item.url_en), allowed_hosts=allowed_hosts
        )
        for item in registry
        if item.product_id != product.product_id
    }
    if link.normalized_url in sibling_urls:
        return link.model_copy(
            update={
                "classification": CrawlLinkType.IGNORE,
                "classification_reason": "registered_sibling_product",
            }
        )

    search_text = " ".join(
        value for value in (link.anchor_text, link.context, parsed.path) if value
    ).casefold()
    if not link.in_main_content:
        return link.model_copy(
            update={
                "classification": CrawlLinkType.IGNORE,
                "classification_reason": "outside_main_content",
            }
        )
    if "calculator" in search_text or "հաշվիչ" in search_text:
        return link.model_copy(
            update={
                "classification": CrawlLinkType.IGNORE,
                "classification_reason": "calculator_reference",
            }
        )
    path_lower = parsed.path.casefold()
    if path_lower.endswith(_DOCUMENT_EXTENSIONS) or any(
        marker in path_lower for marker in _DOCUMENT_PATH_MARKERS
    ):
        return link.model_copy(
            update={
                "classification": CrawlLinkType.DOCUMENT,
                "classification_reason": "document_extension_or_path",
            }
        )
    if any(keyword in search_text for keyword in _IGNORE_KEYWORDS):
        return link.model_copy(
            update={
                "classification": CrawlLinkType.IGNORE,
                "classification_reason": "excluded_action_or_global_link",
            }
        )
    if any(keyword in search_text for keyword in _SUPPORTING_KEYWORDS):
        return link.model_copy(
            update={
                "classification": CrawlLinkType.SUPPORTING_PAGE,
                "classification_reason": "relevant_link_context",
            }
        )
    if "/special-offers/" in path_lower or "/campaigns/" in path_lower:
        return link.model_copy(
            update={
                "classification": CrawlLinkType.SUPPORTING_PAGE,
                "classification_reason": "direct_product_campaign_or_offer",
            }
        )
    if _under_product_path(link.normalized_url, str(product.url_en)):
        return link.model_copy(
            update={
                "classification": CrawlLinkType.SUPPORTING_PAGE,
                "classification_reason": "under_same_product_path",
            }
        )
    return link.model_copy(
        update={
            "classification": CrawlLinkType.IGNORE,
            "classification_reason": "no_product_relevance_signal",
        }
    )


def _append_link(
    result: list[DiscoveredLink],
    *,
    value: str,
    element: Tag,
    attribute: str,
    origin: LinkOrigin,
    root: Tag,
    page_url: str,
    allowed_hosts: tuple[str, ...],
) -> None:
    if not value.strip() or value.lstrip().lower().startswith(
        ("#", "javascript:", "mailto:", "tel:", "data:")
    ):
        return
    try:
        normalized = normalize_crawl_url(value, base_url=page_url)
    except (DisallowedSourceUrl, ValueError):
        return
    parsed = urlsplit(normalized)
    allowed = {host.lower().rstrip(".") for host in allowed_hosts}
    if (parsed.hostname or "").lower().rstrip(".") in allowed:
        try:
            normalized = validate_source_url(normalized, allowed_hosts)
        except DisallowedSourceUrl:
            return
    anchor_text = _clean_text(element.get_text(" ", strip=True)) or None
    context_parent = element.find_parent(["p", "li", "td", "th"])
    context = (
        _clean_text(context_parent.get_text(" ", strip=True))[:2000] or None
        if isinstance(context_parent, Tag)
        else None
    )
    result.append(
        DiscoveredLink(
            original_url=value,
            normalized_url=normalized,
            referrer_url=page_url,
            tag=element.name,
            attribute=attribute,
            anchor_text=anchor_text,
            context=context,
            origin=origin,
            in_main_content=_inside_root(element, root)
            and not _is_boilerplate(element),
        )
    )


def _script_literals(value: str) -> tuple[str, ...]:
    candidates: list[str] = []
    for match in _SCRIPT_LITERAL.finditer(html.unescape(value).replace("\\/", "/")):
        candidate = match.group("url").strip()
        lowered = candidate.casefold()
        if (
            lowered.endswith(_DOCUMENT_EXTENSIONS)
            or any(marker in lowered for marker in _DOCUMENT_PATH_MARKERS)
            or "download" in lowered
            or "document" in lowered
        ):
            candidates.append(candidate)
    return tuple(candidates)


def _content_root(soup: BeautifulSoup) -> Tag:
    for selector in (
        "main",
        "article",
        "[role='main']",
        "#wsc_main_content",
        "#main-content",
        ".main-content",
        "#content",
        ".content",
    ):
        candidate = soup.select_one(selector)
        if isinstance(candidate, Tag):
            return candidate
    return soup.body or soup


def _inside_root(element: Tag, root: Tag) -> bool:
    return element is root or root in element.parents


def _is_boilerplate(element: Tag) -> bool:
    for ancestor in (element, *element.parents):
        if not isinstance(ancestor, Tag):
            continue
        if ancestor.name in {"header", "nav", "footer", "aside"}:
            return True
        tokens = set(re.findall(r"[a-z]+", _element_markers(ancestor).lower()))
        if tokens & _BOILERPLATE_MARKERS:
            return True
    return False


def _element_markers(element: Tag) -> str:
    classes = element.get("class", ())
    class_text = " ".join(classes) if isinstance(classes, list) else str(classes)
    return " ".join(
        (str(element.get("id", "")), class_text, str(element.get("role", "")))
    )


def _clean_text(value: str) -> str:
    return _SPACE.sub(" ", value).strip()


def _under_product_path(candidate_url: str, product_url: str) -> bool:
    candidate_path = urlsplit(candidate_url).path.rstrip("/").casefold()
    product_path = urlsplit(product_url).path.rstrip("/").casefold()
    if product_path.startswith("/en/"):
        product_path = product_path[3:]
    if candidate_path.startswith("/en/"):
        candidate_path = candidate_path[3:]
    return candidate_path.startswith(product_path + "/")
