from datetime import UTC, datetime

from app.domain.change_detection import compare_snapshots
from app.domain.models import LoanTariff, ProductType, TariffSnapshot, TariffValue


def _value(value: str) -> TariffValue:
    return TariffValue(status="FOUND", raw_value=value, normalized_value=value)


def _snapshot(rate: str) -> TariffSnapshot:
    missing = TariffValue(status="NOT_FOUND")
    return TariffSnapshot(
        product=ProductType.CONSUMER_LOAN,
        retrieved_at=datetime.now(UTC),
        tariff=LoanTariff(
            currency=_value("AMD"),
            term=missing,
            amount=missing,
            nominal_interest_rate=_value(rate),
            effective_interest_rate=missing,
            collateral=missing,
            application_fee=missing,
            disbursement_fee=missing,
            service_fee=missing,
            salary_customer_privileges=missing,
        ),
    )


def test_first_observation_is_not_a_change() -> None:
    assert compare_snapshots(None, _snapshot("12.5%")) == []


def test_only_changed_field_is_reported() -> None:
    changes = compare_snapshots(_snapshot("12.5%"), _snapshot("13.5%"))
    assert [change.field for change in changes] == ["nominal_interest_rate"]
