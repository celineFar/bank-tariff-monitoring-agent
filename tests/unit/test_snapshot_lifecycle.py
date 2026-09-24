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
    ExtractionReviewItem,
    ExtractionStatus,
    LoanCategory,
    LoanProduct,
    PartialLoanProduct,
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
    ValidatedFieldResult,
    ValidationIssue,
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
    detect_large_rate_changes,
    detect_review_signals,
    evidence_changed,
    extraction_is_acceptable,
    non_reviewable_extraction_failure,
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


def test_conflicting_pdf_and_web_values_are_preserved_as_review_candidates() -> None:
    base = _result()
    pdf_id = "ev_abcdef0123456789abcdef01"
    web_citation = (
        base.validated_fields[0]
        .evidence[0]
        .model_copy(update={"quote": "Interest rate 12.5%"})
    )
    pdf_locator = SourceLocator(
        source_url="https://ameriabank.am/tariffs.pdf",
        source_type=SourceType.PDF,
    )
    pdf_citation = web_citation.model_copy(
        update={
            "evidence_id": pdf_id,
            "source_item_id": "pdf-rate",
            "source_url": "https://ameriabank.am/tariffs.pdf",
            "source_type": SourceType.PDF,
            "quote": "Interest rate 15.5%",
            "locator": pdf_locator,
        }
    )
    web_evidence = base.evidence_catalog[0].model_copy(
        update={"content": "Interest rate 12.5%", "conditions": ("AMD",)}
    )
    pdf_evidence = web_evidence.model_copy(
        update={
            "evidence_id": pdf_id,
            "document_id": "pdf",
            "source_item_id": "pdf-rate",
            "content": "Interest rate 15.5%",
            "conditions": ("AMD",),
            "locator": pdf_locator,
        }
    )
    conflicting = base.validated_fields[0].model_copy(
        update={
            "field": ExtractionField.INTEREST_RATE,
            "status": ExtractionStatus.CONFLICTING,
            "value": None,
            "evidence": (web_citation, pdf_citation),
        }
    )
    result = base.model_copy(
        update={
            "validated_fields": (conflicting,),
            "evidence_catalog": (web_evidence, pdf_evidence),
        }
    )

    signals = detect_review_signals(result)

    assert extraction_is_acceptable(result) is False
    assert signals[0]["reason"] == "official_source_conflict"
    candidates = signals[0]["candidates"]
    assert isinstance(candidates, list)
    assert all(isinstance(item, dict) for item in candidates)
    assert [item.get("value") for item in candidates if isinstance(item, dict)] == [
        "12.5",
        "15.5",
    ]
    assert [
        item.get("source_type") for item in candidates if isinstance(item, dict)
    ] == ["page", "pdf"]
    first_candidate = candidates[0]
    assert isinstance(first_candidate, dict)
    assert first_candidate["conditions"] == ["AMD"]


def test_ambiguous_applicability_and_missing_required_field_route_to_review() -> None:
    base = _result()
    citation = base.validated_fields[0].evidence
    ambiguous = base.validated_fields[0].model_copy(
        update={
            "field": ExtractionField.FEES,
            "status": ExtractionStatus.AMBIGUOUS,
            "value": None,
            "evidence": citation,
        }
    )
    missing = base.validated_fields[0].model_copy(
        update={
            "field": ExtractionField.REQUIRED_DOCUMENTS,
            "status": ExtractionStatus.NOT_STATED,
            "value": None,
            "evidence": (),
        }
    )
    result = base.model_copy(update={"validated_fields": (ambiguous, missing)})

    signals = detect_review_signals(result)

    assert [item["reason"] for item in signals] == [
        "source_applicability",
        "missing_required_field",
    ]
    assert extraction_is_acceptable(result) is False


def test_evidence_backed_explicit_empty_value_is_not_unsupported_missing() -> None:
    base = _result()
    explicit_empty = base.validated_fields[0].model_copy(
        update={
            "field": ExtractionField.REQUIRED_DOCUMENTS,
            "status": ExtractionStatus.FOUND,
            "value": (),
        }
    )
    result = base.model_copy(update={"validated_fields": (explicit_empty,)})

    assert detect_review_signals(result) == ()
    assert extraction_is_acceptable(result) is True


def test_model_execution_failure_fails_without_human_review() -> None:
    base = _result(review=True)
    failed = ExtractionReviewItem(
        review_id="review_0123456789abcdef01234567",
        batch_id="rates",
        field=ExtractionField.INTEREST_RATE,
        model_name="test-model",
        validation_issues=(
            ValidationIssue(
                message="model request failed",
                error_type="APIError",
            ),
        ),
    )
    result = base.model_copy(update={"review_items": (failed,)})

    assert (
        non_reviewable_extraction_failure(result)
        == "semantic_extraction.execution_failed"
    )


def test_agreeing_official_sources_do_not_create_review_signal() -> None:
    base = _result()
    assert base.loan_product is not None
    duplicate = (
        base.validated_fields[0]
        .evidence[0]
        .model_copy(
            update={
                "evidence_id": "ev_abcdef0123456789abcdef01",
                "source_item_id": "second-source",
            }
        )
    )
    agreed = base.validated_fields[0].model_copy(
        update={"evidence": (*base.validated_fields[0].evidence, duplicate)}
    )
    duplicate_evidence = base.evidence_catalog[0].model_copy(
        update={
            "evidence_id": duplicate.evidence_id,
            "source_item_id": duplicate.source_item_id,
            "document_id": "second-official-source",
        }
    )
    product = base.loan_product.model_copy(
        update={
            "product_name": base.loan_product.product_name.model_copy(
                update={"evidence": agreed.evidence}
            )
        }
    )
    result = base.model_copy(
        update={
            "loan_product": product,
            "validated_fields": (agreed,),
            "evidence_catalog": (*base.evidence_catalog, duplicate_evidence),
        }
    )

    assert detect_review_signals(result) == ()
    assert extraction_is_acceptable(result) is True
    assert len(result.loan_product.product_name.evidence) == 2


def test_large_rate_change_threshold_is_three_absolute_percentage_points() -> None:
    previous = {
        "interest_rate": {
            "status": "found",
            "value": [{"value": {"min": "10", "max": "12"}}],
        }
    }
    below = {
        "interest_rate": {
            "status": "found",
            "value": [{"value": {"min": "12.99", "max": "12"}}],
        }
    }
    threshold = {
        "interest_rate": {
            "status": "found",
            "value": [{"value": {"min": "13", "max": "12"}}],
        }
    }

    assert detect_large_rate_changes(previous, below) == ()
    signals = detect_large_rate_changes(previous, threshold)
    assert signals[0]["reason"] == "large_rate_change"
    assert signals[0]["absolute_percentage_point_change"] == "3"


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


# The rate guard, against the two ways it failed on real Overdraft runs.


def _rate_entry(low: str, high: str, *conditions: tuple[str, str]) -> dict:
    return {
        "value": {"min": low, "max": high},
        "conditions": [
            {"dimension": dimension, "operator": "=", "value": value}
            for dimension, value in conditions
        ],
    }


_ARCA = "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital"
_GOLD = "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital"


def test_reworded_and_reordered_entries_are_not_a_rate_change() -> None:
    """Identical rates must not alarm because the extractor reworded a condition.

    Taken from two runs over the same page. The scoring entry's wording changed,
    which moved it to the front of the sorted list, and the dimension names
    changed too. Pairing by position compared Arca's 23.13 with the scoring
    entry's 16.06 and reported a 7.07-point change on rates that had not moved.
    """
    previous = {
        "effective_rate": {
            "value": [
                _rate_entry("23.13", "23.13", ("card_type", _ARCA)),
                _rate_entry("21.92", "21.92", ("card_type", _GOLD)),
                _rate_entry(
                    "16.06",
                    "23.13",
                    ("program", "scoring-based loans or specific industries"),
                ),
            ]
        }
    }
    current = {
        "effective_rate": {
            "value": [
                _rate_entry(
                    "16.06",
                    "23.13",
                    (
                        "application_type",
                        "scoring-based loans or loans to workers of specific industries",
                    ),
                    ("currency", "AMD"),
                ),
                _rate_entry(
                    "23.13", "23.13", ("card_tier", _ARCA), ("currency", "AMD")
                ),
                _rate_entry(
                    "21.92", "21.92", ("card_tier", _GOLD), ("currency", "AMD")
                ),
            ]
        }
    }

    assert detect_large_rate_changes(previous, current) == ()


def test_a_real_jump_is_found_on_the_entry_it_belongs_to() -> None:
    previous = {
        "interest_rate": {
            "value": [
                _rate_entry("21", "21", ("card_type", _ARCA)),
                _rate_entry("15", "21", ("program", "scoring-based loans")),
            ]
        }
    }
    current = {
        "interest_rate": {
            "value": [
                _rate_entry("19", "25", ("program", "scoring-based loans")),
                _rate_entry("21", "21", ("card_tier", _ARCA)),
            ]
        }
    }

    signals = detect_large_rate_changes(previous, current)

    assert len(signals) == 1
    assert signals[0]["field"] == "interest_rate"
    assert signals[0]["absolute_percentage_point_change"] == "4"
    # Both ends moved four points. On a tie the first key in sorted order is
    # reported, so the signal is the same on every run -- the old positional
    # code iterated a set, and which tied change it reported could vary.
    assert (signals[0]["previous"], signals[0]["current"]) == ("21", "25")


def test_an_entry_without_a_counterpart_is_not_a_rate_change() -> None:
    """A dropped or added tier is structural; change detection reports it."""
    previous = {
        "interest_rate": {"value": [_rate_entry("21", "21", ("card_type", _ARCA))]}
    }
    current = {
        "interest_rate": {"value": [_rate_entry("30", "30", ("card_type", _GOLD))]}
    }

    assert detect_large_rate_changes(previous, current) == ()


def test_a_rate_jump_is_guarded_even_when_a_field_review_is_also_needed() -> None:
    """The run that is already irregular is the one that most needs the guard.

    Gating the check on an otherwise-clean extraction meant a reviewer answering
    an unrelated field review would activate a snapshot whose rate had jumped,
    without ever being shown the jump.
    """
    result = _result(review=True)
    rate = ValidatedFieldResult(
        field=ExtractionField.INTEREST_RATE,
        status=ExtractionStatus.FOUND,
        value=[_rate_entry("19", "25", ("program", "scoring-based loans"))],
        evidence=result.validated_fields[0].evidence,
        batch_id="rates",
    )
    partial = result.partial_product.model_copy(
        update={"fields": (*result.partial_product.fields, rate)}
    )
    result = result.model_copy(
        update={
            "partial_product": partial,
            "validated_fields": (*result.validated_fields, rate),
        }
    )
    previous = _snapshot(
        {
            "interest_rate": {
                "status": "found",
                "value": [_rate_entry("15", "21", ("program", "scoring-based loans"))],
            }
        }
    )

    snapshot = build_snapshot_attempt(
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        result=result,
        previous_accepted_snapshot_id=previous.id,
        previous_accepted_snapshot=previous,
    )

    reasons = [signal["reason"] for signal in snapshot.validation["review_signals"]]
    assert "large_rate_change" in reasons
    assert snapshot.status is SnapshotStatus.REVIEW_REQUIRED
    assert snapshot.validation["accepted"] is False
