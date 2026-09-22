"""Versioned contracts for accepted, evidence-linked tariff read projections."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue, model_validator

from app.domain.models import OfferingId, ProductType
from app.domain.semantic_extraction import ExtractionField, ExtractionStatus, RateBasis

FIELD_PATH_VERSION = 1


class FieldPath(StrEnum):
    PRODUCT_NAME = "identity.product_name"
    FORMAL_TERMS_NAME = "identity.formal_terms_name"
    CATEGORY = "identity.category"
    VARIANT_NAME = "identity.variant_name"
    VARIANT_PURPOSE = "identity.variant_purpose"
    PURPOSE = "identity.purpose"
    AMOUNT_MINIMUM = "amount.minimum"
    AMOUNT_MAXIMUM = "amount.maximum"
    AMOUNT_SALARY_MULTIPLE_MINIMUM = "amount.salary_multiple.minimum"
    AMOUNT_SALARY_MULTIPLE_MAXIMUM = "amount.salary_multiple.maximum"
    AMOUNT_PROPERTY_VALUE_MINIMUM = "amount.property_value_pct.minimum"
    AMOUNT_PROPERTY_VALUE_MAXIMUM = "amount.property_value_pct.maximum"
    AMOUNT_FORMULA = "amount.formula"
    NOMINAL_RATE_MINIMUM = "rate.nominal.minimum"
    NOMINAL_RATE_MAXIMUM = "rate.nominal.maximum"
    NOMINAL_RATE_FORMULA = "rate.nominal.formula"
    EFFECTIVE_RATE_MINIMUM = "rate.effective.minimum"
    EFFECTIVE_RATE_MAXIMUM = "rate.effective.maximum"
    EFFECTIVE_RATE_FORMULA = "rate.effective.formula"
    TERM_MINIMUM_MONTHS = "term.minimum_months"
    TERM_MAXIMUM_MONTHS = "term.maximum_months"
    TERM_INDEFINITE = "term.indefinite"
    TERM_END_CONDITION = "term.end_condition"
    FEE_APPLICATION = "fee.application"
    FEE_DISBURSEMENT = "fee.disbursement"
    FEE_SERVICE = "fee.service"
    FEE_ORIGINATION = "fee.origination"
    FEE_EARLY_REPAYMENT = "fee.early_repayment"
    FEE_INSURANCE = "fee.insurance"
    FEE_OTHER = "fee.other"
    REPAYMENT_METHOD = "repayment.method"
    ELIGIBILITY_REQUIREMENT = "eligibility.requirement"
    ELIGIBILITY_RESIDENCY = "eligibility.residency"
    ELIGIBILITY_AGE_MINIMUM = "eligibility.age.minimum"
    ELIGIBILITY_AGE_MAXIMUM = "eligibility.age.maximum"
    APPLICATION_CHANNEL = "application.channel"
    DOCUMENT_REQUIRED = "document.required"
    SPECIAL_CONDITION = "condition.special"
    SALARY_PRIVILEGE = "privilege.salary_customer"
    COLLATERAL_REQUIREMENT = "collateral.requirement"
    COLLATERAL_ALTERNATIVE = "collateral.alternative"
    INCOME_VERIFICATION_REQUIRED = "income_verification.required"
    CREDITWORTHINESS_REQUIRED = "creditworthiness_assessment.required"
    PROPERTY_MARKET = "mortgage.property_market"
    DOWN_PAYMENT_MINIMUM = "mortgage.down_payment.minimum_pct"
    DOWN_PAYMENT_MAXIMUM = "mortgage.down_payment.maximum_pct"
    LTV_MINIMUM = "mortgage.ltv.minimum_pct"
    LTV_MAXIMUM = "mortgage.ltv.maximum_pct"
    PROPERTY_REQUIREMENT = "mortgage.property_requirement"
    CREDIT_LIMIT_MINIMUM = "revolving.credit_limit.minimum"
    CREDIT_LIMIT_MAXIMUM = "revolving.credit_limit.maximum"
    CREDIT_LIMIT_SALARY_MULTIPLE_MINIMUM = (
        "revolving.credit_limit.salary_multiple.minimum"
    )
    CREDIT_LIMIT_SALARY_MULTIPLE_MAXIMUM = (
        "revolving.credit_limit.salary_multiple.maximum"
    )
    CREDIT_LIMIT_PROPERTY_VALUE_MINIMUM = (
        "revolving.credit_limit.property_value_pct.minimum"
    )
    CREDIT_LIMIT_PROPERTY_VALUE_MAXIMUM = (
        "revolving.credit_limit.property_value_pct.maximum"
    )
    CREDIT_LIMIT_FORMULA = "revolving.credit_limit.formula"
    GRACE_PERIOD_DAYS = "revolving.grace_period_days"
    REVOLVING_ENABLED = "revolving.enabled"
    LINKED_ACCOUNT_OR_CARD = "revolving.linked_account_or_card"


SOURCE_FIELD_PATHS: dict[ExtractionField, tuple[FieldPath, ...]] = {
    ExtractionField.PRODUCT_NAME: (FieldPath.PRODUCT_NAME,),
    ExtractionField.FORMAL_TERMS_NAMES: (FieldPath.FORMAL_TERMS_NAME,),
    ExtractionField.VARIANTS: (FieldPath.VARIANT_NAME, FieldPath.VARIANT_PURPOSE),
    ExtractionField.CATEGORY: (FieldPath.CATEGORY,),
    ExtractionField.PURPOSE: (FieldPath.PURPOSE,),
    ExtractionField.LOAN_AMOUNT: (
        FieldPath.AMOUNT_MINIMUM,
        FieldPath.AMOUNT_MAXIMUM,
        FieldPath.AMOUNT_SALARY_MULTIPLE_MINIMUM,
        FieldPath.AMOUNT_SALARY_MULTIPLE_MAXIMUM,
        FieldPath.AMOUNT_PROPERTY_VALUE_MINIMUM,
        FieldPath.AMOUNT_PROPERTY_VALUE_MAXIMUM,
        FieldPath.AMOUNT_FORMULA,
    ),
    ExtractionField.INTEREST_RATE: (
        FieldPath.NOMINAL_RATE_MINIMUM,
        FieldPath.NOMINAL_RATE_MAXIMUM,
        FieldPath.NOMINAL_RATE_FORMULA,
    ),
    ExtractionField.EFFECTIVE_RATE: (
        FieldPath.EFFECTIVE_RATE_MINIMUM,
        FieldPath.EFFECTIVE_RATE_MAXIMUM,
        FieldPath.EFFECTIVE_RATE_FORMULA,
    ),
    ExtractionField.TERM: (
        FieldPath.TERM_MINIMUM_MONTHS,
        FieldPath.TERM_MAXIMUM_MONTHS,
        FieldPath.TERM_INDEFINITE,
        FieldPath.TERM_END_CONDITION,
    ),
    ExtractionField.FEES: (
        FieldPath.FEE_APPLICATION,
        FieldPath.FEE_DISBURSEMENT,
        FieldPath.FEE_SERVICE,
        FieldPath.FEE_ORIGINATION,
        FieldPath.FEE_EARLY_REPAYMENT,
        FieldPath.FEE_INSURANCE,
        FieldPath.FEE_OTHER,
    ),
    ExtractionField.REPAYMENT: (FieldPath.REPAYMENT_METHOD,),
    ExtractionField.ELIGIBILITY: (FieldPath.ELIGIBILITY_REQUIREMENT,),
    ExtractionField.RESIDENCY_REQUIREMENTS: (FieldPath.ELIGIBILITY_RESIDENCY,),
    ExtractionField.AGE_REQUIREMENTS: (
        FieldPath.ELIGIBILITY_AGE_MINIMUM,
        FieldPath.ELIGIBILITY_AGE_MAXIMUM,
    ),
    ExtractionField.APPLICATION_CHANNEL: (FieldPath.APPLICATION_CHANNEL,),
    ExtractionField.REQUIRED_DOCUMENTS: (FieldPath.DOCUMENT_REQUIRED,),
    ExtractionField.SPECIAL_CONDITIONS: (FieldPath.SPECIAL_CONDITION,),
    ExtractionField.COLLATERAL: (
        FieldPath.COLLATERAL_REQUIREMENT,
        FieldPath.COLLATERAL_ALTERNATIVE,
    ),
    ExtractionField.INCOME_VERIFICATION_REQUIRED: (
        FieldPath.INCOME_VERIFICATION_REQUIRED,
    ),
    ExtractionField.CREDITWORTHINESS_ASSESSMENT_REQUIRED: (
        FieldPath.CREDITWORTHINESS_REQUIRED,
    ),
    ExtractionField.PROPERTY_MARKET: (FieldPath.PROPERTY_MARKET,),
    ExtractionField.DOWN_PAYMENT_PCT: (
        FieldPath.DOWN_PAYMENT_MINIMUM,
        FieldPath.DOWN_PAYMENT_MAXIMUM,
    ),
    ExtractionField.LTV_PCT: (FieldPath.LTV_MINIMUM, FieldPath.LTV_MAXIMUM),
    ExtractionField.PROPERTY_REQUIREMENTS: (FieldPath.PROPERTY_REQUIREMENT,),
    ExtractionField.CREDIT_LIMIT: (
        FieldPath.CREDIT_LIMIT_MINIMUM,
        FieldPath.CREDIT_LIMIT_MAXIMUM,
        FieldPath.CREDIT_LIMIT_SALARY_MULTIPLE_MINIMUM,
        FieldPath.CREDIT_LIMIT_SALARY_MULTIPLE_MAXIMUM,
        FieldPath.CREDIT_LIMIT_PROPERTY_VALUE_MINIMUM,
        FieldPath.CREDIT_LIMIT_PROPERTY_VALUE_MAXIMUM,
        FieldPath.CREDIT_LIMIT_FORMULA,
    ),
    ExtractionField.GRACE_PERIOD_DAYS: (FieldPath.GRACE_PERIOD_DAYS,),
    ExtractionField.REVOLVING: (FieldPath.REVOLVING_ENABLED,),
    ExtractionField.LINKED_ACCOUNT_OR_CARD: (FieldPath.LINKED_ACCOUNT_OR_CARD,),
}

if set(SOURCE_FIELD_PATHS) != set(ExtractionField):
    raise RuntimeError(
        "canonical field-path registry does not cover every extraction field"
    )

# Only explicit wording can assign a named category. Ambiguous/multiple matches stay OTHER.
_FEE_TERMS: dict[FieldPath, tuple[str, ...]] = {
    FieldPath.FEE_APPLICATION: ("application fee", "հայտի վճար", "դիմումի վճար"),
    FieldPath.FEE_DISBURSEMENT: ("disbursement fee", "տրամադրման վճար"),
    FieldPath.FEE_SERVICE: ("service fee", "սպասարկման վճար"),
    FieldPath.FEE_ORIGINATION: ("origination fee", "ձևակերպման վճար"),
    FieldPath.FEE_EARLY_REPAYMENT: ("early repayment fee", "վաղաժամկետ մարման վճար"),
    FieldPath.FEE_INSURANCE: ("insurance fee", "ապահովագրության վճար"),
}


def fee_field_path(description: str) -> FieldPath:
    normalized = " ".join(description.casefold().split())
    matches = tuple(
        path
        for path, phrases in _FEE_TERMS.items()
        if any(phrase in normalized for phrase in phrases)
    )
    return matches[0] if len(matches) == 1 else FieldPath.FEE_OTHER


class StructuredTariffModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class QueryOperation(StrEnum):
    SINGLE = "single"
    COMPARE = "compare"
    FAMILY_RANK = "family_rank"
    HISTORY = "history"


class QueryStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INCOMPARABLE = "incomparable"
    MISSING = "missing"


class ResolutionPlan(StructuredTariffModel):
    """Server-held, per-turn authorization for business-data scope."""

    session_id: str = Field(min_length=1)
    turn_id: str = Field(min_length=1)
    question_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    issued_at: datetime
    expires_at: datetime
    bank: str = "ameria"
    product: ProductType
    offering_ids: tuple[OfferingId, ...] = ()
    operation: QueryOperation
    fields: tuple[FieldPath, ...] = ()
    conditions: dict[str, JsonValue] = Field(default_factory=dict)
    taxonomy_version: int = FIELD_PATH_VERSION

    @model_validator(mode="after")
    def validate_scope(self) -> ResolutionPlan:
        if any(
            item.tzinfo is None or item.utcoffset() is None
            for item in (self.issued_at, self.expires_at)
        ):
            raise ValueError("plan timestamps must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("plan expiry must follow issue time")
        if self.taxonomy_version != FIELD_PATH_VERSION:
            raise ValueError("unsupported field-path version")
        if len(set(self.offering_ids)) != len(self.offering_ids):
            raise ValueError("duplicate offering IDs")
        if any(item.product is not self.product for item in self.offering_ids):
            raise ValueError("offering outside resolved product family")
        if self.operation is QueryOperation.SINGLE and len(self.offering_ids) != 1:
            raise ValueError("single query requires one offering")
        if self.operation is QueryOperation.COMPARE and len(self.offering_ids) < 2:
            raise ValueError("comparison requires at least two offerings")
        if (
            self.operation
            in {
                QueryOperation.SINGLE,
                QueryOperation.COMPARE,
                QueryOperation.FAMILY_RANK,
            }
            and not self.fields
        ):
            raise ValueError("tariff query requires canonical fields")
        return self


class FactEvidence(StructuredTariffModel):
    evidence_id: str = Field(pattern=r"^ev_[0-9a-f]{24}$")
    quote: str = Field(min_length=1)
    source_url: HttpUrl
    source_item_id: str = Field(min_length=1)
    locator: dict[str, JsonValue]
    document_id: UUID | None = None
    document_checksum: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def require_locator(self) -> FactEvidence:
        if not self.locator:
            raise ValueError("evidence requires a source locator")
        return self


class TariffFact(StructuredTariffModel):
    snapshot_id: UUID
    offering_id: OfferingId
    field_path: FieldPath
    variant_key: str = Field(min_length=1)
    status: ExtractionStatus
    value: JsonValue = None
    number: Decimal | None = None
    unit: str | None = None
    currency: str | None = None
    rate_basis: RateBasis | None = None
    conditions: tuple[dict[str, JsonValue], ...] = ()
    evidence: tuple[FactEvidence, ...] = ()
    taxonomy_version: int = FIELD_PATH_VERSION

    @model_validator(mode="after")
    def validate_evidence(self) -> TariffFact:
        if self.taxonomy_version != FIELD_PATH_VERSION:
            raise ValueError("unsupported field-path version")
        if self.status is ExtractionStatus.FOUND and (
            self.value is None or not self.evidence
        ):
            raise ValueError("found tariff fact requires value and evidence")
        if self.status is ExtractionStatus.NOT_STATED and (
            self.value is not None or self.evidence
        ):
            raise ValueError("not-stated fact cannot have value or evidence")
        return self


class TariffQueryResult(StructuredTariffModel):
    status: QueryStatus
    operation: QueryOperation
    product: ProductType
    offering_ids: tuple[OfferingId, ...]
    facts: tuple[TariffFact, ...] = ()
    answer: str | None = None
    reason: str | None = None
    as_of: datetime | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
