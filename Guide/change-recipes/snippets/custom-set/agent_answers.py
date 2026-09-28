from types import SimpleNamespace

import pytest

from app.agent import INSTRUCTION
from app.plugins import ToolPolicyPlugin
from app.tools import configure_services, resolve_request
from tests.unit.test_tool_flows import _Chat


class _NeverInterprets:
    async def resolve_turn(self, *args, **kwargs):
        raise AssertionError("a refused topic must not reach Gemini")


def test_prompt_says_armenian_and_refused() -> None:
    assert "Always answer in Armenian" in INSTRUCTION
    assert '"refused"' in INSTRUCTION


@pytest.mark.asyncio
async def test_other_bank_is_refused_and_business_tools_stay_blocked() -> None:
    configure_services(request_resolver=_NeverInterprets())
    try:
        chat = _Chat()
        chat.say("What is ACBA's consumer loan rate?")
        result = await resolve_request(chat)
        assert result == {"status": "refused", "reason_code": "policy.refused_topic"}
        blocked = await ToolPolicyPlugin().before_tool_callback(
            tool=SimpleNamespace(name="answer_tariff_query"),
            tool_args={},
            tool_context=chat,
        )
        assert blocked["reason_code"] == "policy.resolve_first"
    finally:
        configure_services()
