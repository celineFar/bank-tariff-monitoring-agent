"""Tool policy the model cannot argue with.

The prompt says how to talk; this plugin decides what may run. Every business
tool needs a `resolve_request` from the same invocation, and a failing tool
becomes a typed envelope instead of an exception the model has to interpret.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from app.tools._state import RESOLUTION_KEY

logger = logging.getLogger(__name__)

BUSINESS_TOOLS = frozenset(
    {
        "get_current_tariffs",
        "get_tariff_history",
        "answer_tariff_query",
        "run_tariff_monitoring",
        "review_pending_candidates",
        "get_monitoring_status",
    }
)


class ToolPolicyPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="tool_policy")

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict[str, Any] | None:
        """Reject a business tool unless this invocation resolved the request.

        A resumed invocation keeps its id, so the replay of a monitoring call
        after a review pause passes the same check it passed the first time.
        """
        if tool.name not in BUSINESS_TOOLS:
            return None
        resolution = tool_context.state.get(RESOLUTION_KEY) or {}
        invocation = getattr(tool_context, "invocation_id", None)
        if not isinstance(resolution, dict) or (
            not invocation or resolution.get("invocation_id") != invocation
        ):
            return {
                "status": "rejected",
                "reason_code": "policy.resolve_first",
                "message": "Call resolve_request for this message first.",
            }
        return None

    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        """Turn a tool failure into a typed envelope the model can report.

        ADK's pause (`NodeInterruptedError`) and cancellation (`CancelledError`)
        are `BaseException`s and never reach this callback; the guard below
        keeps that true if a future version routes them here.
        """
        if isinstance(error, asyncio.CancelledError):  # pragma: no cover
            return None
        logger.error(
            "tool %s failed: %s", tool.name, type(error).__name__, exc_info=error
        )
        return {
            "status": "error",
            "reason_code": "tool.exception",
            "error_type": type(error).__name__,
        }
