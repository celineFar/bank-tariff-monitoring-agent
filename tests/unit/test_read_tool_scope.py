"""Least privilege at the tool boundary (plan §6.6).

The model never chooses what data a tool may touch: read tools take no scope
argument and read the turn's grant; the monitoring offer is computed from that
grant; the spend grant is bound to one invocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from google.genai import types

from app.config import load_seed_catalog
from app.config.models import IntentResolutionSettings
from app.domain.intent import FreshnessStatus
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import OfferingRunStatus
from app.domain.structured_tariffs import QueryOperation
from app.domain.tariff_queries import CurrentTariffItem, CurrentTariffResult
from app.services.intent_resolution import RequestResolver
from app.tools import (
    answer_tariff_query,
    configure_services,
    get_current_tariffs,
    get_tariff_history,
    resolve_request,
    review_pending_candidates,
    run_tariff_monitoring,
)

NOW = datetime(2026, 9, 25, tzinfo=UTC)


@dataclass
class _Context:
    state: dict[str, object] = field(default_factory=dict)
    invocation_id: str = "turn-1"
    session: object = field(
        default_factory=lambda: SimpleNamespace(id="chat-1", events=[])
    )
    node_inputs: list[dict] = field(default_factory=list)

    async def run_node(self, node, node_input):
        self.node_inputs.append(node_input)
        return {"status": "succeeded"}


async def _resolve(context: _Context, text: str) -> dict:
    """The user says `text` in the current turn, then the agent resolves it."""
    context.session.events.append(
        SimpleNamespace(
            author="user",
            invocation_id=context.invocation_id,
            content=types.Content(role="user", parts=[types.Part(text=text)]),
        )
    )
    return await resolve_request(text, context)


class _Current:
    def __init__(self, missing: bool = False) -> None:
        self.calls: list[dict] = []
        self.missing = missing

    async def get_current(self, **kwargs):
        self.calls.append(kwargs)
        offerings = kwargs.get("offering_ids") or (OfferingId.MORTGAGE_EXPRESS,)
        return CurrentTariffResult(
            as_of=NOW,
            items=tuple(
                CurrentTariffItem(
                    product=offering.product,
                    offering_id=offering,
                    freshness=FreshnessStatus.MISSING,
                )
                for offering in offerings
            )
            if self.missing
            else (),
        )


class _History:
    def __init__(self) -> None:
        self.queries = []

    async def query(self, query):
        self.queries.append(query)
        return SimpleNamespace(model_dump=lambda mode: {"status": "unavailable"})


class _Answers:
    def __init__(self) -> None:
        self.plans = []

    async def answer_plan(self, plan, question):
        self.plans.append(plan)
        return SimpleNamespace(model_dump=lambda mode: {"status": "answered"})


@pytest.fixture
def wired():
    current, history, answers = _Current(), _History(), _Answers()
    configure_services(
        None,
        None,
        RequestResolver(load_seed_catalog(), IntentResolutionSettings()),
        current_tariff_service=current,
        tariff_history_service=history,
        answer_router=answers,
        monitoring_node=object(),
    )
    yield SimpleNamespace(current=current, history=history, answers=answers)
    configure_services(None, None)


# --- read tools read only the grant ------------------------------------------


@pytest.mark.asyncio
async def test_read_tools_without_a_grant_are_rejected(wired) -> None:
    context = _Context()

    assert (await get_current_tariffs(context))["reason_code"] == "query.plan_absent"
    assert (await get_tariff_history("what_changed", context))[
        "reason_code"
    ] == "query.plan_absent"
    assert wired.current.calls == []
    assert wired.history.queries == []


@pytest.mark.asyncio
async def test_a_grant_from_another_turn_or_session_is_rejected(wired) -> None:
    context = _Context()
    await _resolve(context, "current Express Mortgage rate")

    context.invocation_id = "turn-2"
    other_turn = await get_current_tariffs(context)
    context.invocation_id = "turn-1"
    context.session = SimpleNamespace(id="chat-2", events=context.session.events)
    other_session = await get_current_tariffs(context)

    assert other_turn["reason_code"] == "query.plan_invalid"
    assert other_session["reason_code"] == "query.plan_invalid"
    assert wired.current.calls == []


@pytest.mark.asyncio
async def test_an_expired_grant_is_rejected(wired) -> None:
    context = _Context()
    await _resolve(context, "current Express Mortgage rate")
    raw = context.state["tariff_resolution_plan"]
    assert isinstance(raw, dict)
    plan = dict(raw)
    plan["issued_at"] = (NOW - timedelta(days=2)).isoformat()
    plan["expires_at"] = (NOW - timedelta(days=1)).isoformat()
    context.state["tariff_resolution_plan"] = plan

    assert (await get_current_tariffs(context))["reason_code"] == "query.plan_invalid"


@pytest.mark.asyncio
async def test_read_tools_are_reusable_in_a_turn_but_answering_is_one_use(
    wired,
) -> None:
    question = "What is the Express Mortgage rate?"
    context = _Context()
    await _resolve(context, question)

    first = await get_current_tariffs(context)
    second = await get_current_tariffs(context)
    answered = await answer_tariff_query(question, context)
    replayed = await answer_tariff_query(question, context)

    assert "reason_code" not in first and "reason_code" not in second
    assert answered == {"status": "answered"}
    assert replayed["reason_code"] == "query.plan_replayed"
    assert wired.current.calls[0] == {
        "product": ProductType.MORTGAGE,
        "offering_ids": (OfferingId.MORTGAGE_EXPRESS,),
    }


@pytest.mark.asyncio
async def test_a_broad_current_question_gets_a_scope_only_family_grant(wired) -> None:
    context = _Context()
    resolution = await _resolve(context, "current mortgage tariffs")

    plan = context.state["tariff_resolution_plan"]
    assert resolution["intent"] == "get_current_tariffs"
    assert plan["operation"] == QueryOperation.CURRENT.value
    assert plan["fields"] == []
    assert set(plan["offering_ids"]) == {
        item.value for item in OfferingId if item.product is ProductType.MORTGAGE
    }
    # A scope-only grant has no field shape, so the answer tool declines it.
    declined = await answer_tariff_query("current mortgage tariffs", context)
    assert declined["reason_code"] == "query.scope_only_plan"
    assert wired.answers.plans == []


@pytest.mark.asyncio
async def test_a_familyless_history_question_reads_both_families(wired) -> None:
    context = _Context()
    resolution = await _resolve(context, "What changed recently?")

    await get_tariff_history("what_changed", context, limit=500)

    assert resolution["intent"] == "get_change_history"
    assert context.state["tariff_resolution_plan"]["product"] is None
    assert context.state["tariff_resolution_plan"]["operation"] == "history"
    (query,) = wired.history.queries
    assert query.product is None and query.offering_ids == ()


@pytest.mark.asyncio
async def test_history_scope_is_the_grant_even_if_the_model_passes_more(wired) -> None:
    context = _Context()
    await _resolve(context, "What changed for Express Mortgage?")

    # ADK drops arguments a function does not declare; the tool has no scope
    # parameter to receive them in the first place.
    await get_tariff_history("what_changed", context)

    (query,) = wired.history.queries
    assert query.product is ProductType.MORTGAGE
    assert query.offering_ids == (OfferingId.MORTGAGE_EXPRESS,)


# --- the offer is derived from the grant ---------------------------------------


@pytest.mark.asyncio
async def test_the_monitoring_offer_is_the_grant_scope_bound_to_the_turn() -> None:
    configure_services(
        None,
        None,
        RequestResolver(load_seed_catalog(), IntentResolutionSettings()),
        current_tariff_service=_Current(missing=True),
    )
    try:
        context = _Context()
        await _resolve(context, "What is the Express Mortgage rate?")
        await get_current_tariffs(context)
    finally:
        configure_services(None, None)

    assert context.state["monitoring_confirmation_offer"] == {
        "product": "mortgage",
        "offering_id": "mortgage_express",
        "invocation_id": "turn-1",
    }


@pytest.mark.asyncio
async def test_a_familyless_grant_never_writes_an_offer() -> None:
    configure_services(
        None,
        None,
        RequestResolver(load_seed_catalog(), IntentResolutionSettings()),
        current_tariff_service=_Current(missing=True),
    )
    try:
        context = _Context()
        await _resolve(context, "show me all current tariffs")
        assert context.state["tariff_resolution_plan"]["product"] is None
        await get_current_tariffs(context)
    finally:
        configure_services(None, None)

    assert context.state.get("monitoring_confirmation_offer") is None


# --- the spend grant --------------------------------------------------------------


def _authorized(product="mortgage", offering_id="mortgage_express", turn="turn-1"):
    return _Context(
        state={
            "monitoring_authorization": {
                "product": product,
                "offering_id": offering_id,
                "invocation_id": turn,
            },
            "resolution": {"invocation_id": turn, "previous_invocation_id": None},
        },
        invocation_id=turn,
    )


@pytest.mark.asyncio
async def test_monitoring_runs_the_node_only_for_the_granted_scope(wired) -> None:
    context = _authorized()

    result = await run_tariff_monitoring("mortgage", "mortgage_express", context)

    assert result == {"status": "succeeded"}
    assert context.node_inputs == [
        {"product": "mortgage", "offering_id": "mortgage_express", "question": None}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("offering_id", "turn"),
    [
        ("mortgage_primary", "turn-1"),  # model argues with resolver
        (None, "turn-1"),  # model widens to the family
        ("mortgage_express", "turn-2"),  # grant from another turn
    ],
)
async def test_monitoring_outside_the_grant_is_rejected(
    wired, offering_id, turn
) -> None:
    context = _authorized()
    context.invocation_id = turn

    result = await run_tariff_monitoring("mortgage", offering_id, context)

    assert result["reason_code"] == "run.intent_not_authorized"
    assert context.node_inputs == []


@pytest.mark.asyncio
async def test_cross_family_scope_is_rejected_before_authorization(wired) -> None:
    context = _authorized(product="consumer_loan", offering_id="mortgage_express")

    result = await run_tariff_monitoring("consumer_loan", "mortgage_express", context)

    assert result["reason_code"] == "run.invalid_scope"


@pytest.mark.asyncio
async def test_family_scope_needs_a_confirmation_the_same_turn_cannot_give(
    wired,
) -> None:
    context = _authorized(offering_id=None)

    asked = await run_tariff_monitoring("mortgage", None, context)
    asked_again = await run_tariff_monitoring("mortgage", None, context)

    assert asked["status"] == "needs_scope_confirmation"
    assert asked["offering_count"] == len(
        [item for item in OfferingId if item.product is ProductType.MORTGAGE]
    )
    # A second call in the same turn is not a user's confirmation.
    assert asked_again["status"] == "needs_scope_confirmation"
    assert context.node_inputs == []


@pytest.mark.asyncio
async def test_family_scope_runs_after_yes_in_the_next_turn_and_on_replay(
    wired,
) -> None:
    context = _authorized(offering_id=None)
    await run_tariff_monitoring("mortgage", None, context)
    offer = context.state["monitoring_confirmation_offer"]

    context.invocation_id = "turn-2"
    confirmation = await _resolve(context, "yes")
    first = await run_tariff_monitoring("mortgage", None, context)
    replay = await run_tariff_monitoring("mortgage", None, context)

    assert offer == {
        "product": "mortgage",
        "invocation_id": "turn-1",
        "offering_id": None,
    }
    assert confirmation["intent"] == "start_monitoring_run"
    assert first == replay == {"status": "succeeded"}
    assert len(context.node_inputs) == 2


# --- review tool ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reviewing_requires_a_resolution_this_turn_and_its_scope(wired) -> None:
    context = _Context()
    unresolved = await review_pending_candidates(context)
    await _resolve(context, "review the Express Mortgage candidates")
    widened = await review_pending_candidates(context, product="consumer_loan")
    allowed = await review_pending_candidates(
        context, product="mortgage", offering_id="mortgage_express"
    )

    assert unresolved["reason_code"] == "policy.resolve_first"
    assert widened["reason_code"] == "review.scope_not_resolved"
    assert allowed == {"status": "succeeded"}
    assert context.node_inputs == [
        {"product": "mortgage", "offering_id": "mortgage_express", "review_only": True}
    ]


# --- status tool --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_reports_active_runs_pending_reviews_and_freshness() -> None:
    from app.tools import get_monitoring_status
    from tests.fixtures.monitoring_node import Reviews, Runs, queued_run, review_task

    runs, reviews = Runs(), Reviews()
    running = runs.add(queued_run(), owner="worker-1")
    runs.execution(
        running.id,
        OfferingId.OVERDRAFT,
        status=OfferingRunStatus.RUNNING,
        stage="normalization",
    )
    task = review_task(running, OfferingId.OVERDRAFT, "interest_rate")
    reviews.tasks[task.id] = task
    configure_services(
        None,
        None,
        current_tariff_service=_Current(missing=True),
        runs=runs,
        reviews=reviews,
    )
    try:
        status = await get_monitoring_status(_Context())
    finally:
        configure_services(None, None)

    assert status["active_runs"] == [
        {
            "product": "consumer_loan",
            "offering_id": "overdraft",
            "status": "queued",
            "started_by": "scheduler",
            "stages": {"overdraft": "normalization"},
        }
    ]
    assert status["pending_reviews"] == {"overdraft": 1}
    assert status["latest_accepted_at"] == {"mortgage_express": None}
