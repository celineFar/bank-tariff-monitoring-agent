from __future__ import annotations

import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.acquisition import SourceType
from app.domain.models import ProductType
from app.domain.normalization import SourceReference
from app.domain.pdf_extraction import PdfAdmission

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DiscoveryModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ProductAssociation(StrEnum):
    CURRENT_PRODUCT = "current_product"
    HISTORICAL_VERSION = "historical_version"
    FUTURE_VERSION = "future_version"
    RELATED_PRODUCT = "related_product"
    GLOBAL_NAVIGATION = "global_navigation"
    GENERIC_BANK_INFORMATION = "generic_bank_information"
    UNKNOWN = "unknown"


class InformationRole(StrEnum):
    PRODUCT_TERMS = "product_terms"
    PRODUCT_DESCRIPTION = "product_description"
    ELIGIBILITY = "eligibility"
    PRICING = "pricing"
    FEES = "fees"
    REPAYMENT = "repayment"
    DOCUMENTS = "documents"
    FAQ = "faq"
    CAMPAIGN_TERMS = "campaign_terms"
    LEGAL_DISCLOSURE = "legal_disclosure"
    RELATED_PRODUCT = "related_product"
    NAVIGATION = "navigation"
    OTHER = "other"


class Relevance(StrEnum):
    RELEVANT = "relevant"
    POSSIBLY_RELEVANT = "possibly_relevant"
    IRRELEVANT = "irrelevant"


class Authority(StrEnum):
    OFFICIAL_TERMS = "official_terms"
    OFFICIAL_PRODUCT_CONTENT = "official_product_content"
    OFFICIAL_FAQ = "official_faq"
    OFFICIAL_CAMPAIGN_CONTENT = "official_campaign_content"
    MARKETING_CONTENT = "marketing_content"
    UNKNOWN = "unknown"


class TemporalStatus(StrEnum):
    CURRENT = "current"
    FUTURE = "future"
    TIME_BOUNDED = "time_bounded"
    POSSIBLY_STALE = "possibly_stale"
    UNKNOWN = "unknown"


class DecisionSource(StrEnum):
    RULE = "rule"
    CACHE = "cache"
    LAYOUT_PROFILE = "layout_profile"
    LLM = "llm"
    INHERITED = "inherited"
    HUMAN_OVERRIDE = "human_override"


class DiscoveryScope(StrEnum):
    DOCUMENT = "document"
    SECTION = "section"
    BLOCK = "block"
    TABLE = "table"
    API_PAYLOAD = "api_payload"


class EffectivePeriod(DiscoveryModel):
    raw: str = Field(min_length=1, max_length=1000)
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def validate_order(self) -> EffectivePeriod:
        if self.start and self.end and self.end < self.start:
            raise ValueError("effective period end must not precede start")
        return self


class DiscoveryCandidate(DiscoveryModel):
    source_id: str = Field(min_length=1, max_length=500)
    document_id: str = Field(min_length=1, max_length=200)
    scope: DiscoveryScope
    source_type: SourceType
    title: str = Field(default="", max_length=1000)
    heading_path: tuple[str, ...] = ()
    context_text: str = Field(min_length=1, max_length=12_000)
    mime_type: str = Field(min_length=1, max_length=255)
    extraction_method: str = Field(min_length=1, max_length=100)
    quality_score: float | None = Field(default=None, ge=0, le=1)
    member_source_ids: tuple[str, ...] = ()
    all_members_hidden: bool = False
    has_scalar_candidates: bool = False
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)
    content_fingerprint: str
    structural_fingerprint: str
    selection_reason: str = Field(min_length=1, max_length=1000)
    pdf_admission: PdfAdmission | None = None

    @model_validator(mode="after")
    def validate_fingerprints(self) -> DiscoveryCandidate:
        if not _SHA256.fullmatch(self.content_fingerprint):
            raise ValueError("content_fingerprint must be a lowercase SHA-256 digest")
        if not _SHA256.fullmatch(self.structural_fingerprint):
            raise ValueError("structural_fingerprint must be a lowercase SHA-256 digest")
        return self


class SourceAssessment(DiscoveryModel):
    source_id: str = Field(min_length=1, max_length=500)
    document_id: str = Field(min_length=1, max_length=200)
    scope: DiscoveryScope
    product_association: ProductAssociation
    role: InformationRole
    relevance: Relevance
    authority: Authority
    temporal_status: TemporalStatus
    effective_periods: tuple[EffectivePeriod, ...] = Field(default=(), max_length=20)
    conditions: tuple[str, ...] = Field(default=(), max_length=50)
    reason: str = Field(min_length=1, max_length=2000)
    decision_source: DecisionSource
    inherited_from: str | None = None
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    structural_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)


class PriorAssessment(DiscoveryModel):
    product_association: ProductAssociation
    role: InformationRole
    relevance: Relevance
    authority: Authority
    temporal_status: TemporalStatus
    effective_periods: tuple[EffectivePeriod, ...] = Field(default=(), max_length=20)
    conditions: tuple[str, ...] = Field(default=(), max_length=50)
    reason: str = Field(min_length=1, max_length=2000)


class DiscoveryPromptItem(DiscoveryModel):
    source_id: str
    scope: DiscoveryScope
    source_type: SourceType
    title: str
    heading_path: tuple[str, ...]
    content: str
    mime_type: str
    extraction_method: str
    quality_score: float | None
    prior_assessment: PriorAssessment | None = None


class DiscoveryBatch(DiscoveryModel):
    id: str
    product: ProductType
    items: tuple[DiscoveryPromptItem, ...] = Field(min_length=1)


class ModelSourceAssessment(DiscoveryModel):
    source_id: str
    product_association: ProductAssociation
    role: InformationRole
    relevance: Relevance
    authority: Authority
    temporal_status: TemporalStatus
    effective_periods: tuple[EffectivePeriod, ...] = Field(default=(), max_length=20)
    conditions: tuple[str, ...] = Field(default=(), max_length=50)
    reason: str = Field(min_length=1, max_length=2000)


class DiscoveryBatchResponse(DiscoveryModel):
    items: tuple[ModelSourceAssessment, ...] = Field(min_length=1)


class SourceDiscoveryPlan(DiscoveryModel):
    product: ProductType
    canonical_url: str
    input_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: str
    prompt_version: str
    model_name: str
    deterministic_assessments: tuple[SourceAssessment, ...] = ()
    cache_hits: tuple[SourceAssessment, ...] = ()
    llm_candidates: tuple[DiscoveryCandidate, ...] = ()
    batches: tuple[DiscoveryBatch, ...] = ()
    inherited_item_count: int = Field(default=0, ge=0)


class ExtractionContextItem(DiscoveryModel):
    source_id: str
    document_id: str
    scope: DiscoveryScope
    role: InformationRole
    authority: Authority
    temporal_status: TemporalStatus
    precedence: int = Field(ge=1)
    text: str = Field(min_length=1)
    conditions: tuple[str, ...] = ()
    effective_periods: tuple[EffectivePeriod, ...] = ()
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)


class ExtractionContext(DiscoveryModel):
    product: ProductType
    items: tuple[ExtractionContextItem, ...] = ()


class SourceDiscoveryResult(DiscoveryModel):
    product: ProductType
    input_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: str
    prompt_version: str
    model_name: str
    assessments: tuple[SourceAssessment, ...]
    extraction_context: ExtractionContext
    llm_batch_count: int = Field(ge=0)
    reused_assessment_count: int = Field(ge=0)
