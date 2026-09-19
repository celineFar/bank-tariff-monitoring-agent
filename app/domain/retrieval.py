from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.domain.models import KnowledgeDocumentKind, OfferingId, ProductType


class RetrievalModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class TariffField(StrEnum):
    AMOUNT = "amount"
    TERM = "term"
    NOMINAL_RATE = "nominal_rate"
    EFFECTIVE_RATE = "effective_rate"
    APPLICATION_FEE = "application_fee"
    DISBURSEMENT_FEE = "disbursement_fee"
    SERVICE_FEE = "service_fee"
    COLLATERAL = "collateral"
    SALARY_PRIVILEGES = "salary_privileges"


class RetrievalStatus(StrEnum):
    FOUND = "FOUND"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RetrievalRequest(RetrievalModel):
    query: str = Field(min_length=1, max_length=2000)
    bank: str = Field(min_length=1, max_length=100)
    product: ProductType
    fields: tuple[TariffField, ...] = Field(min_length=1)
    offering_id: OfferingId | None = None
    document_kinds: tuple[KnowledgeDocumentKind, ...] = ()

    @field_validator("query", "bank")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("fields")
    @classmethod
    def deduplicate_fields(
        cls, values: tuple[TariffField, ...]
    ) -> tuple[TariffField, ...]:
        return tuple(dict.fromkeys(values))


class RetrievalCandidate(RetrievalModel):
    chunk_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    lexical_score: float = Field(ge=0, le=1)
    vector_score: float = Field(ge=0, le=1)
    lexical_rank: int | None = Field(default=None, ge=1)
    vector_rank: int | None = Field(default=None, ge=1)
    document_id: UUID
    document_checksum: str = Field(min_length=64, max_length=64)
    document_name: str = Field(min_length=1)
    source_url: HttpUrl
    final_url: HttpUrl
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    section: str | None = None
    language: str = Field(min_length=2)
    retrieved_at: datetime
    extraction_method: str = Field(min_length=1)
    quality_score: float | None = Field(default=None, ge=0, le=1)
    offering_id: OfferingId | None = None
    document_kind: KnowledgeDocumentKind = KnowledgeDocumentKind.SOURCE


class RankExplanation(RetrievalModel):
    method: str = "weighted_rrf_plus_relevance"
    lexical_rank: int | None
    vector_rank: int | None
    lexical_weight: float
    vector_weight: float
    rrf_k: int
    rrf_score: float = Field(ge=0, le=1)
    relevance_score: float = Field(ge=0, le=1)
    formula: str


class RetrievalHit(RetrievalModel):
    chunk_id: str
    content: str
    lexical_score: float = Field(ge=0, le=1)
    vector_score: float = Field(ge=0, le=1)
    final_score: float = Field(ge=0, le=1)
    rank_explanation: RankExplanation
    document_id: UUID
    document_checksum: str
    document_name: str
    source_url: HttpUrl
    final_url: HttpUrl
    page_start: int | None
    page_end: int | None
    section: str | None
    language: str
    retrieved_at: datetime
    extraction_method: str
    quality_score: float | None

    offering_id: OfferingId | None = None
    document_kind: KnowledgeDocumentKind = KnowledgeDocumentKind.SOURCE


class RetrievalResult(RetrievalModel):
    status: RetrievalStatus
    hits: tuple[RetrievalHit, ...]
    reason: str | None = None
    candidates_considered: int = Field(ge=0)
