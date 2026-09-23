from __future__ import annotations

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    SourceReference,
)
from app.domain.source_discovery import (
    Authority,
    DecisionSource,
    DiscoveryScope,
    ExtractionContext,
    InformationRole,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.services.source_selection import build_selected_source_bundle

URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"


def test_selected_bundle_keeps_layout_order_and_removes_rejected_blocks() -> None:
    locator = SourceLocator(source_url=URL, source_type=SourceType.PAGE)
    kept = _block("kept", "Current mortgage rate", locator)
    removed = _block("removed", "Global navigation", locator)
    bundle = NormalizedSourceBundle(
        canonical_url=URL,
        acquisition_content_hash="a" * 64,
        documents=(
            NormalizedDocument(
                id="page",
                name="Mortgage",
                source_url=URL,
                source_type=SourceType.PAGE,
                mime_type="text/html",
                content_sha256="b" * 64,
                extraction_method="browser",
                blocks=(kept, removed),
            ),
        ),
    )
    discovery = SourceDiscoveryResult(
        product=ProductType.MORTGAGE,
        input_content_hash="a" * 64,
        policy_version="1",
        prompt_version="1",
        model_name="test",
        assessments=(
            _assessment(kept, Relevance.RELEVANT),
            _assessment(removed, Relevance.IRRELEVANT),
        ),
        extraction_context=ExtractionContext(product=ProductType.MORTGAGE),
        llm_batch_count=1,
        reused_assessment_count=0,
    )

    selected = build_selected_source_bundle(bundle, discovery)

    assert [block.id for block in selected.documents[0].blocks] == ["kept"]
    assert selected.acquisition_content_hash == bundle.acquisition_content_hash


def _block(identifier: str, text: str, locator: SourceLocator) -> NormalizedBlock:
    return NormalizedBlock(
        id=identifier,
        type=NormalizedBlockType.PARAGRAPH,
        raw_text=text,
        text=text,
        source_refs=(SourceReference(source_item_id=identifier, locator=locator),),
    )


def _assessment(block: NormalizedBlock, relevance: Relevance) -> SourceAssessment:
    return SourceAssessment(
        source_id=block.id,
        document_id="page",
        scope=DiscoveryScope.BLOCK,
        product_association=ProductAssociation.CURRENT_PRODUCT,
        role=InformationRole.PRODUCT_TERMS,
        relevance=relevance,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        reason="test",
        decision_source=DecisionSource.RULE,
        input_fingerprint="c" * 64,
        structural_fingerprint="d" * 64,
        source_refs=block.source_refs,
    )
