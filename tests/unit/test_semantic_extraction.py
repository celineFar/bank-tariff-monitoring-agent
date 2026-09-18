from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.config import SemanticExtractionSettings
from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    SourceReference,
)
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractedValue,
    ExtractionBatchResponse,
    ExtractionField,
    ExtractionStatus,
    ModelCitation,
    ModelFieldResult,
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
from app.services.extraction_evidence import build_evidence_catalog
from app.services.semantic_extraction import (
    InMemorySemanticExtractionRepository,
    SemanticExtractionService,
    _validate_response,
)

URL = "https://ameriabank.am/en/personal/loans/consumer-loan"


def _reference(identifier: str) -> SourceReference:
    return SourceReference(
        source_item_id=identifier,
        locator=SourceLocator(source_url=URL, source_type=SourceType.PAGE),
    )


def _fixture() -> tuple[NormalizedSourceBundle, SourceDiscoveryResult]:
    blocks = (
        NormalizedBlock(
            id="title",
            type=NormalizedBlockType.HEADING,
            raw_text="Consumer loan",
            text="Consumer loan",
            source_refs=(_reference("title"),),
        ),
        NormalizedBlock(
            id="terms",
            type=NormalizedBlockType.PARAGRAPH,
            raw_text="Amount AMD 100,000-10,000,000; fixed annual rate 20%; term 60 months",
            text="Amount AMD 100,000-10,000,000; fixed annual rate 20%; term 60 months",
            heading_path=("Loan terms",),
            source_refs=(_reference("terms"),),
        ),
    )
    bundle = NormalizedSourceBundle(
        canonical_url=URL,
        acquisition_content_hash="a" * 64,
        documents=(
            NormalizedDocument(
                id="page",
                name="Consumer loan",
                source_url=URL,
                source_type=SourceType.PAGE,
                mime_type="text/html",
                content_sha256="b" * 64,
                extraction_method="browser",
                blocks=blocks,
            ),
        ),
    )
    assessments = tuple(
        SourceAssessment(
            source_id=block.id,
            document_id="page",
            scope=DiscoveryScope.BLOCK,
            product_association=ProductAssociation.CURRENT_PRODUCT,
            role=(
                InformationRole.PRODUCT_DESCRIPTION
                if block.id == "title"
                else InformationRole.PRODUCT_TERMS
            ),
            relevance=Relevance.RELEVANT,
            authority=Authority.OFFICIAL_PRODUCT_CONTENT,
            temporal_status=TemporalStatus.CURRENT,
            reason="Official current product evidence",
            decision_source=DecisionSource.LLM,
            input_fingerprint="c" * 64,
            structural_fingerprint="d" * 64,
            source_refs=block.source_refs,
        )
        for block in blocks
    )
    discovery = SourceDiscoveryResult(
        product=ProductType.CONSUMER_LOAN,
        input_content_hash="a" * 64,
        policy_version="1",
        prompt_version="1",
        model_name="test-model",
        assessments=assessments,
        extraction_context=ExtractionContext(product=ProductType.CONSUMER_LOAN),
        llm_batch_count=1,
        reused_assessment_count=0,
    )
    return bundle, discovery


class FakeExtractor:
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, batch):
        self.calls += 1
        citation = ModelCitation(
            evidence_id=batch.evidence[0].evidence_id,
            quote=batch.evidence[0].content,
        )
        results = []
        for field in batch.fields:
            if field is ExtractionField.CATEGORY:
                result = ModelFieldResult(
                    field=field,
                    status=ExtractionStatus.FOUND,
                    value_json='"consumer_loan"',
                    evidence=(citation,),
                )
            elif field is ExtractionField.PRODUCT_NAME:
                result = ModelFieldResult(
                    field=field,
                    status=ExtractionStatus.FOUND,
                    value_json='"Consumer loan"',
                    evidence=(citation,),
                )
            else:
                result = ModelFieldResult(
                    field=field, status=ExtractionStatus.NOT_STATED
                )
            results.append(result)
        return ExtractionBatchResponse(results=tuple(results))


def test_found_value_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        ExtractedValue[str](value="Consumer loan", status=ExtractionStatus.FOUND)


def test_model_response_schema_uses_portable_json_string() -> None:
    schema = ExtractionBatchResponse.model_json_schema()
    value_schema = schema["$defs"]["ModelFieldResult"]["properties"]["value_json"]

    assert value_schema["anyOf"][0]["type"] == "string"
    assert "JsonValue" not in schema["$defs"]


def test_evidence_catalog_restores_full_normalized_content() -> None:
    bundle, discovery = _fixture()
    evidence = build_evidence_catalog(bundle, discovery)

    assert {item.source_item_id for item in evidence} == {"title", "terms"}
    assert any("10,000,000" in item.content for item in evidence)
    assert all(item.evidence_id.startswith("ev_") for item in evidence)


def test_response_rejects_invented_or_non_verbatim_citation() -> None:
    evidence = EvidenceItem(
        evidence_id="ev_" + "a" * 24,
        document_id="page",
        source_item_id="terms",
        content="Fixed annual rate 20%",
        role=InformationRole.PRICING,
        authority=Authority.OFFICIAL_TERMS,
        temporal_status=TemporalStatus.CURRENT,
        precedence=1,
        locator=SourceLocator(source_url=URL, source_type=SourceType.PAGE),
    )
    from app.domain.semantic_extraction import ExtractionBatch

    batch = ExtractionBatch(
        id="batch",
        product=ProductType.CONSUMER_LOAN,
        group="rates",
        fields=(ExtractionField.INTEREST_RATE,),
        evidence=(evidence,),
        content_fingerprint="f" * 64,
    )
    response = ExtractionBatchResponse(
        results=(
            ModelFieldResult(
                field=ExtractionField.INTEREST_RATE,
                status=ExtractionStatus.FOUND,
                value_json=(
                    '[{"value":{"min":20,"max":20,"rate_type":"fixed",'
                    '"basis":"annual"},"conditions":[]}]'
                ),
                evidence=(
                    ModelCitation(
                        evidence_id=evidence.evidence_id,
                        quote="rate is approximately twenty",
                    ),
                ),
            ),
        )
    )

    with pytest.raises(ValueError, match="not present"):
        _validate_response(batch, response)


@pytest.mark.asyncio
async def test_service_assembles_product_and_reuses_exact_cached_batches() -> None:
    bundle, discovery = _fixture()
    extractor = FakeExtractor()
    repository = InMemorySemanticExtractionRepository()
    service = SemanticExtractionService(
        extractor=extractor,
        repository=repository,
        settings=SemanticExtractionSettings(),
        model_name="gemini-3.1-flash-lite",
    )

    first = await service.extract(
        bundle, discovery, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    first_calls = extractor.calls
    second = await service.extract(
        bundle, discovery, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert first.loan_product.product_name.value == "Consumer loan"
    assert first.loan_product.category.value == "consumer_loan"
    assert first_calls == 5
    assert extractor.calls == first_calls
    assert second.reused_batch_count == 5
