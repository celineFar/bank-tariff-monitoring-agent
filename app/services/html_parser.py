from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from app.domain.acquisition import (
    ContentBlock,
    ContentBlockType,
    ImageArtifact,
    InteractiveControlArtifact,
    LinkArtifact,
    SourceLocator,
    SourceType,
    TableArtifact,
    TableCellArtifact,
)
from app.security.urls import DisallowedSourceUrl, validate_source_url

_WHITESPACE = re.compile(r"[\t\r\f\v ]+")
_BLOCK_TAGS = frozenset(
    {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt", "dd", "details"}
)
_DOCUMENT_EXTENSIONS = frozenset({".pdf"})
_SECTIONING_TAGS = frozenset({"article", "aside", "main", "section"})
_SITE_CHROME_ROLES = frozenset({"navigation", "banner", "contentinfo"})
_ACCORDION_TITLE = re.compile(
    r"(?:accordion|faq).*(?:title|header|question|trigger)", re.I
)
_ACCORDION_PANEL = re.compile(r"(?:accordion|faq).*(?:panel|content|answer)", re.I)
_CARD_CONTAINER = re.compile(r"(?:^|[-_])card(?:$|__item$|[-_]item$)", re.I)
_NESTED_HEADING_BLOCKS = frozenset(
    {"div", "section", "article", "p", "table", "details", "ul", "ol"}
)
_SUPERSCRIPT_DIGITS = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_LINE_BREAK_TAGS = frozenset(
    {
        "p",
        "div",
        "section",
        "article",
        "main",
        "aside",
        "header",
        "footer",
        "nav",
        "form",
        "fieldset",
        "figure",
        "figcaption",
        "blockquote",
        "address",
        "details",
        "summary",
        "li",
        "dl",
        "dt",
        "dd",
        "table",
        "caption",
        "thead",
        "tbody",
        "tfoot",
    }
    | _HEADING_TAGS
)
# Containers whose own text (outside any child block) becomes a paragraph block.
_BARE_TEXT_CONTAINERS = frozenset(
    {"div", "section", "article", "main", "aside", "form", "figure", "figcaption"}
)
# Children left out of a container's own text: they are blocks of their own, or
# controls and media that carry no page content.
_NOT_OWN_TEXT = _LINE_BREAK_TAGS | {
    "ul",
    "ol",
    "pre",
    "button",
    "select",
    "option",
    "textarea",
    "input",
    "svg",
    "iframe",
    "canvas",
    "video",
    "audio",
    "object",
    "hr",
}
# Ancestors whose block already includes all descendant text.
_COVERING_ANCESTORS = ("li", "dt", "dd", "p", "details", "table", "button")
# The smallest items that describe one link, and how much of their text to keep.
_LINK_CONTEXT_TAGS = ("tr", "li", "p", "dd", "dt", *sorted(_HEADING_TAGS))
_LINK_CONTEXT_CHARS = 600
# Containers that bound a heading: a heading inside one does not label what
# follows the container.
_HEADING_SCOPES = frozenset({"section", "article", "details"})


@dataclass(frozen=True, slots=True)
class ParsedHtml:
    canonical_url: str
    title: str | None
    language: str | None
    visible_text: str
    # Visible text outside the site's header, menus and footer: the part of the
    # page that is about this page.
    main_text: str
    markdown: str | None
    blocks: tuple[ContentBlock, ...]
    tables: tuple[TableArtifact, ...]
    links: tuple[LinkArtifact, ...]
    images: tuple[ImageArtifact, ...]
    interactive_controls: tuple[InteractiveControlArtifact, ...]
    # Ids of the blocks, tables, links, images and controls that sit in the
    # site's header, navigation or footer. The page's identity leaves them out:
    # a footer module that loads late must not rename the page.
    chrome_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class _GridValue:
    text: str
    markdown: str


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
        chrome_ids: set[str] = set()
        links, links_by_element = self._links(root, source_url, chrome_ids)
        images = self._images(root, source_url, chrome_ids)
        interactive_controls = self._interactive_controls(root, source_url, chrome_ids)
        blocks, tables, chrome_block_ids = self._blocks_and_tables(
            root, source_url, links_by_element
        )
        chrome_ids |= chrome_block_ids
        chrome_ids |= {
            block.table_id
            for block in blocks
            if block.table_id and block.id in chrome_block_ids
        }
        visible_text = self._clean(" ".join(block.text for block in blocks))
        main_text = self._clean(
            " ".join(block.text for block in blocks if block.id not in chrome_block_ids)
        )
        markdown = self._markdown(blocks, tables)
        return ParsedHtml(
            canonical_url=canonical_url,
            title=title,
            language=language,
            visible_text=visible_text,
            main_text=main_text,
            markdown=markdown or None,
            blocks=blocks,
            tables=tables,
            links=links,
            images=images,
            interactive_controls=interactive_controls,
            chrome_ids=frozenset(chrome_ids),
        )

    def _blocks_and_tables(
        self,
        root: Tag,
        source_url: str,
        links_by_element: dict[int, LinkArtifact],
    ) -> tuple[tuple[ContentBlock, ...], tuple[TableArtifact, ...], frozenset[str]]:
        blocks: list[ContentBlock] = []
        tables: list[TableArtifact] = []
        chrome_block_ids: set[str] = set()
        # (level, text, id of the container that bounds the heading, or None).
        # Accordion titles enter at level 0: they head their panel only.
        headings: list[tuple[int, str, int | None]] = []
        block_ids: dict[int, str] = {}
        accordion_titles, accordion_panels = self._accordion_parts(root)
        accordion_block_ids: dict[int, str] = {}
        card_elements = self._card_elements(root)
        block_parts = frozenset(accordion_titles) | frozenset(card_elements)
        paired_dd: set[int] = set()
        # Ids are fixed up front, in document order, so an outer table can point
        # at a table nested in one of its cells before that table is reached.
        table_refs: dict[int, str] = {}
        for table_element in root.find_all("table"):
            if self._is_hidden(table_element) or any(
                id(parent) in block_parts for parent in table_element.parents
            ):
                continue
            table_refs[id(table_element)] = f"t{len(table_refs) + 1}"

        def is_candidate(tag: Tag) -> bool:
            return (
                tag.name in _BLOCK_TAGS
                or tag.name == "table"
                or tag.name in _BARE_TEXT_CONTAINERS
                or id(tag) in accordion_titles
                or id(tag) in card_elements
            )

        def heading_scope(element: Tag) -> int | None:
            for parent in element.parents:
                if (
                    parent.name in _HEADING_SCOPES
                    or parent.get("role") == "tabpanel"
                    or id(parent) in accordion_panels
                    or id(parent) in card_elements
                ):
                    return id(parent)
            return None

        for element in root.find_all(is_candidate):
            if not isinstance(element, Tag) or self._is_hidden(element):
                continue
            if element.find_parent("table") is not None and element.name != "table":
                continue
            if element.name == "p" and element.find_parent(
                ["li", "details", "dt", "dd"]
            ):
                continue
            if element.name in {"li", "dt", "dd"} and element.find_parent("details"):
                continue
            if element.name == "li" and element.find_parent("li") is not None:
                # The outer item's block already lists the nested items.
                continue
            if element.name == "dd" and id(element) in paired_dd:
                continue
            if element.name == "details" and element.find_parent("details"):
                continue
            if any(id(parent) in accordion_titles for parent in element.parents):
                continue
            if any(id(parent) in card_elements for parent in element.parents):
                continue
            is_part = id(element) in block_parts
            bare_text = not is_part and element.name in _BARE_TEXT_CONTAINERS
            if bare_text and element.find_parent(list(_COVERING_ANCESTORS)) is not None:
                continue

            ancestor_ids = {id(parent) for parent in element.parents}
            headings = [
                entry
                for entry in headings
                if entry[2] is None or entry[2] in ancestor_ids
            ]

            is_heading = element.name in _HEADING_TAGS
            own_text = {"exclude": _NOT_OWN_TEXT, "exclude_ids": block_parts}
            text_options: dict[str, object] = own_text if bare_text else {}
            text = self._structured_text(
                element,
                markdown=False,
                exclude_nested_blocks=is_heading,
                table_refs=table_refs,
                **text_options,  # type: ignore[arg-type]
            )
            if not text:
                continue
            block_id = f"b{len(blocks) + 1}"
            if not bare_text:
                # A container's own stray text is not the parent of the blocks
                # inside it; only real blocks are.
                block_ids[id(element)] = block_id
            if self._in_site_chrome(element):
                chrome_block_ids.add(block_id)
            locator = self._locator(element, source_url, block_id)
            parent_id = self._accordion_parent_id(
                element, accordion_panels, accordion_block_ids
            ) or self._parent_block_id(element, block_ids)
            link_ids = self._contained_link_ids(
                element,
                links_by_element,
                **text_options,  # type: ignore[arg-type]
            )
            block_markdown = self._structured_text(
                element,
                markdown=True,
                links_by_element=links_by_element,
                exclude_nested_blocks=is_heading,
                table_refs=table_refs,
                **text_options,  # type: ignore[arg-type]
            )
            heading_path = tuple(value for _, value, _ in headings)
            table_id: str | None = None
            key_value: tuple[str, str] | None = None

            if element.name == "table":
                table_id = table_refs.get(id(element)) or f"t{len(tables) + 1}"
                table = self._table(
                    element,
                    table_id,
                    locator,
                    source_url,
                    links_by_element,
                    table_refs,
                )
                tables.append(table)
                block_type = ContentBlockType.TABLE
                block_markdown = None
            elif id(element) in accordion_titles:
                block_type = ContentBlockType.ACCORDION
                container_id = accordion_titles[id(element)]
                accordion_block_ids[container_id] = block_id
                headings.append((0, text, container_id))
            elif id(element) in card_elements:
                block_type = ContentBlockType.CARD
            elif is_heading:
                level = int(element.name[1])
                headings = [entry for entry in headings if entry[0] < level]
                heading_path = tuple(value for _, value, _ in headings)
                headings.append((level, text, heading_scope(element)))
                block_type = ContentBlockType.HEADING
            elif element.name == "li":
                block_type = ContentBlockType.LIST
            elif element.name in {"dt", "dd"}:
                block_type = ContentBlockType.KEY_VALUE
                if element.name == "dt":
                    pair = self._definition_values(element, links_by_element)
                    if pair is not None:
                        values, value_markdown, value_links, value_ids = pair
                        paired_dd.update(value_ids)
                        key = text.rstrip(":").strip()
                        key_value = (key, values)
                        text = f"{key}: {values}"
                        block_markdown = (
                            f"{block_markdown.rstrip(':').strip()}: {value_markdown}"
                        )
                        link_ids = (*link_ids, *value_links)
            elif element.name == "details":
                block_type = ContentBlockType.ACCORDION
            else:
                block_type = ContentBlockType.PARAGRAPH

            blocks.append(
                ContentBlock(
                    id=block_id,
                    type=block_type,
                    text=text,
                    markdown=block_markdown,
                    heading_path=heading_path,
                    parent_id=parent_id,
                    link_ids=link_ids,
                    locator=locator,
                    visible=True,
                    table_id=table_id,
                    key_value=key_value,
                )
            )
        return tuple(blocks), tuple(tables), frozenset(chrome_block_ids)

    def _definition_values(
        self, term: Tag, links_by_element: dict[int, LinkArtifact]
    ) -> tuple[str, str, tuple[str, ...], tuple[int, ...]] | None:
        """The visible `dd` values that follow a `dt`, up to the next `dt`."""
        values: list[Tag] = []
        for sibling in term.find_next_siblings():
            if sibling.name == "dt":
                break
            if sibling.name == "dd" and not self._is_hidden(sibling):
                values.append(sibling)
        texts = [self._structured_text(value, markdown=False) for value in values]
        if not any(texts):
            return None
        markdowns = [
            self._structured_text(
                value, markdown=True, links_by_element=links_by_element
            )
            for value in values
        ]
        return (
            "\n".join(text for text in texts if text),
            "\n".join(text for text in markdowns if text),
            tuple(
                link_id
                for value in values
                for link_id in self._contained_link_ids(value, links_by_element)
            ),
            tuple(id(value) for value in values),
        )

    @staticmethod
    def _in_site_chrome(element: Tag) -> bool:
        """Whether the element sits in the site's navigation, banner or footer.

        Follows the ARIA mapping: `nav` is always navigation, but a `header` or
        `footer` is the site's banner or footer only when it is not inside an
        article, aside, main or section -- there it belongs to that content.
        """
        ancestors = [
            current
            for current in (element, *element.parents)
            if isinstance(current, Tag)
        ]
        for index, current in enumerate(ancestors):
            if str(current.get("role") or "").lower() in _SITE_CHROME_ROLES:
                return True
            if current.name == "nav":
                return True
            if current.name in {"header", "footer"} and not any(
                outer.name in _SECTIONING_TAGS for outer in ancestors[index + 1 :]
            ):
                return True
        return False

    def _links(
        self, root: Tag, source_url: str, chrome_ids: set[str]
    ) -> tuple[tuple[LinkArtifact, ...], dict[int, LinkArtifact]]:
        links: list[LinkArtifact] = []
        by_element: dict[int, LinkArtifact] = {}
        for element in root.find_all("a", href=True):
            if not isinstance(element, Tag) or self._is_hidden(element):
                continue
            raw_href = str(element["href"])
            resolved = urljoin(source_url, raw_href)
            fragment = urldefrag(resolved).fragment or None
            absolute = self._normalized_http_url(resolved)
            if not absolute:
                continue
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
            artifact = LinkArtifact(
                id=link_id,
                url=absolute,
                raw_href=raw_href,
                fragment=fragment,
                text=self._clean(element.get_text(" ", strip=True)),
                title=self._clean(str(element.get("title") or "")) or None,
                rel=rel,
                declared_mime_type=declared_type,
                same_allowlisted_source=same_source,
                downloadable=downloadable,
                locator=self._locator(element, source_url, link_id),
                context_text=self._link_context(element),
            )
            links.append(artifact)
            if self._in_site_chrome(element):
                chrome_ids.add(link_id)
            by_element[id(element)] = artifact
        return tuple(links), by_element

    @classmethod
    def _link_context(cls, anchor: Tag) -> str:
        """The text of the smallest item that holds the link: its table row,
        list item, paragraph, definition or heading.

        A PDF's dates and "archive" words must come from its own row, not from
        the whole table or list it sits in, where neighbouring links' dates
        would decide for it.
        """
        item = anchor.find_parent(list(_LINK_CONTEXT_TAGS))
        if item is None:
            return ""
        return cls._structured_text(item, markdown=False)[:_LINK_CONTEXT_CHARS]

    def _table(
        self,
        element: Tag,
        table_id: str,
        locator: SourceLocator,
        source_url: str,
        links_by_element: dict[int, LinkArtifact],
        table_refs: dict[int, str] | None = None,
    ) -> TableArtifact:
        caption_tag = element.find("caption", recursive=False)
        caption = (
            self._clean(caption_tag.get_text(" ", strip=True))
            if isinstance(caption_tag, Tag)
            else None
        )
        # Only this table's own rows: a table nested in a cell keeps its rows.
        physical_rows = [
            row
            for row in element.find_all("tr")
            if row.find_parent("table") is element
            and row.find_all(["th", "td"], recursive=False)
        ]
        active: dict[int, tuple[_GridValue, int]] = {}
        grid_rows: list[tuple[tuple[str, ...], tuple[str, ...], list[Tag]]] = []
        cells: list[TableCellArtifact] = []
        column_count = 0

        for row_index, row in enumerate(physical_rows):
            logical: dict[int, _GridValue] = {}
            next_active: dict[int, tuple[_GridValue, int]] = {}
            for column, (value, remaining) in active.items():
                logical[column] = value
                if remaining > 1:
                    next_active[column] = (value, remaining - 1)

            physical_cells = list(row.find_all(["th", "td"], recursive=False))
            in_thead = row.find_parent("thead") is not None
            row_has_data_cells = any(cell.name == "td" for cell in physical_cells)
            cursor = 0
            for physical_cell in physical_cells:
                while cursor in logical:
                    cursor += 1
                rowspan = self._positive_span(physical_cell.get("rowspan"))
                colspan = self._positive_span(physical_cell.get("colspan"))
                text = self._structured_text(
                    physical_cell, markdown=False, table_refs=table_refs
                )
                cell_markdown = self._structured_text(
                    physical_cell,
                    markdown=True,
                    links_by_element=links_by_element,
                    table_refs=table_refs,
                )
                if not text:
                    # A cell whose only content is an icon (a check mark, a
                    # cross) says so through the image's alt text.
                    text = cell_markdown = self._image_text(physical_cell)
                # HTML's own header semantics only; whether a bold first row is
                # a header is decided with the whole table in view, in
                # normalization.
                scope = str(physical_cell.get("scope") or "").lower()
                row_header = (
                    physical_cell.name == "th"
                    and not in_thead
                    and (
                        scope in {"row", "rowgroup"}
                        or (row_has_data_cells and scope not in {"col", "colgroup"})
                    )
                )
                is_header = in_thead or (physical_cell.name == "th" and not row_header)
                cell_id = f"{table_id}.r{row_index}.c{cursor}"
                cells.append(
                    TableCellArtifact(
                        id=cell_id,
                        row_index=row_index,
                        column_index=cursor,
                        rowspan=rowspan,
                        colspan=colspan,
                        tag=physical_cell.name,
                        is_header=is_header,
                        row_header=row_header,
                        bold=self._all_bold(physical_cell),
                        text=text,
                        markdown=cell_markdown,
                        link_ids=self._contained_link_ids(
                            physical_cell, links_by_element
                        ),
                        locator=self._locator(physical_cell, source_url, cell_id),
                    )
                )
                for offset in range(colspan):
                    value = (
                        _GridValue(text=text, markdown=cell_markdown)
                        if offset == 0
                        else _GridValue(text="", markdown="")
                    )
                    logical[cursor + offset] = value
                    if rowspan > 1:
                        next_active[cursor + offset] = (value, rowspan - 1)
                cursor += colspan

            active = next_active
            width = max(logical, default=-1) + 1
            column_count = max(column_count, width)
            text_row = tuple(logical[index].text for index in range(width))
            markdown_row = tuple(logical[index].markdown for index in range(width))
            grid_rows.append((text_row, markdown_row, physical_cells))

        normalized_rows = [
            (
                text_row + ("",) * (column_count - len(text_row)),
                markdown_row + ("",) * (column_count - len(markdown_row)),
                physical_cells,
            )
            for text_row, markdown_row, physical_cells in grid_rows
        ]

        context_title = self._context_title(element)
        title: str | None = None
        headers: tuple[str, ...] = ()
        markdown_headers: tuple[str, ...] = ()
        headers_inferred = False
        rows: list[tuple[str, ...]] = []
        markdown_rows: list[tuple[str, ...]] = []
        notes: list[str] = []
        markdown_notes: list[str] = []

        for text_row, markdown_row, physical_cells in normalized_rows:
            full_width = (
                len(physical_cells) == 1
                and self._positive_span(physical_cells[0].get("colspan"))
                >= column_count
            )
            if full_width and not rows and not headers and title is None:
                title = text_row[0]
                continue
            if full_width:
                notes.append(text_row[0])
                markdown_notes.append(markdown_row[0])
                continue
            if not rows and not headers and self._looks_like_header_row(physical_cells):
                headers = text_row
                markdown_headers = markdown_row
                continue
            rows.append(text_row)
            markdown_rows.append(markdown_row)

        if (
            not headers
            and column_count == 3
            and any(cell.rowspan > 1 for cell in cells)
        ):
            headers = ("Section", "Item", "Terms")
            markdown_headers = headers
            headers_inferred = True

        if context_title:
            title = f"{context_title} — {title}" if title else context_title

        return TableArtifact(
            id=table_id,
            caption=caption,
            context_title=context_title,
            title=title,
            column_count=column_count,
            headers=headers,
            markdown_headers=markdown_headers,
            headers_inferred=headers_inferred,
            rows=tuple(rows),
            markdown_rows=tuple(markdown_rows),
            notes=tuple(notes),
            markdown_notes=tuple(markdown_notes),
            cells=tuple(cells),
            locator=locator,
        )

    def _images(
        self, root: Tag, source_url: str, chrome_ids: set[str]
    ) -> tuple[ImageArtifact, ...]:
        images: list[ImageArtifact] = []
        for element in root.find_all("img"):
            if not isinstance(element, Tag) or self._is_hidden(element):
                continue
            raw_url = (
                element.get("src")
                or element.get("data-src")
                or element.get("data-lazy-src")
            )
            if not raw_url:
                continue
            absolute = self._normalized_http_url(urljoin(source_url, str(raw_url)))
            if not absolute:
                continue
            try:
                validate_source_url(absolute, self._allowed_hosts)
                same_source = True
            except DisallowedSourceUrl:
                same_source = False
            image_id = f"img{len(images) + 1}"
            if self._in_site_chrome(element):
                chrome_ids.add(image_id)
            alt = self._clean(str(element.get("alt") or ""))
            images.append(
                ImageArtifact(
                    id=image_id,
                    url=absolute,
                    alt=alt,
                    title=self._clean(str(element.get("title") or "")) or None,
                    width=str(element.get("width")) if element.get("width") else None,
                    height=(
                        str(element.get("height")) if element.get("height") else None
                    ),
                    same_allowlisted_source=same_source,
                    decorative=not alt,
                    locator=self._locator(element, source_url, image_id),
                )
            )
        return tuple(images)

    def _interactive_controls(
        self, root: Tag, source_url: str, chrome_ids: set[str]
    ) -> tuple[InteractiveControlArtifact, ...]:
        controls: list[InteractiveControlArtifact] = []
        selector = (
            "button, summary, [role='button'], [role='tab'], "
            "[data-acquisition-tab-control='true'], "
            "input[type='button'], input[type='submit']"
        )
        for element in root.select(selector):
            if not isinstance(element, Tag) or self._is_hidden(element):
                continue
            control_id = f"ctl{len(controls) + 1}"
            if self._in_site_chrome(element):
                chrome_ids.add(control_id)
            expanded = element.get("aria-expanded")
            controls.append(
                InteractiveControlArtifact(
                    id=control_id,
                    element=element.name,
                    role=str(element.get("role")) if element.get("role") else None,
                    text=self._clean(
                        str(element.get("value") or element.get_text(" ", strip=True))
                    ),
                    aria_label=(
                        self._clean(str(element.get("aria-label")))
                        if element.get("aria-label")
                        else None
                    ),
                    aria_expanded=(
                        expanded == "true" if expanded in {"true", "false"} else None
                    ),
                    aria_controls=(
                        str(element.get("aria-controls"))
                        if element.get("aria-controls")
                        else None
                    ),
                    disabled=element.has_attr("disabled")
                    or element.get("aria-disabled") == "true",
                    locator=self._locator(element, source_url, control_id),
                )
            )
        return tuple(controls)

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
        lines = [
            _WHITESPACE.sub(" ", line).strip()
            for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        ]
        return "\n".join(line for line in lines if line)

    @classmethod
    def _structured_text(
        cls,
        element: Tag,
        *,
        markdown: bool,
        links_by_element: dict[int, LinkArtifact] | None = None,
        exclude_nested_blocks: bool = False,
        exclude: frozenset[str] = frozenset(),
        exclude_ids: frozenset[int] = frozenset(),
        table_refs: dict[int, str] | None = None,
    ) -> str:
        links_by_element = links_by_element or {}
        table_refs = table_refs or {}
        excluded = exclude | (
            _NESTED_HEADING_BLOCKS if exclude_nested_blocks else frozenset()
        )

        def render(node: object, list_depth: int = 0) -> str:
            if isinstance(node, Comment):
                return ""
            if isinstance(node, NavigableString):
                return str(node)
            if not isinstance(node, Tag):
                return ""
            if node is not element and (
                node.name in excluded or id(node) in exclude_ids
            ):
                return ""
            if node.name == "br":
                return "\n"
            if node.name == "a":
                label = cls._clean(
                    "".join(render(child, list_depth) for child in node.children)
                )
                link = links_by_element.get(id(node))
                if markdown and link and label:
                    safe_label = label.replace("]", "\\]")
                    target = str(link.url)
                    if link.fragment:
                        target = f"{target}#{link.fragment}"
                    return f"[{safe_label}](<{target}>)"
                return label
            if node.name == "table" and node is not element and id(node) in table_refs:
                # A nested table is its own table; the outer text points at it
                # instead of flattening its rows into one cell.
                return f"\n[table {table_refs[id(node)]}]\n"
            if node.name in {"ul", "ol"}:
                items: list[str] = []
                for index, item in enumerate(
                    node.find_all("li", recursive=False), start=1
                ):
                    body = cls._clean(
                        "".join(
                            render(child, list_depth + 1) for child in item.children
                        )
                    )
                    marker = f"{index}." if node.name == "ol" else "•"
                    items.append(f"{marker} {body}")
                return "\n".join(items) + "\n"
            if node.name == "tr":
                cells = (
                    " ".join(cls._clean(render(cell, list_depth)).split("\n"))
                    for cell in node.find_all(["td", "th"], recursive=False)
                )
                return " | ".join(cell for cell in cells if cell) + "\n"
            content = "".join(render(child, list_depth) for child in node.children)
            if node.name == "sup":
                cleaned = cls._clean(content)
                if cleaned and all(
                    character in "0123456789+-=()" for character in cleaned
                ):
                    cleaned = cleaned.translate(_SUPERSCRIPT_DIGITS)
                elif markdown and cleaned:
                    cleaned = f"<sup>{cleaned}</sup>"
                return f" {cleaned} " if cleaned else ""
            if node.name in _LINE_BREAK_TAGS:
                # Block-level boundaries end a line, so text from neighbouring
                # elements never runs together ("Consumer loanUp to ...").
                return "\n" + content + "\n"
            return content

        return cls._clean(render(element))

    @classmethod
    def _is_hidden(cls, element: Tag) -> bool:
        for current in (element, *element.parents):
            if not isinstance(current, Tag):
                continue
            visibility = current.get("data-acquisition-visible")
            if visibility == "false":
                return True
            if visibility == "true":
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
    def _positive_span(value: object) -> int:
        try:
            parsed = int(str(value)) if value is not None else 1
        except ValueError:
            return 1
        return max(parsed, 1)

    @staticmethod
    def _all_bold(cell: Tag) -> bool:
        """Whether every visible character of the cell sits inside `strong`/`b`."""
        found = False
        for node in cell.find_all(string=True):
            if isinstance(node, Comment) or not str(node).strip():
                continue
            found = True
            parent = node.parent
            while parent is not None and parent is not cell:
                if parent.name in {"strong", "b"}:
                    break
                parent = parent.parent
            else:
                return False
        return found

    @classmethod
    def _looks_like_header_row(cls, cells: list[Tag]) -> bool:
        if not cells:
            return False
        if any(
            cell.name == "th" or cell.get("scope") in {"col", "row"} for cell in cells
        ):
            return True
        return all(
            (strong := cell.find("strong")) is not None
            and cls._clean(cell.get_text(" ", strip=True))
            == cls._clean(strong.get_text(" ", strip=True))
            for cell in cells
        )

    @classmethod
    def _image_text(cls, element: Tag) -> str:
        return cls._clean(
            " ".join(
                str(image.get("alt") or image.get("title") or "")
                for image in element.find_all("img")
            )
        )

    @staticmethod
    def _contained_link_ids(
        element: Tag,
        links_by_element: dict[int, LinkArtifact],
        *,
        exclude: frozenset[str] = frozenset(),
        exclude_ids: frozenset[int] = frozenset(),
    ) -> tuple[str, ...]:
        """Links inside the element, skipping those under an excluded descendant.

        A container's own-text block passes the same exclusions as its text,
        so it claims only the links in that text, not every link of the page
        region it wraps (which would make it every PDF's origin block).
        """

        def own(anchor: Tag) -> bool:
            for parent in anchor.parents:
                if parent is element:
                    return True
                if parent.name in exclude or id(parent) in exclude_ids:
                    return False
            return True

        return tuple(
            link.id
            for anchor in element.find_all("a", href=True)
            if (link := links_by_element.get(id(anchor))) is not None
            and (not (exclude or exclude_ids) or own(anchor))
        )

    @staticmethod
    def _class_text(element: Tag) -> str:
        return " ".join(str(value) for value in (element.get("class") or ()))

    @classmethod
    def _card_elements(cls, root: Tag) -> dict[int, Tag]:
        candidates: list[Tag] = []
        for element in root.find_all(["article", "div", "li"]):
            if not isinstance(element, Tag):
                continue
            classes = tuple(str(value) for value in (element.get("class") or ()))
            if any(_CARD_CONTAINER.search(value) for value in classes):
                candidates.append(element)
        candidate_ids = {id(element) for element in candidates}
        return {
            id(element): element
            for element in candidates
            if not any(
                id(descendant) in candidate_ids
                for descendant in element.find_all(["article", "div", "li"])
            )
        }

    @classmethod
    def _context_title(cls, element: Tag) -> str | None:
        for current in (element, *element.parents):
            if not isinstance(current, Tag):
                continue
            value = cls._clean(str(current.get("data-acquisition-context-title") or ""))
            if value:
                return value
        return None

    @classmethod
    def _accordion_parts(cls, root: Tag) -> tuple[dict[int, int], dict[int, int]]:
        titles: dict[int, int] = {}
        panels: dict[int, int] = {}
        for container in root.find_all(["div", "section", "article"]):
            direct_children = [
                child
                for child in container.find_all(recursive=False)
                if isinstance(child, Tag)
            ]
            title = next(
                (
                    child
                    for child in direct_children
                    if _ACCORDION_TITLE.search(cls._class_text(child))
                    or (
                        child.get("role") in {"button", "heading"}
                        and child.get("aria-controls")
                    )
                ),
                None,
            )
            panel = next(
                (
                    child
                    for child in direct_children
                    if _ACCORDION_PANEL.search(cls._class_text(child))
                    or child.get("role") == "region"
                ),
                None,
            )
            if title is not None and panel is not None:
                titles[id(title)] = id(container)
                panels[id(panel)] = id(container)
        return titles, panels

    @staticmethod
    def _accordion_parent_id(
        element: Tag,
        accordion_panels: dict[int, int],
        accordion_block_ids: dict[int, str],
    ) -> str | None:
        for parent in element.parents:
            container_id = accordion_panels.get(id(parent))
            if container_id is not None:
                return accordion_block_ids.get(container_id)
        return None

    @staticmethod
    def _markdown_value(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", "<br>")

    @classmethod
    def _markdown(
        cls, blocks: tuple[ContentBlock, ...], tables: tuple[TableArtifact, ...]
    ) -> str:
        tables_by_id = {table.id: table for table in tables}
        lines: list[str] = []
        for block in blocks:
            value = block.markdown or block.text
            if block.type is ContentBlockType.HEADING:
                level = min(len(block.heading_path) + 1, 6)
                lines.append(f"{'#' * level} {value}")
            elif block.type is ContentBlockType.ACCORDION:
                lines.append(f"**{value}**")
            elif block.type is ContentBlockType.LIST:
                lines.append(f"- {value}")
            elif block.type is ContentBlockType.TABLE:
                table = tables_by_id.get(block.table_id or "")
                if table:
                    if table.caption:
                        lines.append(f"**{table.caption}**")
                    if table.title:
                        lines.append(f"**{table.title}**")
                    headers = table.markdown_headers or table.headers
                    if not headers and table.column_count:
                        headers = tuple(
                            f"Column {index}"
                            for index in range(1, table.column_count + 1)
                        )
                    rows = table.markdown_rows or table.rows
                    if headers:
                        lines.append(
                            "| "
                            + " | ".join(cls._markdown_value(item) for item in headers)
                            + " |"
                        )
                        lines.append(
                            "| " + " | ".join("---" for _ in range(len(headers))) + " |"
                        )
                        lines.extend(
                            "| "
                            + " | ".join(cls._markdown_value(item) for item in row)
                            + " |"
                            for row in rows
                        )
                    lines.extend(
                        f"> {cls._markdown_value(note)}"
                        for note in (table.markdown_notes or table.notes)
                    )
            else:
                lines.append(value)
            lines.append("")
        return "\n".join(lines).strip()
