from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.semantic_extraction import (
    EvidenceCitation,
    EvidenceItem,
    ExtractedValue,
    ExtractionField,
    ExtractionStatus,
    LoanCategory,
    LoanProduct,
    PartialLoanProduct,
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
    ValidatedFieldResult,
)
from app.domain.source_discovery import (
    Authority,
    InformationRole,
    TemporalStatus,
)
from app.services.snapshot_lifecycle import (
    build_snapshot_attempt,
    canonical_sha256,
    canonical_tariff_payload,
    compare_accepted_snapshots,
    evidence_changed,
    extraction_is_acceptable,
)

NOW = datetime(2026, 9, 19, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
EVIDENCE_ID = "ev_0123456789abcdef01234567"


def _result(*, review: bool = False) -> SemanticExtractionResult:
    locator = SourceLocator(
        source_url=URL,
        source_type=SourceType.PAGE,
        block_id="rate",
    )
    citation = EvidenceCitation(
        evidence_id=EVIDENCE_ID,
        source_item_id="rate",
        source_url=URL,
        source_type=SourceType.PAGE,
        quote="Consumer loan",
        locator=locator,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
    )
    product_name = ExtractedValue[str](
        value="Consumer loan",
        evidence=(citation,),
        status=ExtractionStatus.FOUND,
    )
    product = LoanProduct.model_construct(
        product_name=product_name,
        category=LoanCategory.CONSUMER_LOAN,
        canonical_url=URL,
        retrieved_at=NOW,
    )
    evidence = EvidenceItem(
        evidence_id=EVIDENCE_ID,
        document_id="page",
        source_item_id="rate",
        content="Consumer loan",
        role=InformationRole.PRICING,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        precedence=1,
        locator=locator,
    )
    validated = ValidatedFieldResult(
        field=ExtractionField.PRODUCT_NAME,
        status=ExtractionStatus.FOUND,
        value="Consumer loan",
        evidence=(citation,),
        batch_id="identity",
    )
    return SemanticExtractionResult(
        product=ProductType.CONSUMER_LOAN,
        model_name="test-model",
        status=(
            SemanticExtractionRunStatus.COMPLETED_WITH_REVIEW
            if review
            else SemanticExtractionRunStatus.COMPLETED
        ),
        loan_product=None if review else product,
        partial_product=(
            PartialLoanProduct(
                canonical_url=URL,
                retrieved_at=NOW,
                category=LoanCategory.CONSUMER_LOAN,
                fields=(validated,),
            )
            if review
            else None
        ),
        evidence_catalog=(evidence,),
        batch_results=(),
        validated_fields=(validated,),
        review_items=(),
        reused_batch_count=0,
    )


def _snapshot(
    payload,
    *,
    accepted: bool = True,
    evidence=(),
    created_at: datetime = NOW,
) -> SnapshotAttempt:
    return SnapshotAttempt(
        id=uuid4(),
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        status=SnapshotStatus.ACCEPTED if accepted else SnapshotStatus.REVIEW_REQUIRED,
        normalized_tariff=payload,
        evidence=evidence,
        canonical_sha256=canonical_sha256(payload),
        created_at=created_at,
        accepted_at=created_at if accepted else None,
    )


def test_canonical_payload_ignores_provenance_time_and_sequence_order() -> None:
    first = canonical_tariff_payload(
        {
            "retrieved_at": NOW.isoformat(),
            "rates": [
                {"value": "14", "conditions": [{"value": "USD"}]},
                {"value": "13.5", "conditions": [{"value": "AMD"}]},
            ],
            "evidence": [{"evidence_id": "first", "quote": "13.5%"}],
        }
    )
    second = canonical_tariff_payload(
        {
            "rates": [
                {"conditions": [{"value": "AMD"}], "value": "13.5"},
                {"conditions": [{"value": "USD"}], "value": "14"},
            ],
            "retrieved_at": (NOW + timedelta(days=1)).isoformat(),
            "evidence": [{"evidence_id": "second", "quote": "updated location"}],
        }
    )

    assert first == second
    assert canonical_sha256(first) == canonical_sha256(second)


def test_complete_supported_extraction_is_accepted() -> None:
    result = _result()

    assert extraction_is_acceptable(result) is True
    snapshot = build_snapshot_attempt(
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        result=result,
        previous_accepted_snapshot_id=None,
    )

    assert snapshot.status is SnapshotStatus.ACCEPTED
    assert snapshot.accepted_at == NOW
    assert snapshot.validation["accepted"] is True


def test_review_result_remains_candidate_and_is_not_compared() -> None:
    result = _result(review=True)

    assert extraction_is_acceptable(result) is False
    snapshot = build_snapshot_attempt(
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        result=result,
        previous_accepted_snapshot_id=None,
    )

    assert snapshot.status is SnapshotStatus.REVIEW_REQUIRED
    assert snapshot.accepted_at is None
    assert compare_accepted_snapshots(None, snapshot) is None


def test_comparison_reports_only_meaningful_top_level_changes() -> None:
    previous = _snapshot(
        {"interest_rate": {"status": "found", "value": "13.5"}, "term": 60}
    )
    current = _snapshot(
        {"interest_rate": {"status": "found", "value": "14"}, "term": 60},
        created_at=NOW + timedelta(days=1),
    )

    changes = compare_accepted_snapshots(previous, current)

    assert changes is not None
    assert [change.field for change in changes.changes] == ["interest_rate"]
    assert changes.previous_snapshot_id == previous.id


def test_equivalent_tariff_with_changed_evidence_is_provenance_only() -> None:
    payload = {"interest_rate": {"status": "found", "value": "13.5"}}
    previous = _snapshot(payload, evidence=({"evidence_id": "one"},))
    current = _snapshot(
        payload,
        evidence=({"evidence_id": "two"},),
        created_at=NOW + timedelta(days=1),
    )

    changes = compare_accepted_snapshots(previous, current)

    assert changes is not None
    assert changes.changes == ()
    assert evidence_changed(previous, current) is True


def test_first_observation_and_unchanged_snapshot_emit_no_field_changes() -> None:
    current = _snapshot({"term": {"status": "found", "value": 60}})
    first = compare_accepted_snapshots(None, current)
    repeated = compare_accepted_snapshots(current, _snapshot(current.normalized_tariff))

    assert first is not None
    assert first.previous_snapshot_id is None
    assert first.changes == ()
    assert repeated is not None
    assert repeated.previous_snapshot_id == current.id
    assert repeated.changes == ()


def test_status_transition_is_a_meaningful_change() -> None:
    previous = _snapshot({"interest_rate": {"status": "not_stated", "value": None}})
    current = _snapshot({"interest_rate": {"status": "found", "value": "13.5"}})

    changes = compare_accepted_snapshots(previous, current)

    assert changes is not None
    assert len(changes.changes) == 1
    assert changes.changes[0].field == "interest_rate"
