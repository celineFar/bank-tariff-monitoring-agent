from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import io
import json
import re
import statistics
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urljoin, urlparse

import pdfplumber
from bs4 import BeautifulSoup, Tag
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.domain.discovery import IngestedSource
from app.domain.extraction import (
    ExtractedBlock,
    ExtractedBlockType,
    ExtractedDocument,
    ExtractedDocumentContent,
    ExtractedLink,
    ExtractedPage,
    ExtractedPageTable,
    ExtractedTable,
    ExtractedTableRow,
    ExtractionStatistics,
    ExtractionStatus,
    ExtractionWarning,
    OcrAssessment,
    PdfDocumentMetadata,
    SourceLocator,
    extraction_id_for,
)
from app.repositories.contracts import ContentExtractionRepository
from app.services.contracts import ArtifactStore

_HTML_MIME_TYPES = frozenset(("text/html", "application/xhtml+xml"))
_PDF_MIME_TYPE = "application/pdf"
_HTML_EXTRACTOR_NAME = "deterministic-html"
_HTML_EXTRACTOR_VERSION = "1.1"
_PDF_EXTRACTOR_NAME = "pdfplumber"
_PDF_EXTRACTOR_VERSION = "1.0"
_INVALID_UNICODE_THRESHOLD = 0.02
_UNREADABLE_CHARACTER_THRESHOLD = 0.10
_MAX_PDF_PAGES = 500
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
_FACT_CONTAINER_MARKERS = frozenset(("detail", "feature", "info", "parameter", "stat"))


class ContentExtractionErrorCode(StrEnum):
    ARTIFACT_INTEGRITY = "artifact_integrity"
    UNSUPPORTED_MIME_TYPE = "unsupported_mime_type"
    EMPTY_DOCUMENT = "empty_document"
    MALFORMED_PDF = "malformed_pdf"
    ENCRYPTED_PDF = "encrypted_pdf"
    PDF_TOO_LARGE = "pdf_too_large"


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


@dataclass(frozen=True)
class _ExtractionResult:
    language: str | None
    extractor: str
    extractor_version: str
    status: ExtractionStatus
    blocks: tuple[ExtractedBlock, ...]
    pages: tuple[ExtractedPage, ...]
    pdf_metadata: PdfDocumentMetadata | None
    ocr: OcrAssessment
    statistics: ExtractionStatistics
    warnings: tuple[ExtractionWarning, ...]


class DocumentContentExtractor:
    """Verify an ingested artifact, extract it, persist JSON, then record metadata."""

    def __init__(
        self,
        artifact_store: ArtifactStore,
        repository: ContentExtractionRepository,
        *,
        min_text_characters_per_page: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if min_text_characters_per_page < 0:
            raise ValueError("minimum text characters per page cannot be negative")
        self._artifact_store = artifact_store
        self._repository = repository
        self._min_text_characters_per_page = min_text_characters_per_page
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
        if mime_type in _HTML_MIME_TYPES:
            html = await asyncio.to_thread(_extract_html, source, content)
            extracted = _ExtractionResult(
                language=html.language,
                extractor=_HTML_EXTRACTOR_NAME,
                extractor_version=_HTML_EXTRACTOR_VERSION,
                status=ExtractionStatus.SUCCESS,
                blocks=html.blocks,
                pages=(),
                pdf_metadata=None,
                ocr=OcrAssessment(status=ExtractionStatus.SUCCESS),
                statistics=_statistics(html.blocks, html.warnings),
                warnings=html.warnings,
            )
        elif mime_type == _PDF_MIME_TYPE:
            extracted = await asyncio.to_thread(
                _extract_pdf,
                source,
                content,
                self._min_text_characters_per_page,
            )
        else:
            raise ContentExtractionError(
                ContentExtractionErrorCode.UNSUPPORTED_MIME_TYPE,
                f"no content extractor is registered for {mime_type!r}",
            )
        extraction_id = extraction_id_for(
            source_sha256=source.artifact.sha256,
            source_storage_key=source.artifact.storage_key,
            source_mime_type=mime_type,
            product_id=source.product_id,
            source_url=source.source_url,
            final_url=source.final_url,
            language=extracted.language,
            extractor=extracted.extractor,
            extractor_version=extracted.extractor_version,
        )
        document_content = ExtractedDocumentContent(
            extraction_id=extraction_id,
            product_id=source.product_id,
            source_url=source.source_url,
            final_url=source.final_url,
            source_storage_key=source.artifact.storage_key,
            source_sha256=source.artifact.sha256,
            source_mime_type=mime_type,
            language=extracted.language,
            extractor=extracted.extractor,
            extractor_version=extracted.extractor_version,
            status=extracted.status,
            blocks=extracted.blocks,
            pages=extracted.pages,
            pdf_metadata=extracted.pdf_metadata,
            ocr=extracted.ocr,
            statistics=extracted.statistics,
            warnings=extracted.warnings,
        )
        encoded = _canonical_json(document_content)
        representation = await self._artifact_store.put_extracted(
            content=encoded,
            sha256=hashlib.sha256(encoded).hexdigest(),
            source_sha256=source.artifact.sha256,
            extractor=extracted.extractor,
            extractor_version=extracted.extractor_version,
        )
        result = ExtractedDocument(
            **document_content.model_dump(),
            representation_artifact=representation,
            extracted_at=self._clock(),
        )
        await self._repository.save_extraction(result)
        return result


def _extract_pdf(
    source: IngestedSource,
    content: bytes,
    min_text_characters_per_page: int,
) -> _ExtractionResult:
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise ContentExtractionError(
                ContentExtractionErrorCode.ENCRYPTED_PDF,
                "encrypted PDFs cannot be extracted deterministically",
            )
        page_count = len(reader.pages)
    except ContentExtractionError:
        raise
    except (PdfReadError, OSError, ValueError) as exc:
        raise ContentExtractionError(
            ContentExtractionErrorCode.MALFORMED_PDF,
            f"PDF validation failed: {exc}",
        ) from exc

    if page_count == 0:
        raise ContentExtractionError(
            ContentExtractionErrorCode.EMPTY_DOCUMENT,
            "PDF contained no pages",
        )
    if page_count > _MAX_PDF_PAGES:
        raise ContentExtractionError(
            ContentExtractionErrorCode.PDF_TOO_LARGE,
            f"PDF has {page_count} pages; limit is {_MAX_PDF_PAGES}",
        )

    try:
        metadata = _pdf_metadata(reader)
    except (PdfReadError, TypeError, ValueError) as exc:
        raise ContentExtractionError(
            ContentExtractionErrorCode.MALFORMED_PDF,
            f"PDF metadata extraction failed: {exc}",
        ) from exc
    pages: list[ExtractedPage] = []
    warnings: list[ExtractionWarning] = []
    page_reasons: dict[int, tuple[str, ...]] = {}
    try:
        with pdfplumber.open(io.BytesIO(content)) as document:
            if len(document.pages) != page_count:
                raise ContentExtractionError(
                    ContentExtractionErrorCode.MALFORMED_PDF,
                    "PDF parsers disagreed about the page count",
                )
            for page_number, page in enumerate(document.pages, start=1):
                extracted_page, reasons = _extract_pdf_page(
                    source.artifact.sha256,
                    page_number,
                    page,
                    min_text_characters_per_page,
                )
                pages.append(extracted_page)
                warnings.extend(extracted_page.warnings)
                if reasons:
                    page_reasons[page_number] = reasons
    except ContentExtractionError:
        raise
    except Exception as exc:
        raise ContentExtractionError(
            ContentExtractionErrorCode.MALFORMED_PDF,
            f"PDF layout extraction failed: {exc}",
        ) from exc

    requiring_ocr = tuple(page_reasons)
    if requiring_ocr:
        primary_reason = next(
            reason for candidate in page_reasons.values() for reason in candidate
        )
        status = ExtractionStatus.NEEDS_OCR
        ocr = OcrAssessment(
            status=status,
            pages_requiring_ocr=requiring_ocr,
            reason=primary_reason,
            page_reasons=page_reasons,
        )
    else:
        status = ExtractionStatus.SUCCESS
        ocr = OcrAssessment(status=status)

    page_tuple = tuple(pages)
    warning_tuple = tuple(warnings)
    return _ExtractionResult(
        language=source.language,
        extractor=_PDF_EXTRACTOR_NAME,
        extractor_version=_PDF_EXTRACTOR_VERSION,
        status=status,
        blocks=(),
        pages=page_tuple,
        pdf_metadata=metadata,
        ocr=ocr,
        statistics=_statistics((), warning_tuple, pages=page_tuple, ocr=ocr),
        warnings=warning_tuple,
    )


def _pdf_metadata(reader: PdfReader) -> PdfDocumentMetadata:
    raw = reader.metadata

    def value(name: str) -> str | None:
        if raw is None:
            return None
        item = getattr(raw, name, None)
        return str(item) if item is not None else None

    return PdfDocumentMetadata(
        title=value("title"),
        author=value("author"),
        subject=value("subject"),
        creator=value("creator"),
        producer=value("producer"),
        creation_date=value("creation_date"),
        modification_date=value("modification_date"),
        is_encrypted=False,
        pypdf_version=importlib.metadata.version("pypdf"),
        pdfplumber_version=importlib.metadata.version("pdfplumber"),
    )


def _extract_pdf_page(
    source_sha256: str,
    page_number: int,
    page: Any,
    min_text_characters_per_page: int,
) -> tuple[ExtractedPage, tuple[str, ...]]:
    page_warnings: list[ExtractionWarning] = []
    locator = SourceLocator(page=page_number)
    text_failed = False
    try:
        words = page.extract_words(
            use_text_flow=True,
            keep_blank_chars=False,
            extra_attrs=["size"],
        )
    except Exception as exc:
        words = []
        text_failed = True
        page_warnings.append(
            ExtractionWarning(
                code="text_extraction_failed",
                message=f"text extraction failed: {type(exc).__name__}",
                source_locator=locator,
            )
        )

    blocks = _pdf_blocks(source_sha256, page_number, words)
    page_tables: list[ExtractedPageTable] = []
    table_failed = False
    try:
        discovered_tables = page.find_tables()
        for found in discovered_tables:
            rows = found.extract()
            normalized_rows = tuple(
                ExtractedTableRow(
                    cells=tuple(_normalize_pdf_cell(cell) for cell in row),
                    is_header=index == 0,
                )
                for index, row in enumerate(rows)
                if row and any(_normalize_pdf_cell(cell) for cell in row)
            )
            if not normalized_rows:
                continue
            bbox = tuple(float(coordinate) for coordinate in found.bbox)
            page_tables.append(
                ExtractedPageTable(
                    ordinal=len(page_tables),
                    table=ExtractedTable(rows=normalized_rows),
                    source_locator=SourceLocator(
                        page=page_number,
                        bounding_box=bbox,
                    ),
                )
            )
    except Exception as exc:
        table_failed = True
        page_warnings.append(
            ExtractionWarning(
                code="table_extraction_failed",
                message=f"table extraction failed: {type(exc).__name__}",
                source_locator=locator,
            )
        )

    text = "\n".join(block.text for block in blocks)
    character_count = len(text)
    try:
        image_count = len(page.images or ())
    except Exception as exc:
        image_count = 0
        page_warnings.append(
            ExtractionWarning(
                code="image_detection_failed",
                message=f"image detection failed: {type(exc).__name__}",
                source_locator=locator,
            )
        )
    invalid_ratio = _invalid_unicode_ratio(text)
    unreadable_ratio = _unreadable_character_ratio(text)
    is_empty = character_count == 0 and image_count == 0
    is_image_only = image_count > 0 and (
        character_count == 0
        or (
            min_text_characters_per_page > 0
            and character_count < min_text_characters_per_page
        )
    )
    reasons: list[str] = []
    if text_failed:
        reasons.append("text_extraction_failed")
    elif is_image_only:
        reasons.append("image_only")
    elif 0 < character_count < min_text_characters_per_page:
        reasons.append("insufficient_text")
    if invalid_ratio > _INVALID_UNICODE_THRESHOLD:
        reasons.append("invalid_unicode")
    if unreadable_ratio > _UNREADABLE_CHARACTER_THRESHOLD:
        reasons.append("unreadable_text")
    if table_failed:
        reasons.append("table_extraction_failed")
    if is_empty:
        page_warnings.append(
            ExtractionWarning(
                code="empty_page",
                message="page contains neither extractable text nor images",
                source_locator=locator,
            )
        )
    for reason in reasons:
        page_warnings.append(
            ExtractionWarning(
                code=f"ocr_{reason}",
                message=f"page requires OCR because of {reason.replace('_', ' ')}",
                source_locator=locator,
            )
        )

    return (
        ExtractedPage(
            page_number=page_number,
            width=float(page.width),
            height=float(page.height),
            blocks=blocks,
            tables=tuple(page_tables),
            warnings=tuple(page_warnings),
            text_character_count=character_count,
            image_count=image_count,
            invalid_unicode_ratio=invalid_ratio,
            unreadable_character_ratio=unreadable_ratio,
            is_empty=is_empty,
            is_image_only=is_image_only,
            is_scanned=is_image_only,
            needs_ocr=bool(reasons),
        ),
        tuple(reasons),
    )


def _pdf_blocks(
    source_sha256: str, page_number: int, words: list[dict[str, Any]]
) -> tuple[ExtractedBlock, ...]:
    if not words:
        return ()
    sizes = [float(word.get("size") or 0) for word in words]
    positive_sizes = [size for size in sizes if size > 0]
    body_size = statistics.median(positive_sizes) if positive_sizes else 0
    lines: list[list[dict[str, Any]]] = []
    for word in words:
        if not lines or abs(float(word["top"]) - float(lines[-1][0]["top"])) > 3:
            lines.append([word])
        else:
            lines[-1].append(word)

    blocks: list[ExtractedBlock] = []
    section: tuple[str, ...] = ()
    for line in lines:
        text = _SPACE.sub(" ", " ".join(str(word["text"]) for word in line)).strip()
        if not text:
            continue
        line_size = max(float(word.get("size") or 0) for word in line)
        is_heading = body_size > 0 and line_size >= body_size * 1.2 and len(text) <= 200
        block_type = (
            ExtractedBlockType.HEADING if is_heading else ExtractedBlockType.PARAGRAPH
        )
        if is_heading:
            section = (text,)
        bbox = (
            min(float(word["x0"]) for word in line),
            min(float(word["top"]) for word in line),
            max(float(word["x1"]) for word in line),
            max(float(word["bottom"]) for word in line),
        )
        ordinal = len(blocks)
        identity = "\x1f".join(
            (source_sha256, str(page_number), str(ordinal), block_type.value, text)
        )
        blocks.append(
            ExtractedBlock(
                block_id=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                ordinal=ordinal,
                block_type=block_type,
                section=section,
                text=text,
                heading_level=1 if is_heading else None,
                source_locator=SourceLocator(
                    page=page_number,
                    bounding_box=bbox,
                ),
            )
        )
    return tuple(blocks)


def _normalize_pdf_cell(value: object) -> str:
    return _SPACE.sub(" ", str(value or "")).strip()


def _invalid_unicode_ratio(text: str) -> float:
    if not text:
        return 0.0
    invalid = sum(
        character == "\ufffd"
        or 0xD800 <= ord(character) <= 0xDFFF
        or ord(character) in {0xFFFE, 0xFFFF}
        for character in text
    )
    return invalid / len(text)


def _unreadable_character_ratio(text: str) -> float:
    if not text:
        return 0.0
    unreadable = sum(
        unicodedata.category(character) in {"Cc", "Co", "Cs"}
        and character not in "\n\r\t"
        for character in text
    )
    repeated = sum(
        len(match.group(0))
        for match in re.finditer(r"([^\s])\1{11,}", text, flags=re.UNICODE)
    )
    return min(1.0, (unreadable + repeated) / len(text))


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
            text
            for cell in row.find_all(("th", "td"), recursive=False)
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
                parts.append(
                    f"{current.name}:nth-of-type({siblings.index(current) + 1})"
                )
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
    *,
    pages: tuple[ExtractedPage, ...] = (),
    ocr: OcrAssessment | None = None,
) -> ExtractionStatistics:
    page_blocks = tuple(block for page in pages for block in page.blocks)
    all_blocks = blocks + page_blocks
    page_tables = tuple(table for page in pages for table in page.tables)
    return ExtractionStatistics(
        block_count=len(all_blocks),
        heading_count=sum(
            block.block_type is ExtractedBlockType.HEADING for block in all_blocks
        ),
        paragraph_count=sum(
            block.block_type is ExtractedBlockType.PARAGRAPH for block in all_blocks
        ),
        list_item_count=sum(
            block.block_type is ExtractedBlockType.LIST_ITEM for block in all_blocks
        ),
        table_count=sum(
            block.block_type is ExtractedBlockType.TABLE for block in blocks
        )
        + len(page_tables),
        table_row_count=sum(
            len(block.table.rows) for block in blocks if block.table is not None
        )
        + sum(len(table.table.rows) for table in page_tables),
        link_count=sum(len(block.links) for block in all_blocks),
        text_character_count=sum(len(block.text) for block in all_blocks),
        warning_count=len(warnings),
        page_count=len(pages),
        empty_page_count=sum(page.is_empty for page in pages),
        image_only_page_count=sum(page.is_image_only for page in pages),
        pages_requiring_ocr_count=len(ocr.pages_requiring_ocr) if ocr else 0,
    )


def _canonical_json(content: ExtractedDocumentContent) -> bytes:
    payload: dict[str, Any] = content.model_dump(mode="json")
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
