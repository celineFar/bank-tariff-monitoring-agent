"""`resolve_request`: the only tool that decides scope, and the grants it issues."""

from __future__ import annotations

from collections import Counter

from google.adk.tools import ToolContext

from app.domain.intent import ConversationResolutionState, RequestIntent
from app.domain.interpretation import OfferKind, PendingOffer
from app.domain.review import ReviewStatus
from app.services.intent_resolution import InterpretationUnavailable
from app.services.interpretation_validation import offer_accepted
from app.services.structured_query_planning import issue_read_grant
from app.tools._services import services
from app.tools._state import (
    FULL_PRODUCT_ACK_KEY,
    MONITOR_AUTHORIZATION_KEY,
    MONITOR_OFFER_KEY,
    MONITORING_ANSWER_REQUEST_KEY,
    RESOLUTION_KEY,
    RESOLUTION_RESULT_KEY,
    RESOLUTION_STATE_KEY,
    TARIFF_PLAN_KEY,
    TARIFF_PLAN_USED_KEY,
    current_user_text,
    invocation_id,
    resolution_record,
    tariff_session_id,
    tariff_turn_id,
)

_READ_INTENTS = frozenset(
    {
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        RequestIntent.GET_CURRENT_TARIFFS,
        RequestIntent.GET_CHANGE_HISTORY,
    }
)
_ANSWERED_AFTER_RUN = frozenset(
    {
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        RequestIntent.GET_CURRENT_TARIFFS,
    }
)


async def resolve_request(tool_context: ToolContext) -> dict[str, object]:
    """Resolve this message's intent and scope; starts no business work.

    Reads the user's message itself. Call it once per message: a repeat call
    in the same turn returns the same result.
    """
    if services.request_resolver is None:
        return {"status": "unavailable", "reason_code": "intent.service_unavailable"}
    invocation = invocation_id(tool_context)
    stored = tool_context.state.get(RESOLUTION_RESULT_KEY)
    if (
        invocation is not None
        and isinstance(stored, dict)
        and stored.get("invocation_id") == invocation
    ):
        # Once per turn (RR13): a repeat call neither re-interprets nor
        # touches the grants the first call issued.
        return stored["result"]
    user_text = current_user_text(tool_context)
    if not user_text or not user_text.strip():
        return {"status": "rejected", "reason_code": "intent.no_user_message"}

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
    pending_offer = _pending_offer(offer, previous_invocation)

    try:
        turn = await services.request_resolver.resolve_turn(
            user_text, state, pending_offer=pending_offer
        )
    except InterpretationUnavailable:
        # Nothing is granted and the offer stays for a retry of the same reply.
        return _remember(
            tool_context,
            invocation,
            {
                "status": "unavailable",
                "reason_code": "intent.interpretation_unavailable",
            },
        )

    # Each resolution replaces any prior business-data authorization, and an
    # offer lives for one turn only.
    tool_context.state[TARIFF_PLAN_KEY] = None
    tool_context.state[TARIFF_PLAN_USED_KEY] = False
    tool_context.state[MONITOR_AUTHORIZATION_KEY] = None
    tool_context.state[MONITOR_OFFER_KEY] = None
    tool_context.state[RESOLUTION_STATE_KEY] = turn.state.model_dump(mode="json")
    resolution = turn.resolution
    resolved_intent = resolution.continuation_intent or resolution.intent
    tool_context.state[RESOLUTION_KEY] = {
        "invocation_id": invocation,
        "previous_invocation_id": (
            previous_invocation if isinstance(previous_invocation, str) else None
        ),
        "intent": resolved_intent.value,
        "product": resolution.product.value if resolution.product else None,
        "offering_id": resolution.offering_id.value if resolution.offering_id else None,
    }
    result = resolution.model_dump(mode="json")

    # The spend grant (V4): an explicit monitoring request for a resolved
    # scope, or an explicit yes to the offer made in the previous turn.
    accepted = offer_accepted(resolution, pending_offer)
    if accepted and pending_offer is not None:
        tool_context.state[MONITOR_AUTHORIZATION_KEY] = {
            "product": pending_offer.product.value,
            "offering_id": (
                pending_offer.offering_id.value if pending_offer.offering_id else None
            ),
            "invocation_id": invocation,
        }
        if pending_offer.kind is OfferKind.SCOPE_CONFIRMATION:
            # The family-wide run is confirmed for this turn (and its replays).
            tool_context.state[FULL_PRODUCT_ACK_KEY] = {
                "product": pending_offer.product.value,
                "invocation_id": invocation,
                "confirmed": True,
            }
        result["refresh_confirmation"] = True
    elif (
        resolved_intent is RequestIntent.START_MONITORING_RUN
        and not resolution.needs_clarification
        and resolution.product is not None
    ):
        tool_context.state[MONITOR_AUTHORIZATION_KEY] = {
            "product": resolution.product.value,
            "offering_id": (
                resolution.offering_id.value if resolution.offering_id else None
            ),
            "invocation_id": invocation,
        }
        # A fresh monitoring request answers no earlier question.
        tool_context.state[MONITORING_ANSWER_REQUEST_KEY] = None

    if resolved_intent in _ANSWERED_AFTER_RUN and not resolution.needs_clarification:
        tool_context.state[MONITORING_ANSWER_REQUEST_KEY] = {
            "question": resolution.standalone_question,
            "product": resolution.product.value if resolution.product else None,
            "offering_ids": [
                item.value
                for item in resolution.offering_ids
                or ((resolution.offering_id,) if resolution.offering_id else ())
            ],
            "shape": (
                resolution.query.model_dump(mode="json") if resolution.query else None
            ),
        }

    if resolved_intent in _READ_INTENTS and not resolution.needs_clarification:
        try:
            plan = issue_read_grant(
                resolution,
                question=resolution.standalone_question or user_text.strip()[:1000],
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
    return _remember(tool_context, invocation, result)


def _pending_offer(offer: object, previous_invocation: object) -> PendingOffer | None:
    """The offer or scope question from the previous turn, and only that one."""
    if (
        not isinstance(offer, dict)
        or not isinstance(previous_invocation, str)
        or offer.get("invocation_id") != previous_invocation
    ):
        return None
    try:
        return PendingOffer(
            kind=OfferKind(offer.get("kind") or OfferKind.MONITORING.value),
            product=offer.get("product"),
            offering_id=offer.get("offering_id"),
        )
    except ValueError:
        return None


def _remember(
    tool_context: ToolContext, invocation: str | None, result: dict[str, object]
) -> dict[str, object]:
    if invocation is not None:
        tool_context.state[RESOLUTION_RESULT_KEY] = {
            "invocation_id": invocation,
            "result": result,
        }
    return result


async def _pending_review_counts() -> dict[str, int]:
    """Pending reviews per offering, so the agent can mention them unprompted."""
    if services.reviews is None:
        return {}
    try:
        tasks = await services.reviews.list(status=ReviewStatus.PENDING, limit=500)
    except Exception:
        return {}
    return dict(Counter(task.offering_id.value for task in tasks))
