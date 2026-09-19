from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, HttpUrl

from app.domain.acquisition import SourceLocator
from app.domain.knowledge import KnowledgeChunk, KnowledgeDocument
from app.domain.models import KnowledgeDocumentKind, OfferingId, ProductType
from app.domain.monitoring import SnapshotAttempt
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    NormalizedTable,
)
from app.domain.semantic_extraction import ExtractedValue, LoanProduct


@dataclass(frozen=True, slots=True)
class _ProjectionUnit:
    content: str
    section: str | None
    locators: tuple[SourceLocator, ...]
    source_item_ids: tuple[str, ...]
    extraction_method: str
    quality_score: float | None
    unit_type: str


class KnowledgeProjectionService:
    def __init__(self, *, max_chunk_chars: int = 6_000) -> None:
        if max_chunk_chars < 500:
            raise ValueError("max_chunk_chars must be at least 500")
        self._max_chunk_chars = max_chunk_chars

    def project_sources(
        self,
        *,
        run_id: UUID,
        product: ProductType,
        offering_id: OfferingId,
        bundle: NormalizedSourceBundle,
        retrieved_at: datetime,
        language: str,
        selected_document_ids: frozenset[str] | None = None,
    ) -> tuple[KnowledgeDocument, ...]:
        if offering_id.product is not product:
            raise ValueError("offering does not belong to product")
        documents = (
            document
            for document in bundle.documents
            if selected_document_ids is None or document.id in selected_document_ids
        )
        return tuple(
            self._project_source_document(
                run_id=run_id,
                product=product,
                offering_id=offering_id,
                document=document,
                retrieved_at=retrieved_at,
                language=language,
            )
            for document in documents
            if document.blocks or document.tables
        )

    def project_summary(
        self,
        *,
        run_id: UUID,
        product: ProductType,
        offering_id: OfferingId,
        display_name: str,
        source_url: HttpUrl | str,
        value: LoanProduct | SnapshotAttempt,
        language: str,
    ) -> KnowledgeDocument:
        if offering_id.product is not product:
            raise ValueError("offering does not belong to product")
        content, evidence_ids = render_offering_summary(
            display_name=display_name,
            offering_id=offering_id,
            product=product,
            value=value,
        )
        retrieved_at = (
            value.retrieved_at if isinstance(value, LoanProduct) else value.created_at
        )
        chunks = self._chunks_from_units(
            (
                _ProjectionUnit(
                    content=content,
                    section="Offering summary",
                    locators=(),
                    source_item_ids=(),
                    extraction_method="deterministic_summary",
                    quality_score=None,
                    unit_type="offering_summary",
                ),
            ),
            language=language,
            common_metadata={
                "authoritative_evidence": False,
                "evidence_ids": list(evidence_ids),
                "offering_id": offering_id.value,
            },
        )
        return KnowledgeDocument(
            run_id=run_id,
            product=product,
            offering_id=offering_id,
            document_kind=KnowledgeDocumentKind.OFFERING_SUMMARY,
            document_key=f"offering-summary:{offering_id.value}",
            document_name=f"{display_name} - deterministic summary",
            source_url=source_url,
            final_url=source_url,
            mime_type="text/markdown",
            content_sha256=_sha256(content),
            retrieved_at=retrieved_at,
            extraction_method="deterministic_summary",
            metadata={
                "authoritative_evidence": False,
                "evidence_ids": list(evidence_ids),
                "summary_schema": "loan_product_or_snapshot_v1",
            },
            chunks=chunks,
        )

    def _project_source_document(
        self,
        *,
        run_id: UUID,
        product: ProductType,
        offering_id: OfferingId,
        document: NormalizedDocument,
        retrieved_at: datetime,
        language: str,
    ) -> KnowledgeDocument:
        table_by_id = {table.id: table for table in document.tables}
        rendered_tables: set[str] = set()
        units: list[_ProjectionUnit] = []
        for block in document.blocks:
            if block.type is NormalizedBlockType.TABLE and block.table_id:
                table = table_by_id.get(block.table_id)
                if table is not None:
                    units.append(_table_unit(table, document))
                    rendered_tables.add(table.id)
                    continue
            units.append(_block_unit(block, document))
        units.extend(
            _table_unit(table, document)
            for table in document.tables
            if table.id not in rendered_tables
        )
        chunks = self._chunks_from_units(
            tuple(units),
            language=language,
            common_metadata={
                "normalized_document_id": document.id,
                "source_type": document.source_type.value,
            },
        )
        return KnowledgeDocument(
            run_id=run_id,
            product=product,
            offering_id=offering_id,
            document_kind=KnowledgeDocumentKind.SOURCE,
            document_key=document.id,
            document_name=document.name,
            source_url=document.source_url,
            final_url=document.source_url,
            mime_type=document.mime_type,
            content_sha256=document.content_sha256,
            retrieved_at=retrieved_at,
            extraction_method=document.extraction_method,
            quality_score=document.quality_score,
            metadata={
                "normalized_document_id": document.id,
                "source_type": document.source_type.value,
                "pdf_input_mode": (
                    document.pdf_input_mode.value if document.pdf_input_mode else None
                ),
            },
            chunks=chunks,
        )

    def _chunks_from_units(
        self,
        units: Sequence[_ProjectionUnit],
        *,
        language: str,
        common_metadata: dict[str, Any],
    ) -> tuple[KnowledgeChunk, ...]:
        expanded = tuple(
            piece
            for unit in units
            for piece in _split_unit(unit, self._max_chunk_chars)
            if piece.content.strip()
        )
        groups: list[list[_ProjectionUnit]] = []
        current: list[_ProjectionUnit] = []
        current_size = 0
        for unit in expanded:
            separator_size = 2 if current else 0
            if (
                current
                and current_size + separator_size + len(unit.content)
                > self._max_chunk_chars
            ):
                groups.append(current)
                current = []
                current_size = 0
            current.append(unit)
            current_size += separator_size + len(unit.content)
        if current:
            groups.append(current)

        chunks: list[KnowledgeChunk] = []
        for ordinal, group in enumerate(groups):
            locators = _unique_locators(
                locator for unit in group for locator in unit.locators
            )
            page_numbers = sorted(
                {
                    locator.pdf_page
                    for locator in locators
                    if locator.pdf_page is not None
                }
            )
            sections = tuple(
                dict.fromkeys(unit.section for unit in group if unit.section)
            )
            source_item_ids = tuple(
                dict.fromkeys(
                    item_id for unit in group for item_id in unit.source_item_ids
                )
            )
            methods = tuple(dict.fromkeys(unit.extraction_method for unit in group))
            scores = tuple(
                unit.quality_score for unit in group if unit.quality_score is not None
            )
            chunks.append(
                KnowledgeChunk(
                    ordinal=ordinal,
                    content="\n\n".join(unit.content for unit in group),
                    page_start=page_numbers[0] if page_numbers else None,
                    page_end=page_numbers[-1] if page_numbers else None,
                    section=" / ".join(sections)[:500] or None,
                    language=language,
                    extraction_method="+".join(methods),
                    quality_score=min(scores) if scores else None,
                    metadata={
                        **common_metadata,
                        "locators": [
                            locator.model_dump(mode="json", exclude_none=True)
                            for locator in locators
                        ],
                        "source_item_ids": list(source_item_ids),
                        "unit_types": list(
                            dict.fromkeys(unit.unit_type for unit in group)
                        ),
                    },
                )
            )
        if not chunks:
            raise ValueError("projection produced no knowledge chunks")
        return tuple(chunks)


def render_offering_summary(
    *,
    display_name: str,
    offering_id: OfferingId,
    product: ProductType,
    value: LoanProduct | SnapshotAttempt,
) -> tuple[str, tuple[str, ...]]:
    lines = [
        f"# {display_name}",
        "",
        f"Offering ID: {offering_id.value}",
        f"Product family: {product.value}",
        "Document kind: deterministic offering summary",
        "Evidence policy: retrieve official source chunks for citations.",
    ]
    evidence_ids: list[str] = []
    if isinstance(value, LoanProduct):
        lines.extend((f"As of: {value.retrieved_at.isoformat()}", ""))
        for field_name, field_value in value:
            if field_name in {"canonical_url", "retrieved_at"}:
                continue
            lines.extend(_render_summary_field(field_name, field_value, evidence_ids))
    else:
        lines.extend((f"As of: {value.created_at.isoformat()}", ""))
        for field_name in sorted(value.normalized_tariff):
            lines.append(f"## {_humanize(field_name)}")
            lines.append(_stable_text(value.normalized_tariff[field_name]))
            lines.append("")
        evidence_ids.extend(_evidence_ids(value.evidence))
    return "\n".join(lines).strip() + "\n", tuple(dict.fromkeys(evidence_ids))


def _render_summary_field(
    field_name: str,
    value: Any,
    evidence_ids: list[str],
) -> list[str]:
    lines = [f"## {_humanize(field_name)}"]
    if isinstance(value, ExtractedValue):
        lines.append(f"Status: {value.status.value}")
        if value.value is not None:
            lines.append(_stable_text(value.value))
        ids = tuple(citation.evidence_id for citation in value.evidence)
        if ids:
            lines.append("Evidence IDs: " + ", ".join(ids))
            evidence_ids.extend(ids)
    else:
        lines.append(_stable_text(value))
        evidence_ids.extend(_evidence_ids(value))
    lines.append("")
    return lines


def _block_unit(
    block: NormalizedBlock, document: NormalizedDocument
) -> _ProjectionUnit:
    heading = " / ".join(block.heading_path) or None
    if block.type is NormalizedBlockType.HEADING:
        content = f"## {block.text}"
    elif block.type is NormalizedBlockType.LIST:
        content = "\n".join(
            f"- {line.lstrip('-* ').strip()}"
            for line in block.text.splitlines()
            if line.strip()
        )
    else:
        content = block.markdown or block.text
    return _ProjectionUnit(
        content=content.strip(),
        section=heading,
        locators=tuple(reference.locator for reference in block.source_refs),
        source_item_ids=tuple(
            reference.source_item_id for reference in block.source_refs
        ),
        extraction_method=block.extraction_method,
        quality_score=document.quality_score,
        unit_type=block.type.value,
    )


def _table_unit(
    table: NormalizedTable, document: NormalizedDocument
) -> _ProjectionUnit:
    lines = [f"### {table.title}"] if table.title else []
    if table.headers:
        lines.extend(
            (
                "| "
                + " | ".join(_escape_cell(value) for value in table.headers)
                + " |",
                "| " + " | ".join("---" for _ in table.headers) + " |",
            )
        )
    for row in table.rows:
        lines.append(
            "| "
            + " | ".join(_escape_cell(cell.markdown or cell.text) for cell in row.cells)
            + " |"
        )
    for note in table.notes:
        marker = f"{note.marker} " if note.marker else ""
        lines.append(f"> {marker}{note.text}")
    references = [*table.source_refs]
    for row in table.rows:
        for cell in row.cells:
            references.extend(cell.source_refs)
    for note in table.notes:
        references.extend(note.source_refs)
    return _ProjectionUnit(
        content="\n".join(lines).strip(),
        section=table.title,
        locators=tuple(reference.locator for reference in references),
        source_item_ids=tuple(reference.source_item_id for reference in references),
        extraction_method=document.extraction_method,
        quality_score=document.quality_score,
        unit_type="table",
    )


def _split_unit(unit: _ProjectionUnit, limit: int) -> tuple[_ProjectionUnit, ...]:
    if len(unit.content) <= limit:
        return (unit,)
    pieces: list[str] = []
    current = ""
    for line in unit.content.splitlines():
        candidate = f"{current}\n{line}".strip() if current else line
        if current and len(candidate) > limit:
            pieces.extend(_hard_split(current, limit))
            current = line
        else:
            current = candidate
    if current:
        pieces.extend(_hard_split(current, limit))
    return tuple(
        _ProjectionUnit(
            content=piece,
            section=unit.section,
            locators=unit.locators,
            source_item_ids=unit.source_item_ids,
            extraction_method=unit.extraction_method,
            quality_score=unit.quality_score,
            unit_type=unit.unit_type,
        )
        for piece in pieces
    )


def _hard_split(content: str, limit: int) -> list[str]:
    pieces: list[str] = []
    remaining = content.strip()
    while len(remaining) > limit:
        split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def _unique_locators(
    locators: Iterable[SourceLocator],
) -> tuple[SourceLocator, ...]:
    unique: dict[str, SourceLocator] = {}
    for locator in locators:
        key = json.dumps(locator.model_dump(mode="json"), sort_keys=True)
        unique.setdefault(key, locator)
    return tuple(unique.values())


def _evidence_ids(value: Any) -> list[str]:
    if isinstance(value, BaseModel):
        return _evidence_ids(value.model_dump(mode="python"))
    if isinstance(value, dict):
        found = []
        if isinstance(value.get("evidence_id"), str):
            found.append(value["evidence_id"])
        for nested in value.values():
            found.extend(_evidence_ids(nested))
        return found
    if isinstance(value, (list, tuple)):
        return [item for nested in value for item in _evidence_ids(nested)]
    return []


def _stable_text(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    return str(value)


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _escape_cell(value: str) -> str:
    return (
        value.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("|", "\\|")
        .replace("\n", "<br>")
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
