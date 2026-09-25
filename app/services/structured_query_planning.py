"""Deterministic, bounded query shape derived from resolved catalog scope."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.domain.catalog import normalize_catalog_term
from app.domain.intent import IntentResolution
from app.domain.models import OfferingId, ProductType
from app.domain.structured_tariffs import (
    FieldPath,
    QueryOperation,
    RankDirection,
    ResolutionPlan,
)

_CORE = (
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
_RULES: tuple[tuple[tuple[str, ...], tuple[FieldPath, ...]], ...] = (
    (
        ("amount", "borrow", "loan size", "գումար", "չափ"),
        (
            FieldPath.AMOUNT_MINIMUM,
            FieldPath.AMOUNT_MAXIMUM,
            FieldPath.CREDIT_LIMIT_MINIMUM,
            FieldPath.CREDIT_LIMIT_MAXIMUM,
        ),
    ),
    (
        ("nominal", "անվանական"),
        (FieldPath.NOMINAL_RATE_MINIMUM, FieldPath.NOMINAL_RATE_MAXIMUM),
    ),
    (
        ("effective", "փաստացի"),
        (FieldPath.EFFECTIVE_RATE_MINIMUM, FieldPath.EFFECTIVE_RATE_MAXIMUM),
    ),
    (
        ("interest", "rate", "տոկոս", "տոկոսադրույք"),
        (
            FieldPath.NOMINAL_RATE_MINIMUM,
            FieldPath.NOMINAL_RATE_MAXIMUM,
            FieldPath.EFFECTIVE_RATE_MINIMUM,
            FieldPath.EFFECTIVE_RATE_MAXIMUM,
        ),
    ),
    (
        ("term", "repayment", "ժամկետ", "մարում"),
        (
            FieldPath.TERM_MINIMUM_MONTHS,
            FieldPath.TERM_MAXIMUM_MONTHS,
            FieldPath.REPAYMENT_METHOD,
        ),
    ),
    (
        # A tariff sheet is not one fee, so generic tariff words stay on the
        # core field set instead of narrowing to fee paths.
        ("fee", "charge", "վճար"),
        (
            FieldPath.FEE_APPLICATION,
            FieldPath.FEE_DISBURSEMENT,
            FieldPath.FEE_SERVICE,
            FieldPath.FEE_ORIGINATION,
            FieldPath.FEE_EARLY_REPAYMENT,
            FieldPath.FEE_INSURANCE,
            FieldPath.FEE_OTHER,
        ),
    ),
    (("salary", "payroll", "աշխատավարձ"), (FieldPath.SALARY_PRIVILEGE,)),
    (
        ("collateral", "security", "գրավ", "ապահով"),
        (FieldPath.COLLATERAL_REQUIREMENT, FieldPath.COLLATERAL_ALTERNATIVE),
    ),
    (
        ("down payment", "initial contribution", "կանխավճար", "նախնական վճար"),
        (
            FieldPath.DOWN_PAYMENT_MINIMUM,
            FieldPath.DOWN_PAYMENT_MAXIMUM,
            FieldPath.COLLATERAL_ALTERNATIVE,
        ),
    ),
    (
        ("currency", "currencies", "արժույթ"),
        (
            FieldPath.AMOUNT_MINIMUM,
            FieldPath.AMOUNT_MAXIMUM,
            FieldPath.NOMINAL_RATE_MINIMUM,
            FieldPath.EFFECTIVE_RATE_MINIMUM,
        ),
    ),
    (
        ("purpose", "use", "used for", "նպատակ"),
        (FieldPath.PURPOSE, FieldPath.VARIANT_PURPOSE),
    ),
)
_RANK_LOW = ("lowest", "smallest", "cheapest", "ամենացածր", "ամենափոքր")
_RANK_HIGH = ("highest", "largest", "longest", "ամենաբարձր", "ամենամեծ", "ամենաերկար")
_COMPARE = ("compare", "differ", "difference", "versus", " vs ", "համեմատ", "տարբեր")
_HISTORY = (
    "changed since",
    "what changed",
    "tariff changes",
    "փոփոխվել",
    "փոփոխություն",
)


def _has(query: str, words: tuple[str, ...]) -> bool:
    return any(normalize_catalog_term(word) in query for word in words)


@dataclass(frozen=True)
class QuerySelection:
    product: ProductType
    offering_ids: tuple[OfferingId, ...]
    operation: QueryOperation
    fields: tuple[FieldPath, ...]
    conditions: dict[str, str]
    rank_direction: RankDirection | None = None


def select_tariff_query(query: str, resolution: IntentResolution) -> QuerySelection:
    """Use only the resolver's family/IDs; never infer a new product ID from text."""
    if resolution.needs_clarification or resolution.product is None:
        raise ValueError("tariff query requires resolved, unambiguous product scope")
    return select_typed_query(
        query,
        product=resolution.product,
        offering_ids=resolution.offering_ids
        or ((resolution.offering_id,) if resolution.offering_id is not None else ()),
    )


def select_typed_query(
    query: str,
    *,
    product: ProductType,
    offering_ids: tuple[OfferingId, ...] = (),
) -> QuerySelection:
    """Derive the same bounded shape from an already-typed caller scope."""
    normalized = normalize_catalog_term(query)
    ids = offering_ids or tuple(item for item in OfferingId if item.product is product)
    if any(item.product is not product for item in ids):
        raise ValueError("query scope exceeds resolved product family")
    if _has(normalized, _HISTORY):
        operation = QueryOperation.HISTORY
        direction = None
    elif len(ids) > 1 and _has(normalized, _COMPARE):
        operation = QueryOperation.COMPARE
        direction = None
    elif len(ids) > 1 and _has(normalized, _RANK_LOW + _RANK_HIGH):
        operation = QueryOperation.FAMILY_RANK
        direction = (
            RankDirection.LOWEST
            if _has(normalized, _RANK_LOW)
            else RankDirection.HIGHEST
        )
    elif len(ids) > 1:
        raise ValueError("multi-offering query requires comparison or rank intent")
    else:
        operation = QueryOperation.SINGLE
        direction = None
    selected = tuple(
        dict.fromkeys(
            field
            for terms, fields in _RULES
            if _has(normalized, terms)
            for field in fields
        )
    )
    if not selected and operation is not QueryOperation.HISTORY:
        selected = _CORE
    if operation is QueryOperation.FAMILY_RANK:
        if _has(normalized, ("fee", "charge", "վճար")):
            selected = (FieldPath.FEE_APPLICATION,)
        elif _has(normalized, ("term", "repayment", "ժամկետ")):
            selected = (FieldPath.TERM_MAXIMUM_MONTHS,)
        elif _has(normalized, ("amount", "borrow", "գումար", "չափ")):
            selected = (FieldPath.AMOUNT_MAXIMUM,)
        elif _has(normalized, ("effective", "փաստացի")):
            selected = (FieldPath.EFFECTIVE_RATE_MINIMUM,)
        else:
            selected = (FieldPath.NOMINAL_RATE_MINIMUM,)
    currencies = [
        currency
        for currency in ("AMD", "USD", "EUR")
        if currency.lower() in normalized.split()
    ]
    conditions = {"currency": currencies[0]} if len(currencies) == 1 else {}
    return QuerySelection(
        product=product,
        offering_ids=ids,
        operation=operation,
        fields=selected[:20],
        conditions=conditions,
        rank_direction=direction,
    )


def issue_resolution_plan(
    query: str,
    resolution: IntentResolution,
    *,
    session_id: str,
    turn_id: str,
    issued_at: datetime | None = None,
) -> ResolutionPlan:
    return _plan(
        query,
        select_tariff_query(query, resolution),
        session_id=session_id,
        turn_id=turn_id,
        issued_at=issued_at,
    )


def issue_read_grant(
    query: str,
    resolution: IntentResolution,
    *,
    history: bool,
    session_id: str,
    turn_id: str,
    issued_at: datetime | None = None,
) -> ResolutionPlan:
    """The per-turn read grant every business-data read tool consumes (§6.6).

    When the resolver's scope yields an answerable query shape, the grant is
    exactly that plan, so `answer_tariff_query` behaves as before. Otherwise
    (a broad family question, or no family named where the resolver allows
    that) the grant is scope-only: CURRENT, or HISTORY for change questions,
    with no fields. Scope always comes from the resolver, never from text the
    model supplies.
    """
    if resolution.needs_clarification:
        raise ValueError("a read grant requires a resolved scope")
    if resolution.product is not None:
        try:
            return issue_resolution_plan(
                query,
                resolution,
                session_id=session_id,
                turn_id=turn_id,
                issued_at=issued_at,
            )
        except ValueError:
            pass
        offering_ids = resolution.offering_ids or (
            (resolution.offering_id,)
            if resolution.offering_id is not None
            else tuple(
                item for item in OfferingId if item.product is resolution.product
            )
        )
    else:
        offering_ids = ()
    current = issued_at or datetime.now(UTC)
    return ResolutionPlan(
        session_id=session_id,
        turn_id=turn_id,
        question_sha256=hashlib.sha256(query.encode("utf-8")).hexdigest(),
        issued_at=current,
        expires_at=current + timedelta(minutes=30),
        product=resolution.product,
        offering_ids=offering_ids,
        operation=QueryOperation.HISTORY if history else QueryOperation.CURRENT,
    )


def issue_typed_resolution_plan(
    query: str,
    *,
    product: ProductType,
    offering_ids: tuple[OfferingId, ...] = (),
    session_id: str,
    turn_id: str,
    issued_at: datetime | None = None,
) -> ResolutionPlan:
    """Build the same authorization plan for a typed API caller without a session."""
    return _plan(
        query,
        select_typed_query(query, product=product, offering_ids=offering_ids),
        session_id=session_id,
        turn_id=turn_id,
        issued_at=issued_at,
    )


def _plan(
    query: str,
    selection: QuerySelection,
    *,
    session_id: str,
    turn_id: str,
    issued_at: datetime | None = None,
) -> ResolutionPlan:
    current = issued_at or datetime.now(UTC)
    return ResolutionPlan(
        session_id=session_id,
        turn_id=turn_id,
        question_sha256=hashlib.sha256(query.encode("utf-8")).hexdigest(),
        issued_at=current,
        expires_at=current + timedelta(minutes=30),
        product=selection.product,
        offering_ids=selection.offering_ids,
        operation=selection.operation,
        rank_direction=selection.rank_direction,
        fields=selection.fields,
        conditions=selection.conditions,
    )
