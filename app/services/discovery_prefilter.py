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
from app.domain.source_discovery import DiscoveryCandidate, DiscoveryScope

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


def build_discovery_candidates(
    bundle: NormalizedSourceBundle,
) -> tuple[DiscoveryCandidate, ...]:
    candidates: list[DiscoveryCandidate] = []
    for document in bundle.documents:
        if document.source_type is SourceType.PAGE:
            candidates.append(_page_document_candidate(document))
            candidates.extend(_page_section_candidates(document))
            candidates.extend(_table_candidate(document, table) for table in document.tables)
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
    document: NormalizedDocument,
) -> tuple[DiscoveryCandidate, ...]:
    links = {link.id: link for link in document.links}
    groups: dict[tuple[str, ...], list[NormalizedBlock]] = defaultdict(list)
    for block in document.blocks:
        if block.table_id:
            continue
        if block.heading_path:
            key = (*block.heading_path, f"parent:{block.parent_id or '-'}")
        elif block.type is NormalizedBlockType.LIST:
            # The site emits its global menu as many adjacent unheaded list
            # blocks. Grouping them makes one auditable navigation decision.
            key = ("<root-navigation-lists>",)
        else:
            # Root material is kept granular so global navigation does not absorb
            # an otherwise useful unheaded product block.
            key = ("<root>", block.id)
        groups[key].append(block)

    result: list[DiscoveryCandidate] = []
    for key, blocks in groups.items():
        heading_path = blocks[0].heading_path
        title = heading_path[-1] if heading_path else "Unheaded page content"
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
        if linked:
            unique_links = {link.id: link for link in linked}
            link_context = "\n".join(
                "LINK: "
                f"{link.text or '(no text)'} -> {link.url} "
                f"[downloadable={link.downloadable}]"
                for link in unique_links.values()
            )
            context = _bounded(f"{context}\n{link_context}")
        identity = json.dumps(
            {"document": document.id, "key": key},
            ensure_ascii=False,
            sort_keys=True,
        )
        group_id = hashlib.sha256(identity.encode()).hexdigest()[:16]
        result.append(
            _candidate(
                source_id=f"{document.id}::section::{group_id}",
                document=document,
                scope=DiscoveryScope.SECTION,
                title=title,
                heading_path=heading_path,
                context=context,
                member_ids=member_ids,
                refs=_block_refs(blocks),
                all_hidden=all(not block.visible for block in blocks),
                has_scalars=any(block.scalar_candidates for block in blocks),
                content_identity=tuple(
                    (
                        block.id,
                        block.text,
                        block.markdown,
                        block.fields,
                        block.visible,
                        block.link_ids,
                    )
                    for block in blocks
                ),
                selection_reason=(
                    "Page blocks sharing heading and parent context are assessed together."
                ),
            )
        )
    return tuple(result)


def _table_candidate(
    document: NormalizedDocument, table: NormalizedTable
) -> DiscoveryCandidate:
    lines = []
    if table.headers:
        lines.append(" | ".join(table.headers))
    for row in table.rows:
        lines.append(" | ".join(cell.text for cell in row.cells))
    if table.notes:
        lines.extend(f"NOTE: {note.text}" for note in table.notes)
    context = _bounded("\n".join(lines)) or table.title or "Empty table"
    return _candidate(
        source_id=member_source_id(document.id, "table", table.id),
        document=document,
        scope=DiscoveryScope.TABLE,
        title=table.title or "Untitled table",
        heading_path=(),
        context=context,
        member_ids=(),
        refs=table.source_refs,
        all_hidden=False,
        has_scalars=any(
            cell.scalar_candidates for row in table.rows for cell in row.cells
        ),
        content_identity=table.model_dump(mode="json"),
        selection_reason="Structured tables are assessed independently from surrounding prose.",
    )


def _document_candidate(document: NormalizedDocument) -> DiscoveryCandidate:
    scope = (
        DiscoveryScope.API_PAYLOAD
        if document.source_type is SourceType.API
        else DiscoveryScope.DOCUMENT
    )
    blocks = list(document.blocks)
    context = _representative_blocks(blocks)
    table_context = "\n".join(
        " | ".join(table.headers)
        + "\n"
        + "\n".join(" | ".join(cell.text for cell in row.cells) for row in table.rows)
        for table in document.tables
    )
    if table_context:
        context = _bounded(f"{context}\n{table_context}")
    if not context:
        context = f"Document has no extracted text. URL: {document.source_url}"
    member_ids = tuple(
        member_source_id(document.id, "block", block.id) for block in blocks
    ) + tuple(
        member_source_id(document.id, "table", table.id)
        for table in document.tables
    )
    return _candidate(
        source_id=f"document::{document.id}",
        document=document,
        scope=scope,
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
            "pdf_admission": (
                document.pdf_admission.model_dump(mode="json")
                if document.pdf_admission
                else None
            ),
        },
        selection_reason=(
            "API leaves are grouped at payload scope to avoid one model decision per JSON leaf."
            if scope is DiscoveryScope.API_PAYLOAD
            else "Linked documents are first assessed as one source-level unit."
        ),
        pdf_admission=document.pdf_admission,
    )


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
) -> DiscoveryCandidate:
    structural = {
        "document_url": str(document.source_url),
        "heading_path": heading_path,
        "mime_type": document.mime_type,
        "scope": scope.value,
        "source_type": document.source_type.value,
        "title": title,
    }
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
    return len(block.scalar_candidates) * 10 + sum(term in text for term in _TARIFF_TERMS)


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
