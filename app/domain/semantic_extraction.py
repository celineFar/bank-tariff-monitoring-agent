from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.source_discovery import Authority, InformationRole, TemporalStatus

T = TypeVar("T")


class ExtractionModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ExtractionStatus(StrEnum):
    FOUND = "found"
    NOT_STATED = "not_stated"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"


class LoanCategory(StrEnum):
    CONSUMER_LOAN = "consumer_loan"
    OVERDRAFT = "overdraft"
    CREDIT_LINE = "credit_line"
    MORTGAGE = "mortgage"


class RateType(StrEnum):
    FIXED = "fixed"
    VARIABLE = "variable"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class RateBasis(StrEnum):
    ANNUAL = "annual"
    MONTHLY = "monthly"


class PropertyMarket(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    COMMERCIAL = "commercial"
    CONSTRUCTION = "construction"
    RENOVATION = "renovation"
    MIXED = "mixed"
    NOT_APPLICABLE = "not_applicable"


class Condition(ExtractionModel):
    dimension: str = Field(min_length=1, max_length=200)
    operator: str | None = Field(default=None, max_length=50)
    value: str = Field(min_length=1, max_length=1000)


class ConditionalValue(ExtractionModel, Generic[T]):
    value: T
    conditions: tuple[Condition, ...] = Field(default=(), max_length=30)


class MoneyRange(ExtractionModel):
    min: Decimal | None = Field(default=None, ge=0)
    max: Decimal | None = Field(default=None, ge=0)
    currency: Literal["AMD", "USD", "EUR"] | None = None

    @model_validator(mode="after")
    def validate_range(self) -> MoneyRange:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("money minimum must not exceed maximum")
        if self.min is None and self.max is None:
            raise ValueError("money range requires a minimum or maximum")
        return self


class AbsoluteMoneyRange(ExtractionModel):
    type: Literal["absolute"] = "absolute"
    range: MoneyRange


class SalaryMultiple(ExtractionModel):
    type: Literal["salary_multiple"] = "salary_multiple"
    min_multiple: Decimal | None = Field(default=None, ge=0)
    max_multiple: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> SalaryMultiple:
        if self.min_multiple is None and self.max_multiple is None:
            raise ValueError("salary multiple requires a minimum or maximum")
        if (
            self.min_multiple is not None
            and self.max_multiple is not None
            and self.min_multiple > self.max_multiple
        ):
            raise ValueError("salary multiple minimum must not exceed maximum")
        return self


class PropertyValuePercentage(ExtractionModel):
    type: Literal["property_value_percentage"] = "property_value_percentage"
    min_pct: Decimal | None = Field(default=None, ge=0, le=100)
    max_pct: Decimal | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_range(self) -> PropertyValuePercentage:
        if self.min_pct is None and self.max_pct is None:
            raise ValueError("property percentage requires a minimum or maximum")
        if (
            self.min_pct is not None
            and self.max_pct is not None
            and self.min_pct > self.max_pct
        ):
            raise ValueError("property percentage minimum must not exceed maximum")
        return self


class OtherAmountFormula(ExtractionModel):
    type: Literal["other_formula"] = "other_formula"
    expression: str = Field(min_length=1, max_length=2000)


LoanAmount = Annotated[
    AbsoluteMoneyRange
    | SalaryMultiple
    | PropertyValuePercentage
    | OtherAmountFormula,
    Field(discriminator="type"),
]


class Rate(ExtractionModel):
    min: Decimal | None = Field(default=None, ge=0)
    max: Decimal | None = Field(default=None, ge=0)
    rate_type: RateType = RateType.UNKNOWN
    basis: RateBasis = RateBasis.ANNUAL

    @model_validator(mode="after")
    def validate_range(self) -> Rate:
        if self.min is None and self.max is None:
            raise ValueError("rate requires a minimum or maximum")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("rate minimum must not exceed maximum")
        return self


class TermRange(ExtractionModel):
    min_months: int | None = Field(default=None, gt=0)
    max_months: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> TermRange:
        if self.min_months is None and self.max_months is None:
            raise ValueError("term requires a minimum or maximum")
        if (
            self.min_months is not None
            and self.max_months is not None
            and self.min_months > self.max_months
        ):
            raise ValueError("term minimum must not exceed maximum")
        return self


class EvidenceCitation(ExtractionModel):
    evidence_id: str = Field(pattern=r"^ev_[0-9a-f]{24}$")
    source_item_id: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl
    source_type: SourceType
    quote: str = Field(min_length=1, max_length=1500)
    section: str | None = Field(default=None, max_length=1000)
    locator: SourceLocator
    authority: Authority


class ExtractedValue(ExtractionModel, Generic[T]):
    value: T | None = None
    evidence: tuple[EvidenceCitation, ...] = Field(default=(), max_length=100)
    status: ExtractionStatus
    explanation: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_state(self) -> ExtractedValue[T]:
        if self.status is ExtractionStatus.FOUND:
            if self.value is None or not self.evidence:
                raise ValueError("found value requires value and evidence")
        elif self.status is ExtractionStatus.NOT_STATED:
            if self.value is not None or self.evidence:
                raise ValueError("not_stated requires no value or evidence")
        elif not self.evidence:
            raise ValueError("ambiguous/conflicting value requires evidence")
        return self


class ConsumerLoanDetails(ExtractionModel):
    type: Literal["consumer_loan"] = "consumer_loan"
    collateral: ExtractedValue[tuple[str, ...]]
    income_verification_required: ExtractedValue[bool]


class MortgageDetails(ExtractionModel):
    type: Literal["mortgage"] = "mortgage"
    property_market: ExtractedValue[PropertyMarket]
    down_payment_pct: ExtractedValue[tuple[ConditionalValue[Decimal], ...]]
    ltv_pct: ExtractedValue[tuple[ConditionalValue[Decimal], ...]]
    collateral: ExtractedValue[tuple[str, ...]]
    income_verification_required: ExtractedValue[bool]
    property_requirements: ExtractedValue[tuple[str, ...]]


class OverdraftDetails(ExtractionModel):
    type: Literal["overdraft"] = "overdraft"
    credit_limit: ExtractedValue[tuple[LoanAmount, ...]]
    grace_period_days: ExtractedValue[int]
    revolving: ExtractedValue[bool]
    linked_account_or_card: ExtractedValue[str]


class CreditLineDetails(ExtractionModel):
    type: Literal["credit_line"] = "credit_line"
    credit_limit: ExtractedValue[tuple[LoanAmount, ...]]
    grace_period_days: ExtractedValue[int]
    revolving: ExtractedValue[bool]


LoanDetails = Annotated[
    ConsumerLoanDetails | MortgageDetails | OverdraftDetails | CreditLineDetails,
    Field(discriminator="type"),
]


class LoanProduct(ExtractionModel):
    product_name: ExtractedValue[str]
    category: LoanCategory
    purpose: ExtractedValue[tuple[str, ...]]
    loan_amount: ExtractedValue[tuple[ConditionalValue[LoanAmount], ...]]
    interest_rate: ExtractedValue[tuple[ConditionalValue[Rate], ...]]
    effective_rate: ExtractedValue[tuple[ConditionalValue[Rate], ...]]
    term: ExtractedValue[tuple[ConditionalValue[TermRange], ...]]
    fees: ExtractedValue[tuple[str, ...]]
    repayment: ExtractedValue[tuple[str, ...]]
    eligibility: ExtractedValue[tuple[str, ...]]
    residency_requirements: ExtractedValue[tuple[str, ...]]
    age_requirements: ExtractedValue[str]
    application_channel: ExtractedValue[tuple[str, ...]]
    required_documents: ExtractedValue[tuple[str, ...]]
    special_conditions: ExtractedValue[tuple[str, ...]]
    details: LoanDetails
    canonical_url: HttpUrl
    retrieved_at: datetime


class ExtractionField(StrEnum):
    PRODUCT_NAME = "product_name"
    CATEGORY = "category"
    PURPOSE = "purpose"
    LOAN_AMOUNT = "loan_amount"
    INTEREST_RATE = "interest_rate"
    EFFECTIVE_RATE = "effective_rate"
    TERM = "term"
    FEES = "fees"
    REPAYMENT = "repayment"
    ELIGIBILITY = "eligibility"
    RESIDENCY_REQUIREMENTS = "residency_requirements"
    AGE_REQUIREMENTS = "age_requirements"
    APPLICATION_CHANNEL = "application_channel"
    REQUIRED_DOCUMENTS = "required_documents"
    SPECIAL_CONDITIONS = "special_conditions"
    COLLATERAL = "collateral"
    INCOME_VERIFICATION_REQUIRED = "income_verification_required"
    PROPERTY_MARKET = "property_market"
    DOWN_PAYMENT_PCT = "down_payment_pct"
    LTV_PCT = "ltv_pct"
    PROPERTY_REQUIREMENTS = "property_requirements"
    CREDIT_LIMIT = "credit_limit"
    GRACE_PERIOD_DAYS = "grace_period_days"
    REVOLVING = "revolving"
    LINKED_ACCOUNT_OR_CARD = "linked_account_or_card"


class EvidenceItem(ExtractionModel):
    evidence_id: str = Field(pattern=r"^ev_[0-9a-f]{24}$")
    document_id: str
    source_item_id: str
    content: str = Field(min_length=1)
    section: str | None = None
    role: InformationRole
    authority: Authority
    temporal_status: TemporalStatus
    precedence: int = Field(ge=1)
    conditions: tuple[str, ...] = ()
    locator: SourceLocator


class ModelCitation(ExtractionModel):
    evidence_id: str = Field(pattern=r"^ev_[0-9a-f]{24}$")
    quote: str = Field(min_length=1, max_length=1500)


class ModelFieldResult(ExtractionModel):
    field: ExtractionField
    status: ExtractionStatus
    value_json: str | None = Field(default=None, max_length=50_000)
    evidence: tuple[ModelCitation, ...] = Field(default=(), max_length=20)
    explanation: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_state(self) -> ModelFieldResult:
        if self.status is ExtractionStatus.FOUND:
            if self.value_json is None or not self.evidence:
                raise ValueError("found model result requires value and evidence")
        elif self.status is ExtractionStatus.NOT_STATED:
            if self.value_json is not None or self.evidence:
                raise ValueError("not_stated model result requires no value or evidence")
        elif not self.evidence:
            raise ValueError("ambiguous/conflicting model result requires evidence")
        return self


class ExtractionBatch(ExtractionModel):
    id: str
    product: ProductType
    group: str
    fields: tuple[ExtractionField, ...] = Field(min_length=1)
    evidence: tuple[EvidenceItem, ...] = Field(min_length=1)
    content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExtractionBatchResponse(ExtractionModel):
    results: tuple[ModelFieldResult, ...] = Field(min_length=1)


class SemanticExtractionPlan(ExtractionModel):
    product: ProductType
    canonical_url: HttpUrl
    input_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: str
    prompt_version: str
    model_name: str
    evidence_catalog: tuple[EvidenceItem, ...]
    batches: tuple[ExtractionBatch, ...]
    cache_hits: tuple[ExtractionBatchResponse, ...] = ()


class SemanticExtractionResult(ExtractionModel):
    product: ProductType
    model_name: str
    loan_product: LoanProduct
    evidence_catalog: tuple[EvidenceItem, ...]
    batch_results: tuple[ExtractionBatchResponse, ...]
    reused_batch_count: int = Field(ge=0)
