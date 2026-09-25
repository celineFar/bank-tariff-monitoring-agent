from __future__ import annotations

from app.agent import INSTRUCTION, app, root_agent
from app.plugins import ToolPolicyPlugin


def _tool_names() -> set[str]:
    return {
        getattr(tool, "name", None) or getattr(tool, "__name__", "")
        for tool in root_agent.tools
    }


def test_one_resumable_app_with_the_policy_plugin() -> None:
    assert app.name == "app"
    assert app.root_agent is root_agent
    assert app.resumability_config is not None
    assert app.resumability_config.is_resumable is True
    assert any(isinstance(plugin, ToolPolicyPlugin) for plugin in app.plugins)


def test_the_agent_exposes_exactly_the_seven_tools() -> None:
    assert _tool_names() == {
        "resolve_request",
        "get_current_tariffs",
        "get_tariff_history",
        "answer_tariff_query",
        "get_monitoring_status",
        "run_tariff_monitoring",
        "review_pending_candidates",
    }


def test_sdk_automatic_function_calling_is_disabled() -> None:
    # Ported from test_cli.py: ADK, not the SDK, must dispatch tool calls, or
    # plugins, resumability and the monitoring node's pause are bypassed.
    config = root_agent.generate_content_config
    assert config.automatic_function_calling.disable is True


def test_the_prompt_is_short_and_carries_no_control_flow_rules() -> None:
    assert len(INSTRUCTION.splitlines()) <= 25
    lowered = INSTRUCTION.lower()
    for leftover in (
        "request_input",
        "wait_for_monitoring_run",
        "get_next_monitoring_review",
        "submit_monitoring_review_input",
        "stop_and_wait",
        "run id",
        "do not call",
    ):
        assert leftover not in lowered
