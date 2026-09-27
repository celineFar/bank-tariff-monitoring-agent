"""Regression tests for the resolution-and-RAG fix plan, one per item (RR*).

Written in Phase 0 against the target APIs; each failed before its fix.
Imports of the new modules happen inside the tests, so one missing module
does not stop the others from being collected.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from google.genai import types

from app.config import load_seed_catalog
from app.config.models import IntentResolutionSettings
from app.domain.intent import RequestIntent, RequestLanguage
from app.domain.models import OfferingId, ProductType
from app.domain.semantic_extraction import ExtractionStatus, RateBasis
from app.domain.structured_tariffs import (
    FactEvidence,
    FieldPath,
    OfferingProfile,
    QueryOperation,
    QueryStatus,
    RankDirection,
    ResolutionPlan,
    TariffFact,
)
from app.services.structured_tariff_query import StructuredTariffQueryService

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)
RATES = (FieldPath.NOMINAL_RATE_MINIMUM, FieldPath.NOMINAL_RATE_MAXIMUM)


# --- helpers -------------------------------------------------------------------


@dataclass
class _Context:
    state: dict[str, object] = field(default_factory=dict)
    invocation_id: str = "turn-0"
    session: object = field(
        default_factory=lambda: SimpleNamespace(id="chat-1", events=[])
    )
    node_inputs: list[dict] = field(default_factory=list)

    def say(self, text: str) -> None:
        """A new user turn: a new invocation with the user's message."""
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


def _resolver(script):
    from app.services.intent_resolution import RequestResolver
    from tests.fixtures.interpretations import ScriptedInterpreter

    return RequestResolver(
        load_seed_catalog(),
        IntentResolutionSettings(),
        interpreter=ScriptedInterpreter(script),
    )


def _wire(script, **services):
    from app.tools import configure_services

    configure_services(None, None, _resolver(script), **services)


def _unwire():
    from app.tools import configure_services

    configure_services(None, None)


def _evidence(n: int) -> FactEvidence:
    return FactEvidence(
        evidence_id=f"ev_{n:024x}",
        quote=f"quote {n}",
        source_url="https://ameriabank.am/en/overdraft",
        source_item_id=f"item-{n}",
        authority="official_terms",
        locator={"source_url": "https://ameriabank.am/en/overdraft", "pdf_page": 1},
    )


def _fact(
    offering: OfferingId,
    snapshot: UUID,
    path: FieldPath,
    number: str | None,
    *,
    currency: str | None = "AMD",
    conditions: tuple[dict, ...] = (),
    unit: str | None = "percent",
    status: ExtractionStatus = ExtractionStatus.FOUND,
    value: str | None = None,
    n: int = 1,
) -> TariffFact:
    found = status is ExtractionStatus.FOUND
    return TariffFact(
        fact_id=hashlib.sha256(f"{offering}{snapshot}{path}{n}".encode()).hexdigest(),
        snapshot_id=snapshot,
        offering_id=offering,
        field_path=path,
        variant_key=f"v{n}",
        status=status,
        value=(value or number) if found else None,
        number=Decimal(number) if found and number is not None else None,
        unit=unit,
        currency=currency,
        rate_basis=RateBasis.ANNUAL if unit == "percent" else None,
        conditions=conditions,
        evidence=(_evidence(n),) if found else (),
    )


def _profile(offering: OfferingId, snapshot: UUID) -> OfferingProfile:
    return OfferingProfile(
        snapshot_id=snapshot,
        bank="ameria",
        product=offering.product,
        offering_id=offering,
        display_name=offering.value.replace("_", " ").title(),
        accepted_at=NOW - timedelta(days=1),
    )


class _Repository:
    def __init__(self, profiles, facts, changes=()):
        self.profiles = profiles
        self.facts_ = facts
        self.changes = changes

    async def active_profiles(self, *, bank, product, offering_ids):
        return tuple(p for p in self.profiles if p.offering_id in offering_ids)

    async def facts(self, *, snapshots, fields, include_inactive=False):
        return tuple(
            f
            for f in self.facts_
            if f.snapshot_id in snapshots and f.field_path in fields
        )

    async def lexical_units(self, **_):
        return ()

    async def vector_units(self, **_):
        return ()

    async def accepted_changes(self, *, product, offering_ids, limit):
        return self.changes


def _plan(question: str, **values) -> ResolutionPlan:
    defaults = {
        "session_id": "s",
        "turn_id": "t",
        "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
        "issued_at": NOW - timedelta(minutes=1),
        "expires_at": NOW + timedelta(minutes=5),
    }
    return ResolutionPlan(**{**defaults, **values})


# --- RR7 ------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rr7_lowest_mortgage_resolves_without_crashing() -> None:
    from tests.fixtures.interpretations import interp

    resolver = _resolver(
        {
            "lowest mortgage": interp(
                RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
                product=ProductType.MORTGAGE,
                family_wide=True,
                operation=QueryOperation.FAMILY_RANK,
                fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
                rank_field=FieldPath.NOMINAL_RATE_MINIMUM,
                rank_direction=RankDirection.LOWEST,
            )
        }
    )
    turn = await resolver.resolve_turn("lowest mortgage")

    assert turn.resolution.product is ProductType.MORTGAGE
    assert turn.resolution.query.operation is QueryOperation.FAMILY_RANK


# --- RR9 / RR10 / RR12 ---------------------------------------------------------------


def _mortgage_rate_question(language=RequestLanguage.ENGLISH):
    from tests.fixtures.interpretations import interp

    return interp(
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        product=ProductType.MORTGAGE,
        operation=QueryOperation.SINGLE,
        fields=RATES,
        language=language,
        standalone_question="What is the mortgage interest rate?",
    )


@pytest.mark.xfail(strict=True, reason="RR9: the plan is built from the reply '3'")
@pytest.mark.asyncio
async def test_rr9_numeric_reply_plans_the_original_question() -> None:
    from app.domain.interpretation import ReplyKind
    from app.tools import resolve_request
    from tests.fixtures.interpretations import interp

    standalone = "What is the Mortgage Loan for Diaspora interest rate?"
    _wire(
        {
            "What's the mortgage rate?": _mortgage_rate_question(),
            "3": interp(
                RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
                replies_to=ReplyKind.CLARIFICATION,
                product=ProductType.MORTGAGE,
                offering_ids=(OfferingId.MORTGAGE_DIASPORA,),
                operation=QueryOperation.SINGLE,
                fields=RATES,
                standalone_question=standalone,
            ),
        }
    )
    try:
        context = _Context()
        context.say("What's the mortgage rate?")
        first = await resolve_request(context)
        context.say("3")
        second = await resolve_request(context)
    finally:
        _unwire()

    assert first["needs_clarification"] is True
    assert second["offering_id"] == OfferingId.MORTGAGE_DIASPORA.value
    plan = context.state["tariff_resolution_plan"]
    assert set(plan["fields"]) == {item.value for item in RATES}
    assert plan["question_sha256"] == hashlib.sha256(standalone.encode()).hexdigest()


@pytest.mark.asyncio
async def test_rr10_family_reply_to_a_single_value_question_asks_for_the_offering() -> (
    None
):
    from app.domain.interpretation import ReplyKind
    from tests.fixtures.interpretations import interp

    resolver = _resolver(
        {
            "What is the interest?": interp(
                RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
                operation=QueryOperation.SINGLE,
                fields=RATES,
            ),
            "mortgage": interp(
                RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
                replies_to=ReplyKind.CLARIFICATION,
                product=ProductType.MORTGAGE,
                operation=QueryOperation.SINGLE,
                fields=RATES,
            ),
        }
    )
    first = await resolver.resolve_turn("What is the interest?")
    second = await resolver.resolve_turn("mortgage", first.state)

    assert first.resolution.needs_clarification is True
    assert second.resolution.needs_clarification is True
    assert {c.offering_id for c in second.resolution.candidates} == {
        item for item in OfferingId if item.product is ProductType.MORTGAGE
    }


@pytest.mark.asyncio
async def test_rr12_numeric_reply_keeps_the_conversation_language() -> None:
    from app.domain.interpretation import ReplyKind
    from tests.fixtures.interpretations import interp

    question = "Ինչքա՞ն է հիփոթեքի տոկոսադրույքը"
    resolver = _resolver(
        {
            question: _mortgage_rate_question(RequestLanguage.ARMENIAN),
            "2": interp(
                RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
                replies_to=ReplyKind.CLARIFICATION,
                language=RequestLanguage.ENGLISH,
                product=ProductType.MORTGAGE,
                offering_ids=(OfferingId.MORTGAGE_PRIMARY,),
                operation=QueryOperation.SINGLE,
                fields=RATES,
            ),
        }
    )
    first = await resolver.resolve_turn(question)
    second = await resolver.resolve_turn("2", first.state)

    assert second.resolution.language is RequestLanguage.ARMENIAN


# --- RR13 / RR14 / RR15 ----------------------------------------------------------------


def _express_rate():
    from tests.fixtures.interpretations import interp

    return interp(
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        product=ProductType.MORTGAGE,
        offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
        operation=QueryOperation.SINGLE,
        fields=RATES,
    )


@pytest.mark.xfail(strict=True, reason="RR13: a second resolve_request wipes the grant")
@pytest.mark.asyncio
async def test_rr13_second_resolution_in_a_turn_keeps_the_grant() -> None:
    from app.tools import resolve_request
    from tests.fixtures.interpretations import ScriptedInterpreter

    _wire({"What's the express mortgage rate?": _express_rate()})
    try:
        context = _Context()
        context.say("What's the express mortgage rate?")
        first = await resolve_request(context)
        plan = context.state["tariff_resolution_plan"]
        second = await resolve_request(context)
        from app.tools import services

        interpreter: ScriptedInterpreter = services.request_resolver._interpreter
    finally:
        _unwire()

    assert second == first
    assert context.state["tariff_resolution_plan"] == plan
    assert interpreter.calls == 1


@pytest.mark.xfail(
    strict=True, reason="RR14: a thumbs-up to the monitoring offer raises"
)
@pytest.mark.asyncio
async def test_rr14_thumbs_up_takes_up_the_monitoring_offer() -> None:
    from app.domain.interpretation import ReplyKind
    from app.tools import resolve_request
    from tests.fixtures.interpretations import interp

    _wire(
        {
            "What's the express mortgage rate?": _express_rate(),
            "👍": interp(
                RequestIntent.START_MONITORING_RUN,
                replies_to=ReplyKind.MONITORING_OFFER,
                accepts=True,
            ),
        }
    )
    try:
        context = _Context()
        context.say("What's the express mortgage rate?")
        await resolve_request(context)
        # What get_current_tariffs stores when the value is missing.
        context.state["monitoring_confirmation_offer"] = {
            "product": "mortgage",
            "offering_id": "mortgage_express",
            "invocation_id": context.invocation_id,
        }
        context.say("👍")
        await resolve_request(context)
    finally:
        _unwire()

    assert context.state["monitoring_authorization"] == {
        "product": "mortgage",
        "offering_id": "mortgage_express",
        "invocation_id": context.invocation_id,
    }


@pytest.mark.xfail(
    strict=True, reason="RR15: any next-turn spend grant confirms the family"
)
@pytest.mark.asyncio
async def test_rr15_an_unrelated_refresh_request_does_not_confirm_the_family() -> None:
    from app.tools import resolve_request, run_tariff_monitoring
    from tests.fixtures.interpretations import interp

    refresh = interp(
        RequestIntent.START_MONITORING_RUN,
        product=ProductType.MORTGAGE,
        family_wide=True,
    )
    _wire(
        {
            "Refresh all mortgage loans": refresh,
            "how often do you refresh mortgage rates?": refresh,
        },
        monitoring_node=object(),
    )
    try:
        context = _Context()
        context.say("Refresh all mortgage loans")
        await resolve_request(context)
        first = await run_tariff_monitoring("mortgage", None, context)
        context.say("how often do you refresh mortgage rates?")
        await resolve_request(context)
        second = await run_tariff_monitoring("mortgage", None, context)
    finally:
        _unwire()

    assert first["status"] == "needs_scope_confirmation"
    assert second["status"] == "needs_scope_confirmation"
    assert context.node_inputs == []


# --- RR23 / RR24 / RR26 ------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True, reason="RR23: conditional variants make every rank incomparable"
)
@pytest.mark.asyncio
async def test_rr23_identical_conditional_variants_rank_as_answered() -> None:
    question = "Which consumer loan has the lowest rate?"
    offerings = (OfferingId.OVERDRAFT, OfferingId.CREDIT_LINE)
    snapshots = {offering: uuid4() for offering in offerings}
    facts = tuple(
        _fact(
            offering,
            snapshots[offering],
            FieldPath.NOMINAL_RATE_MINIMUM,
            number,
            conditions=({"dimension": "card_type", "value": card},),
            n=n,
        )
        for offering in offerings
        for n, (number, card) in enumerate((("21", "classic"), ("20", "gold")))
    )
    service = StructuredTariffQueryService(
        _Repository(tuple(_profile(o, snapshots[o]) for o in offerings), facts)
    )
    plan = _plan(
        question,
        product=ProductType.CONSUMER_LOAN,
        offering_ids=offerings,
        operation=QueryOperation.FAMILY_RANK,
        rank_direction=RankDirection.LOWEST,
        fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
    )
    result = await service.answer(plan, question, now=NOW)

    assert result.status is QueryStatus.ANSWERED


@pytest.mark.xfail(
    strict=True, reason="RR24: a currency word drops currency-less facts"
)
@pytest.mark.asyncio
async def test_rr24_currency_keeps_facts_without_a_currency() -> None:
    question = "What is the overdraft repayment term in AMD?"
    snapshot = uuid4()
    facts = (
        _fact(
            OfferingId.OVERDRAFT,
            snapshot,
            FieldPath.REPAYMENT_METHOD,
            None,
            currency=None,
            unit=None,
            value="annuity",
        ),
        _fact(
            OfferingId.OVERDRAFT,
            snapshot,
            FieldPath.TERM_MAXIMUM_MONTHS,
            "36",
            currency="USD",
            unit="months",
            n=2,
        ),
    )
    service = StructuredTariffQueryService(
        _Repository((_profile(OfferingId.OVERDRAFT, snapshot),), facts)
    )
    plan = _plan(
        question,
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.OVERDRAFT,),
        operation=QueryOperation.SINGLE,
        fields=(FieldPath.REPAYMENT_METHOD, FieldPath.TERM_MAXIMUM_MONTHS),
        conditions={"currency": "AMD"},
    )
    result = await service.answer(plan, question, now=NOW)

    assert result.status is QueryStatus.ANSWERED
    assert [f.field_path for f in result.facts] == [FieldPath.REPAYMENT_METHOD]


@pytest.mark.xfail(
    strict=True, reason="RR26: one added field withholds the whole history"
)
@pytest.mark.asyncio
async def test_rr26_a_change_that_adds_a_field_still_answers() -> None:
    from app.domain.monitoring import SnapshotChange, SnapshotChangeSet

    question = "What changed in the overdraft?"
    old, new = uuid4(), uuid4()
    facts = (
        _fact(OfferingId.OVERDRAFT, old, FieldPath.NOMINAL_RATE_MINIMUM, "21", n=1),
        _fact(OfferingId.OVERDRAFT, new, FieldPath.NOMINAL_RATE_MINIMUM, "20", n=2),
        _fact(
            OfferingId.OVERDRAFT,
            old,
            FieldPath.FEE_SERVICE,
            None,
            status=ExtractionStatus.NOT_STATED,
            n=3,
        ),
        _fact(
            OfferingId.OVERDRAFT, new, FieldPath.FEE_SERVICE, "5000", unit="money", n=4
        ),
    )
    change = SnapshotChangeSet(
        id=uuid4(),
        run_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        previous_snapshot_id=old,
        current_snapshot_id=new,
        changes=(
            SnapshotChange(field="interest_rate", previous="21", current="20"),
            SnapshotChange(field="fees", previous=None, current="5000"),
        ),
        created_at=NOW - timedelta(hours=1),
    )
    service = StructuredTariffQueryService(
        _Repository((_profile(OfferingId.OVERDRAFT, new),), facts, (change,))
    )
    plan = _plan(
        question,
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.OVERDRAFT,),
        operation=QueryOperation.HISTORY,
    )
    result = await service.answer(plan, question, now=NOW)

    assert result.status is QueryStatus.ANSWERED
    items = result.metadata["changes"][0]["changes"]
    assert {item["field"] for item in items} == {"interest_rate", "fees"}


# --- RR27 / RR28 -------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True, reason="RR27: the after-run answer uses the run's scope"
)
@pytest.mark.asyncio
async def test_rr27_offering_request_joining_a_family_run_answers_the_offering() -> (
    None
):
    from app.domain.interpretation import QueryShape
    from app.domain.monitoring import MonitoringRun, RunCommand, RunStatus, RunTrigger
    from app.services.monitoring_node import (
        MonitoringAnswerRequest,
        MonitoringNodeInput,
        MonitoringResult,
        _with_answer,
    )

    class _Router:
        def __init__(self) -> None:
            self.plans: list = []

        async def answer_plan(self, plan, question):
            self.plans.append(plan)
            return SimpleNamespace(
                status=QueryStatus.ANSWERED,
                model_dump=lambda mode: {"status": "answered"},
            )

    run = MonitoringRun(
        id=uuid4(),
        command=RunCommand(product=ProductType.MORTGAGE, trigger=RunTrigger.SCHEDULE),
        status=RunStatus.SUCCEEDED,
        created_at=NOW,
        updated_at=NOW,
    )
    request = MonitoringNodeInput(
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_EXPRESS,
        answer=MonitoringAnswerRequest(
            question="What is the Express Mortgage rate?",
            product=ProductType.MORTGAGE,
            offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
            shape=QueryShape(operation=QueryOperation.SINGLE, fields=RATES),
        ),
    )
    router = _Router()
    result = await _with_answer(
        router, MonitoringResult(status="succeeded"), run, request
    )

    assert router.plans[0].offering_ids == (OfferingId.MORTGAGE_EXPRESS,)
    assert result.answer_status == "answered"


@pytest.mark.xfail(
    strict=True, reason="RR28: history values reach the model without evidence"
)
def test_rr28_history_values_carry_a_compact_citation() -> None:
    from app.domain.intent import HistoryQuery, HistoryRequestKind
    from app.domain.tariff_queries import HistoryResultStatus, TariffHistoryResult
    from app.tools.reads import tariff_history_payload
    from tests.fixtures.structured_tariffs import accepted_snapshot

    snapshot = accepted_snapshot("consumer")
    result = TariffHistoryResult(
        query=HistoryQuery(kind=HistoryRequestKind.SHOW_HISTORY),
        status=HistoryResultStatus.HISTORY_FOUND,
        window_start=NOW - timedelta(days=30),
        window_end=NOW,
        snapshots=(snapshot,),
    )
    payload = tariff_history_payload(result)

    citations = payload["snapshots"][0]["citations"]
    assert citations
    first = next(iter(citations.values()))[0]
    assert first["source_url"].startswith("https://")
    assert 0 < len(first["quote"]) <= 300
