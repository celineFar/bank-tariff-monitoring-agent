from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.domain.models import OfferingId
from app.domain.structured_tariffs import QueryStatus, TariffQueryResult
from app.tools import answer_tariff_query, configure_services, resolve_request
from tests.fixtures.interpretations import scripted_resolver

QUESTION = "What is the nominal interest rate for Overdraft?"


class FakeContext:
    def __init__(self, question: str = QUESTION) -> None:
        self.state: dict[str, object] = {}
        self.invocation_id = "turn-1"
        self.session = SimpleNamespace(
            id="session-1",
            events=[
                SimpleNamespace(
                    author="user",
                    invocation_id="turn-1",
                    content=SimpleNamespace(parts=[SimpleNamespace(text=question)]),
                )
            ],
        )


class FakeQueryService:
    def __init__(self) -> None:
        self.calls = []

    async def answer(self, plan, question):
        self.calls.append((plan, question))
        return TariffQueryResult(
            status=QueryStatus.MISSING,
            operation=plan.operation,
            product=plan.product,
            offering_ids=plan.offering_ids,
            reason="fixture has no accepted projection",
        )


@pytest.fixture
def wired_services():
    service = FakeQueryService()
    resolver = scripted_resolver()
    configure_services(request_resolver=resolver, structured_query_service=service)
    yield service
    configure_services()


STANDALONE = "What is the nominal interest rate for the Overdraft?"


@pytest.mark.asyncio
async def test_absent_or_tampered_plan_is_rejected_before_query(wired_services):
    context = FakeContext()
    assert (await answer_tariff_query(context))["reason_code"] == "query.plan_absent"
    await resolve_request(context)
    plan = dict(context.state["tariff_resolution_plan"])
    assert plan["question"] == STANDALONE
    # A plan whose question no longer matches its hash is refused.
    context.state["tariff_resolution_plan"] = {**plan, "question": "different"}
    assert (await answer_tariff_query(context))["reason_code"] == "query.plan_invalid"
    assert wired_services.calls == []


@pytest.mark.asyncio
async def test_stale_turn_expired_plan_and_replay_rejected(wired_services):
    context = FakeContext()
    await resolve_request(context)
    context.invocation_id = "turn-2"
    assert (await answer_tariff_query(context))["reason_code"] == "query.plan_invalid"
    context.invocation_id = "turn-1"
    plan = dict(context.state["tariff_resolution_plan"])
    plan["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    context.state["tariff_resolution_plan"] = plan
    assert (await answer_tariff_query(context))["reason_code"] == "query.plan_invalid"
    # A repeat resolution in the same turn returns the first result and does
    # not re-issue the grant (RR13).
    await resolve_request(context)
    assert context.state["tariff_resolution_plan"] == plan
    # The next turn resolves afresh.
    context.invocation_id = "turn-2"
    context.session.events.append(
        SimpleNamespace(
            author="user",
            invocation_id="turn-2",
            content=SimpleNamespace(parts=[SimpleNamespace(text=QUESTION)]),
        )
    )
    await resolve_request(context)
    result = await answer_tariff_query(context)
    assert result["status"] == "missing"
    assert (await answer_tariff_query(context))["reason_code"] == "query.plan_replayed"
    assert len(wired_services.calls) == 1
    assert wired_services.calls[0][1] == STANDALONE


@pytest.mark.asyncio
async def test_the_model_passes_no_text_and_no_scope(wired_services):
    context = FakeContext()
    with pytest.raises(TypeError):
        await resolve_request("What are mortgage rates?", context)
    resolved = await resolve_request(context)
    assert resolved["query_plan"]["offering_ids"] == [OfferingId.OVERDRAFT.value]
    assert resolved["route"] == "answer_tariff_query"
    assert (await answer_tariff_query(context))["status"] == "missing"
    assert wired_services.calls[0][0].offering_ids == (OfferingId.OVERDRAFT,)
    with pytest.raises(TypeError):
        await answer_tariff_query(QUESTION, context)
    with pytest.raises(TypeError):
        await answer_tariff_query(context, offering_ids=[OfferingId.CREDIT_LINE])


@pytest.mark.asyncio
async def test_a_turn_without_a_user_message_is_rejected(wired_services):
    context = FakeContext()
    context.session.events.clear()
    assert (await resolve_request(context))["reason_code"] == "intent.no_user_message"
