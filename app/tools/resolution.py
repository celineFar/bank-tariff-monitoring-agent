"""`resolve_request`: the only tool that decides scope, and the grants it issues."""

from __future__ import annotations

from collections import Counter

from google.adk.tools import ToolContext

from app.domain.catalog import normalize_catalog_term
from app.domain.intent import ConversationResolutionState, RequestIntent
from app.domain.review import ReviewStatus
from app.services.structured_query_planning import issue_read_grant
from app.tools._services import services
from app.tools._state import (
    MONITOR_AUTHORIZATION_KEY,
    MONITOR_OFFER_KEY,
    ORIGINAL_QUESTION_KEY,
    RESOLUTION_KEY,
    RESOLUTION_STATE_KEY,
    TARIFF_LAST_USED_TURN_KEY,
    TARIFF_PLAN_KEY,
    TARIFF_PLAN_USED_KEY,
    current_user_text,
    invocation_id,
    issued_last_turn,
    resolution_record,
    tariff_session_id,
    tariff_turn_id,
)

AFFIRMATIVE_REPLIES = frozenset(
    {
        "yes",
        "yes please",
        "refresh",
        "go ahead",
        "yes go ahead",
        "confirm",
        "այո",
        "թարմացրու",
    }
)
_READ_INTENTS = frozenset(
    {
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        RequestIntent.GET_CURRENT_TARIFFS,
        RequestIntent.GET_CHANGE_HISTORY,
    }
)


async def resolve_request(
    query: str,
    tool_context: ToolContext,
) -> dict[str, object]:
    """Resolve intent and product/offering scope without starting business work."""
    if services.request_resolver is None:
        return {
            "status": "unavailable",
            "reason_code": "intent.service_unavailable",
        }
    invocation = invocation_id(tool_context)
    if invocation and tool_context.state.get(TARIFF_LAST_USED_TURN_KEY) == invocation:
        return {"status": "rejected", "reason_code": "intent.turn_already_used"}
    # Each resolution replaces any prior business-data authorization.
    tool_context.state[TARIFF_PLAN_KEY] = None
    tool_context.state[TARIFF_PLAN_USED_KEY] = False
    user_text = current_user_text(tool_context)
    if user_text is not None and query != user_text:
        return {"status": "rejected", "reason_code": "intent.query_mismatch"}
    previous = resolution_record(tool_context)
    previous_invocation = (
        previous.get("invocation_id")
        if previous.get("invocation_id") != invocation
        else previous.get("previous_invocation_id")
    )
    raw_state = tool_context.state.get(RESOLUTION_STATE_KEY)
    try:
        state = ConversationResolutionState.model_validate(raw_state or {})
    except ValueError:
        state = ConversationResolutionState()

    offer = tool_context.state.get(MONITOR_OFFER_KEY)
    tool_context.state[MONITOR_OFFER_KEY] = None
    if normalize_catalog_term(query) in AFFIRMATIVE_REPLIES and isinstance(offer, dict):
        _record_resolution(
            tool_context,
            invocation=invocation,
            previous_invocation=previous_invocation,
            intent=RequestIntent.START_MONITORING_RUN,
            product=offer.get("product"),
            offering_id=offer.get("offering_id"),
        )
        # Only the offer made in the turn just before this reply may be taken
        # up; an older offer authorizes nothing.
        if issued_last_turn(offer, tool_context):
            authorization = {
                "product": offer.get("product"),
                "offering_id": offer.get("offering_id"),
            }
            tool_context.state[MONITOR_AUTHORIZATION_KEY] = {
                **authorization,
                "invocation_id": invocation,
            }
            return {
                "intent": RequestIntent.START_MONITORING_RUN.value,
                "language": "hy" if any("Ա" <= char <= "ֆ" for char in query) else "en",
                "method": "exact",
                **authorization,
                "needs_clarification": False,
                "expects_single_value": False,
                "refresh_confirmation": True,
            }
    tool_context.state[MONITOR_AUTHORIZATION_KEY] = None

    turn = await services.request_resolver.resolve_turn(query, state)
    tool_context.state[RESOLUTION_STATE_KEY] = turn.state.model_dump(mode="json")
    resolution = turn.resolution
    resolved_intent = resolution.continuation_intent or resolution.intent
    _record_resolution(
        tool_context,
        invocation=invocation,
        previous_invocation=previous_invocation,
        intent=resolved_intent,
        product=resolution.product.value if resolution.product else None,
        offering_id=resolution.offering_id.value if resolution.offering_id else None,
    )
    if resolved_intent in {
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        RequestIntent.GET_CURRENT_TARIFFS,
    }:
        tool_context.state[ORIGINAL_QUESTION_KEY] = query
    elif resolved_intent is RequestIntent.START_MONITORING_RUN:
        tool_context.state[ORIGINAL_QUESTION_KEY] = None
    if (
        resolved_intent is RequestIntent.START_MONITORING_RUN
        and not resolution.needs_clarification
        and resolution.product is not None
    ):
        tool_context.state[MONITOR_AUTHORIZATION_KEY] = {
            "product": resolution.product.value,
            "offering_id": (
                resolution.offering_id.value
                if resolution.offering_id is not None
                else None
            ),
            "invocation_id": invocation,
        }
    result = resolution.model_dump(mode="json")
    if resolved_intent in _READ_INTENTS and not resolution.needs_clarification:
        try:
            plan = issue_read_grant(
                query,
                resolution,
                history=resolved_intent is RequestIntent.GET_CHANGE_HISTORY,
                session_id=tariff_session_id(tool_context),
                turn_id=tariff_turn_id(tool_context),
            )
        except ValueError:
            plan = None
        if plan is not None:
            tool_context.state[TARIFF_PLAN_KEY] = plan.model_dump(mode="json")
            result["query_plan"] = {
                "operation": plan.operation.value,
                "offering_ids": [item.value for item in plan.offering_ids],
                "fields": [item.value for item in plan.fields],
                "conditions": plan.conditions,
                "rank_direction": (
                    plan.rank_direction.value if plan.rank_direction else None
                ),
            }
    pending = await _pending_review_counts()
    if pending:
        result["pending_reviews"] = pending
    if not state.introduction_shown:
        result["catalog_intro"] = services.request_resolver.catalog_payload(
            resolution.language,
            complete=False,
        )
    if resolved_intent is RequestIntent.LIST_SUPPORTED_PRODUCTS:
        result["supported_catalog"] = services.request_resolver.catalog_payload(
            resolution.language,
            complete=True,
        )
    return result


def _record_resolution(
    tool_context: ToolContext,
    *,
    invocation: str | None,
    previous_invocation: object,
    intent: RequestIntent,
    product: object,
    offering_id: object,
) -> None:
    """What the plugin and the monitoring tools check: resolved, this turn."""
    tool_context.state[RESOLUTION_KEY] = {
        "invocation_id": invocation,
        "previous_invocation_id": (
            previous_invocation if isinstance(previous_invocation, str) else None
        ),
        "intent": intent.value,
        "product": product,
        "offering_id": offering_id,
    }


async def _pending_review_counts() -> dict[str, int]:
    """Pending reviews per offering, so the agent can mention them unprompted."""
    if services.reviews is None:
        return {}
    try:
        tasks = await services.reviews.list(status=ReviewStatus.PENDING, limit=500)
    except Exception:
        return {}
    return dict(Counter(task.offering_id.value for task in tasks))
