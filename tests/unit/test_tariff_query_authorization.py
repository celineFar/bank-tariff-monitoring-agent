from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.domain.models import OfferingId
from app.domain.structured_tariffs import QueryStatus, TariffQueryResult
from app.services.intent_resolution import RequestResolver
from app.tools import answer_tariff_query, configure_services, resolve_request

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
    resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings())
    configure_services(None, None, resolver, structured_query_service=service)
    yield service
    configure_services(None, None)


@pytest.mark.asyncio
async def test_absent_plan_and_changed_question_rejected_before_query(wired_services):
    context = FakeContext()
    assert (await answer_tariff_query(QUESTION, context))[
        "reason_code"
    ] == "query.plan_absent"
    await resolve_request(QUESTION, context)
    assert (await answer_tariff_query("different", context))[
        "reason_code"
    ] == "query.plan_invalid"
    assert wired_services.calls == []


@pytest.mark.asyncio
async def test_stale_turn_expired_plan_and_replay_rejected(wired_services):
    context = FakeContext()
    await resolve_request(QUESTION, context)
    context.invocation_id = "turn-2"
    assert (await answer_tariff_query(QUESTION, context))[
        "reason_code"
    ] == "query.plan_invalid"
    context.invocation_id = "turn-1"
    plan = dict(context.state["tariff_resolution_plan"])
    plan["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    context.state["tariff_resolution_plan"] = plan
    assert (await answer_tariff_query(QUESTION, context))[
        "reason_code"
    ] == "query.plan_invalid"
    await resolve_request(QUESTION, context)
    result = await answer_tariff_query(QUESTION, context)
    assert result["status"] == "missing"
    assert (await answer_tariff_query(QUESTION, context))[
        "reason_code"
    ] == "query.plan_replayed"
    assert len(wired_services.calls) == 1


@pytest.mark.asyncio
async def test_resolution_must_match_actual_user_message_and_scope_cannot_widen(
    wired_services,
):
    context = FakeContext()
    assert (await resolve_request("What are mortgage rates?", context))[
        "reason_code"
    ] == "intent.query_mismatch"
    resolved = await resolve_request(QUESTION, context)
    assert resolved["query_plan"]["offering_ids"] == [OfferingId.OVERDRAFT.value]
    assert (await answer_tariff_query(QUESTION, context))["status"] == "missing"
    assert wired_services.calls[0][0].offering_ids == (OfferingId.OVERDRAFT,)
    with pytest.raises(TypeError):
        await answer_tariff_query(
            QUESTION, context, offering_ids=[OfferingId.CREDIT_LINE]
        )
