"""Deterministic comparability rules for accepted tariff extrema."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.domain.semantic_extraction import RateBasis
from app.domain.structured_tariffs import FieldPath


class IncomparabilityReason(StrEnum):
    DIFFERENT_FIELD = "different_field"
    UNSUPPORTED_FIELD = "unsupported_field"
    MISSING_NUMBER = "missing_number"
    DIFFERENT_CURRENCY = "different_currency"
    DIFFERENT_RATE_BASIS = "different_rate_basis"
    DIFFERENT_UNIT = "different_unit"
    DIFFERENT_FEE_SCOPE = "different_fee_scope"
    UNCLASSIFIED_FEE = "unclassified_fee"


RANKABLE_PATHS = frozenset(
    {
        FieldPath.AMOUNT_MINIMUM,
        FieldPath.AMOUNT_MAXIMUM,
        FieldPath.NOMINAL_RATE_MINIMUM,
        FieldPath.NOMINAL_RATE_MAXIMUM,
        FieldPath.EFFECTIVE_RATE_MINIMUM,
        FieldPath.EFFECTIVE_RATE_MAXIMUM,
        FieldPath.TERM_MINIMUM_MONTHS,
        FieldPath.TERM_MAXIMUM_MONTHS,
        FieldPath.DOWN_PAYMENT_MINIMUM,
        FieldPath.DOWN_PAYMENT_MAXIMUM,
        FieldPath.LTV_MINIMUM,
        FieldPath.LTV_MAXIMUM,
        FieldPath.CREDIT_LIMIT_MINIMUM,
        FieldPath.CREDIT_LIMIT_MAXIMUM,
        FieldPath.GRACE_PERIOD_DAYS,
        FieldPath.FEE_APPLICATION,
        FieldPath.FEE_DISBURSEMENT,
        FieldPath.FEE_SERVICE,
        FieldPath.FEE_ORIGINATION,
        FieldPath.FEE_EARLY_REPAYMENT,
        FieldPath.FEE_INSURANCE,
    }
)


class ComparableMeasure(BaseModel):
    model_config = ConfigDict(frozen=True)

    field_path: FieldPath
    number: Decimal | None
    unit: str
    currency: str | None = None
    rate_basis: RateBasis | None = None
    fee_scope: str | None = None
    conditions: tuple[str, ...] = ()


def comparison_issue(
    left: ComparableMeasure, right: ComparableMeasure
) -> IncomparabilityReason | None:
    """Return why two disclosed scalar values cannot share one numeric ranking."""
    if left.field_path is not right.field_path:
        return IncomparabilityReason.DIFFERENT_FIELD
    if left.field_path is FieldPath.FEE_OTHER:
        return IncomparabilityReason.UNCLASSIFIED_FEE
    if left.field_path not in RANKABLE_PATHS:
        return IncomparabilityReason.UNSUPPORTED_FIELD
    if left.number is None or right.number is None:
        return IncomparabilityReason.MISSING_NUMBER
    if left.unit != right.unit:
        return IncomparabilityReason.DIFFERENT_UNIT
    if left.currency != right.currency:
        return IncomparabilityReason.DIFFERENT_CURRENCY
    if left.rate_basis != right.rate_basis:
        return IncomparabilityReason.DIFFERENT_RATE_BASIS
    if left.fee_scope != right.fee_scope:
        return IncomparabilityReason.DIFFERENT_FEE_SCOPE
    return None
