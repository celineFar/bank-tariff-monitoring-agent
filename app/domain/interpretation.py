"""The request interpreter's contract (fix plan T1).

`InterpretationRequest` is what the tool-free Gemini call sees; its reply is a
`RequestInterpretation`, every value an enum or a bounded string. Code turns the
reply into an `IntentResolution` (`app.services.interpretation_validation`);
the interpretation itself authorizes nothing.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.intent import RequestIntent, RequestLanguage
from app.domain.models import OfferingId, ProductType
from app.domain.query_shape import Currency, QueryShape, ReplyKind

__all__ = [
    "Currency",
    "InterpretationClarification",
    "InterpretationContext",
    "InterpretationRequest",
    "InterpretedIntent",
    "OfferKind",
    "PendingClarificationView",
    "PendingOffer",
    "QueryShape",
    "ReplyKind",
    "RequestInterpretation",
    "ScopeView",
    "route_for",
]

MAX_QUESTION_CHARS = 1000


class InterpretedIntent(StrEnum):
    """`RequestIntent` without `clarification_response`: a reply to a
    clarification is marked by `replies_to`, never by an intent of its own."""

    LIST_SUPPORTED_PRODUCTS = RequestIntent.LIST_SUPPORTED_PRODUCTS.value
    ANSWER_INDEXED_TARIFF_QUESTION = RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION.value
    GET_CURRENT_TARIFFS = RequestIntent.GET_CURRENT_TARIFFS.value
    START_MONITORING_RUN = RequestIntent.START_MONITORING_RUN.value
    GET_RUN_STATUS = RequestIntent.GET_RUN_STATUS.value
    GET_CHANGE_HISTORY = RequestIntent.GET_CHANGE_HISTORY.value
    UNSUPPORTED_OR_GENERAL = RequestIntent.UNSUPPORTED_OR_GENERAL.value
    REVIEW_PENDING_CANDIDATES = RequestIntent.REVIEW_PENDING_CANDIDATES.value


class InterpretationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class OfferKind(StrEnum):
    MONITORING = "monitoring"
    SCOPE_CONFIRMATION = "scope_confirmation"


class ScopeView(InterpretationModel):
    product: ProductType
    offering_ids: tuple[OfferingId, ...] = ()


class OptionView(InterpretationModel):
    id: str
    label: str


class PendingClarificationView(InterpretationModel):
    question: str
    intent: RequestIntent
    options: tuple[OptionView, ...]


class PendingOffer(InterpretationModel):
    """An offer or question from the previous turn that a reply may answer."""

    kind: OfferKind
    product: ProductType
    offering_id: OfferingId | None = None


class InterpretationContext(InterpretationModel):
    conversation_language: RequestLanguage | None = None
    last_scope: ScopeView | None = None
    last_question: str | None = None
    pending_clarification: PendingClarificationView | None = None
    pending_offer: PendingOffer | None = None


class _OutputModel(BaseModel):
    # Part of the interpreter's response schema, which rejects additionalProperties.
    model_config = ConfigDict(frozen=True, extra="ignore")


class InterpretationClarification(_OutputModel):
    needed: bool = False
    option_ids: tuple[str, ...] = ()


class RequestInterpretation(_OutputModel):
    intent: InterpretedIntent
    replies_to: ReplyKind = ReplyKind.NONE
    accepts: bool | None = None
    language: RequestLanguage
    product: ProductType | None = None
    offering_ids: tuple[OfferingId, ...] = ()
    family_wide: bool = False
    standalone_question: str = ""
    query: QueryShape | None = None
    clarification: InterpretationClarification = Field(
        default_factory=InterpretationClarification
    )

    @field_validator("standalone_question")
    @classmethod
    def bound_question(cls, value: str) -> str:
        return value.strip()[:MAX_QUESTION_CHARS]

    @field_validator("offering_ids")
    @classmethod
    def unique_offerings(cls, value: tuple[OfferingId, ...]) -> tuple[OfferingId, ...]:
        return tuple(dict.fromkeys(value))

    @property
    def request_intent(self) -> RequestIntent:
        return RequestIntent(self.intent.value)


class InterpretationRequest(InterpretationModel):
    message: str
    context: InterpretationContext
    catalog: tuple[dict[str, object], ...]
    allowed: dict[str, object]


_ROUTES: dict[RequestIntent, str | None] = {
    RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION: "answer_tariff_query",
    RequestIntent.GET_CURRENT_TARIFFS: "get_current_tariffs",
    RequestIntent.GET_CHANGE_HISTORY: "get_tariff_history",
    RequestIntent.START_MONITORING_RUN: "run_tariff_monitoring",
    RequestIntent.REVIEW_PENDING_CANDIDATES: "review_pending_candidates",
    RequestIntent.GET_RUN_STATUS: "get_monitoring_status",
    RequestIntent.LIST_SUPPORTED_PRODUCTS: None,
    RequestIntent.UNSUPPORTED_OR_GENERAL: None,
    RequestIntent.CLARIFICATION_RESPONSE: None,
}


def route_for(intent: RequestIntent) -> str | None:
    """The tool that serves an intent (T2); code decides it, not the model."""
    return _ROUTES[intent]
