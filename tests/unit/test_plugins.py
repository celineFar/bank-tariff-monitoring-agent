from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.plugins import BUSINESS_TOOLS, ToolPolicyPlugin


def _tool(name: str):
    return SimpleNamespace(name=name)


def _context(invocation_id: str = "turn-1", resolved_in: str | None = "turn-1"):
    state = {}
    if resolved_in is not None:
        state["resolution"] = {"invocation_id": resolved_in, "intent": "x"}
    return SimpleNamespace(state=state, invocation_id=invocation_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", sorted(BUSINESS_TOOLS))
async def test_business_tool_without_resolution_this_turn_is_rejected(name) -> None:
    plugin = ToolPolicyPlugin()

    never = await plugin.before_tool_callback(
        tool=_tool(name), tool_args={}, tool_context=_context(resolved_in=None)
    )
    earlier = await plugin.before_tool_callback(
        tool=_tool(name), tool_args={}, tool_context=_context(resolved_in="turn-0")
    )

    assert never["reason_code"] == "policy.resolve_first"
    assert earlier["reason_code"] == "policy.resolve_first"


@pytest.mark.asyncio
async def test_business_tool_resolved_this_invocation_passes() -> None:
    result = await ToolPolicyPlugin().before_tool_callback(
        tool=_tool("run_tariff_monitoring"), tool_args={}, tool_context=_context()
    )

    assert result is None


@pytest.mark.asyncio
async def test_a_replayed_call_in_a_resumed_invocation_passes() -> None:
    """A resumed invocation keeps its id, and the resolution was persisted."""
    context = _context(invocation_id="turn-7", resolved_in="turn-7")
    plugin = ToolPolicyPlugin()

    first = await plugin.before_tool_callback(
        tool=_tool("run_tariff_monitoring"), tool_args={}, tool_context=context
    )
    replay = await plugin.before_tool_callback(
        tool=_tool("run_tariff_monitoring"), tool_args={}, tool_context=context
    )

    assert first is None and replay is None


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["resolve_request", "adk_request_input"])
async def test_non_business_tools_are_never_blocked(name) -> None:
    result = await ToolPolicyPlugin().before_tool_callback(
        tool=_tool(name), tool_args={}, tool_context=_context(resolved_in=None)
    )

    assert result is None


@pytest.mark.asyncio
async def test_a_tool_exception_becomes_a_typed_envelope() -> None:
    result = await ToolPolicyPlugin().on_tool_error_callback(
        tool=_tool("get_tariff_history"),
        tool_args={},
        tool_context=_context(),
        error=LookupError("secret detail"),
    )

    assert result == {
        "status": "error",
        "reason_code": "tool.exception",
        "error_type": "LookupError",
    }


@pytest.mark.asyncio
async def test_pause_and_cancellation_are_not_exceptions_the_plugin_sees() -> None:
    from google.adk.workflow._errors import NodeInterruptedError

    # ADK only routes `Exception` to on_tool_error_callback; both control-flow
    # signals are BaseExceptions, so a review pause or Ctrl-C passes through.
    assert not issubclass(NodeInterruptedError, Exception)
    assert not issubclass(asyncio.CancelledError, Exception)
