from copy import deepcopy

import pytest

from app.domain.structured_tariffs import FieldPath, RetrievalUnitKind
from app.services.structured_projection import (
    RENDERER_VERSION,
    StructuredTariffProjector,
    _clean,
)
from tests.fixtures.structured_tariffs import accepted_snapshot


@pytest.mark.parametrize("case", ["consumer", "reviewed_consumer", "mortgage"])
def test_projection_preserves_typed_facts_and_evidence(case: str) -> None:
    snapshot = accepted_snapshot(case)
    projector = StructuredTariffProjector()
    projected = projector.project(snapshot, display_name="Synthetic offering")
    assert projected == projector.project(snapshot, display_name="Synthetic offering")
    assert projected.profile.snapshot_id == snapshot.id
    assert all(fact.snapshot_id == snapshot.id for fact in projected.facts)
    assert all(
        fact.evidence for fact in projected.facts if fact.status.value == "found"
    )
    assert all(unit.fact_ids and unit.evidence_ids for unit in projected.units)
    assert any(unit.kind is RetrievalUnitKind.PROFILE for unit in projected.units)
    assert all(
        unit.kind in {RetrievalUnitKind.PROFILE, RetrievalUnitKind.FIELD_DETAIL}
        for unit in projected.units
    )
    if case == "mortgage":
        assert any(
            fact.field_path is FieldPath.DOWN_PAYMENT_MINIMUM
            for fact in projected.facts
        )
        assert projected.profile.property_market == "primary"
    else:
        assert {
            fact.currency
            for fact in projected.facts
            if fact.field_path is FieldPath.AMOUNT_MAXIMUM
        } == {"AMD", "USD"}
        assert any(
            fact.field_path is FieldPath.AMOUNT_FORMULA for fact in projected.facts
        )
        assert any(
            fact.field_path is FieldPath.FEE_APPLICATION for fact in projected.facts
        )
        if case == "reviewed_consumer":
            rates = [
                fact
                for fact in projected.facts
                if fact.field_path is FieldPath.NOMINAL_RATE_MINIMUM
            ]
            assert any(fact.number == 11 for fact in rates)


def test_projection_rejects_pending_snapshot() -> None:
    snapshot = accepted_snapshot("consumer").model_copy(
        update={"status": "review_required", "accepted_at": None}
    )
    with pytest.raises(ValueError, match="only final accepted"):
        StructuredTariffProjector().project(snapshot, display_name="Synthetic offering")


def test_projection_rejects_canonical_extraction_mismatch() -> None:
    snapshot = accepted_snapshot("consumer").model_copy(
        update={"normalized_tariff": {"amount": "wrong"}}
    )
    with pytest.raises(ValueError, match="disagree"):
        StructuredTariffProjector().project(snapshot, display_name="Synthetic offering")


def test_projection_rejects_quote_not_in_captured_evidence() -> None:
    snapshot = accepted_snapshot("consumer")
    extraction = deepcopy(snapshot.semantic_extraction)
    extraction["loan_product"]["interest_rate"]["evidence"][0]["quote"] = (
        "unsupported quote"
    )
    changed = snapshot.model_copy(update={"semantic_extraction": extraction})
    with pytest.raises(ValueError, match="missing from captured evidence"):
        StructuredTariffProjector().project(changed, display_name="Synthetic offering")


def test_projection_rejects_unofficial_source() -> None:
    snapshot = accepted_snapshot("consumer")
    extraction = deepcopy(snapshot.semantic_extraction)
    extraction["loan_product"]["interest_rate"]["evidence"][0]["authority"] = (
        "marketing_content"
    )
    changed = snapshot.model_copy(update={"semantic_extraction": extraction})
    with pytest.raises(ValueError, match="authority disagrees"):
        StructuredTariffProjector().project(changed, display_name="Synthetic offering")


def test_rendered_retrieval_text_strips_html_and_markdown_link_syntax() -> None:
    assert (
        _clean("Rate <sup>promo</sup> [terms](<https://example.com>)")
        == "Rate promo terms"
    )


def test_projection_groups_range_bounds_and_preserves_currency_conditions() -> None:
    projected = StructuredTariffProjector().project(
        accepted_snapshot("consumer"), display_name="Synthetic offering"
    )
    minimums = [
        fact for fact in projected.facts if fact.field_path is FieldPath.AMOUNT_MINIMUM
    ]
    maximums = [
        fact for fact in projected.facts if fact.field_path is FieldPath.AMOUNT_MAXIMUM
    ]
    assert {fact.currency for fact in minimums} == {"AMD", "USD"}
    for minimum in minimums:
        partner = next(
            maximum
            for maximum in maximums
            if maximum.variant_key == minimum.variant_key
        )
        assert partner.currency == minimum.currency
        assert partner.conditions == minimum.conditions


def test_projection_paths_round_trip_through_taxonomy() -> None:
    projected = StructuredTariffProjector().project(
        accepted_snapshot("mortgage"), display_name="Synthetic offering"
    )
    assert all(
        FieldPath(fact.field_path.value) is fact.field_path for fact in projected.facts
    )
    assert all(unit.renderer_version == RENDERER_VERSION for unit in projected.units)
    detail_units = [
        unit for unit in projected.units if unit.kind is RetrievalUnitKind.FIELD_DETAIL
    ]
    rate_unit = next(
        unit
        for unit in detail_units
        if FieldPath.NOMINAL_RATE_MINIMUM in unit.field_paths
    )
    # Retrieval text carries the human field label as well as the canonical path.
    assert "minimum nominal interest rate" in rate_unit.detail_text
    assert "rate.nominal.minimum" in rate_unit.detail_text
    assert "նվազագույն անվանական տոկոսադրույք" in rate_unit.alias_purpose_text
    assert "նվազագույն" not in rate_unit.content
    assert all(
        set(unit.evidence_ids)
        <= {
            evidence.evidence_id
            for fact in projected.facts
            if fact.fact_id in unit.fact_ids
            for evidence in fact.evidence
        }
        for unit in projected.units
    )


def test_projection_rejects_citation_url_that_disagrees_with_locator() -> None:
    snapshot = accepted_snapshot("consumer")
    extraction = deepcopy(snapshot.semantic_extraction)
    extraction["loan_product"]["interest_rate"]["evidence"][0]["source_url"] = (
        "https://ameriabank.am/other"
    )
    changed = snapshot.model_copy(update={"semantic_extraction": extraction})
    with pytest.raises(ValueError, match="URL/type disagrees"):
        StructuredTariffProjector().project(changed, display_name="Synthetic offering")


def test_profile_unit_contains_only_evidence_backed_identity_fields() -> None:
    projected = StructuredTariffProjector().project(
        accepted_snapshot("consumer"), display_name="Synthetic offering"
    )
    profile_unit = next(
        unit for unit in projected.units if unit.kind is RetrievalUnitKind.PROFILE
    )
    assert profile_unit.fact_ids
    assert profile_unit.evidence_ids
    assert all(path.value.startswith("identity.") for path in profile_unit.field_paths)
    assert "<" not in profile_unit.content


def test_salary_customer_condition_is_explicit_and_evidence_backed() -> None:
    projection = StructuredTariffProjector().project(
        accepted_snapshot("consumer"), display_name="Synthetic offering"
    )
    privileges = [
        fact
        for fact in projection.facts
        if fact.field_path is FieldPath.SALARY_PRIVILEGE
    ]
    assert len(privileges) == 1
    assert "Salary" in privileges[0].value
    assert privileges[0].evidence
