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
    REVIEW_PENDING_CANDIDATES = "review_pending_candidates"


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
    continuation_intent: RequestIntent | None = None
    language: RequestLanguage
    normalized_query: str = Field(min_length=1, max_length=1000)
    method: ResolutionMethod
    product: ProductType | None = None
    offering_id: OfferingId | None = None
    offering_ids: tuple[OfferingId, ...] = ()
    candidates: tuple[ResolutionCandidate, ...] = ()
    needs_clarification: bool = False
    expects_single_value: bool = False

    @model_validator(mode="after")
    def validate_resolution(self) -> IntentResolution:
        if self.product is None and self.offering_id is not None:
            raise ValueError("offering_id requires product")
        if self.product is not None:
            validate_offering_product(self.product, self.offering_id)
        if len(set(self.offering_ids)) != len(self.offering_ids):
            raise ValueError("duplicate resolved offering IDs")
        if self.offering_ids and self.product is None:
            raise ValueError("resolved offering IDs require product")
        if any(item.product is not self.product for item in self.offering_ids):
            raise ValueError("resolved offering outside product family")
        if (
            self.offering_id is not None
            and self.offering_ids
            and (self.offering_ids != (self.offering_id,))
        ):
            raise ValueError("single and multiple offering scopes disagree")
        if self.needs_clarification:
            if self.method is not ResolutionMethod.CLARIFICATION:
                raise ValueError("clarification requires clarification method")
            if len(self.candidates) < 2:
                raise ValueError("clarification requires at least two candidates")
            if self.product is not None or self.offering_id is not None:
                raise ValueError("ambiguous resolution cannot select a scope")
        elif self.method is ResolutionMethod.CLARIFICATION:
            raise ValueError("clarification method requires needs_clarification")
        if self.intent is RequestIntent.CLARIFICATION_RESPONSE:
            if self.continuation_intent in {
                None,
                RequestIntent.CLARIFICATION_RESPONSE,
            }:
                raise ValueError(
                    "clarification response requires a continuation intent"
                )
        elif self.continuation_intent is not None:
            raise ValueError(
                "continuation_intent is only valid for clarification responses"
            )
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


class ConversationResolutionState(IntentModel):
    introduction_shown: bool = False
    pending_clarification: PendingClarification | None = None
    latest_product: ProductType | None = None
    latest_offering_id: OfferingId | None = None
    latest_offering_ids: tuple[OfferingId, ...] = ()

    @model_validator(mode="after")
    def validate_scope(self) -> ConversationResolutionState:
        if self.latest_product is None and self.latest_offering_id is not None:
            raise ValueError("latest_offering_id requires latest_product")
        if self.latest_product is not None:
            validate_offering_product(
                self.latest_product,
                self.latest_offering_id,
            )
        if any(
            item.product is not self.latest_product for item in self.latest_offering_ids
        ):
            raise ValueError("latest offering outside product family")
        return self


class ResolutionTurn(IntentModel):
    resolution: IntentResolution
    state: ConversationResolutionState


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
    # A subset of the family, from a chat read grant; empty = no subset filter.
    offering_ids: tuple[OfferingId, ...] = ()
    start_at: datetime | None = None
    end_at: datetime | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_query(self) -> HistoryQuery:
        if self.product is None and (self.offering_id is not None or self.offering_ids):
            raise ValueError("offering_id requires product")
        if self.product is not None:
            validate_offering_product(self.product, self.offering_id)
            for offering in self.offering_ids:
                validate_offering_product(self.product, offering)
        if self.offering_id is not None and self.offering_ids:
            raise ValueError("use offering_id or offering_ids, not both")
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
