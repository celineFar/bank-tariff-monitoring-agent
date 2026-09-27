"""The shape of a tariff question: what to read inside a granted scope.

Kept apart from `app.domain.intent` and `app.domain.interpretation` so both can
use it without an import cycle.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.structured_tariffs import FieldPath, QueryOperation, RankDirection

MAX_SHAPE_FIELDS = 20


class ReplyKind(StrEnum):
    """What pending question, if any, a message answers."""

    NONE = "none"
    CLARIFICATION = "clarification"
    MONITORING_OFFER = "monitoring_offer"
    SCOPE_CONFIRMATION = "scope_confirmation"


class Currency(StrEnum):
    AMD = "AMD"
    USD = "USD"
    EUR = "EUR"


# The operations an interpretation may propose. `current` is a scope-only grant
# that code issues for the get_current_tariffs intent, never a proposed shape.
SHAPE_OPERATIONS = frozenset(
    {
        QueryOperation.SINGLE,
        QueryOperation.COMPARE,
        QueryOperation.OVERVIEW,
        QueryOperation.FAMILY_RANK,
        QueryOperation.HISTORY,
    }
)


class QueryShape(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    operation: QueryOperation
    fields: tuple[FieldPath, ...] = Field(default=())
    rank_field: FieldPath | None = None
    rank_direction: RankDirection | None = None
    currency: Currency | None = None

    @field_validator("fields")
    @classmethod
    def bound_fields(cls, value: tuple[FieldPath, ...]) -> tuple[FieldPath, ...]:
        # Deduplicate and bound instead of failing: the list is a proposal.
        return tuple(dict.fromkeys(value))[:MAX_SHAPE_FIELDS]

    @model_validator(mode="after")
    def validate_operation(self) -> QueryShape:
        if self.operation not in SHAPE_OPERATIONS:
            raise ValueError(f"{self.operation.value} is not a question shape")
        return self
