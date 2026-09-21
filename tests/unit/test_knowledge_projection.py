from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.knowledge import chunk_id, document_version_id
from app.domain.models import KnowledgeDocumentKind, OfferingId, ProductType
from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    NormalizedTable,
    NormalizedTableCell,
    NormalizedTableRow,
    SourceReference,
)
from app.domain.semantic_extraction import (
    EvidenceCitation,
    ExtractedValue,
    ExtractionStatus,
    LoanCategory,
    LoanProduct,
)
from app.domain.source_discovery import Authority
from app.services.knowledge_projection import KnowledgeProjectionService

NOW = datetime(2026, 9, 19, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"


def _ref(
    item_id: str,
    *,
    source_type: SourceType | None = None,
    page: int | None = None,
    json_path: str | None = None,
) -> SourceReference:
    source_type = source_type or SourceType.PAGE
    return SourceReference(
        source_item_id=item_id,
        locator=SourceLocator(
            source_url=URL,
            source_type=source_type,
            block_id=item_id,
            css_selector=f"#{item_id}" if source_type is SourceType.PAGE else None,
            pdf_page=page,
            json_path=json_path,
        ),
    )


def _bundle(*, long: bool = False) -> NormalizedSourceBundle:
    paragraph = "A" * 300 if long else "Nominal annual interest rate is 13.5%."
    blocks = (
        NormalizedBlock(
            id="heading",
            type=NormalizedBlockType.HEADING,
            raw_text="Rates",
            text="Rates",
            heading_path=("Rates",),
            source_refs=(_ref("heading"),),
        ),
        NormalizedBlock(
            id="rate",
            type=NormalizedBlockType.PARAGRAPH,
            raw_text=paragraph,
            text=paragraph,
            heading_path=("Rates",),
            source_refs=(
                _ref("rate", source_type=SourceType.PDF, page=4),
                _ref("rate-api", source_type=SourceType.API, json_path="$.rates[0]"),
            ),
            extraction_method="pdf_model",
        ),
        NormalizedBlock(
            id="term",
            type=NormalizedBlockType.PARAGRAPH,
            raw_text="B" * 300 if long else "Maximum term is 60 months.",
            text="B" * 300 if long else "Maximum term is 60 months.",
            heading_path=("Terms",),
            source_refs=(_ref("term", source_type=SourceType.PDF, page=5),),
            extraction_method="pdf_model",
        ),
    )
    table_ref = _ref("fees")
    table = NormalizedTable(
        id="fees",
        title="Fees",
        headers=("Fee", "Amount"),
        rows=(
            NormalizedTableRow(
                id="fee-row",
                cells=(
                    NormalizedTableCell(
                        raw_text="Application",
                        text="Application",
                        source_refs=(table_ref,),
                    ),
                    NormalizedTableCell(
                        raw_text="0 AMD",
                        text="0 AMD",
                        source_refs=(table_ref,),
                    ),
                ),
            ),
        ),
        source_refs=(table_ref,),
    )
    document = NormalizedDocument(
        id="consumer-page",
        name="Consumer loans",
        source_url=URL,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256="a" * 64,
        extraction_method="browser",
        quality_score=0.95,
        blocks=blocks,
        tables=(table,),
    )
    return NormalizedSourceBundle(
        canonical_url=URL,
        acquisition_content_hash="b" * 64,
        documents=(document,),
    )


def _source_documents(*, long: bool = False):
    return KnowledgeProjectionService(max_chunk_chars=500).project_sources(
        run_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        bundle=_bundle(long=long),
        retrieved_at=NOW,
        language="en",
    )


def test_small_normalized_document_stays_whole_and_preserves_all_locators() -> None:
    (document,) = _source_documents()

    assert document.document_kind is KnowledgeDocumentKind.SOURCE
    assert len(document.chunks) == 1
    chunk = document.chunks[0]
    assert "Nominal annual interest rate is 13.5%." in chunk.content
    assert "| Application | 0 AMD |" in chunk.content
    assert chunk.page_start == 4
    assert chunk.page_end == 5
    assert set(chunk.metadata["source_item_ids"]) == {
        "heading",
        "rate",
        "rate-api",
        "term",
        "fees",
    }
    locators = chunk.metadata["locators"]
    assert any(locator.get("css_selector") == "#heading" for locator in locators)
    assert any(locator.get("pdf_page") == 4 for locator in locators)
    assert any(locator.get("json_path") == "$.rates[0]" for locator in locators)


def test_oversized_content_splits_at_units_with_repeatable_ids() -> None:
    first = _source_documents(long=True)[0]
    second = KnowledgeProjectionService(max_chunk_chars=500).project_sources(
        run_id=first.run_id,
        product=first.product,
        offering_id=first.offering_id,
        bundle=_bundle(long=True),
        retrieved_at=NOW,
        language="en",
    )[0]

    assert len(first.chunks) > 1
    assert all(len(chunk.content) <= 500 for chunk in first.chunks)
    assert document_version_id(first) == document_version_id(second)
    assert [chunk_id(first, chunk) for chunk in first.chunks] == [
        chunk_id(second, chunk) for chunk in second.chunks
    ]
    assert [chunk.content for chunk in first.chunks] == [
        chunk.content for chunk in second.chunks
    ]


def test_selected_document_filter_excludes_unselected_sources() -> None:
    documents = KnowledgeProjectionService().project_sources(
        run_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        bundle=_bundle(),
        retrieved_at=NOW,
        language="en",
        selected_document_ids=frozenset({"not-this-document"}),
    )

    assert documents == ()


def test_snapshot_summary_is_deterministic_and_non_authoritative() -> None:
    snapshot = SnapshotAttempt(
        id=uuid4(),
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        status=SnapshotStatus.ACCEPTED,
        normalized_tariff={
            "term": {"max_months": 60},
            "interest_rate": {"max": "13.5", "min": "13.5"},
        },
        evidence=({"evidence_id": "ev_0123456789abcdef01234567"},),
        canonical_sha256="c" * 64,
        created_at=NOW,
        accepted_at=NOW,
    )
    service = KnowledgeProjectionService()
    kwargs = {
        "run_id": snapshot.run_id,
        "product": ProductType.CONSUMER_LOAN,
        "offering_id": OfferingId.CONSUMER_STANDARD,
        "display_name": "Consumer loans",
        "source_url": URL,
        "value": snapshot,
        "language": "en",
    }

    first = service.project_summary(**kwargs)
    second = service.project_summary(**kwargs)

    assert first.document_kind is KnowledgeDocumentKind.OFFERING_SUMMARY
    assert first.metadata["authoritative_evidence"] is False
    assert first.chunks[0].metadata["authoritative_evidence"] is False
    assert first.content_sha256 == second.content_sha256
    assert first.chunks == second.chunks
    assert "## Interest Rate" in first.chunks[0].content
    evidence_ids = first.metadata["evidence_ids"]
    assert isinstance(evidence_ids, list)
    assert "ev_0123456789abcdef01234567" in evidence_ids


def test_loan_product_summary_retains_evidence_ids() -> None:
    citation = EvidenceCitation(
        evidence_id="ev_0123456789abcdef01234567",
        source_item_id="rate",
        source_url=URL,
        source_type=SourceType.PAGE,
        quote="13.5%",
        locator=SourceLocator(
            source_url=URL,
            source_type=SourceType.PAGE,
            block_id="rate",
        ),
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
    )
    product_name = ExtractedValue[str](
        value="Consumer loans",
        evidence=(citation,),
        status=ExtractionStatus.FOUND,
    )
    product = LoanProduct.model_construct(
        product_name=product_name,
        category=LoanCategory.CONSUMER_LOAN,
        canonical_url=URL,
        retrieved_at=NOW,
    )

    summary = KnowledgeProjectionService().project_summary(
        run_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        display_name="Consumer loans",
        source_url=URL,
        value=product,
        language="en",
    )

    assert "Status: found" in summary.chunks[0].content
    assert summary.metadata["evidence_ids"] == [citation.evidence_id]


def test_projection_rejects_cross_family_offering() -> None:
    with pytest.raises(ValueError, match="does not belong"):
        KnowledgeProjectionService().project_sources(
            run_id=uuid4(),
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.MORTGAGE_PRIMARY,
            bundle=_bundle(),
            retrieved_at=NOW,
            language="en",
        )
