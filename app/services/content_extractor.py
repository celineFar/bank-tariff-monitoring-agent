from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from app.domain.discovery import IngestedSource
from app.domain.extraction import (
    ExtractedBlock,
    ExtractedBlockType,
    ExtractedDocument,
    ExtractedDocumentContent,
    ExtractedLink,
    ExtractedTable,
    ExtractedTableRow,
    ExtractionStatistics,
    ExtractionWarning,
    SourceLocator,
    extraction_id_for,
)
from app.repositories.contracts import ContentExtractionRepository
from app.services.contracts import ArtifactStore

_HTML_MIME_TYPES = frozenset(("text/html", "application/xhtml+xml"))
_EXTRACTOR_NAME = "deterministic-html"
_EXTRACTOR_VERSION = "1.1"
_SPACE = re.compile(r"\s+")
_CSS_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_IGNORED_TAGS = frozenset(
    (
        "script",
        "style",
        "noscript",
        "template",
        "svg",
        "canvas",
        "iframe",
        "input",
        "button",
        "select",
        "textarea",
        "option",
        "nav",
        "footer",
        "header",
        "aside",
    )
)
_BOILERPLATE_MARKERS = frozenset(
    (
        "breadcrumb",
        "cookie",
        "footer",
        "header",
        "menu",
        "navigation",
        "newsletter",
        "popup",
        "share",
        "sidebar",
        "social",
    )
)
_LABEL_MARKERS = frozenset(("label", "name", "title", "caption", "key"))
_VALUE_MARKERS = frozenset(
    ("value", "amount", "description", "content", "text", "data")
)
_FACT_CONTAINER_MARKERS = frozenset(
    ("detail", "feature", "info", "parameter", "stat")
)


class ContentExtractionErrorCode(StrEnum):
    ARTIFACT_INTEGRITY = "artifact_integrity"
    UNSUPPORTED_MIME_TYPE = "unsupported_mime_type"
    EMPTY_DOCUMENT = "empty_document"


class ContentExtractionError(RuntimeError):
    def __init__(self, code: ContentExtractionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class _BlockDraft:
    block_type: ExtractedBlockType
    text: str
    section: tuple[str, ...]
    css_path: str
    label: str | None = None
    heading_level: int | None = None
    links: tuple[ExtractedLink, ...] = ()
    table: ExtractedTable | None = None


@dataclass(frozen=True)
class _HtmlResult:
    language: str | None
    blocks: tuple[ExtractedBlock, ...]
    warnings: tuple[ExtractionWarning, ...]


class DocumentContentExtractor:
    """Verify an ingested artifact, extract it, persist JSON, then record metadata."""

    def __init__(
        self,
        artifact_store: ArtifactStore,
        repository: ContentExtractionRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._artifact_store = artifact_store
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))

    async def extract(self, source: IngestedSource) -> ExtractedDocument:
        content = await self._artifact_store.read(source.artifact.storage_key)
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != source.artifact.sha256:
            raise ContentExtractionError(
                ContentExtractionErrorCode.ARTIFACT_INTEGRITY,
                "persisted source bytes did not match their SHA-256 metadata",
            )
        if len(content) != source.artifact.size_bytes:
            raise ContentExtractionError(
                ContentExtractionErrorCode.ARTIFACT_INTEGRITY,
                "persisted source size did not match its metadata",
            )

        mime_type = source.artifact.mime_type.partition(";")[0].strip().casefold()
        if mime_type not in _HTML_MIME_TYPES:
            raise ContentExtractionError(
                ContentExtractionErrorCode.UNSUPPORTED_MIME_TYPE,
                f"no content extractor is registered for {mime_type!r}",
            )

        html = await asyncio.to_thread(_extract_html, source, content)
        extraction_id = extraction_id_for(
            source_sha256=source.artifact.sha256,
            source_storage_key=source.artifact.storage_key,
            source_mime_type=mime_type,
            product_id=source.product_id,
            source_url=source.source_url,
            final_url=source.final_url,
            language=html.language,
            extractor=_EXTRACTOR_NAME,
            extractor_version=_EXTRACTOR_VERSION,
        )
        statistics = _statistics(html.blocks, html.warnings)
        document_content = ExtractedDocumentContent(
            extraction_id=extraction_id,
            product_id=source.product_id,
            source_url=source.source_url,
            final_url=source.final_url,
            source_storage_key=source.artifact.storage_key,
            source_sha256=source.artifact.sha256,
            source_mime_type=mime_type,
            language=html.language,
            extractor=_EXTRACTOR_NAME,
            extractor_version=_EXTRACTOR_VERSION,
            blocks=html.blocks,
            statistics=statistics,
            warnings=html.warnings,
        )
        encoded = _canonical_json(document_content)
        representation = await self._artifact_store.put_extracted(
            content=encoded,
            sha256=hashlib.sha256(encoded).hexdigest(),
        )
        result = ExtractedDocument(
            **document_content.model_dump(),
            representation_artifact=representation,
            extracted_at=self._clock(),
        )
        await self._repository.save_extraction(result)
        return result


def _extract_html(source: IngestedSource, content: bytes) -> _HtmlResult:
    soup = BeautifulSoup(content, "html.parser")
    for element in soup.find_all(_is_ignored_element):
        element.decompose()
    # DNN pages wrap the complete document in one ASP.NET form. Keep its content
    # while dropping the interactive container and controls.
    for form in soup.find_all("form"):
        form.unwrap()

    warnings: list[ExtractionWarning] = []
    root = _primary_content(soup)
    if root is None:
        raise ContentExtractionError(
            ContentExtractionErrorCode.EMPTY_DOCUMENT,
            "saved HTML did not contain a usable content root",
        )
    if root.name == "body":
        warnings.append(
            ExtractionWarning(
                code="body_fallback",
                message="no explicit primary-content container was found",
                source_locator=SourceLocator(css_path=_css_path(root)),
            )
        )

    language = source.language or _document_language(soup)
    if language is None:
        warnings.append(
            ExtractionWarning(
                code="language_unknown",
                message="neither ingestion metadata nor the HTML declared a language",
                source_locator=SourceLocator(css_path=_css_path(root)),
            )
        )

    drafts: list[_BlockDraft] = []
    headings: list[str] = []

    def add_element(element: Tag) -> None:
        if element.name and re.fullmatch(r"h[1-6]", element.name):
            text = _text(element)
            if not text:
                return
            level = int(element.name[1])
            del headings[level - 1 :]
            while len(headings) < level - 1:
                headings.append("")
            headings.append(text)
            drafts.append(
                _BlockDraft(
                    block_type=ExtractedBlockType.HEADING,
                    text=text,
                    section=tuple(item for item in headings if item),
                    css_path=_css_path(element),
                    heading_level=level,
                    links=_links(element, source.final_url, warnings),
                )
            )
            return

        if element.name == "dl":
            for term in element.find_all("dt", recursive=False):
                value = term.find_next_sibling("dd")
                label = _text(term)
                text = _text(value) if isinstance(value, Tag) else ""
                if label and text:
                    drafts.append(
                        _BlockDraft(
                            block_type=ExtractedBlockType.FACT,
                            text=text,
                            label=label,
                            section=tuple(item for item in headings if item),
                            css_path=_css_path(term.parent or term),
                            links=_links(value, source.final_url, warnings),
                        )
                    )
            return

        fact = _fact_parts(element)
        if fact is not None:
            label_element, value_element = fact
            drafts.append(
                _BlockDraft(
                    block_type=ExtractedBlockType.FACT,
                    text=_text(value_element),
                    label=_text(label_element),
                    section=tuple(item for item in headings if item),
                    css_path=_css_path(element),
                    links=_links(value_element, source.final_url, warnings),
                )
            )
            return

        if element.name == "table":
            table = _table(element)
            if table is not None:
                text = "\n".join(" | ".join(row.cells) for row in table.rows)
                drafts.append(
                    _BlockDraft(
                        block_type=ExtractedBlockType.TABLE,
                        text=text,
                        section=tuple(item for item in headings if item),
                        css_path=_css_path(element),
                        links=_links(element, source.final_url, warnings),
                        table=table,
                    )
                )
            return

        block_type = {
            "p": ExtractedBlockType.PARAGRAPH,
            "li": ExtractedBlockType.LIST_ITEM,
        }.get(element.name)
        if block_type is not None:
            text = _text(element)
            if text:
                drafts.append(
                    _BlockDraft(
                        block_type=block_type,
                        text=text,
                        section=tuple(item for item in headings if item),
                        css_path=_css_path(element),
                        links=_links(element, source.final_url, warnings),
                    )
                )
            return

        if element.name == "a" and _text(element):
            links = _links(element, source.final_url, warnings)
            if links:
                drafts.append(
                    _BlockDraft(
                        block_type=ExtractedBlockType.LINK,
                        text=_text(element),
                        section=tuple(item for item in headings if item),
                        css_path=_css_path(element),
                        links=links,
                    )
                )
            return

        for child in element.find_all(recursive=False):
            if isinstance(child, Tag):
                add_element(child)

    add_element(root)
    if not drafts:
        raise ContentExtractionError(
            ContentExtractionErrorCode.EMPTY_DOCUMENT,
            "saved HTML primary content did not contain extractable blocks",
        )

    blocks = tuple(
        ExtractedBlock(
            block_id=_block_id(source.artifact.sha256, ordinal, draft),
            ordinal=ordinal,
            block_type=draft.block_type,
            section=draft.section,
            text=draft.text,
            label=draft.label,
            heading_level=draft.heading_level,
            links=draft.links,
            table=draft.table,
            source_locator=SourceLocator(css_path=draft.css_path),
        )
        for ordinal, draft in enumerate(drafts)
    )
    return _HtmlResult(language=language, blocks=blocks, warnings=tuple(warnings))


def _primary_content(soup: BeautifulSoup) -> Tag | None:
    selectors = (
        "#wsc_main_content",
        "main",
        '[role="main"]',
        "article",
        ".DnnModule",
        ".main-content",
        ".content",
        "body",
    )
    for selector in selectors:
        element = soup.select_one(selector)
        if isinstance(element, Tag) and _text(element):
            return element
    return None


def _is_ignored_element(element: Tag) -> bool:
    if element.name in _IGNORED_TAGS:
        return True
    if element.get("hidden") is not None or element.get("aria-hidden") == "true":
        return True
    role = str(element.get("role", "")).casefold()
    if role in {"navigation", "banner", "contentinfo", "complementary"}:
        return True
    tokens = _marker_tokens(element)
    return bool(tokens & _BOILERPLATE_MARKERS)


def _marker_tokens(element: Tag) -> set[str]:
    class_attribute = element.get("class")
    if isinstance(class_attribute, list):
        classes = " ".join(str(item) for item in class_attribute)
    else:
        classes = str(class_attribute or "")
    raw = " ".join(
        (
            str(element.get("id", "")),
            classes,
        )
    ).casefold()
    return {item for item in re.split(r"[^a-z0-9]+", raw) if item}


def _fact_parts(element: Tag) -> tuple[Tag, Tag] | None:
    if element.name in {"html", "body", "main", "article", "table", "ul", "ol"}:
        return None
    children = [child for child in element.find_all(recursive=False) if _text(child)]
    if len(children) != 2:
        return None
    headings = [
        child
        for child in children
        if child.name and re.fullmatch(r"h[1-6]", child.name)
    ]
    paragraphs = [child for child in children if child.name == "p"]
    if (
        len(headings) == 1
        and len(paragraphs) == 1
        and _marker_tokens(element) & _FACT_CONTAINER_MARKERS
    ):
        # Ameria feature cards place the value in a styled heading and its label
        # in the following paragraph (for example, amount then "Loan amount").
        return paragraphs[0], headings[0]
    label = next(
        (child for child in children if _marker_tokens(child) & _LABEL_MARKERS),
        None,
    )
    value = next(
        (child for child in children if _marker_tokens(child) & _VALUE_MARKERS),
        None,
    )
    if label is None or value is None or label is value:
        return None
    if not _text(label) or not _text(value):
        return None
    return label, value


def _table(element: Tag) -> ExtractedTable | None:
    rows: list[ExtractedTableRow] = []
    for row in element.find_all("tr"):
        cells = tuple(
            text for cell in row.find_all(("th", "td"), recursive=False)
            if (text := _text(cell))
        )
        if cells:
            rows.append(
                ExtractedTableRow(
                    cells=cells,
                    is_header=bool(row.find("th", recursive=False)),
                )
            )
    if not rows:
        return None
    caption_element = element.find("caption")
    caption = _text(caption_element) if isinstance(caption_element, Tag) else None
    return ExtractedTable(caption=caption or None, rows=tuple(rows))


def _links(
    element: Tag,
    base_url: str,
    warnings: list[ExtractionWarning],
) -> tuple[ExtractedLink, ...]:
    links: list[ExtractedLink] = []
    candidates = [element] if element.name == "a" else element.find_all("a")
    for anchor in candidates:
        href = str(anchor.get("href", "")).strip()
        text = _text(anchor)
        target = urljoin(base_url, href)
        if not text or urlparse(target).scheme.casefold() not in {"http", "https"}:
            if href:
                warnings.append(
                    ExtractionWarning(
                        code="unsafe_link_ignored",
                        message="a non-HTTP link target was omitted",
                        source_locator=SourceLocator(css_path=_css_path(anchor)),
                    )
                )
            continue
        link = ExtractedLink(text=text, target=target)
        if link not in links:
            links.append(link)
    return tuple(links)


def _document_language(soup: BeautifulSoup) -> str | None:
    html = soup.find("html")
    if not isinstance(html, Tag):
        return None
    value = str(html.get("lang", "")).strip().replace("_", "-").casefold()
    return value or None


def _text(element: Tag | None) -> str:
    if element is None:
        return ""
    return _SPACE.sub(" ", element.get_text(" ", strip=True)).strip()


def _css_path(element: Tag) -> str:
    parts: list[str] = []
    current: Tag | None = element
    while isinstance(current, Tag) and current.name != "[document]":
        identifier = str(current.get("id", ""))
        if identifier and _CSS_IDENTIFIER.fullmatch(identifier):
            parts.append(f"{current.name}#{identifier}")
            break
        parent = current.parent
        if isinstance(parent, Tag):
            siblings = list(parent.find_all(current.name, recursive=False))
            if len(siblings) > 1:
                parts.append(f"{current.name}:nth-of-type({siblings.index(current) + 1})")
            else:
                parts.append(current.name)
        else:
            parts.append(current.name)
        current = parent if isinstance(parent, Tag) else None
    return " > ".join(reversed(parts))


def _block_id(source_sha256: str, ordinal: int, draft: _BlockDraft) -> str:
    identity = "\x1f".join(
        (
            source_sha256,
            str(ordinal),
            draft.block_type.value,
            draft.css_path,
            draft.label or "",
            draft.text,
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _statistics(
    blocks: tuple[ExtractedBlock, ...],
    warnings: tuple[ExtractionWarning, ...],
) -> ExtractionStatistics:
    return ExtractionStatistics(
        block_count=len(blocks),
        heading_count=sum(
            block.block_type is ExtractedBlockType.HEADING for block in blocks
        ),
        paragraph_count=sum(
            block.block_type is ExtractedBlockType.PARAGRAPH for block in blocks
        ),
        list_item_count=sum(
            block.block_type is ExtractedBlockType.LIST_ITEM for block in blocks
        ),
        table_count=sum(
            block.block_type is ExtractedBlockType.TABLE for block in blocks
        ),
        table_row_count=sum(
            len(block.table.rows) for block in blocks if block.table is not None
        ),
        link_count=sum(len(block.links) for block in blocks),
        text_character_count=sum(len(block.text) for block in blocks),
        warning_count=len(warnings),
    )


def _canonical_json(content: ExtractedDocumentContent) -> bytes:
    payload: dict[str, Any] = content.model_dump(mode="json")
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
