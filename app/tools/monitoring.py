"""Monitoring tools: thin, authorization-checking wrappers around the node.

The work itself — execute, stream progress, pause per review, apply, answer —
happens in `app/services/monitoring_node.py`, inside this tool's own call, so
the model sees one call and one result however many reviews came in between.
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

from google.adk.tools import ToolContext

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import RunStatus, RunTrigger
from app.domain.review import ReviewStatus
from app.tools._services import services
from app.tools._state import (
    FULL_PRODUCT_ACK_KEY,
    MONITOR_AUTHORIZATION_KEY,
    MONITOR_OFFER_KEY,
    ORIGINAL_QUESTION_KEY,
    invocation_id,
    issued_last_turn,
    issued_this_turn,
    resolution_record,
)

_ACTIVE = (RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.AWAITING_REVIEW)
_ORIGIN = {
    RunTrigger.ADK: "chat",
    RunTrigger.SCHEDULE: "scheduler",
    RunTrigger.API: "api",
    RunTrigger.USER: "api",
}


async def run_tariff_monitoring(
    product: Literal["consumer_loan", "mortgage"],
    offering_id: str | None,
    tool_context: ToolContext,
) -> dict[str, object]:
    """Monitor the official page for the resolved scope and answer from the result.

    Shows progress and asks the user for any review itself; returns once the
    run is finished.
    """
    if services.monitoring_node is None:
        return {
            "status": "unavailable",
            "product": product,
            "reason_code": "run.service_unavailable",
        }
    try:
        resolved_product = ProductType(product)
        resolved_offering = OfferingId(offering_id) if offering_id else None
        if (
            resolved_offering is not None
            and resolved_offering.product is not resolved_product
        ):
            raise ValueError("offering outside product family")
    except ValueError:
        return {
            "status": "rejected",
            "product": product,
            "offering_id": offering_id,
            "reason_code": "run.invalid_scope",
        }
    # The spend grant: issued by resolve_request in this invocation, for exactly
    # this scope. A resumed invocation keeps its id, so a replay still passes.
    authorization = tool_context.state.get(MONITOR_AUTHORIZATION_KEY)
    if not issued_this_turn(authorization, tool_context) or (
        authorization.get("product") != resolved_product.value
        or authorization.get("offering_id")
        != (resolved_offering.value if resolved_offering else None)
    ):
        return {
            "status": "rejected",
            "product": product,
            "offering_id": offering_id,
            "reason_code": "run.intent_not_authorized",
        }
    # An unscoped run fans out to every enabled offering in the product family,
    # so it costs a multiple of a single-offering run. Make that scope explicit
    # once before spending it: the question is asked in one turn and can only
    # be answered in the next, never by a second call in the same turn.
    if resolved_offering is None:
        acknowledged = tool_context.state.get(FULL_PRODUCT_ACK_KEY)
        same_product = (
            isinstance(acknowledged, dict)
            and acknowledged.get("product") == resolved_product.value
        )
        answered_now = same_product and issued_last_turn(acknowledged, tool_context)
        confirmed_now = (
            same_product
            and issued_this_turn(acknowledged, tool_context)
            and acknowledged.get("confirmed") is True
        )
        if not (answered_now or confirmed_now):
            family = tuple(
                item.value for item in OfferingId if item.product is resolved_product
            )
            question = {
                "product": resolved_product.value,
                "invocation_id": invocation_id(tool_context),
            }
            tool_context.state[FULL_PRODUCT_ACK_KEY] = {**question, "confirmed": False}
            # "yes" next turn re-issues the spend grant for this same scope.
            tool_context.state[MONITOR_OFFER_KEY] = {**question, "offering_id": None}
            return {
                "status": "needs_scope_confirmation",
                "product": product,
                "offering_id": None,
                "offering_count": len(family),
                "offerings": list(family),
                "reason_code": "run.full_product_scope",
            }
        # Bind the confirmation to this invocation, so the replay after each
        # review pause passes without asking again.
        tool_context.state[FULL_PRODUCT_ACK_KEY] = {
            "product": resolved_product.value,
            "invocation_id": invocation_id(tool_context),
            "confirmed": True,
        }
    tool_context.state[MONITOR_OFFER_KEY] = None
    question = tool_context.state.get(ORIGINAL_QUESTION_KEY)
    return await tool_context.run_node(
        services.monitoring_node,
        {
            "product": resolved_product.value,
            "offering_id": resolved_offering.value if resolved_offering else None,
            "question": question if isinstance(question, str) else None,
        },
    )


async def review_pending_candidates(
    tool_context: ToolContext,
    product: Literal["consumer_loan", "mortgage"] | None = None,
    offering_id: str | None = None,
) -> dict[str, object]:
    """Walk the user through candidates waiting for review, one at a time.

    Covers runs started elsewhere (the scheduler, the API) as well as this
    chat's. Reviewing starts no new monitoring run.
    """
    if services.monitoring_node is None:
        return {"status": "unavailable", "reason_code": "review.service_unavailable"}
    resolution = resolution_record(tool_context)
    if not issued_this_turn(resolution, tool_context):
        return {"status": "rejected", "reason_code": "policy.resolve_first"}
    # The scope may only narrow what the resolver resolved, never widen it.
    resolved_product = resolution.get("product")
    resolved_offering = resolution.get("offering_id")
    if (resolved_product is not None and product != resolved_product) or (
        resolved_offering is not None and offering_id != resolved_offering
    ):
        return {
            "status": "rejected",
            "product": product,
            "offering_id": offering_id,
            "reason_code": "review.scope_not_resolved",
        }
    return await tool_context.run_node(
        services.monitoring_node,
        {
            "product": product,
            "offering_id": offering_id,
            "review_only": True,
        },
    )


async def get_monitoring_status(tool_context: ToolContext) -> dict[str, object]:
    """Active runs, pending reviews and latest accepted time, for both families."""
    if services.runs is None:
        return {"status": "unavailable", "reason_code": "status.service_unavailable"}
    active: list[dict[str, object]] = []
    for status in _ACTIVE:
        for run in await services.runs.list_by_status(status, limit=50):
            executions = await services.runs.list_offering_executions(run.id)
            active.append(
                {
                    "product": run.command.product.value,
                    "offering_id": (
                        run.command.offering_id.value
                        if run.command.offering_id
                        else None
                    ),
                    "status": run.status.value,
                    "started_by": _ORIGIN.get(run.command.trigger, "api"),
                    "stages": {
                        item.offering_id.value: item.current_stage
                        for item in executions
                        if item.current_stage
                    },
                }
            )
    pending: dict[str, int] = {}
    if services.reviews is not None:
        tasks = await services.reviews.list(status=ReviewStatus.PENDING, limit=500)
        pending = dict(Counter(task.offering_id.value for task in tasks))
    accepted: dict[str, str | None] = {}
    if services.current_tariff_service is not None:
        current = await services.current_tariff_service.get_current()
        accepted = {
            item.offering_id.value: (
                item.accepted_at.isoformat() if item.accepted_at else None
            )
            for item in current.items
        }
    return {
        "status": "ok",
        "active_runs": active,
        "pending_reviews": pending,
        "latest_accepted_at": accepted,
    }
