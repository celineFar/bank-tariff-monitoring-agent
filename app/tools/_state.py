"""Session-state keys and helpers shared by the tools.

Grants (plan §6.6) are written by `resolve_request` and bound to an ADK
invocation id: a resumed invocation keeps its id, so a grant survives the
replay of its own tool call but is useless in any later turn.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from google.adk.tools import ToolContext

RESOLUTION_STATE_KEY = "intent_resolution"
# {"invocation_id", "previous_invocation_id", "intent", "product", "offering_id"}
RESOLUTION_KEY = "resolution"
# {"invocation_id", "result"}: a repeat call in the same turn returns it (RR13).
RESOLUTION_RESULT_KEY = "resolution_result"
TARIFF_PLAN_KEY = "tariff_resolution_plan"  # the read grant
TARIFF_PLAN_USED_KEY = "tariff_resolution_plan_used"
TARIFF_SESSION_KEY = "tariff_resolution_session_id"
MONITOR_AUTHORIZATION_KEY = "monitoring_authorization"  # the spend grant
# {"kind": "monitoring" | "scope_confirmation", "product", "offering_id",
#  "invocation_id"}: answerable in the next turn only.
MONITOR_OFFER_KEY = "monitoring_confirmation_offer"
FULL_PRODUCT_ACK_KEY = "monitoring_full_product_ack"
# {"question", "product", "offering_ids", "shape"}: what a monitoring run
# answers when it finishes (the standalone question, its scope and shape).
MONITORING_ANSWER_REQUEST_KEY = "monitoring_answer_request"


def invocation_id(tool_context: ToolContext) -> str | None:
    value = getattr(tool_context, "invocation_id", None)
    return value if isinstance(value, str) and value else None


def current_user_text(tool_context: ToolContext) -> str | None:
    session = getattr(tool_context, "session", None)
    if session is None:
        return None
    invocation = getattr(tool_context, "invocation_id", None)
    for event in reversed(list(getattr(session, "events", ()) or ())):
        if getattr(event, "author", None) != "user":
            continue
        if invocation and getattr(event, "invocation_id", None) != invocation:
            continue
        parts = getattr(getattr(event, "content", None), "parts", ()) or ()
        values = [
            part.text for part in parts if isinstance(getattr(part, "text", None), str)
        ]
        if values:
            return "".join(values)
    return ""


def tariff_session_id(tool_context: ToolContext) -> str:
    session = getattr(tool_context, "session", None)
    session_id = getattr(session, "id", None)
    if isinstance(session_id, str) and session_id:
        return session_id
    saved = tool_context.state.get(TARIFF_SESSION_KEY)
    if isinstance(saved, str) and saved:
        return saved
    generated = str(uuid4())
    tool_context.state[TARIFF_SESSION_KEY] = generated
    return generated


def tariff_turn_id(tool_context: ToolContext) -> str:
    return invocation_id(tool_context) or str(uuid4())


def resolution_record(tool_context: ToolContext) -> dict[str, Any]:
    raw = tool_context.state.get(RESOLUTION_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def issued_this_turn(grant: object, tool_context: ToolContext) -> bool:
    """A grant is valid only inside the invocation that issued it."""
    current = invocation_id(tool_context)
    return (
        isinstance(grant, dict)
        and current is not None
        and grant.get("invocation_id") == current
    )
