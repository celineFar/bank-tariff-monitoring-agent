from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class ProductType(StrEnum):
    CONSUMER_LOAN = "consumer_loan"
    MORTGAGE = "mortgage"


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
