from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class ProductType(StrEnum):
    CONSUMER_LOAN = "consumer_loan"
    MORTGAGE = "mortgage"


class OfferingId(StrEnum):
    CONSUMER_STANDARD = "consumer_standard"
    OVERDRAFT = "overdraft"
    CREDIT_LINE = "credit_line"
    ONLINE_CONSUMER_FINANCE = "online_consumer_finance"
    MORTGAGE_ONLINE = "mortgage_online"
    MORTGAGE_PRIMARY = "mortgage_primary"
    MORTGAGE_DIASPORA = "mortgage_diaspora"
    MORTGAGE_SECONDARY_MARKET = "mortgage_secondary_market"
    MORTGAGE_COMMERCIAL = "mortgage_commercial"
    MORTGAGE_EXPRESS = "mortgage_express"
    MORTGAGE_NO_INCOME_VERIFICATION = "mortgage_no_income_verification"
    MORTGAGE_RENOVATION = "mortgage_renovation"
    MORTGAGE_CONSTRUCTION = "mortgage_construction"

    @property
    def product(self) -> ProductType:
        if self in {
            OfferingId.CONSUMER_STANDARD,
            OfferingId.OVERDRAFT,
            OfferingId.CREDIT_LINE,
            OfferingId.ONLINE_CONSUMER_FINANCE,
        }:
            return ProductType.CONSUMER_LOAN
        return ProductType.MORTGAGE


class KnowledgeDocumentKind(StrEnum):
    SOURCE = "source"
    OFFERING_SUMMARY = "offering_summary"


class ValueStatus(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"


class Evidence(BaseModel):
    source_url: HttpUrl
    document_name: str
    excerpt: str = Field(max_length=1000)
    page: int | None = Field(default=None, ge=1)
    section: str | None = None


class TariffValue(BaseModel):
    status: ValueStatus
    raw_value: str | None = None
    normalized_value: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class LoanTariff(BaseModel):
    currency: TariffValue
    term: TariffValue
    amount: TariffValue
    nominal_interest_rate: TariffValue
    effective_interest_rate: TariffValue
    collateral: TariffValue
    application_fee: TariffValue
    disbursement_fee: TariffValue
    service_fee: TariffValue
    salary_customer_privileges: TariffValue


class TariffSnapshot(BaseModel):
    bank: str = "ameria"
    product: ProductType
    retrieved_at: datetime
    tariff: LoanTariff


class TariffChange(BaseModel):
    field: str
    previous: str | None
    current: str | None
