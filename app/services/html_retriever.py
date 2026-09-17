from __future__ import annotations

import asyncio
import random
import re
from enum import StrEnum
from urllib.parse import urldefrag, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from app.config import HttpSettings
from app.domain.web import (
    HtmlCandidate,
    HtmlHeading,
    HtmlLink,
    HtmlLinkKind,
    HtmlProvenanceHeaders,
    HtmlTable,
    HtmlTableRow,
    RetrievedHtmlPage,
)
from app.security.urls import DisallowedSourceUrl, validate_source_url
from app.services.restricted_http import (
    Clock,
    RandomValue,
    RestrictedHttpError,
    RestrictedHttpFailure,
    RestrictedHttpResponse,
    RestrictedHttpTransport,
    Sleep,
)

_HTML_MIME_TYPE = "text/html"
_ARMENIAN = re.compile(r"[\u0530-\u058f]")
_SPACE = re.compile(r"[ \t\f\v]+")
_BOILERPLATE_MARKERS = frozenset(
    {
        "breadcrumb",
        "chatbot",
        "cookie",
        "footer",
        "modal",
        "navbar",
        "navigation",
        "newsletter",
        "popup",
        "share",
        "sidebar",
        "social",
        "topbar",
    }
)
_BLOCKED_MARKERS = (
    "access denied",
    "captcha",
    "cf-chl-",
    "cloudflare ray id",
    "verify you are human",
)


class HtmlRetrievalFailure(StrEnum):
    DISALLOWED_URL = "DISALLOWED_URL"
    HTTP_STATUS = "HTTP_STATUS"
    TIMEOUT = "TIMEOUT"
    TRANSPORT = "TRANSPORT"
    REDIRECT_WITHOUT_LOCATION = "REDIRECT_WITHOUT_LOCATION"
    REDIRECT_LIMIT_EXCEEDED = "REDIRECT_LIMIT_EXCEEDED"
    REDIRECT_LOOP = "REDIRECT_LOOP"
    INVALID_CONTENT_LENGTH = "INVALID_CONTENT_LENGTH"
    PAGE_TOO_LARGE = "PAGE_TOO_LARGE"
    UNSUPPORTED_MIME_TYPE = "UNSUPPORTED_MIME_TYPE"
    PROTECTED_OR_BLOCKED = "PROTECTED_OR_BLOCKED"
    NO_USABLE_CONTENT = "NO_USABLE_CONTENT"
    RENDER_FAILED = "RENDER_FAILED"


class HtmlRetrievalError(RuntimeError):
    """Controlled HTML retrieval failure without raw page leakage."""

    def __init__(
        self,
        reason: HtmlRetrievalFailure,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code


class HtmlRetriever:
    """Fetch and clean allowlisted public HTML without executing page code."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: HttpSettings,
        *,
        sleep: Sleep | None = None,
        clock: Clock | None = None,
        random_value: RandomValue | None = None,
    ) -> None:
        self._transport = RestrictedHttpTransport(
            client,
            settings,
            sleep=sleep or asyncio.sleep,
            clock=clock,
            random_value=random_value or random.random,
        )
        self._settings = settings

    async def retrieve(self, candidate: HtmlCandidate) -> RetrievedHtmlPage:
        try:
            response = await self._transport.fetch(
                candidate.url,
                accepted_mime_types={_HTML_MIME_TYPE},
                accept_header="text/html,application/xhtml+xml;q=0.9",
                max_bytes=self._settings.max_html_bytes,
            )
        except RestrictedHttpError as exc:
            raise HtmlRetrievalError(
                _html_failure(exc.reason),
                str(exc),
                status_code=exc.status_code,
            ) from exc

        return self.parse_response(response)

    def parse_response(self, response: RestrictedHttpResponse) -> RetrievedHtmlPage:
        """Parse an already policy-approved static or rendered HTML response."""

        soup = BeautifulSoup(response.content, "html.parser")
        title = (
            _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else None
        )
        canonical_url = _canonical_url(
            soup,
            final_url=response.final_url,
            allowed_hosts=self._settings.allowed_source_hosts,
        )
        language_hint = _language_hint(
            soup,
            final_url=response.final_url,
            content_language=response.provenance_headers.content_language,
        )
        _remove_untrusted_and_boilerplate(soup)
        root = _content_root(soup)
        main_text = _main_text(root)
        raw_lower = response.content[:100_000].lower()
        if len(main_text) < 500 and any(
            marker.encode() in raw_lower for marker in _BLOCKED_MARKERS
        ):
            raise HtmlRetrievalError(
                HtmlRetrievalFailure.PROTECTED_OR_BLOCKED,
                "HTML page appears to be protected or blocked",
            )
        if not main_text:
            raise HtmlRetrievalError(
                HtmlRetrievalFailure.NO_USABLE_CONTENT,
                "HTML page did not contain usable public content",
            )

        headings = _headings(root)
        if title is None and headings:
            title = headings[0].text

        return RetrievedHtmlPage(
            source_url=response.source_url,
            final_url=response.final_url,
            canonical_url=canonical_url,
            title=title,
            headings=headings,
            main_text=main_text,
            tables=_tables(root),
            links=_links(
                root,
                base_url=response.final_url,
                allowed_hosts=self._settings.allowed_source_hosts,
            ),
            language_hint=language_hint,
            mime_type=response.mime_type,
            encoding=soup.original_encoding,
            size_bytes=response.size_bytes,
            sha256=response.sha256,
            retrieval_started_at=response.retrieval_started_at,
            retrieved_at=response.retrieved_at,
            retry_count=response.retry_count,
            provenance_headers=HtmlProvenanceHeaders(
                etag=response.provenance_headers.etag,
                last_modified=response.provenance_headers.last_modified,
                content_language=response.provenance_headers.content_language,
            ),
            raw_html=response.content,
        )


def _html_failure(reason: RestrictedHttpFailure) -> HtmlRetrievalFailure:
    if reason is RestrictedHttpFailure.RESPONSE_TOO_LARGE:
        return HtmlRetrievalFailure.PAGE_TOO_LARGE
    return HtmlRetrievalFailure(reason.value)


def _clean_text(value: str) -> str:
    lines = []
    for raw_line in value.replace("\r", "\n").split("\n"):
        line = _SPACE.sub(" ", raw_line).strip()
        if line:
            lines.append(line)
    return " ".join(lines)


def _canonical_url(
    soup: BeautifulSoup, *, final_url: str, allowed_hosts: tuple[str, ...]
) -> str:
    element = soup.find("link", rel="canonical")
    href = element.get("href") if isinstance(element, Tag) else None
    if not isinstance(href, str) or not href.strip():
        return final_url
    try:
        canonical = validate_source_url(urljoin(final_url, href), allowed_hosts)
    except DisallowedSourceUrl:
        return final_url
    return urldefrag(canonical).url


def _language_hint(
    soup: BeautifulSoup, *, final_url: str, content_language: str | None
) -> str | None:
    html = soup.find("html")
    declared = html.get("lang") if isinstance(html, Tag) else None
    candidate = declared if isinstance(declared, str) else content_language
    if candidate:
        normalized = candidate.split(",", 1)[0].split("-", 1)[0].strip().lower()
        if 2 <= len(normalized) <= 3 and normalized.isalpha():
            return normalized
    if urlsplit(final_url).path.lower().startswith("/en/"):
        return "en"
    visible_text = soup.get_text(" ", strip=True)
    if _ARMENIAN.search(visible_text):
        return "hy"
    return None


def _remove_untrusted_and_boilerplate(soup: BeautifulSoup) -> None:
    for element in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "iframe",
            "svg",
            "canvas",
            "template",
            "input",
            "button",
            "nav",
            "footer",
            "header",
            "aside",
        ]
    ):
        element.decompose()

    # ASP.NET/DNN sites commonly wrap the complete public page in one form.
    # Remove form semantics without discarding the product content inside it.
    for form in soup.find_all("form"):
        form.unwrap()

    for element in list(soup.find_all(True)):
        if element.attrs is None:
            continue
        markers = " ".join(
            (
                str(element.attrs.get("id", "")),
                " ".join(element.attrs.get("class", ())),
                str(element.attrs.get("role", "")),
            )
        ).lower()
        marker_tokens = set(re.findall(r"[a-z]+", markers))
        if marker_tokens & _BOILERPLATE_MARKERS:
            element.decompose()


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
        if isinstance(candidate, Tag) and _clean_text(
            candidate.get_text(" ", strip=True)
        ):
            return candidate
    if soup.body is not None:
        return soup.body
    return soup


def _main_text(root: Tag) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for raw_line in root.get_text("\n", strip=True).splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return "\n".join(lines)


def _headings(root: Tag) -> tuple[HtmlHeading, ...]:
    result: list[HtmlHeading] = []
    for heading in root.find_all(re.compile(r"^h[1-6]$")):
        text = _clean_text(heading.get_text(" ", strip=True))
        if text:
            result.append(HtmlHeading(level=int(heading.name[1]), text=text))
    return tuple(result)


def _tables(root: Tag) -> tuple[HtmlTable, ...]:
    result: list[HtmlTable] = []
    for table in root.find_all("table"):
        caption_element = table.find("caption")
        caption = (
            _clean_text(caption_element.get_text(" ", strip=True))
            if caption_element
            else None
        )
        rows: list[HtmlTableRow] = []
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            values = tuple(
                value
                for cell in cells
                if (value := _clean_text(cell.get_text(" ", strip=True)))
            )
            if values:
                rows.append(
                    HtmlTableRow(
                        cells=values,
                        is_header=any(cell.name == "th" for cell in cells),
                    )
                )
        if rows:
            result.append(HtmlTable(caption=caption, rows=tuple(rows)))
    return tuple(result)


def _links(
    root: Tag, *, base_url: str, allowed_hosts: tuple[str, ...]
) -> tuple[HtmlLink, ...]:
    result: list[HtmlLink] = []
    seen: set[str] = set()
    for anchor in root.find_all("a", href=True):
        href = anchor.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        try:
            validated = validate_source_url(urljoin(base_url, href), allowed_hosts)
        except DisallowedSourceUrl:
            continue
        url = urldefrag(validated).url
        if url in seen:
            continue
        seen.add(url)
        text = _clean_text(anchor.get_text(" ", strip=True)) or None
        context_parent = anchor.find_parent(["p", "li", "td", "th"])
        context = (
            _clean_text(context_parent.get_text(" ", strip=True))[:500] or None
            if context_parent
            else None
        )
        path = urlsplit(url).path.lower()
        if path.endswith(".pdf"):
            kind = HtmlLinkKind.PDF
        elif not path.rsplit("/", 1)[-1] or "." not in path.rsplit("/", 1)[-1]:
            kind = HtmlLinkKind.HTML
        else:
            kind = HtmlLinkKind.OTHER
        result.append(HtmlLink(url=url, text=text, context=context, kind=kind))
    return tuple(result)
