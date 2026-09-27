"""RRS03: multi-turn flows through the real tools, replaying recorded interpretations.

Each flow replays one case of the interpretation case set through
`resolve_request` and the business tools, so the grants, offers and the
whole-family confirmation are checked against what the live interpreter said.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from google.genai import types

from app.config import load_seed_catalog
from app.domain.intent import FreshnessStatus, RequestLanguage
from app.domain.models import OfferingId
from app.domain.tariff_queries import CurrentTariffItem, CurrentTariffResult
from app.services.intent_resolution import RequestResolver
from app.tools import (
    answer_tariff_query,
    configure_services,
    get_current_tariffs,
    resolve_request,
    run_tariff_monitoring,
)
from tests.fixtures.recorded_interpretations import RecordedInterpreter

NOW = datetime(2026, 9, 27, tzinfo=UTC)


@dataclass
class _Chat:
    state: dict[str, object] = field(default_factory=dict)
    invocation_id: str = "turn-0"
    session: object = field(
        default_factory=lambda: SimpleNamespace(id="chat-1", events=[])
    )
    node_inputs: list[dict] = field(default_factory=list)

    def say(self, text: str) -> None:
        number = int(self.invocation_id.split("-")[1]) + 1
        self.invocation_id = f"turn-{number}"
        self.session.events.append(
            SimpleNamespace(
                author="user",
                invocation_id=self.invocation_id,
                content=types.Content(role="user", parts=[types.Part(text=text)]),
            )
        )

    async def run_node(self, node, node_input):
        self.node_inputs.append(node_input)
        return {"status": "succeeded"}


class _MissingCurrent:
    async def get_current(self, **kwargs):
        return CurrentTariffResult(
            as_of=NOW,
            items=tuple(
                CurrentTariffItem(
                    product=offering.product,
                    offering_id=offering,
                    freshness=FreshnessStatus.MISSING,
                )
                for offering in kwargs.get("offering_ids") or ()
            ),
        )


class _Answers:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def answer_plan(self, plan, question):
        self.calls.append((plan, question))
        return SimpleNamespace(model_dump=lambda mode: {"status": "answered"})


@pytest.fixture
def chat():
    answers = _Answers()

    def wire(case_id: str) -> SimpleNamespace:
        interpreter = RecordedInterpreter(case_id=case_id)
        configure_services(
            None,
            None,
            RequestResolver(load_seed_catalog(), interpreter=interpreter),
            current_tariff_service=_MissingCurrent(),
            answer_router=answers,
            monitoring_node=object(),
        )
        return SimpleNamespace(chat=_Chat(), answers=answers, interpreter=interpreter)

    yield wire
    configure_services(None, None)


async def _turn(chat: _Chat, text: str) -> dict:
    chat.say(text)
    return await resolve_request(chat)


# --- offers (RR14) -------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "reply"),
    [
        ("rr14_offer_yes", "yes"),
        ("rr14_offer_ok", "ok"),
        ("rr14_offer_sure", "sure"),
        ("rr14_offer_yes_refresh_it", "yes, refresh it"),
        ("rr14_offer_thumbs_up", "👍"),
        ("rr14_offer_hy_yes", "այո, թարմացրու"),
    ],
)
async def test_a_natural_yes_takes_up_the_offer_and_the_run_answers_the_question(
    chat, case_id, reply
) -> None:
    flow = chat(case_id)
    first = await _turn(flow.chat, "What's the express mortgage rate?")
    await get_current_tariffs(flow.chat)  # missing: stores the offer
    second = await _turn(flow.chat, reply)
    ran = await run_tariff_monitoring("mortgage", "mortgage_express", flow.chat)

    assert second["refresh_confirmation"] is True
    assert flow.chat.state["monitoring_authorization"]["offering_id"] == (
        "mortgage_express"
    )
    assert ran == {"status": "succeeded"}
    # The run answers the question of record, not the reply.
    assert flow.chat.node_inputs[0]["question"] == first["standalone_question"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "reply"),
    [
        ("rr14_offer_declined", "no thanks"),
        ("rr14_offer_ignored_by_new_question", "What's the credit line fee?"),
    ],
)
async def test_a_refusal_or_a_new_question_spends_nothing(chat, case_id, reply) -> None:
    flow = chat(case_id)
    await _turn(flow.chat, "What's the express mortgage rate?")
    await get_current_tariffs(flow.chat)
    second = await _turn(flow.chat, reply)
    ran = await run_tariff_monitoring("mortgage", "mortgage_express", flow.chat)

    assert "refresh_confirmation" not in second
    assert flow.chat.state["monitoring_authorization"] is None
    assert ran["reason_code"] == "run.intent_not_authorized"
    assert flow.chat.state["monitoring_confirmation_offer"] is None


# --- the whole-family confirmation (RR15) ----------------------------------------------


@pytest.mark.asyncio
async def test_the_family_runs_after_an_explicit_yes(chat) -> None:
    flow = chat("rr15_scope_confirmed")
    await _turn(flow.chat, "Refresh all mortgage loans")
    asked = await run_tariff_monitoring("mortgage", None, flow.chat)
    await _turn(flow.chat, "yes, all of them")
    ran = await run_tariff_monitoring("mortgage", None, flow.chat)
    replay = await run_tariff_monitoring("mortgage", None, flow.chat)

    assert asked["status"] == "needs_scope_confirmation"
    assert ran == replay == {"status": "succeeded"}
    assert len(flow.chat.node_inputs) == 2


@pytest.mark.asyncio
async def test_a_refresh_question_does_not_confirm_the_family(chat) -> None:
    flow = chat("rr15_scope_not_confirmed_by_question")
    await _turn(flow.chat, "Refresh all mortgage loans")
    await run_tariff_monitoring("mortgage", None, flow.chat)
    await _turn(flow.chat, "how often do you refresh mortgage rates?")
    second = await run_tariff_monitoring("mortgage", None, flow.chat)

    assert second.get("status") != "succeeded"
    assert flow.chat.node_inputs == []


# --- clarification and follow-ups (RR8, RR9, RR12) --------------------------------------


@pytest.mark.asyncio
async def test_a_numeric_reply_answers_the_original_question(chat) -> None:
    flow = chat("rr9_numeric_reply_keeps_question")
    first = await _turn(flow.chat, "What's the mortgage rate?")
    second = await _turn(flow.chat, "3")
    answered = await answer_tariff_query(flow.chat)

    plan, question = flow.answers.calls[0]
    assert first["needs_clarification"] is True
    assert second["offering_id"] == OfferingId.MORTGAGE_DIASPORA.value
    assert answered == {"status": "answered"}
    assert plan.offering_ids == (OfferingId.MORTGAGE_DIASPORA,)
    assert question == second["standalone_question"] != "3"
    assert "rate.nominal.minimum" in {item.value for item in plan.fields}
    assert "amount.minimum" not in {item.value for item in plan.fields}


@pytest.mark.asyncio
async def test_an_armenian_question_answered_by_number_stays_armenian(chat) -> None:
    flow = chat("rr12_armenian_numeric_reply")
    await _turn(flow.chat, "Ինչքա՞ն է հիփոթեքի տոկոսադրույքը")
    second = await _turn(flow.chat, "2")

    assert second["language"] == RequestLanguage.ARMENIAN.value
    assert second["offering_id"] == OfferingId.MORTGAGE_PRIMARY.value


@pytest.mark.asyncio
async def test_a_follow_up_keeps_the_offering(chat) -> None:
    flow = chat("rr8_follow_up_term")
    await _turn(flow.chat, "What's the express mortgage rate?")
    second = await _turn(flow.chat, "what about the term?")

    assert second["offering_id"] == OfferingId.MORTGAGE_EXPRESS.value
    assert any(field.startswith("term.") for field in second["query_plan"]["fields"])


# --- once per turn (RR13) --------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_repeat_call_in_the_same_turn_is_the_same_result(chat) -> None:
    flow = chat("rr9_numeric_reply_keeps_question")
    await _turn(flow.chat, "What's the mortgage rate?")
    second = await _turn(flow.chat, "3")
    plan = flow.chat.state["tariff_resolution_plan"]
    again = await resolve_request(flow.chat)

    assert again == second
    assert flow.chat.state["tariff_resolution_plan"] == plan
    assert flow.interpreter.calls == 2
