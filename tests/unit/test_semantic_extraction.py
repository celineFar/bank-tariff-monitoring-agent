from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

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
    SemanticExtractionRunStatus,
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
    _normalize_field_contract,
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
        self.batches = []

    async def extract(self, batch):
        self.calls += 1
        self.batches.append(batch)
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
            elif field is ExtractionField.TERM:
                result = ModelFieldResult(
                    field=field,
                    status=ExtractionStatus.FOUND,
                    value_json=(
                        '[{"value":{"min_months":60,"max_months":60},"conditions":[]}]'
                    ),
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
    assert all(
        item.product_association is ProductAssociation.CURRENT_PRODUCT
        for item in evidence
    )


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


@pytest.mark.parametrize(
    ("field", "raw_value", "expected"),
    (
        (
            ExtractionField.LOAN_AMOUNT,
            [
                {
                    "conditions": ["AMD"],
                    "value": {
                        "type": "absolute",
                        "currency": "AMD",
                        "min": 3_000_000,
                        "max": 150_000_000,
                    },
                }
            ],
            150_000_000,
        ),
        (
            ExtractionField.TERM,
            [
                {
                    "min_value": 61,
                    "max_value": 360,
                    "min_unit": "month",
                    "max_unit": "month",
                }
            ],
            360,
        ),
        (
            ExtractionField.DOWN_PAYMENT_PCT,
            [{"value": 0.075, "conditions": ["state-supported program"]}],
            Decimal("7.500"),
        ),
    ),
)
def test_contract_adapter_repairs_known_semantic_shapes(
    field, raw_value, expected
) -> None:
    result = ModelFieldResult(
        field=field,
        status=ExtractionStatus.FOUND,
        value_json=json.dumps(raw_value),
        evidence=(ModelCitation(evidence_id="ev_" + "a" * 24, quote="supported"),),
    )

    normalized, notes = _normalize_field_contract(result)
    value = json.loads(normalized.value_json)

    assert notes
    if field is ExtractionField.LOAN_AMOUNT:
        assert value[0]["value"]["range"]["max"] == expected
        assert value[0]["conditions"][0]["dimension"] == "currency"
    elif field is ExtractionField.TERM:
        assert value[0]["value"]["max_months"] == expected
    else:
        assert Decimal(str(value[0]["value"])) == expected


def test_required_documents_are_deduplicated_without_losing_order() -> None:
    result = ModelFieldResult(
        field=ExtractionField.REQUIRED_DOCUMENTS,
        status=ExtractionStatus.FOUND,
        value_json=json.dumps(
            ["Identity document", " Identity   document ", "Purchase agreement"]
        ),
        evidence=(ModelCitation(evidence_id="ev_" + "a" * 24, quote="supported"),),
    )

    normalized, notes = _normalize_field_contract(result)

    assert json.loads(normalized.value_json) == [
        "Identity document",
        "Purchase agreement",
    ]
    assert notes


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
    assert first_calls == 6
    assert extractor.calls == first_calls
    assert second.reused_batch_count == 6


class InvalidRateExtractor(FakeExtractor):
    async def extract(self, batch):
        response = await super().extract(batch)
        if ExtractionField.INTEREST_RATE not in batch.fields:
            return response
        citation = ModelCitation(
            evidence_id=batch.evidence[0].evidence_id,
            quote=batch.evidence[0].content,
        )
        return ExtractionBatchResponse(
            results=tuple(
                ModelFieldResult(
                    field=item.field,
                    status=ExtractionStatus.FOUND,
                    value_json='[{"min":20,"max":20,"conditions":["salary client"]}]',
                    evidence=(citation,),
                )
                if item.field is ExtractionField.INTEREST_RATE
                else item
                for item in response.results
            )
        )


class RepairingTermExtractor(FakeExtractor):
    async def extract(self, batch):
        response = await super().extract(batch)
        if ExtractionField.TERM not in batch.fields or any(
            item == "repair_field=term" for item in batch.target_scope
        ):
            return response
        return ExtractionBatchResponse(
            results=tuple(
                ModelFieldResult(
                    field=item.field,
                    status=ExtractionStatus.NOT_STATED,
                )
                if item.field is ExtractionField.TERM
                else item
                for item in response.results
            )
        )


@pytest.mark.asyncio
async def test_suspicious_not_stated_field_gets_bounded_repair_and_cached() -> None:
    bundle, discovery = _fixture()
    extractor = RepairingTermExtractor()
    repository = InMemorySemanticExtractionRepository()
    service = SemanticExtractionService(
        extractor=extractor,
        repository=repository,
        settings=SemanticExtractionSettings(),
        model_name="test-model",
    )

    first = await service.extract(
        bundle, discovery, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    calls_after_first = extractor.calls
    second = await service.extract(
        bundle, discovery, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert first.status is SemanticExtractionRunStatus.COMPLETED
    assert first.loan_product is not None
    assert first.loan_product.term.value[0].value.max_months == 60
    assert any(
        output.batch_id.endswith("__repair_term") for output in first.raw_batch_outputs
    )
    original_batch = next(
        batch for batch in extractor.batches if batch.id == "extract_001"
    )
    repair_batch = next(
        batch for batch in extractor.batches if batch.id.endswith("__repair_term")
    )
    assert {item.evidence_id for item in repair_batch.evidence} == {
        item.evidence_id for item in original_batch.evidence
    }
    assert repair_batch.repair_context_json is not None
    assert calls_after_first == 7
    assert extractor.calls == calls_after_first
    assert second.reused_batch_count == 6


class SelectivelyFailingExtractor(FakeExtractor):
    def __init__(self, *, fail_all: bool = False) -> None:
        super().__init__()
        self.fail_all = fail_all

    async def extract(self, batch):
        if self.fail_all or ExtractionField.INTEREST_RATE in batch.fields:
            self.calls += 1
            raise RuntimeError("model response could not be parsed")
        return await super().extract(batch)


@pytest.mark.asyncio
async def test_common_rate_shape_is_adapted_without_losing_valid_fields() -> None:
    bundle, discovery = _fixture()
    extractor = InvalidRateExtractor()
    repository = InMemorySemanticExtractionRepository()
    service = SemanticExtractionService(
        extractor=extractor,
        repository=repository,
        settings=SemanticExtractionSettings(),
        model_name="test-model",
    )

    result = await service.extract(
        bundle, discovery, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert result.status is SemanticExtractionRunStatus.COMPLETED
    assert result.loan_product is not None
    assert result.partial_product.category.value == "consumer_loan"
    assert {item.field for item in result.validated_fields} >= {
        ExtractionField.CATEGORY,
        ExtractionField.PRODUCT_NAME,
    }
    assert result.loan_product.interest_rate.value[0].value.min == 20
    assert result.raw_batch_outputs[1].normalization_notes

    next_plan = await service.plan(bundle, discovery)
    assert all(
        ExtractionField.INTEREST_RATE not in batch.fields for batch in next_plan.batches
    )


@pytest.mark.asyncio
async def test_one_failed_batch_is_routed_to_review_and_other_fields_survive() -> None:
    bundle, discovery = _fixture()
    service = SemanticExtractionService(
        extractor=SelectivelyFailingExtractor(),
        repository=InMemorySemanticExtractionRepository(),
        settings=SemanticExtractionSettings(),
        model_name="test-model",
    )

    result = await service.extract(
        bundle, discovery, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert result.status is SemanticExtractionRunStatus.COMPLETED_WITH_REVIEW
    assert result.validated_fields
    assert any(
        item.field is ExtractionField.INTEREST_RATE and item.raw_result is None
        for item in result.review_items
    )


@pytest.mark.asyncio
async def test_every_failed_batch_remains_a_systemic_failure() -> None:
    bundle, discovery = _fixture()
    service = SemanticExtractionService(
        extractor=SelectivelyFailingExtractor(fail_all=True),
        repository=InMemorySemanticExtractionRepository(),
        settings=SemanticExtractionSettings(),
        model_name="test-model",
    )

    with pytest.raises(RuntimeError, match="could not be parsed"):
        await service.extract(
            bundle, discovery, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC)
        )
