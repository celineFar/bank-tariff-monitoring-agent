from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    NormalizedTable,
    SourceReference,
    normalize_text,
)
from app.domain.source_discovery import (
    CandidateLayout,
    DiscoveryCandidate,
    DiscoveryMember,
    DiscoveryScope,
)

_MAX_CONTEXT_CHARS = 12_000
_TARIFF_TERMS = (
    "interest",
    "rate",
    "apr",
    "amount",
    "term",
    "month",
    "currency",
    "fee",
    "repayment",
    "collateral",
    "eligible",
    "document",
    "mortgage",
    "loan",
    "տոկոս",
    "ժամկետ",
    "գումար",
    "վարկ",
)
# What one prompt item may show by default (`SOURCE_DISCOVERY_MAX_CHARS_PER_ITEM`).
DEFAULT_ITEM_CHARS = 3_000
# Room a member's id and separators take in the prompt.
_MEMBER_OVERHEAD = 12
_SITE_CHROME_KEY = ("<site-chrome>",)
_PAGE_HEADER_KEY = ("<page-header>",)


def build_discovery_candidates(
    bundle: NormalizedSourceBundle,
    *,
    item_chars: int = DEFAULT_ITEM_CHARS,
) -> tuple[DiscoveryCandidate, ...]:
    """Classification units, each small enough to show whole in one prompt item.

    A page section longer than `item_chars` is split into consecutive parts
    rather than cut: every member's text reaches the classifier. Only a single
    block longer than 12,000 characters is cut.
    """
    candidates: list[DiscoveryCandidate] = []
    for document in bundle.documents:
        if document.source_type is SourceType.PAGE:
            candidates.append(_page_document_candidate(document))
            candidates.extend(_page_section_candidates(document, item_chars))
            candidates.extend(
                _table_candidate(document, table, item_chars)
                for table in document.tables
            )
        else:
            candidates.append(_document_candidate(document))
    return tuple(candidates)


def member_source_id(document_id: str, kind: str, item_id: str) -> str:
    return f"{document_id}::{kind}::{item_id}"


def _page_document_candidate(document: NormalizedDocument) -> DiscoveryCandidate:
    source_ref = _document_reference(document)
    return _candidate(
        source_id=f"document::{document.id}",
        document=document,
        scope=DiscoveryScope.DOCUMENT,
        title=document.name,
        heading_path=(),
        context=f"Product page: {document.name}\nURL: {document.source_url}",
        member_ids=(),
        refs=(source_ref,),
        all_hidden=False,
        has_scalars=False,
        content_identity=document.content_sha256,
        selection_reason="The canonical product page always receives a document-level assessment.",
    )


def _page_section_candidates(
    document: NormalizedDocument, item_chars: int
) -> tuple[DiscoveryCandidate, ...]:
    links = {link.id: link for link in document.links}
    blocks_by_id = {block.id: block for block in document.blocks}
    groups: dict[tuple[str, ...], list[NormalizedBlock]] = defaultdict(list)
    seen_heading = False
    for block in document.blocks:
        if block.table_id:
            continue
        if block.heading_path or block.type is NormalizedBlockType.HEADING:
            seen_heading = True
        if block.site_chrome:
            # The site's navigation, banner and footer: one auditable decision,
            # never mixed into the content section whose heading it inherited.
            key = _SITE_CHROME_KEY
        elif block.heading_path:
            key = (*block.heading_path, f"parent:{block.parent_id or '-'}")
        elif not seen_heading:
            # Above the first heading: language switch, phone, "About Bank".
            key = _PAGE_HEADER_KEY
        else:
            # Unheaded content below the first heading stays granular, so a
            # useful list is decided on its own. Keyed by text, not by the
            # positional block id, so an inserted block renames nothing.
            key = ("<root>", _hash(block.text)[:16])
        groups[key].append(block)

    result: list[DiscoveryCandidate] = []
    for key, group in groups.items():
        layout = CandidateLayout.CONTENT
        if key == _SITE_CHROME_KEY:
            layout = CandidateLayout.SITE_CHROME
            title, heading_path = "Site navigation, header and footer", ()
        elif key == _PAGE_HEADER_KEY:
            layout = CandidateLayout.PAGE_HEADER
            title, heading_path = "Page header", ()
        else:
            heading_path = group[0].heading_path
            title = heading_path[-1] if heading_path else "Unheaded page content"
        identity = json.dumps(
            {"document": document.id, "key": key},
            ensure_ascii=False,
            sort_keys=True,
        )
        group_id = hashlib.sha256(identity.encode()).hexdigest()[:16]
        parent = blocks_by_id.get(group[0].parent_id or "")
        # Rule-decided groups are never shown to the classifier, so they are
        # never split.
        parts = (
            _split_members(group, item_chars)
            if layout is CandidateLayout.CONTENT
            else [group]
        )
        for index, blocks in enumerate(parts, start=1):
            part = f"{index}/{len(parts)}" if len(parts) > 1 else None
            result.append(
                _section_candidate(
                    document,
                    blocks,
                    links=links,
                    source_id=(
                        f"{document.id}::section::{group_id}"
                        + (f"::part::{index}" if part else "")
                    ),
                    title=title,
                    heading_path=heading_path,
                    parent=parent.text[:200] if parent is not None else None,
                    part=part,
                    layout=layout,
                )
            )
    return tuple(result)


def _split_members(
    blocks: list[NormalizedBlock], item_chars: int
) -> list[list[NormalizedBlock]]:
    """Consecutive runs of members whose texts fit one prompt item together."""
    parts: list[list[NormalizedBlock]] = [[]]
    size = 0
    for block in blocks:
        length = min(len(block.text), _MAX_CONTEXT_CHARS) + _MEMBER_OVERHEAD
        if parts[-1] and size + length > item_chars:
            parts.append([])
            size = 0
        parts[-1].append(block)
        size += length
    return parts


def _section_candidate(
    document: NormalizedDocument,
    blocks: list[NormalizedBlock],
    *,
    links: dict,
    source_id: str,
    title: str,
    heading_path: tuple[str, ...],
    parent: str | None,
    part: str | None,
    layout: CandidateLayout,
) -> DiscoveryCandidate:
    member_ids = tuple(
        member_source_id(document.id, "block", block.id) for block in blocks
    )
    context = _representative_blocks(blocks)
    linked = tuple(
        links[link_id]
        for block in blocks
        for link_id in block.link_ids
        if link_id in links
    )
    link_context = ""
    if linked:
        unique_links = {link.id: link for link in linked}
        link_context = "\n".join(
            "LINK: "
            f"{link.text or '(no text)'} -> {link.url} "
            f"[downloadable={link.downloadable}]"
            for link in unique_links.values()
        )
        context = _bounded(f"{context}\n{link_context}")
    return _candidate(
        source_id=source_id,
        document=document,
        scope=DiscoveryScope.SECTION,
        title=f"{title} (part {part.replace('/', ' of ')})" if part else title,
        heading_path=heading_path,
        context=context,
        member_ids=member_ids,
        refs=_block_refs(blocks),
        all_hidden=all(not block.visible for block in blocks),
        has_scalars=any(block.scalar_candidates for block in blocks),
        # Content only: block ids are positional, and one new block
        # near the top would otherwise change every section's key.
        content_identity=tuple(
            (
                block.text,
                block.markdown,
                block.fields,
                block.visible,
                tuple(
                    str(links[link_id].url)
                    for link_id in block.link_ids
                    if link_id in links
                ),
            )
            for block in blocks
        ),
        selection_reason=(
            "Page blocks sharing heading and parent context are assessed together."
        ),
        # Sections under one heading are told apart by their parent
        # (the accordion or card title) in the structural key too.
        parent=parent,
        layout=layout,
        members=tuple(
            DiscoveryMember(
                member_source_id=member_id, text=block.text[:_MAX_CONTEXT_CHARS]
            )
            for member_id, block in zip(member_ids, blocks, strict=True)
        ),
        member_context=link_context[:_MAX_CONTEXT_CHARS],
    )


def _table_candidate(
    document: NormalizedDocument, table: NormalizedTable, item_chars: int
) -> DiscoveryCandidate:
    return _candidate(
        source_id=member_source_id(document.id, "table", table.id),
        document=document,
        scope=DiscoveryScope.TABLE,
        title=table.title or "Untitled table",
        heading_path=(),
        context=_table_context(table, item_chars),
        member_ids=(),
        refs=table.source_refs,
        all_hidden=False,
        has_scalars=any(
            cell.scalar_candidates for row in table.rows for cell in row.cells
        ),
        content_identity=_table_identity(table),
        selection_reason="Structured tables are assessed independently from surrounding prose.",
    )


def _table_context(table: NormalizedTable, item_chars: int) -> str:
    """Headers and the label of every row first, then as many full rows as fit.

    The classifier used to get the header and the first rows only, cut at the
    item budget; the row labels show what the whole table is about.
    """
    lines = []
    if table.headers:
        lines.append(" | ".join(table.headers))
    labels = [
        row.cells[0].text for row in table.rows if row.cells and row.cells[0].text
    ]
    if labels:
        lines.append("Row labels: " + "; ".join(labels))
    size = sum(len(line) + 1 for line in lines)
    for row in table.rows:
        line = " | ".join(
            ([f"[{row.section}]"] if row.section else [])
            + [cell.text for cell in row.cells]
        )
        if size + len(line) + 1 > item_chars:
            lines.append("...")
            break
        lines.append(line)
        size += len(line) + 1
    else:
        lines.extend(f"NOTE: {note.text}" for note in table.notes)
    return _bounded("\n".join(lines)) if lines else (table.title or "Empty table")


def _document_candidate(document: NormalizedDocument) -> DiscoveryCandidate:
    blocks = list(document.blocks)
    context = _document_context(document)
    member_ids = tuple(
        member_source_id(document.id, "block", block.id) for block in blocks
    ) + tuple(
        member_source_id(document.id, "table", table.id) for table in document.tables
    )
    return _candidate(
        source_id=f"document::{document.id}",
        document=document,
        scope=DiscoveryScope.DOCUMENT,
        title=document.name,
        heading_path=(),
        context=context,
        member_ids=member_ids,
        refs=(
            _block_refs(blocks)
            + tuple(ref for table in document.tables for ref in table.source_refs)
        )[:20]
        or (_document_reference(document),),
        all_hidden=bool(blocks) and all(not block.visible for block in blocks),
        has_scalars=(
            any(block.scalar_candidates for block in blocks)
            or any(
                cell.scalar_candidates
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            )
        ),
        content_identity={
            "sha256": document.content_sha256,
            "extraction_method": document.extraction_method,
            "pdf_admission": (
                document.pdf_admission.model_dump(mode="json")
                if document.pdf_admission
                else None
            ),
            # The link decision, not who made it: a cache hit is the same input.
            "pdf_selection": (
                [document.pdf_selection.label.value, document.pdf_selection.role.value]
                if document.pdf_selection
                else None
            ),
        },
        selection_reason="Linked documents are first assessed as one source-level unit.",
        pdf_admission=document.pdf_admission,
        pdf_selection=document.pdf_selection,
    )


def _document_context(document: NormalizedDocument) -> str:
    """A linked document's text in reading order, tables shown compactly.

    Page by page: the page's blocks, then its tables as title, headers and the
    first cell of every row. Tables used to follow *all* the blocks, so a long
    document's tables -- where the tariffs are -- never reached the classifier.
    """
    pages: dict[int, list[str]] = defaultdict(list)
    for block in document.blocks:
        pages[_page_number(block.source_refs)].append(block.text)
    for table in document.tables:
        pages[_page_number(table.source_refs)].append(_compact_table(table))
    parts = [f"Document: {document.name}"]
    for page in sorted(pages):
        parts.extend(text for text in pages[page] if text)
    if len(parts) == 1:
        parts.append(f"Document has no extracted text. URL: {document.source_url}")
    return _bounded("\n".join(parts))


def _page_number(refs: tuple[SourceReference, ...]) -> int:
    for ref in refs:
        if ref.locator.pdf_page is not None:
            return ref.locator.pdf_page
    return 0


def _compact_table(table: NormalizedTable) -> str:
    lines = [f"TABLE: {table.title}" if table.title else "TABLE"]
    if table.headers:
        lines.append(" | ".join(table.headers))
    labels = [
        row.cells[0].text for row in table.rows if row.cells and row.cells[0].text
    ]
    if labels:
        lines.append("Rows: " + "; ".join(labels))
    return "\n".join(lines)


def _table_identity(table: NormalizedTable) -> dict[str, object]:
    """A table's content without its positional ids."""
    return {
        "title": table.title,
        "headers": table.headers,
        "rows": [
            [row.section, [cell.text for cell in row.cells]] for row in table.rows
        ],
        "notes": [[note.marker, note.text] for note in table.notes],
    }


def _candidate(
    *,
    source_id: str,
    document: NormalizedDocument,
    scope: DiscoveryScope,
    title: str,
    heading_path: tuple[str, ...],
    context: str,
    member_ids: tuple[str, ...],
    refs: tuple[SourceReference, ...],
    all_hidden: bool,
    has_scalars: bool,
    content_identity: object,
    selection_reason: str,
    pdf_admission=None,
    pdf_selection=None,
    parent: str | None = None,
    layout: CandidateLayout = CandidateLayout.CONTENT,
    members: tuple[DiscoveryMember, ...] = (),
    member_context: str = "",
) -> DiscoveryCandidate:
    structural = {
        "document_url": str(document.source_url),
        "heading_path": heading_path,
        "mime_type": document.mime_type,
        "scope": scope.value,
        "source_type": document.source_type.value,
        "title": title,
    }
    if parent is not None:
        structural["parent"] = parent
    content = {**structural, "content_identity": content_identity}
    return DiscoveryCandidate(
        source_id=source_id,
        document_id=document.id,
        scope=scope,
        source_type=document.source_type,
        title=normalize_text(title),
        heading_path=heading_path,
        context_text=_bounded(context),
        mime_type=document.mime_type,
        extraction_method=document.extraction_method,
        quality_score=document.quality_score,
        member_source_ids=member_ids,
        all_members_hidden=all_hidden,
        has_scalar_candidates=has_scalars,
        source_refs=refs[:20],
        content_fingerprint=_hash(content),
        structural_fingerprint=_hash(structural),
        selection_reason=selection_reason,
        pdf_admission=pdf_admission,
        pdf_selection=pdf_selection,
        layout=layout,
        members=members,
        member_context=member_context,
    )


def _representative_blocks(blocks: list[NormalizedBlock]) -> str:
    ranked = sorted(
        enumerate(blocks),
        key=lambda item: (-_block_score(item[1]), item[0]),
    )
    selected: list[str] = []
    length = 0
    for _, block in ranked:
        prefix = block.fields.get("path")
        value = f"[{prefix}] {block.text}" if prefix else block.text
        if not value or value in selected:
            continue
        remaining = _MAX_CONTEXT_CHARS - length
        if remaining <= 0:
            break
        selected.append(value[:remaining])
        length += len(selected[-1]) + 1
    return "\n".join(selected)


def _block_score(block: NormalizedBlock) -> int:
    text = block.text.casefold()
    return len(block.scalar_candidates) * 10 + sum(
        term in text for term in _TARIFF_TERMS
    )


def _block_refs(blocks: list[NormalizedBlock]) -> tuple[SourceReference, ...]:
    refs: list[SourceReference] = []
    seen: set[tuple[str, str]] = set()
    for block in blocks:
        for ref in block.source_refs:
            key = (ref.source_item_id, ref.locator.model_dump_json())
            if key not in seen:
                seen.add(key)
                refs.append(ref)
            if len(refs) == 20:
                return tuple(refs)
    return tuple(refs)


def _document_reference(document: NormalizedDocument) -> SourceReference:
    return SourceReference(
        source_item_id=document.id,
        locator=SourceLocator(
            source_url=document.source_url,
            source_type=document.source_type,
        ),
    )


def _bounded(value: str) -> str:
    normalized = value.strip()
    return normalized[:_MAX_CONTEXT_CHARS] or "No textual content"


def _hash(value: object) -> str:
    serialized = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(serialized.encode()).hexdigest()
