from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.models import OfferingId, ProductType
from app.domain.semantic_extraction import ExtractionField, ExtractionStatus, RateBasis
from app.domain.structured_tariffs import (
    FIELD_PATH_VERSION,
    SOURCE_FIELD_PATHS,
    FieldPath,
    QueryOperation,
    ResolutionPlan,
    TariffFact,
    fee_field_path,
)
from app.domain.tariff_comparison import (
    ComparableMeasure,
    IncomparabilityReason,
    comparison_issue,
)
from tests.fixtures.structured_tariffs import accepted_snapshot

NOW = datetime(2026, 9, 21, tzinfo=UTC)


def _plan(**changes):
    values = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "question_sha256": "a" * 64,
        "issued_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "product": ProductType.CONSUMER_LOAN,
        "offering_ids": (OfferingId.CONSUMER_STANDARD,),
        "operation": QueryOperation.SINGLE,
        "fields": (FieldPath.NOMINAL_RATE_MINIMUM,),
    }
    values.update(changes)
    return ResolutionPlan(**values)


def test_field_registry_covers_every_extracted_field() -> None:
    assert set(SOURCE_FIELD_PATHS) == set(ExtractionField)
    assert all(SOURCE_FIELD_PATHS.values())
    assert FIELD_PATH_VERSION == 1
    assert FieldPath("amount.maximum") is FieldPath.AMOUNT_MAXIMUM
    with pytest.raises(ValueError):
        FieldPath("unknown_rate")


def test_fee_mapping_is_conservative() -> None:
    assert fee_field_path("Application fee") is FieldPath.FEE_APPLICATION
    assert fee_field_path("Դիմումի վճար") is FieldPath.FEE_APPLICATION
    assert fee_field_path("Unspecified processing charge") is FieldPath.FEE_OTHER
    assert fee_field_path("Application fee and service fee") is FieldPath.FEE_OTHER


def test_resolution_plan_rejects_scope_expansion_and_invalid_lifetime() -> None:
    assert _plan().operation is QueryOperation.SINGLE
    with pytest.raises(ValidationError, match="one offering"):
        _plan(offering_ids=(OfferingId.CONSUMER_STANDARD, OfferingId.OVERDRAFT))
    with pytest.raises(ValidationError, match="outside resolved product family"):
        _plan(offering_ids=(OfferingId.MORTGAGE_PRIMARY,))
    with pytest.raises(ValidationError, match="expiry"):
        _plan(expires_at=NOW)
    with pytest.raises(ValidationError, match="unsupported field-path version"):
        _plan(taxonomy_version=99)


def test_comparison_requires_same_numeric_dimension_and_units() -> None:
    amd = ComparableMeasure(
        field_path=FieldPath.AMOUNT_MAXIMUM,
        number=Decimal("1000000"),
        unit="money",
        currency="AMD",
    )
    usd = amd.model_copy(update={"currency": "USD"})
    assert comparison_issue(amd, usd) is IncomparabilityReason.DIFFERENT_CURRENCY
    assert comparison_issue(amd, amd) is None
    formula = amd.model_copy(update={"field_path": FieldPath.AMOUNT_FORMULA})
    assert comparison_issue(formula, formula) is IncomparabilityReason.UNSUPPORTED_FIELD
    assert comparison_issue(amd, formula) is IncomparabilityReason.DIFFERENT_FIELD


def test_rate_basis_fee_scope_and_unknown_fee_are_not_silently_compared() -> None:
    annual = ComparableMeasure(
        field_path=FieldPath.NOMINAL_RATE_MINIMUM,
        number=Decimal("12"),
        unit="percent",
        rate_basis=RateBasis.ANNUAL,
        conditions=("salary_customer=true",),
    )
    monthly = annual.model_copy(update={"rate_basis": RateBasis.MONTHLY})
    assert (
        comparison_issue(annual, monthly) is IncomparabilityReason.DIFFERENT_RATE_BASIS
    )
    fee = ComparableMeasure(
        field_path=FieldPath.FEE_APPLICATION,
        number=Decimal("5000"),
        unit="money",
        currency="AMD",
        fee_scope="product",
    )
    assert (
        comparison_issue(fee, fee.model_copy(update={"fee_scope": "general"}))
        is IncomparabilityReason.DIFFERENT_FEE_SCOPE
    )
    other = fee.model_copy(update={"field_path": FieldPath.FEE_OTHER})
    assert comparison_issue(other, other) is IncomparabilityReason.UNCLASSIFIED_FEE


def test_found_fact_requires_evidence() -> None:
    snapshot = accepted_snapshot("consumer")
    with pytest.raises(ValidationError, match="requires value and evidence"):
        TariffFact(
            snapshot_id=snapshot.id,
            offering_id=snapshot.offering_id,
            field_path=FieldPath.AMOUNT_MAXIMUM,
            variant_key="amd",
            status=ExtractionStatus.FOUND,
            value="10000000",
        )


@pytest.mark.parametrize("case", ["consumer", "reviewed_consumer", "mortgage"])
def test_synthetic_accepted_snapshots_are_reparseable(case: str) -> None:
    snapshot = accepted_snapshot(case)
    assert snapshot.model_validate_json(snapshot.model_dump_json()) == snapshot
    assert snapshot.status.value == "accepted"
    assert snapshot.evidence
    assert snapshot.semantic_extraction["loan_product"] is not None
    if case == "reviewed_consumer":
        assert snapshot.semantic_extraction["validated_fields"][0][
            "batch_id"
        ].startswith("review:")
