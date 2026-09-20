from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import validate_offering_product


class IntentModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class RequestIntent(StrEnum):
    LIST_SUPPORTED_PRODUCTS = "list_supported_products"
    ANSWER_INDEXED_TARIFF_QUESTION = "answer_indexed_tariff_question"
    GET_CURRENT_TARIFFS = "get_current_tariffs"
    START_MONITORING_RUN = "start_monitoring_run"
    GET_RUN_STATUS = "get_run_status"
    GET_CHANGE_HISTORY = "get_change_history"
    UNSUPPORTED_OR_GENERAL = "unsupported_or_general"
    CLARIFICATION_RESPONSE = "clarification_response"


class RequestLanguage(StrEnum):
    ENGLISH = "en"
    ARMENIAN = "hy"
    MIXED = "mixed"


class ResolutionMethod(StrEnum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    GEMINI = "gemini"
    CLARIFICATION = "clarification"
    UNRESOLVED = "unresolved"


class ResolutionScope(StrEnum):
    FAMILY = "family"
    OFFERING = "offering"


class ResolutionCandidate(IntentModel):
    candidate_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    scope: ResolutionScope
    product: ProductType
    offering_id: OfferingId | None = None
    score: float = Field(ge=0.0, le=1.0)
    matched_term: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_scope(self) -> ResolutionCandidate:
        validate_offering_product(self.product, self.offering_id)
        if self.scope is ResolutionScope.OFFERING and self.offering_id is None:
            raise ValueError("offering candidate requires offering_id")
        if self.scope is ResolutionScope.FAMILY and self.offering_id is not None:
            raise ValueError("family candidate cannot contain offering_id")
        expected_id = (
            self.offering_id.value
            if self.offering_id is not None
            else self.product.value
        )
        if self.candidate_id != expected_id:
            raise ValueError("candidate_id must match the canonical scope identifier")
        return self


class IntentResolution(IntentModel):
    intent: RequestIntent
    language: RequestLanguage
    normalized_query: str = Field(min_length=1, max_length=1000)
    method: ResolutionMethod
    product: ProductType | None = None
    offering_id: OfferingId | None = None
    candidates: tuple[ResolutionCandidate, ...] = ()
    needs_clarification: bool = False

    @model_validator(mode="after")
    def validate_resolution(self) -> IntentResolution:
        if self.product is None and self.offering_id is not None:
            raise ValueError("offering_id requires product")
        if self.product is not None:
            validate_offering_product(self.product, self.offering_id)
        if self.needs_clarification:
            if self.method is not ResolutionMethod.CLARIFICATION:
                raise ValueError("clarification requires clarification method")
            if len(self.candidates) < 2:
                raise ValueError("clarification requires at least two candidates")
            if self.product is not None or self.offering_id is not None:
                raise ValueError("ambiguous resolution cannot select a scope")
        elif self.method is ResolutionMethod.CLARIFICATION:
            raise ValueError("clarification method requires needs_clarification")
        return self


class ClarificationOption(IntentModel):
    option_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    product: ProductType
    offering_id: OfferingId | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> ClarificationOption:
        validate_offering_product(self.product, self.offering_id)
        return self


class PendingClarification(IntentModel):
    original_query: str = Field(min_length=1, max_length=1000)
    intent: RequestIntent
    language: RequestLanguage
    options: tuple[ClarificationOption, ...] = Field(min_length=2, max_length=20)
    created_at: datetime

    @model_validator(mode="after")
    def validate_state(self) -> PendingClarification:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("clarification timestamp must be timezone-aware")
        option_ids = [option.option_id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("clarification option IDs must be unique")
        return self


class FreshnessStatus(StrEnum):
    MISSING = "missing"
    FRESH = "fresh"
    STALE = "stale"


class FreshnessPolicy(IntentModel):
    max_age_days: int = Field(default=7, ge=1, le=365)


class HistoryRequestKind(StrEnum):
    WHAT_CHANGED = "what_changed"
    SHOW_HISTORY = "show_history"


class HistoryPolicy(IntentModel):
    recent_change_days: int = Field(default=60, ge=1, le=3650)
    default_history_days: int = Field(default=30, ge=1, le=3650)
    max_results: int = Field(default=100, ge=1, le=1000)


class HistoryQuery(IntentModel):
    kind: HistoryRequestKind
    product: ProductType | None = None
    offering_id: OfferingId | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_query(self) -> HistoryQuery:
        if self.product is None and self.offering_id is not None:
            raise ValueError("offering_id requires product")
        if self.product is not None:
            validate_offering_product(self.product, self.offering_id)
        for value in (self.start_at, self.end_at):
            if value is not None and (
                value.tzinfo is None or value.utcoffset() is None
            ):
                raise ValueError("history timestamps must be timezone-aware")
        if (
            self.start_at is not None
            and self.end_at is not None
            and self.end_at < self.start_at
        ):
            raise ValueError("history end_at must not precede start_at")
        return self
