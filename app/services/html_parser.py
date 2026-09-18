from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from app.domain.acquisition import (
    ContentBlock,
    ContentBlockType,
    LinkArtifact,
    SourceLocator,
    SourceType,
    TableArtifact,
)
from app.security.urls import DisallowedSourceUrl, validate_source_url

_WHITESPACE = re.compile(r"\s+")
_BLOCK_TAGS = frozenset(
    {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt", "dd", "details"}
)
_DOCUMENT_EXTENSIONS = frozenset({".pdf"})


@dataclass(frozen=True, slots=True)
class ParsedHtml:
    canonical_url: str
    title: str | None
    language: str | None
    visible_text: str
    markdown: str | None
    blocks: tuple[ContentBlock, ...]
    tables: tuple[TableArtifact, ...]
    links: tuple[LinkArtifact, ...]


class HtmlArtifactParser:
    """Create faithful structural artifacts without assigning loan semantics."""

    def __init__(self, allowed_hosts: tuple[str, ...]) -> None:
        self._allowed_hosts = allowed_hosts

    def parse(self, html: str, *, source_url: str) -> ParsedHtml:
        soup = BeautifulSoup(html, "html.parser")
        for element in soup.select("script, style, noscript, template"):
            element.decompose()

        canonical_url = self._canonical_url(soup, source_url)
        title = (
            self._clean(soup.title.get_text(" ", strip=True)) if soup.title else None
        )
        html_tag = soup.find("html")
        language = None
        if isinstance(html_tag, Tag):
            language = self._clean(str(html_tag.get("lang") or "")) or None

        root = soup.body or soup
        blocks, tables = self._blocks_and_tables(root, source_url)
        links = self._links(root, source_url)
        visible_text = self._clean(" ".join(block.text for block in blocks))
        markdown = self._markdown(blocks, tables)
        return ParsedHtml(
            canonical_url=canonical_url,
            title=title,
            language=language,
            visible_text=visible_text,
            markdown=markdown or None,
            blocks=blocks,
            tables=tables,
            links=links,
        )

    def _blocks_and_tables(
        self, root: Tag, source_url: str
    ) -> tuple[tuple[ContentBlock, ...], tuple[TableArtifact, ...]]:
        blocks: list[ContentBlock] = []
        tables: list[TableArtifact] = []
        headings: list[tuple[int, str]] = []
        block_ids: dict[int, str] = {}

        for element in root.find_all([*_BLOCK_TAGS, "table"]):
            if not isinstance(element, Tag) or self._is_hidden(element):
                continue
            if element.find_parent("table") is not None and element.name != "table":
                continue
            if element.name == "p" and element.find_parent(["li", "details"]):
                continue
            if element.name in {"li", "dt", "dd"} and element.find_parent("details"):
                continue
            if element.name == "details" and element.find_parent("details"):
                continue

            text = self._clean(element.get_text(" ", strip=True))
            if not text:
                continue
            block_id = f"b{len(blocks) + 1}"
            block_ids[id(element)] = block_id
            locator = self._locator(element, source_url, block_id)
            parent_id = self._parent_block_id(element, block_ids)

            if element.name == "table":
                table_id = f"t{len(tables) + 1}"
                table = self._table(element, table_id, locator)
                tables.append(table)
                block_type = ContentBlockType.TABLE
            elif element.name.startswith("h") and len(element.name) == 2:
                level = int(element.name[1])
                headings = [(n, value) for n, value in headings if n < level]
                heading_path = tuple(value for _, value in headings)
                headings.append((level, text))
                blocks.append(
                    ContentBlock(
                        id=block_id,
                        type=ContentBlockType.HEADING,
                        text=text,
                        heading_path=heading_path,
                        parent_id=parent_id,
                        locator=locator,
                        visible=True,
                    )
                )
                continue
            elif element.name == "li":
                block_type = ContentBlockType.LIST
            elif element.name in {"dt", "dd"}:
                block_type = ContentBlockType.KEY_VALUE
            elif element.name == "details":
                block_type = ContentBlockType.ACCORDION
            else:
                block_type = ContentBlockType.PARAGRAPH

            blocks.append(
                ContentBlock(
                    id=block_id,
                    type=block_type,
                    text=text,
                    heading_path=tuple(value for _, value in headings),
                    parent_id=parent_id,
                    locator=locator,
                    visible=True,
                )
            )
        return tuple(blocks), tuple(tables)

    def _links(self, root: Tag, source_url: str) -> tuple[LinkArtifact, ...]:
        links: list[LinkArtifact] = []
        seen: set[str] = set()
        for element in root.find_all("a", href=True):
            if not isinstance(element, Tag) or self._is_hidden(element):
                continue
            absolute = self._normalized_http_url(
                urljoin(source_url, str(element["href"]))
            )
            if not absolute or absolute in seen:
                continue
            seen.add(absolute)
            declared_type = self._clean(str(element.get("type") or "")) or None
            path = urlsplit(absolute).path.lower()
            downloadable = (
                any(path.endswith(extension) for extension in _DOCUMENT_EXTENSIONS)
                or declared_type == "application/pdf"
                or element.has_attr("download")
            )
            link_id = f"l{len(links) + 1}"
            try:
                validate_source_url(absolute, self._allowed_hosts)
                same_source = True
            except DisallowedSourceUrl:
                same_source = False
            rel_value = element.get("rel") or ()
            rel = tuple(str(item) for item in rel_value)
            links.append(
                LinkArtifact(
                    id=link_id,
                    url=absolute,
                    text=self._clean(element.get_text(" ", strip=True)),
                    title=self._clean(str(element.get("title") or "")) or None,
                    rel=rel,
                    declared_mime_type=declared_type,
                    same_allowlisted_source=same_source,
                    downloadable=downloadable,
                    locator=self._locator(element, source_url, link_id),
                )
            )
        return tuple(links)

    def _table(
        self, element: Tag, table_id: str, locator: SourceLocator
    ) -> TableArtifact:
        caption_tag = element.find("caption")
        caption = (
            self._clean(caption_tag.get_text(" ", strip=True))
            if isinstance(caption_tag, Tag)
            else None
        )
        rows: list[tuple[str, ...]] = []
        headers: tuple[str, ...] = ()
        for row in element.find_all("tr"):
            cells = tuple(
                self._clean(cell.get_text(" ", strip=True))
                for cell in row.find_all(["th", "td"], recursive=False)
            )
            if not cells:
                continue
            if not headers and row.find("th", recursive=False):
                headers = cells
            else:
                rows.append(cells)
        return TableArtifact(
            id=table_id,
            caption=caption,
            headers=headers,
            rows=tuple(rows),
            locator=locator,
        )

    def _canonical_url(self, soup: BeautifulSoup, source_url: str) -> str:
        element = soup.select_one("link[rel~='canonical']")
        if isinstance(element, Tag) and element.get("href"):
            candidate = self._normalized_http_url(
                urljoin(source_url, str(element.get("href")))
            )
            if candidate:
                try:
                    return validate_source_url(candidate, self._allowed_hosts)
                except DisallowedSourceUrl:
                    pass
        return source_url

    @staticmethod
    def _normalized_http_url(value: str) -> str | None:
        parsed = urlsplit(urldefrag(value).url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        normalized = parsed._replace(
            scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower()
        )
        return urlunsplit(normalized)

    @classmethod
    def _clean(cls, value: str) -> str:
        return _WHITESPACE.sub(" ", value).strip()

    @classmethod
    def _is_hidden(cls, element: Tag) -> bool:
        for current in (element, *element.parents):
            if not isinstance(current, Tag):
                continue
            if current.has_attr("hidden") or current.get("aria-hidden") == "true":
                return True
            style = str(current.get("style") or "").replace(" ", "").lower()
            if "display:none" in style or "visibility:hidden" in style:
                return True
        return False

    def _locator(self, element: Tag, source_url: str, block_id: str) -> SourceLocator:
        return SourceLocator(
            source_url=source_url,
            source_type=SourceType.PAGE,
            block_id=block_id,
            css_selector=self._css_selector(element),
            xpath=self._xpath(element),
        )

    @staticmethod
    def _css_selector(element: Tag) -> str:
        parts: list[str] = []
        current: Tag | None = element
        while current is not None and current.name not in {"[document]", "html"}:
            if current.get("id"):
                parts.append(f"#{current.get('id')}")
                break
            siblings = (
                list(current.parent.find_all(current.name, recursive=False))
                if isinstance(current.parent, Tag)
                else []
            )
            position = siblings.index(current) + 1 if current in siblings else 1
            parts.append(f"{current.name}:nth-of-type({position})")
            current = current.parent if isinstance(current.parent, Tag) else None
        return " > ".join(reversed(parts))

    @staticmethod
    def _xpath(element: Tag) -> str:
        parts: list[str] = []
        current: Tag | None = element
        while current is not None and current.name != "[document]":
            siblings = (
                list(current.parent.find_all(current.name, recursive=False))
                if isinstance(current.parent, Tag)
                else []
            )
            position = siblings.index(current) + 1 if current in siblings else 1
            parts.append(f"{current.name}[{position}]")
            current = current.parent if isinstance(current.parent, Tag) else None
        return "/" + "/".join(reversed(parts))

    @staticmethod
    def _parent_block_id(element: Tag, block_ids: dict[int, str]) -> str | None:
        for parent in element.parents:
            if id(parent) in block_ids:
                return block_ids[id(parent)]
        return None

    @staticmethod
    def _markdown(
        blocks: tuple[ContentBlock, ...], tables: tuple[TableArtifact, ...]
    ) -> str:
        tables_by_id = {table.id: table for table in tables}
        lines: list[str] = []
        table_index = 0
        for block in blocks:
            if block.type is ContentBlockType.HEADING:
                level = min(len(block.heading_path) + 1, 6)
                lines.append(f"{'#' * level} {block.text}")
            elif block.type is ContentBlockType.LIST:
                lines.append(f"- {block.text}")
            elif block.type is ContentBlockType.TABLE:
                table_index += 1
                table = tables_by_id.get(f"t{table_index}")
                if table:
                    if table.caption:
                        lines.append(f"**{table.caption}**")
                    rows = ([table.headers] if table.headers else []) + list(table.rows)
                    if rows:
                        width = max(len(row) for row in rows)
                        normalized = [row + ("",) * (width - len(row)) for row in rows]
                        lines.append("| " + " | ".join(normalized[0]) + " |")
                        lines.append(
                            "| " + " | ".join("---" for _ in range(width)) + " |"
                        )
                        lines.extend(
                            "| " + " | ".join(row) + " |" for row in normalized[1:]
                        )
            else:
                lines.append(block.text)
            lines.append("")
        return "\n".join(lines).strip()
