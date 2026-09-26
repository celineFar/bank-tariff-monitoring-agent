from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
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
from app.domain.source_discovery import (
    ProductAssociation,
    SourceAssessment,
    TemporalStatus,
)
from app.services.source_selection import assessment_precedence

# Discovery labels a unit may carry and still be indexed for this offering.
# Related products, navigation, and superseded or future versions are left out:
# an offering's index must not answer with a sibling's values.
_INDEXED_ASSOCIATIONS = frozenset(
    {
        ProductAssociation.CURRENT_PRODUCT,
        ProductAssociation.UNKNOWN,
        ProductAssociation.GENERIC_BANK_INFORMATION,
    }
)


@dataclass(frozen=True, slots=True)
class _ProjectionUnit:
    content: str
    section: str | None
    locators: tuple[SourceLocator, ...]
    source_item_ids: tuple[str, ...]
    extraction_method: str
    quality_score: float | None
    unit_type: str
    # The discovery assessment that selected this unit, when known.
    label: SourceAssessment | None = None
    # Leading lines every piece of a split unit repeats: a table's title and
    # header row, so rows after the first split keep their column names (IX10).
    repeat_prefix: str = ""


# Units whose own content already names their context; any other unit that
# starts a chunk is preceded by its heading path (IX10).
_SELF_TITLED_UNITS = frozenset({"heading", "table", "offering_summary"})
_BREADCRUMB_MAX_CHARS = 200


class KnowledgeProjectionService:
    def __init__(self, *, max_chunk_chars: int = 1_500) -> None:
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
        labels: Mapping[str, SourceAssessment] | None = None,
    ) -> tuple[KnowledgeDocument, ...]:
        """Chunks for the documents of a (selected) bundle.

        With `labels` (source item id -> the discovery assessment that selected
        it), units labelled as another product, navigation, or a superseded or
        future version are left out, and every chunk records the labels of the
        units it holds.
        """
        if offering_id.product is not product:
            raise ValueError("offering does not belong to product")
        documents = (
            document
            for document in bundle.documents
            if selected_document_ids is None or document.id in selected_document_ids
        )
        return tuple(
            projected
            for document in documents
            if document.blocks or document.tables
            if (
                projected := self._project_source_document(
                    run_id=run_id,
                    product=product,
                    offering_id=offering_id,
                    document=document,
                    retrieved_at=retrieved_at,
                    language=language,
                    labels=labels,
                )
            )
            is not None
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
                "summary_schema": "loan_product_or_snapshot_v2",
                # Kept out of the content, so the summary's hash changes only
                # when the tariff or its evidence does (IX11).
                "as_of": retrieved_at.isoformat(),
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
        labels: Mapping[str, SourceAssessment] | None = None,
    ) -> KnowledgeDocument | None:
        labels = labels or {}
        table_by_id = {table.id: table for table in document.tables}
        rendered_tables: set[str] = set()
        units: list[_ProjectionUnit] = []
        for block in document.blocks:
            if block.type is NormalizedBlockType.TABLE and block.table_id:
                table = table_by_id.get(block.table_id)
                if table is not None:
                    units.append(_table_unit(table, document, labels.get(table.id)))
                    rendered_tables.add(table.id)
                    continue
            units.append(_block_unit(block, document, labels.get(block.id)))
        units.extend(
            _table_unit(table, document, labels.get(table.id))
            for table in document.tables
            if table.id not in rendered_tables
        )
        units = [unit for unit in units if unit.label is None or _indexed(unit.label)]
        if not units:
            return None
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
            if current and (
                current_size + 2 + len(unit.content) > self._max_chunk_chars
                # A chunk never mixes the offering's own content with generic
                # bank material, so each chunk's labels describe all of it.
                or _association(current[-1]) != _association(unit)
            ):
                groups.append(current)
                current = []
            if current:
                current_size += 2 + len(unit.content)
            else:
                current_size = _breadcrumb_size(unit) + len(unit.content)
            current.append(unit)
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
            unit_labels = [unit.label for unit in group if unit.label is not None]
            label_metadata: dict[str, Any] = (
                {
                    "product_associations": sorted(
                        {label.product_association.value for label in unit_labels}
                    ),
                    "temporal_statuses": sorted(
                        {label.temporal_status.value for label in unit_labels}
                    ),
                    "authorities": sorted(
                        {label.authority.value for label in unit_labels}
                    ),
                    "precedence": min(
                        assessment_precedence(label) for label in unit_labels
                    ),
                }
                if unit_labels
                else {}
            )
            scores = tuple(
                unit.quality_score for unit in group if unit.quality_score is not None
            )
            chunks.append(
                KnowledgeChunk(
                    ordinal=ordinal,
                    content=_breadcrumb_line(group[0])
                    + "\n\n".join(unit.content for unit in group),
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
                        **label_metadata,
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
    # No "As of" line: the time is the document's `retrieved_at` and
    # `metadata.as_of`, so an unchanged tariff keeps its version (IX11).
    lines.append("")
    if isinstance(value, LoanProduct):
        for field_name, field_value in value:
            if field_name in {"canonical_url", "retrieved_at"}:
                continue
            lines.extend(_render_summary_field(field_name, field_value, evidence_ids))
    else:
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


def _indexed(label: SourceAssessment) -> bool:
    return (
        label.product_association in _INDEXED_ASSOCIATIONS
        and label.temporal_status
        not in {
            TemporalStatus.POSSIBLY_STALE,
            TemporalStatus.FUTURE,
        }
    )


def _association(unit: _ProjectionUnit) -> str | None:
    return unit.label.product_association.value if unit.label is not None else None


def _breadcrumb_line(unit: _ProjectionUnit) -> str:
    """The heading path a chunk starting with `unit` opens with, and a newline.

    A chunk that starts mid-section would otherwise carry its heading only in
    metadata, which is neither embedded nor in the text search (IX10).
    """
    if unit.unit_type in _SELF_TITLED_UNITS or not unit.section:
        return ""
    return f"## {unit.section}"[:_BREADCRUMB_MAX_CHARS] + "\n"


def _breadcrumb_size(unit: _ProjectionUnit) -> int:
    return len(_breadcrumb_line(unit))


def _block_unit(
    block: NormalizedBlock,
    document: NormalizedDocument,
    label: SourceAssessment | None = None,
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
        label=label,
    )


def _table_unit(
    table: NormalizedTable,
    document: NormalizedDocument,
    label: SourceAssessment | None = None,
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
    head = "\n".join(lines)
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
        label=label,
        repeat_prefix=head,
    )


def _split_unit(unit: _ProjectionUnit, limit: int) -> tuple[_ProjectionUnit, ...]:
    """Pieces of at most `limit` characters, breadcrumb included.

    Every piece keeps the unit's label and locators (IX13), and a table's
    pieces each repeat its title and header row (IX10).
    """
    budget = limit - _breadcrumb_size(unit)
    if len(unit.content) <= budget:
        return (unit,)
    prefix = unit.repeat_prefix
    body = unit.content
    if prefix and body.startswith(prefix) and len(prefix) + 1 <= budget // 2:
        body = body[len(prefix) :].lstrip("\n")
        piece_limit = budget - len(prefix) - 1
    else:
        prefix = ""
        piece_limit = budget
    pieces: list[str] = []
    current = ""
    for line in body.splitlines():
        candidate = f"{current}\n{line}".strip() if current else line
        if current and len(candidate) > piece_limit:
            pieces.extend(_hard_split(current, piece_limit))
            current = line
        else:
            current = candidate
    if current:
        pieces.extend(_hard_split(current, piece_limit))
    return tuple(
        replace(unit, content=f"{prefix}\n{piece}" if prefix else piece)
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
