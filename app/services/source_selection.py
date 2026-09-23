from __future__ import annotations

from app.domain.normalization import (
    NormalizedDocument,
    NormalizedSourceBundle,
)
from app.domain.source_discovery import (
    Authority,
    DiscoveryScope,
    InformationRole,
    Relevance,
    SourceAssessment,
    SourceDiscoveryResult,
    TemporalStatus,
)


def is_selected_assessment(assessment: SourceAssessment) -> bool:
    return assessment.relevance is not Relevance.IRRELEVANT and (
        assessment.temporal_status
        not in {TemporalStatus.POSSIBLY_STALE, TemporalStatus.FUTURE}
    )


def selected_assessments_by_source_item(
    assessments: tuple[SourceAssessment, ...],
) -> dict[str, SourceAssessment]:
    values: dict[str, SourceAssessment] = {}
    for assessment in assessments:
        if not is_selected_assessment(assessment):
            continue
        for reference in assessment.source_refs:
            current = values.get(reference.source_item_id)
            if current is None or assessment_precedence(
                assessment
            ) < assessment_precedence(current):
                values[reference.source_item_id] = assessment
    return values


def build_selected_source_bundle(
    bundle: NormalizedSourceBundle,
    discovery: SourceDiscoveryResult,
) -> NormalizedSourceBundle:
    selected_items = selected_assessments_by_source_item(discovery.assessments)
    direct_documents = {
        assessment.document_id
        for assessment in discovery.assessments
        if assessment.source_id == f"document::{assessment.document_id}"
        and is_selected_assessment(assessment)
    }
    documents: list[NormalizedDocument] = []
    for document in bundle.documents:
        selected_table_ids = {
            table.id for table in document.tables if table.id in selected_items
        }
        blocks = tuple(
            block
            for block in document.blocks
            if block.id in selected_items
            or (block.table_id is not None and block.table_id in selected_table_ids)
        )
        tables = tuple(
            table for table in document.tables if table.id in selected_table_ids
        )
        if not blocks and not tables and document.id not in direct_documents:
            continue
        selected_link_ids = {link_id for block in blocks for link_id in block.link_ids}
        links = tuple(link for link in document.links if link.id in selected_link_ids)
        documents.append(
            document.model_copy(
                update={"blocks": blocks, "tables": tables, "links": links}
            )
        )
    if not documents:
        raise ValueError("source discovery selected no content for semantic extraction")
    return bundle.model_copy(update={"documents": tuple(documents)})


def assessment_precedence(assessment: SourceAssessment) -> int:
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
