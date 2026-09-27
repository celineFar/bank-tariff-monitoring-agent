"""The read grant: a bounded query plan from a validated resolution (fix plan T3).

The plan's shape - operation, fields, rank, currency - comes from the request
interpreter, already checked by `InterpretationValidator`; its scope comes
from the resolution. This module only bounds and re-checks both. It reads no
words: the keyword planner (`_RULES`, `_has`) is gone (RR20, RR21, RR22).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from app.domain.intent import IntentResolution, RequestIntent
from app.domain.models import OfferingId, ProductType
from app.domain.query_shape import QueryShape
from app.domain.structured_tariffs import (
    FieldPath,
    QueryOperation,
    ResolutionPlan,
)
from app.domain.tariff_comparison import RANKABLE_PATHS

PLAN_LIFETIME = timedelta(minutes=30)

# What a listing answers when the question names no field and the field finder
# finds none: the headline terms of an offering.
CORE_FIELDS = (
    FieldPath.AMOUNT_MINIMUM,
    FieldPath.AMOUNT_MAXIMUM,
    FieldPath.NOMINAL_RATE_MINIMUM,
    FieldPath.NOMINAL_RATE_MAXIMUM,
    FieldPath.EFFECTIVE_RATE_MINIMUM,
    FieldPath.EFFECTIVE_RATE_MAXIMUM,
    FieldPath.TERM_MAXIMUM_MONTHS,
    FieldPath.FEE_APPLICATION,
    FieldPath.FEE_DISBURSEMENT,
    FieldPath.FEE_SERVICE,
    FieldPath.FEE_ORIGINATION,
    FieldPath.FEE_OTHER,
)
_READ_INTENTS = frozenset(
    {
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        RequestIntent.GET_CURRENT_TARIFFS,
        RequestIntent.GET_CHANGE_HISTORY,
    }
)


def issue_read_grant(
    resolution: IntentResolution,
    *,
    session_id: str,
    turn_id: str,
    question: str | None = None,
    issued_at: datetime | None = None,
) -> ResolutionPlan:
    """The per-turn read grant every business-data read tool consumes (§6.6).

    An answer question gets its validated shape. `get_current_tariffs` gets a
    scope-only CURRENT grant, and a history question a HISTORY grant, both of
    which may cover both families when no family was named. Scope always comes
    from the resolution, never from text the model supplies.
    """
    if resolution.needs_clarification:
        raise ValueError("a read grant requires a resolved scope")
    intent = resolution.continuation_intent or resolution.intent
    if intent not in _READ_INTENTS:
        raise ValueError(f"{intent.value} reads no tariff data")
    text = (question or resolution.standalone_question or "").strip()
    if not text:
        raise ValueError("a read grant requires the question of record")
    product = resolution.product
    offerings = resolution.offering_ids or (
        (resolution.offering_id,) if resolution.offering_id is not None else ()
    )
    if product is not None and not offerings:
        offerings = family_offerings(product)
    if intent is RequestIntent.GET_CHANGE_HISTORY:
        fields = resolution.query.fields if resolution.query is not None else ()
        return _plan(
            text,
            product=product,
            offering_ids=offerings,
            shape=QueryShape(operation=QueryOperation.HISTORY, fields=fields),
            session_id=session_id,
            turn_id=turn_id,
            issued_at=issued_at,
        )
    if intent is RequestIntent.GET_CURRENT_TARIFFS or resolution.query is None:
        return _plan(
            text,
            product=product,
            offering_ids=offerings,
            shape=None,
            session_id=session_id,
            turn_id=turn_id,
            issued_at=issued_at,
        )
    if product is None:
        raise ValueError("a tariff answer requires a resolved family")
    return issue_typed_plan(
        text,
        product=product,
        offering_ids=offerings,
        shape=resolution.query,
        session_id=session_id,
        turn_id=turn_id,
        issued_at=issued_at,
    )


def issue_typed_plan(
    question: str,
    *,
    product: ProductType,
    offering_ids: tuple[OfferingId, ...] = (),
    shape: QueryShape,
    session_id: str,
    turn_id: str,
    issued_at: datetime | None = None,
) -> ResolutionPlan:
    """A plan for a caller that already holds a typed scope and shape (the API,
    the after-run answer, demonstrations)."""
    ids = offering_ids or family_offerings(product)
    if any(item.product is not product for item in ids):
        raise ValueError("query scope exceeds resolved product family")
    operation = shape.operation
    if operation is QueryOperation.SINGLE and len(ids) > 1:
        operation = QueryOperation.OVERVIEW
    if operation in {QueryOperation.COMPARE, QueryOperation.OVERVIEW} and len(ids) == 1:
        operation = QueryOperation.SINGLE
    if operation is QueryOperation.FAMILY_RANK:
        rank_field = shape.rank_field or (shape.fields[0] if shape.fields else None)
        if (
            rank_field not in RANKABLE_PATHS
            or shape.rank_direction is None
            or len(ids) < 2
        ):
            raise ValueError("family rank requires one rankable field and a direction")
        shape = shape.model_copy(
            update={"fields": (rank_field,), "rank_field": rank_field}
        )
    return _plan(
        question,
        product=product,
        offering_ids=ids,
        shape=shape.model_copy(update={"operation": operation}),
        session_id=session_id,
        turn_id=turn_id,
        issued_at=issued_at,
    )


def family_offerings(product: ProductType) -> tuple[OfferingId, ...]:
    return tuple(item for item in OfferingId if item.product is product)


def _plan(
    question: str,
    *,
    product: ProductType | None,
    offering_ids: tuple[OfferingId, ...],
    shape: QueryShape | None,
    session_id: str,
    turn_id: str,
    issued_at: datetime | None,
) -> ResolutionPlan:
    current = issued_at or datetime.now(UTC)
    text = question.strip()[:1000]
    return ResolutionPlan(
        session_id=session_id,
        turn_id=turn_id,
        question_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        question=text,
        issued_at=current,
        expires_at=current + PLAN_LIFETIME,
        product=product,
        offering_ids=offering_ids,
        # No shape: a scope-only grant, which offerings the read tools may show.
        operation=shape.operation if shape is not None else QueryOperation.CURRENT,
        rank_direction=shape.rank_direction if shape is not None else None,
        fields=shape.fields if shape is not None else (),
        conditions=(
            {"currency": shape.currency.value}
            if shape is not None and shape.currency is not None
            else {}
        ),
    )
