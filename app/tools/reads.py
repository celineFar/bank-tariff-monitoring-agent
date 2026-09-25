"""Business-data read tools. None of them takes a scope argument (plan §6.6).

Each reads the turn's `ResolutionPlan` (the read grant `resolve_request`
issued) and touches only the family and offerings named in it. The model can
choose *how* to read — the question text, a history window — but never *what*.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from google.adk.tools import ToolContext

from app.domain.intent import FreshnessStatus, HistoryQuery, HistoryRequestKind
from app.domain.structured_tariffs import ANSWERABLE_OPERATIONS, ResolutionPlan
from app.tools._services import services
from app.tools._state import (
    MONITOR_OFFER_KEY,
    TARIFF_LAST_USED_TURN_KEY,
    TARIFF_PLAN_KEY,
    TARIFF_PLAN_USED_KEY,
    invocation_id,
    tariff_session_id,
)


def _read_plan(
    tool_context: ToolContext, *, question: str | None = None
) -> ResolutionPlan | dict[str, object]:
    """The turn's read grant, or a rejection envelope.

    Checks session, turn and expiry; with `question`, also that it is the exact
    text the grant was issued for. Does not check or set the one-use flag.
    """
    raw = tool_context.state.get(TARIFF_PLAN_KEY)
    if not isinstance(raw, dict):
        return {"status": "rejected", "reason_code": "query.plan_absent"}
    try:
        plan = ResolutionPlan.model_validate(raw)
        if plan.session_id != tariff_session_id(tool_context):
            raise ValueError("session mismatch")
        invocation = invocation_id(tool_context)
        if invocation is not None and plan.turn_id != invocation:
            raise ValueError("turn mismatch")
        if (
            question is not None
            and hashlib.sha256(question.encode("utf-8")).hexdigest()
            != plan.question_sha256
        ):
            raise ValueError("question mismatch")
        if not plan.issued_at <= datetime.now(UTC) < plan.expires_at:
            raise ValueError("plan expired")
    except ValueError:
        return {"status": "rejected", "reason_code": "query.plan_invalid"}
    return plan


async def answer_tariff_query(
    query: str, tool_context: ToolContext
) -> dict[str, object]:
    """Read only the server-held per-turn scope from resolve_request."""
    if services.answer_router is None and services.structured_query_service is None:
        return {"status": "unavailable", "reason_code": "query.service_unavailable"}
    if isinstance(tool_context.state.get(TARIFF_PLAN_KEY), dict) and (
        tool_context.state.get(TARIFF_PLAN_USED_KEY)
    ):
        return {"status": "rejected", "reason_code": "query.plan_replayed"}
    plan = _read_plan(tool_context, question=query)
    if isinstance(plan, dict):
        return plan
    if plan.product is None or plan.operation not in ANSWERABLE_OPERATIONS:
        # A scope-only grant: there is no field shape to answer from.
        return {
            "status": "rejected",
            "reason_code": "query.scope_only_plan",
            "hint": "use get_current_tariffs or get_tariff_history for this scope",
        }
    tool_context.state[TARIFF_PLAN_USED_KEY] = True
    tool_context.state[TARIFF_LAST_USED_TURN_KEY] = plan.turn_id
    if services.answer_router is not None:
        result = await services.answer_router.answer_plan(plan, query)
    else:
        result = await services.structured_query_service.answer(plan, query)
    return result.model_dump(mode="json")


async def get_current_tariffs(tool_context: ToolContext) -> dict[str, object]:
    """Read latest accepted tariffs and freshness for this turn's resolved scope."""
    if services.current_tariff_service is None:
        return {"status": "unavailable", "reason_code": "current.service_unavailable"}
    plan = _read_plan(tool_context)
    if isinstance(plan, dict):
        return plan
    try:
        result = await services.current_tariff_service.get_current(
            product=plan.product,
            offering_ids=plan.offering_ids,
        )
    except ValueError:
        return {"status": "rejected", "reason_code": "current.invalid_scope"}
    missing = any(item.freshness is FreshnessStatus.MISSING for item in result.items)
    if missing and plan.product is not None:
        # The offer is computed from the grant, never from a tool argument, so
        # the scope of a later paid run cannot originate with the model.
        tool_context.state[MONITOR_OFFER_KEY] = {
            "product": plan.product.value,
            "offering_id": (
                plan.offering_ids[0].value if len(plan.offering_ids) == 1 else None
            ),
            "invocation_id": invocation_id(tool_context),
        }
    payload = result.model_dump(mode="json")
    if missing:
        # Demonstration artifacts under `end-to-end/` look like completed work
        # but never publish a snapshot, so say what "missing" actually means.
        payload["missing_means"] = (
            "no monitoring run has published an accepted snapshot for this "
            "offering yet; demonstration artifacts do not count"
        )
    return payload


async def get_tariff_history(
    kind: Literal["what_changed", "show_history"],
    tool_context: ToolContext,
    start_at: str | None = None,
    end_at: str | None = None,
    limit: int = 20,
) -> dict[str, object]:
    """Read accepted snapshot history or change sets for this turn's scope.

    The window and page size are clamped by the history service; the family
    and offerings come only from resolve_request.
    """
    if services.tariff_history_service is None:
        return {"status": "unavailable", "reason_code": "history.service_unavailable"}
    plan = _read_plan(tool_context)
    if isinstance(plan, dict):
        return plan
    try:
        query = HistoryQuery.model_validate(
            {
                "kind": HistoryRequestKind(kind),
                "product": plan.product,
                "offering_ids": plan.offering_ids,
                "start_at": start_at,
                "end_at": end_at,
                # A page size is a presentation choice: clamp it, never refuse.
                "limit": max(1, min(int(limit), 100)),
            }
        )
        result = await services.tariff_history_service.query(query)
    except ValueError:
        return {"status": "rejected", "reason_code": "history.invalid_query"}
    return result.model_dump(mode="json")
