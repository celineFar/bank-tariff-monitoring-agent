from __future__ import annotations

import hashlib

from app.domain.normalization import NormalizedSourceBundle
from app.domain.semantic_extraction import EvidenceItem
from app.domain.source_discovery import (
    Authority,
    DiscoveryScope,
    InformationRole,
    Relevance,
    SourceAssessment,
    SourceDiscoveryResult,
)


def build_evidence_catalog(
    bundle: NormalizedSourceBundle,
    discovery: SourceDiscoveryResult,
) -> tuple[EvidenceItem, ...]:
    assessments = _assessment_by_source_item(discovery.assessments)
    evidence: list[EvidenceItem] = []
    for document in bundle.documents:
        for block in document.blocks:
            assessment = assessments.get(block.id)
            if assessment is None or assessment.relevance is Relevance.IRRELEVANT:
                continue
            section = " > ".join(block.heading_path) or None
            evidence.append(
                _evidence_item(
                    document.id,
                    block.id,
                    block.text,
                    section,
                    block.source_refs[0].locator,
                    assessment,
                )
            )
        for table in document.tables:
            assessment = assessments.get(table.id)
            if assessment is None or assessment.relevance is Relevance.IRRELEVANT:
                continue
            headers = " | ".join(table.headers)
            for row in table.rows:
                values = " | ".join(cell.text for cell in row.cells)
                content = f"Headers: {headers}\nRow: {values}" if headers else values
                evidence.append(
                    _evidence_item(
                        document.id,
                        row.id,
                        content,
                        table.title,
                        row.cells[0].source_refs[0].locator,
                        assessment,
                    )
                )
            for index, note in enumerate(table.notes):
                evidence.append(
                    _evidence_item(
                        document.id,
                        f"{table.id}:note:{index}",
                        note.text,
                        table.title,
                        note.source_refs[0].locator,
                        assessment,
                    )
                )
    unique = {item.evidence_id: item for item in evidence}
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (item.precedence, item.document_id, item.source_item_id),
        )
    )


def _assessment_by_source_item(
    assessments: tuple[SourceAssessment, ...],
) -> dict[str, SourceAssessment]:
    values: dict[str, SourceAssessment] = {}
    for assessment in assessments:
        if assessment.relevance is Relevance.IRRELEVANT:
            continue
        for reference in assessment.source_refs:
            current = values.get(reference.source_item_id)
            if current is None or _precedence(assessment) < _precedence(current):
                values[reference.source_item_id] = assessment
    return values


def _evidence_item(
    document_id: str,
    source_item_id: str,
    content: str,
    section: str | None,
    locator,
    assessment: SourceAssessment,
) -> EvidenceItem:
    identity = f"{document_id}\x1f{source_item_id}\x1f{content}"
    evidence_id = "ev_" + hashlib.sha256(identity.encode()).hexdigest()[:24]
    return EvidenceItem(
        evidence_id=evidence_id,
        document_id=document_id,
        source_item_id=source_item_id,
        content=content,
        section=section,
        role=assessment.role,
        authority=assessment.authority,
        temporal_status=assessment.temporal_status,
        precedence=_precedence(assessment),
        conditions=assessment.conditions,
        locator=locator,
    )


def _precedence(assessment: SourceAssessment) -> int:
    if assessment.authority is Authority.OFFICIAL_TERMS:
        return 1
    if assessment.scope is DiscoveryScope.TABLE and assessment.role in {
        InformationRole.PRODUCT_TERMS,
        InformationRole.PRICING,
        InformationRole.FEES,
    }:
        return 2
    if assessment.authority is Authority.OFFICIAL_PRODUCT_CONTENT:
        return 3
    if assessment.authority is Authority.OFFICIAL_FAQ:
        return 4
    if assessment.authority is Authority.OFFICIAL_CAMPAIGN_CONTENT:
        return 5
    return 6
