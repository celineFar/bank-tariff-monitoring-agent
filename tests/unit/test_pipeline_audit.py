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
from app.domain.pdf_extraction import (
    PdfExtractedBlock,
    PdfExtractedBlockType,
    PdfExtractedPage,
    PdfExtractionResponse,
)
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractionBatch,
    ExtractionBatchResponse,
    ExtractionField,
    ExtractionStatus,
    ModelCitation,
    ModelFieldResult,
    SemanticExtractionPlan,
    SemanticExtractionResult,
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
from app.services.pipeline_audit import (
    human_filename,
    render_diff_markdown,
    render_pdf_response_markdown,
    render_semantic_extraction,
    render_source_selection,
)
from scripts.demonstrate_end_to_end import _next_run_directory

URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"


def test_human_filename_is_readable_and_cannot_escape_directory() -> None:
    assert (
        human_filename(
            "../Mortgage terms: primary market.pdf", index=1, extension=".pdf"
        )
        == "002_Mortgage_terms_primary_market.pdf"
    )


def test_diff_report_labels_source_and_normalized_changes() -> None:
    report = render_diff_markdown(
        "Normalization",
        (("Page", "Rate: 13%\n", "Rate: 13.5%\n"),),
    )

    assert "<del>13%</del>" in report
    assert "<ins>13.5%</ins>" in report
    assert "```diff" not in report
    assert "normalized document itself" in report


def test_pdf_response_markdown_keeps_page_and_block_text() -> None:
    response = PdfExtractionResponse(
        pages=(
            PdfExtractedPage(
                page_number=2,
                blocks=(
                    PdfExtractedBlock(
                        type=PdfExtractedBlockType.PARAGRAPH,
                        text="Loan amount AMD 30 million",
                    ),
                ),
            ),
        )
    )

    markdown = render_pdf_response_markdown(
        "Mortgage terms", "https://ameriabank.am/terms.pdf", response
    )

    assert "## PDF page 2" in markdown
    assert "Loan amount AMD 30 million" in markdown
    assert "https://ameriabank.am/terms.pdf" in markdown


def test_end_to_end_runs_use_incrementing_directories(tmp_path) -> None:
    root = tmp_path / "end-to-end"
    first = _next_run_directory(root)
    second = _next_run_directory(root)
    (root / "run_010").mkdir()
    after_gap = _next_run_directory(root)

    assert first.name == "run_001"
    assert second.name == "run_002"
    assert after_gap.name == "run_011"
    assert first.is_dir()
    assert second.is_dir()


def test_source_discovery_report_overlays_semantic_colors_on_normalized_content() -> (
    None
):
    bundle, discovery, _, _ = _audit_fixture()

    report = render_source_selection(bundle, discovery)

    assert "source-discovery semantic overlay" in report
    assert "SELECTED" in report
    assert "background:#ecfdf3" in report
    assert "Fixed annual rate 13.5%" in report
    assert "```text" not in report


def test_extraction_report_highlights_only_exact_cited_quote() -> None:
    bundle, discovery, plan, result = _audit_fixture()

    report = render_semantic_extraction(bundle, discovery, plan, result)

    assert "EX-001" in report
    assert "<mark" in report
    assert "13.5%<sup" in report
    assert "</mark> for AMD loans." in report
    assert "Extraction overlay" in report


def _audit_fixture() -> tuple[
    NormalizedSourceBundle,
    SourceDiscoveryResult,
    SemanticExtractionPlan,
    SemanticExtractionResult,
]:
    locator = SourceLocator(source_url=URL, source_type=SourceType.PAGE)
    reference = SourceReference(source_item_id="terms", locator=locator)
    block = NormalizedBlock(
        id="terms",
        type=NormalizedBlockType.PARAGRAPH,
        raw_text="Fixed annual rate 13.5% for AMD loans.",
        text="Fixed annual rate 13.5% for AMD loans.",
        heading_path=("Terms",),
        source_refs=(reference,),
    )
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
                blocks=(block,),
            ),
        ),
    )
    assessment = SourceAssessment(
        source_id="terms",
        document_id="page",
        scope=DiscoveryScope.BLOCK,
        product_association=ProductAssociation.CURRENT_PRODUCT,
        role=InformationRole.PRICING,
        relevance=Relevance.RELEVANT,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        reason="Current official pricing",
        decision_source=DecisionSource.LLM,
        input_fingerprint="c" * 64,
        structural_fingerprint="d" * 64,
        source_refs=(reference,),
    )
    discovery = SourceDiscoveryResult(
        product=ProductType.MORTGAGE,
        input_content_hash="a" * 64,
        policy_version="1",
        prompt_version="1",
        model_name="test-model",
        assessments=(assessment,),
        extraction_context=ExtractionContext(product=ProductType.MORTGAGE),
        llm_batch_count=1,
        reused_assessment_count=0,
    )
    evidence = EvidenceItem(
        evidence_id="ev_" + "e" * 24,
        document_id="page",
        source_item_id="terms",
        content=block.text,
        section="Terms",
        role=InformationRole.PRICING,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        precedence=2,
        locator=locator,
    )
    batch = ExtractionBatch(
        id="extract_000",
        product=ProductType.MORTGAGE,
        group="core_financial",
        fields=(ExtractionField.INTEREST_RATE,),
        evidence=(evidence,),
        content_fingerprint="f" * 64,
    )
    plan = SemanticExtractionPlan(
        product=ProductType.MORTGAGE,
        canonical_url=URL,
        input_content_hash="a" * 64,
        schema_version="2",
        prompt_version="2",
        model_name="test-model",
        evidence_catalog=(evidence,),
        batches=(batch,),
    )
    response = ExtractionBatchResponse(
        results=(
            ModelFieldResult(
                field=ExtractionField.INTEREST_RATE,
                status=ExtractionStatus.FOUND,
                value_json='[{"value":{"min":13.5,"max":13.5}}]',
                evidence=(
                    ModelCitation(
                        evidence_id=evidence.evidence_id,
                        quote="13.5%",
                    ),
                ),
            ),
        )
    )
    result = SemanticExtractionResult.model_construct(
        product=ProductType.MORTGAGE,
        model_name="test-model",
        loan_product=None,
        evidence_catalog=(evidence,),
        batch_results=(response,),
        reused_batch_count=0,
    )
    return bundle, discovery, plan, result
