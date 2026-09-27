"""Regression cases from the first live evaluation (2026-09-27).

One test (or a few) per item of
fix-process/1st-iteration-fixes/1st-iteration-fix-plan.md; F-numbers refer to it.
Captured data comes from tests/fixtures/first_iteration.py. No test calls a model.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config import SemanticExtractionSettings
from app.domain.models import OfferingId, ProductType
from app.domain.semantic_extraction import (
    ExtractionBatchResponse,
    ExtractionField,
    ExtractionStatus,
)
from app.domain.structured_tariffs import (
    FieldPath,
    QueryOperation,
    QueryStatus,
    RankDirection,
)
from app.services.structured_projection import StructuredTariffProjector
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.fixtures.first_iteration import (
    captured_accepted_snapshot,
    commercial_raw_answer,
)

NOW = datetime(2026, 9, 22, tzinfo=UTC)


# --- helpers ---------------------------------------------------------------------


def _projection(offering_id: str):
    return StructuredTariffProjector().project(
        captured_accepted_snapshot(offering_id), display_name=offering_id
    )


def _query_plan(question: str, **changes):
    import hashlib

    from app.domain.structured_tariffs import ResolutionPlan

    values = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
        "issued_at": NOW - timedelta(minutes=1),
        "expires_at": NOW + timedelta(minutes=5),
        "product": ProductType.CONSUMER_LOAN,
        "offering_ids": (OfferingId.CONSUMER_STANDARD,),
        "operation": QueryOperation.SINGLE,
        "fields": (FieldPath.NOMINAL_RATE_MINIMUM,),
        "conditions": {},
    }
    values.update(changes)
    return ResolutionPlan(**values)


class _ProjectionRepository:
    """Active profiles and facts of the given captured projections."""

    def __init__(self, *projections) -> None:
        self.profiles = tuple(item.profile for item in projections)
        self.facts_ = tuple(fact for item in projections for fact in item.facts)

    async def active_profiles(self, *, bank, product, offering_ids):
        return tuple(item for item in self.profiles if item.offering_id in offering_ids)

    async def facts(self, *, snapshots, fields, include_inactive=False):
        return tuple(
            item
            for item in self.facts_
            if item.snapshot_id in snapshots and item.field_path in fields
        )

    async def lexical_units(self, **_):
        return ()

    async def accepted_changes(self, **_):
        return ()


class _States:
    """Why an in-scope offering has no published data (F1, F4)."""

    def __init__(self, states) -> None:
        self.states = states

    async def offering_states(self, *, bank, product, offering_ids):
        from app.domain.structured_tariffs import OfferingDataState

        return {
            offering: OfferingDataState(**self.states[offering])
            for offering in offering_ids
            if offering in self.states
        }


# --- F1: rankings disclose offerings without published data ------------------------

RANK_QUESTION = "Which consumer loan has the lowest nominal interest rate in AMD?"


@pytest.mark.asyncio
async def test_f1_a_ranking_names_every_offering_it_could_not_rank() -> None:
    repository = _ProjectionRepository(
        _projection("overdraft"), _projection("credit_line")
    )
    states = _States(
        {
            OfferingId.CONSUMER_STANDARD: {
                "state": "awaiting_review",
                "pending_reviews": 1,
            },
            OfferingId.ONLINE_CONSUMER_FINANCE: {"state": "never_monitored"},
        }
    )
    service = StructuredTariffQueryService(repository, offering_states=states)
    plan = _query_plan(
        RANK_QUESTION,
        operation=QueryOperation.FAMILY_RANK,
        offering_ids=(
            OfferingId.CONSUMER_STANDARD,
            OfferingId.OVERDRAFT,
            OfferingId.CREDIT_LINE,
            OfferingId.ONLINE_CONSUMER_FINANCE,
        ),
        fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
        rank_direction=RankDirection.LOWEST,
        conditions={"currency": "AMD"},
    )

    result = await service.answer(plan, RANK_QUESTION, now=NOW)

    assert result.status is QueryStatus.ANSWERED
    coverage = {item["offering_id"]: item for item in result.metadata["coverage"]}
    assert coverage["overdraft"]["state"] == "ranked"
    assert coverage["credit_line"]["state"] == "ranked"
    assert coverage["consumer_standard"]["state"] == "awaiting_review"
    assert coverage["consumer_standard"]["pending_reviews"] == 1
    assert coverage["online_consumer_finance"]["state"] == "never_monitored"
    not_ranked = {
        item["offering_id"]: item["reason"] for item in result.metadata["not_ranked"]
    }
    assert not_ranked == {
        "consumer_standard": "awaiting_review",
        "online_consumer_finance": "never_monitored",
    }
    assert result.answer.startswith("ranked 2 of 4")


# --- F2: a single-currency offering's rate takes that currency ----------------------


def test_f2_online_consumer_finance_rate_inherits_its_amount_currency() -> None:
    rates = [
        fact
        for fact in _projection("online_consumer_finance").facts
        if fact.field_path.value.startswith("rate.nominal")
    ]
    assert rates
    assert {fact.currency for fact in rates} == {"AMD"}
    assert all(
        any(
            isinstance(item, dict) and "inferred" in str(item.get("value", ""))
            for item in fact.conditions
        )
        for fact in rates
    )


def test_f2_a_two_currency_offering_is_left_alone() -> None:
    # Overdraft states its own currency on every rate; nothing is inferred.
    rates = [
        fact
        for fact in _projection("overdraft").facts
        if fact.field_path.value.startswith("rate.nominal")
    ]
    assert rates and all(fact.currency == "AMD" for fact in rates)
    assert not any(
        "inferred" in str(item.get("value", ""))
        for fact in rates
        for item in fact.conditions
        if isinstance(item, dict)
    )


# --- F3: "terms" asks for the offering's key terms ---------------------------------


def test_f3_purpose_and_terms_asks_for_amount_rate_and_term() -> None:
    from tests.fixtures.recorded_interpretations import load_recordings

    entries = load_recordings()["target_q15_online_finance_purpose"]
    fields = set()
    for entry in entries.values():
        fields.update((entry["interpretation"].get("query") or {}).get("fields") or [])
    assert "identity.purpose" in fields
    assert any(field.startswith("amount.") for field in fields)
    assert any(field.startswith("rate.") for field in fields)
    assert any(field.startswith("term.") for field in fields)


def test_f3_the_interpreter_is_told_what_broad_words_mean() -> None:
    from app.services import intent_resolution

    prompt = intent_resolution.INTERPRETER_INSTRUCTION
    assert '"terms"' in prompt and "key terms" in prompt


# --- F4: the reason an answer is missing --------------------------------------------


@pytest.mark.asyncio
async def test_f4_a_missing_answer_says_the_offering_awaits_review() -> None:
    question = "What repayment term does the Primary Market Mortgage offer?"
    states = _States(
        {
            OfferingId.MORTGAGE_PRIMARY: {
                "state": "awaiting_review",
                "pending_reviews": 2,
            }
        }
    )
    service = StructuredTariffQueryService(
        _ProjectionRepository(), offering_states=states
    )
    result = await service.answer(
        _query_plan(
            question,
            product=ProductType.MORTGAGE,
            offering_ids=(OfferingId.MORTGAGE_PRIMARY,),
            fields=(FieldPath.TERM_MAXIMUM_MONTHS,),
        ),
        question,
        now=NOW,
    )
    assert result.status is QueryStatus.MISSING
    assert result.reason_code == "awaiting_review"
    assert result.metadata["coverage"][0]["pending_reviews"] == 2


# --- F5: a fee the bank does not publish --------------------------------------------


@pytest.mark.asyncio
async def test_f5_a_fee_missing_from_the_published_fee_list_is_not_stated() -> None:
    question = "What application fee applies to the Express Mortgage?"
    service = StructuredTariffQueryService(
        _ProjectionRepository(_projection("mortgage_express"))
    )
    result = await service.answer(
        _query_plan(
            question,
            product=ProductType.MORTGAGE,
            offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
            fields=(FieldPath.FEE_APPLICATION,),
        ),
        question,
        now=NOW,
    )
    assert result.status is QueryStatus.INSUFFICIENT_EVIDENCE
    assert result.reason_code == "not_stated_in_source"
    # The fee list that was checked is cited, so the answer can point at it.
    assert result.facts and all(fact.evidence for fact in result.facts)


# --- F6: the catalog intro only for greetings ----------------------------------------


@pytest.fixture
def recorded_chat():
    from app.config import load_seed_catalog
    from app.services.intent_resolution import RequestResolver
    from app.tools import configure_services
    from tests.fixtures.recorded_interpretations import RecordedInterpreter
    from tests.unit.test_tool_flows import _Chat

    def wire(case_id: str):
        configure_services(
            request_resolver=RequestResolver(
                load_seed_catalog(), interpreter=RecordedInterpreter(case_id=case_id)
            ),
        )
        return _Chat()

    yield wire

    configure_services()


@pytest.mark.asyncio
async def test_f6_a_tariff_question_gets_no_catalog_intro(recorded_chat) -> None:
    from app.tools import resolve_request

    chat = recorded_chat("target_q01_overdraft_nominal_rate")
    chat.say("What is the nominal interest rate of the Overdraft?")
    result = await resolve_request(chat)
    assert "catalog_intro" not in result


@pytest.mark.asyncio
async def test_f6_a_catalog_question_still_gets_the_intro(recorded_chat) -> None:
    from app.tools import resolve_request

    chat = recorded_chat("eval_list_catalog")
    chat.say("Which Ameria loan products do you support?")
    result = await resolve_request(chat)
    assert "catalog_intro" in result


# --- F7: long and stitched quotes -----------------------------------------------------

LTV_TEXT = (
    "Loan-to-value ratio. 1. For AMD loans with a term of 61-240 months: up to 90% of "
    "the lower of the appraised market value or purchase price of pledged property. "
    "For AMD loans with a term above 240 months: up to 80% of the lower of the two."
)
LTV_VALUE = json.dumps(
    [
        {
            "value": 90,
            "conditions": [{"dimension": "term_range", "value": "61-240 months"}],
        },
        {
            "value": 80,
            "conditions": [{"dimension": "term_range", "value": "above 240 months"}],
        },
    ]
)
STITCHED = (
    "For AMD loans with a term of 61-240 months: up to 90%... "
    "For AMD loans with a term above 240 months: up to 80%"
)


@pytest.mark.asyncio
async def test_f7_a_quote_stitched_with_an_ellipsis_is_split_into_verbatim_parts() -> (
    None
):
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        ScriptedExtractor,
        _mortgage_bundle,
        _service,
    )

    bundle, discovery = _mortgage_bundle(LTV_TEXT)
    extractor = ScriptedExtractor({ExtractionField.LTV_PCT: (LTV_VALUE, STITCHED)})
    result = await _service(extractor).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    assert ExtractionField.LTV_PCT not in {item.field for item in result.review_items}
    ltv = next(
        item
        for item in result.validated_fields
        if item.field is ExtractionField.LTV_PCT
    )
    assert len(ltv.evidence) == 2
    assert all("..." not in citation.quote for citation in ltv.evidence)


def test_f7_the_commercial_answers_fit_the_response_schema() -> None:
    for attempt in (1, 2):
        ExtractionBatchResponse.model_validate_json(commercial_raw_answer(attempt))


def test_f7_the_prompt_states_the_quote_limit() -> None:
    from app.services.semantic_extraction import (
        SEMANTIC_EXTRACTION_INSTRUCTION as EXTRACTION_INSTRUCTION,
    )

    assert "300 characters" in EXTRACTION_INSTRUCTION
    assert "never use '...'" in EXTRACTION_INSTRUCTION


# --- F8 / F20: one invalid field does not discard the call --------------------------


def _with_bad_citation(raw: str) -> str:
    data = json.loads(raw)
    data["results"][3]["evidence"][0]["evidence_id"] = "not-an-evidence-id"
    return json.dumps(data)


def test_f8_an_invalid_result_is_dropped_and_the_rest_kept() -> None:
    from app.services.semantic_extraction import parse_batch_response

    parsed = parse_batch_response(_with_bad_citation(commercial_raw_answer(1)))
    assert len(parsed.response.results) == 7
    assert [field for field, _ in parsed.dropped] == [ExtractionField.LTV_PCT]


@pytest.mark.asyncio
async def test_f8_a_dropped_field_reaches_review_with_its_schema_error() -> None:
    from app.domain.semantic_extraction import ValidationIssue
    from app.services.semantic_extraction import ExtractorOutput
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        ScriptedExtractor,
        _mortgage_bundle,
        _service,
    )

    issue = ValidationIssue(
        location=("evidence", 0, "quote"),
        message="String should have at most 10000 characters",
        error_type="string_too_long",
    )

    class DropsLtv(ScriptedExtractor):
        async def extract(self, batch):
            response = await super().extract(batch)
            if ExtractionField.LTV_PCT not in batch.fields:
                return response
            return ExtractorOutput(
                response=ExtractionBatchResponse(
                    results=tuple(
                        item
                        for item in response.results
                        if item.field is not ExtractionField.LTV_PCT
                    )
                ),
                dropped=((ExtractionField.LTV_PCT, (issue,)),),
            )

    bundle, discovery = _mortgage_bundle(LTV_TEXT)
    settings = SemanticExtractionSettings(max_repairs_per_run=0)
    result = await _service(DropsLtv(), settings=settings).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    (review,) = [
        item for item in result.review_items if item.field is ExtractionField.LTV_PCT
    ]
    assert review.validation_issues[0].error_type == "string_too_long"
    assert review.validation_issues[0].location[0] == "ltv_pct"
    # The call's other fields were kept, not sent to review with it.
    assert any(
        item.field is ExtractionField.CATEGORY for item in result.validated_fields
    )


def test_f20_a_schema_failure_names_where_it_failed() -> None:
    from app.services.semantic_extraction import (
        SemanticExtractionCallError,
        parse_batch_response,
    )

    parsed = parse_batch_response(_with_bad_citation(commercial_raw_answer(1)))
    ((_, issues),) = parsed.dropped
    assert issues[0].location[:3] == ("evidence", 0, "evidence_id")
    with pytest.raises(SemanticExtractionCallError, match=r"results\[0\]"):
        parse_batch_response('{"results": [{"field": "ltv_pct", "status": "bogus"}]}')


# --- F10: Ameria's income-document wording ---------------------------------------------

INCOME_TEXT = (
    "Documents required after initial approval: Proof of employment and/or other "
    "income. If you apply for a loan online, you only need an identity document."
)
INCOME_VALUE = json.dumps({"default_required": True, "exceptions": []})


@pytest.mark.asyncio
async def test_f10_proof_of_employment_and_other_income_is_explicit() -> None:
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        ScriptedExtractor,
        _mortgage_bundle,
        _service,
    )

    bundle, discovery = _mortgage_bundle(INCOME_TEXT)
    extractor = ScriptedExtractor(
        {
            ExtractionField.INCOME_VERIFICATION_REQUIRED: (
                INCOME_VALUE,
                "Proof of employment and/or other income",
            )
        }
    )
    result = await _service(extractor).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    assert ExtractionField.INCOME_VERIFICATION_REQUIRED not in {
        item.field for item in result.review_items
    }


@pytest.mark.asyncio
async def test_f10_a_creditworthiness_passage_is_still_not_income_evidence() -> None:
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        ScriptedExtractor,
        _mortgage_bundle,
        _service,
    )

    text = "The decision is made based on your creditworthiness criteria."
    bundle, discovery = _mortgage_bundle(text)
    extractor = ScriptedExtractor(
        {
            ExtractionField.INCOME_VERIFICATION_REQUIRED: (
                INCOME_VALUE,
                "creditworthiness criteria",
            )
        }
    )
    result = await _service(extractor).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    assert ExtractionField.INCOME_VERIFICATION_REQUIRED in {
        item.field for item in result.review_items
    }


# --- F11: broken JSON in value_json is repaired, never guessed ------------------------


@pytest.mark.asyncio
async def test_f11_an_unparseable_value_is_sent_to_the_repair_call() -> None:
    """Guard: this already works; the 2026-09-27 JSON reviews came from F10/F12."""
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        ScriptedExtractor,
        _mortgage_bundle,
        _service,
    )

    class BrokenThenRepaired(ScriptedExtractor):
        async def extract(self, batch):
            response = await super().extract(batch)
            if "__repair_" in batch.id:
                return response
            return ExtractionBatchResponse(
                results=tuple(
                    item.model_copy(update={"value_json": item.value_json[:-1]})
                    if item.field is ExtractionField.INCOME_VERIFICATION_REQUIRED
                    else item
                    for item in response.results
                )
            )

    bundle, discovery = _mortgage_bundle(INCOME_TEXT)
    extractor = BrokenThenRepaired(
        {
            ExtractionField.INCOME_VERIFICATION_REQUIRED: (
                INCOME_VALUE,
                "Documents required after initial approval",
            )
        }
    )
    result = await _service(extractor).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    repairs = [
        output.batch_id
        for output in result.raw_batch_outputs
        if "__repair_income_verification_required" in output.batch_id
    ]
    assert repairs


# --- F12: repair budget ------------------------------------------------------------------


def test_f12_six_repairs_per_offering_by_default() -> None:
    from app.config.environment import EnvironmentSettings

    assert SemanticExtractionSettings().max_repairs_per_run == 6
    assert (
        EnvironmentSettings.model_fields[
            "semantic_extraction_max_repairs_per_run"
        ].default
        == 6
    )


@pytest.mark.asyncio
async def test_f12_skipped_repairs_are_logged_by_field(caplog) -> None:
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        ScriptedExtractor,
        _mortgage_bundle,
        _service,
    )

    bundle, discovery = _mortgage_bundle(INCOME_TEXT)
    extractor = ScriptedExtractor(
        {
            ExtractionField.INCOME_VERIFICATION_REQUIRED: (
                "{broken",
                "Proof of employment",
            )
        }
    )
    settings = SemanticExtractionSettings(max_repairs_per_run=0)
    with caplog.at_level(logging.WARNING):
        await _service(extractor, settings=settings).extract(
            bundle, discovery, retrieved_at=RETRIEVED_AT
        )
    assert "income_verification_required" in caplog.text


# --- F13: confirm that the source does not state a required field ----------------------


def test_f13_confirm_not_stated_is_offered_only_for_a_missing_field() -> None:
    from app.domain.review import ReviewDecisionType, ReviewReason
    from app.services.review_resolution import review_policy

    confirm = getattr(ReviewDecisionType, "CONFIRM_NOT_STATED", None)
    missing, _ = review_policy(ReviewReason.MISSING_REQUIRED_FIELD)
    invalid, _ = review_policy(ReviewReason.EXTRACTION_INVALID)
    if confirm is None:
        pytest.xfail("F13")
    assert confirm in missing
    assert confirm not in invalid


@pytest.mark.asyncio
async def test_f13_confirming_a_missing_field_publishes_the_snapshot() -> None:
    from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
    from app.domain.review import ReviewDecision, ReviewDecisionType
    from app.domain.semantic_extraction import SemanticExtractionResult
    from app.services.review_decisions import ReviewDecisionService
    from tests.unit.test_multi_review_approval import (
        NOW as REVIEW_NOW,
    )
    from tests.unit.test_multi_review_approval import (
        _extraction,
        _Reviews,
        _Snapshots,
        _task,
    )

    extraction = _extraction((ExtractionField.REPAYMENT,))
    snapshot = SnapshotAttempt(
        id=uuid4(),
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        status=SnapshotStatus.REVIEW_REQUIRED,
        normalized_tariff={},
        semantic_extraction=extraction.model_dump(mode="json"),
        validation={"accepted": False, "review_signals": []},
        canonical_sha256="a" * 64,
        created_at=REVIEW_NOW,
    )
    snapshots = _Snapshots(snapshot)
    task = _task(snapshot.id, ExtractionField.REPAYMENT)
    reviews = _Reviews([task], snapshots)

    await ReviewDecisionService(reviews, snapshots).apply(
        task.id,
        ReviewDecision(
            decision_type=ReviewDecisionType.CONFIRM_NOT_STATED,
            reason="The page and its PDFs state no repayment method.",
        ),
        reviewer="reviewer-1",
    )

    (update,) = reviews.updates
    assert update.ready_for_activation is True
    stored = SemanticExtractionResult.model_validate(update.semantic_extraction)
    repayment = next(
        item
        for item in stored.validated_fields
        if item.field is ExtractionField.REPAYMENT
    )
    assert repayment.status is ExtractionStatus.NOT_STATED
    assert repayment.confirmed_not_stated is True


@pytest.mark.asyncio
async def test_f13_a_remembered_confirmation_is_replayed_on_the_next_run() -> None:
    from app.domain.semantic_extraction import (
        RememberedReviewDecision,
        ValidatedFieldResult,
    )
    from app.repositories.review_memory import InMemoryReviewDecisionMemory
    from app.services.semantic_extraction import (
        InMemorySemanticExtractionRepository,
        SemanticExtractionService,
    )
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        ScriptedExtractor,
        _mortgage_bundle,
    )

    memory = InMemoryReviewDecisionMemory()
    service = SemanticExtractionService(
        ScriptedExtractor(),
        InMemorySemanticExtractionRepository(),
        SemanticExtractionSettings(),
        model_name="model-a",
        review_memory=memory,
    )
    bundle, discovery = _mortgage_bundle("Loan amount: AMD 3-150 million")
    discovery = discovery.model_copy(update={"offering_id": "mortgage_diaspora"})
    first = await service.extract(bundle, discovery, retrieved_at=RETRIEVED_AT)
    repayment = next(
        item
        for item in first.validated_fields
        if item.field is ExtractionField.REPAYMENT
    )
    assert repayment.status is ExtractionStatus.NOT_STATED
    assert repayment.confirmed_not_stated is False
    await memory.remember(
        RememberedReviewDecision(
            offering_id="mortgage_diaspora",
            field=ExtractionField.REPAYMENT,
            prompt_fingerprint=repayment.prompt_fingerprint,
            result_fingerprint=repayment.result_fingerprint,
            decision=ValidatedFieldResult(
                field=ExtractionField.REPAYMENT,
                status=ExtractionStatus.NOT_STATED,
                explanation="Reviewer confirmed not stated: page checked",
                batch_id="memory:review-1",
                confirmed_not_stated=True,
            ),
            reviewer="analyst",
            review_id="review-1",
        )
    )

    second = await service.extract(bundle, discovery, retrieved_at=RETRIEVED_AT)
    replayed = next(
        item
        for item in second.validated_fields
        if item.field is ExtractionField.REPAYMENT
    )
    assert replayed.confirmed_not_stated is True


# --- F9: the hero banner above the first heading ----------------------------------------


def test_f9_hero_tariff_lines_are_content_not_page_header() -> None:
    from app.domain.normalization import NormalizedBlockType
    from app.domain.source_discovery import CandidateLayout, DiscoveryScope
    from app.services.discovery_prefilter import build_discovery_candidates
    from tests.unit.test_source_discovery_fixes import _block, _bundle, _page

    page = _page(
        _block("b2", "EN • ՀԱՅ", block_type=NormalizedBlockType.LIST),
        _block("b3", "Apply online: Get a mortgage without income verification"),
        _block("b4", "Repayment term: 61 – 360 months"),  # noqa: RUF001 (the page's dash)
        _block("b5", "Loan amount: Up to AMD 100 million"),
        _block("b6", "Down payment: From 30%"),
        _block("b7", "Mortgage", block_type=NormalizedBlockType.HEADING),
    )
    sections = [
        candidate
        for candidate in build_discovery_candidates(_bundle(page))
        if candidate.scope is DiscoveryScope.SECTION
    ]
    header = next(c for c in sections if c.layout is CandidateLayout.PAGE_HEADER)
    assert header.member_source_ids == (
        "page:1::block::b2",
        "page:1::block::b3",
    )
    hero = [
        c
        for c in sections
        if c.layout is CandidateLayout.CONTENT
        and "page:1::block::b5" in c.member_source_ids
    ]
    assert hero and set(hero[0].member_source_ids) == {
        "page:1::block::b4",
        "page:1::block::b5",
        "page:1::block::b6",
    }


# --- F15, F16, F17: fee citations and readable locators ---------------------------------


def test_f15_each_fee_cites_its_own_evidence() -> None:
    fees = [
        fact
        for fact in _projection("credit_line").facts
        if fact.field_path.value.startswith("fee.")
    ]
    assert fees
    assert max(len(fact.evidence) for fact in fees) <= 3


def test_f16_fact_citations_carry_a_readable_section() -> None:
    facts = _projection("credit_line").facts
    sections = [
        evidence.locator.get("section") for fact in facts for evidence in fact.evidence
    ]
    assert any(sections)


def test_f16_the_model_sees_compact_citations_without_internal_ids() -> None:
    from app.tools.reads import model_facing_result

    fact = next(
        fact
        for fact in _projection("credit_line").facts
        if fact.field_path is FieldPath.EFFECTIVE_RATE_MAXIMUM
    )
    payload = model_facing_result(
        {"status": "answered", "facts": [fact.model_dump(mode="json")]}
    )
    (citation, *_) = payload["facts"][0]["evidence"]
    assert set(citation) <= {"source_url", "section", "page", "quote"}
    assert "xpath" not in json.dumps(payload)


def test_f17_an_unsecured_offering_lists_no_collateral_service_fees() -> None:
    descriptions = [
        str((fact.value or {}).get("description", "")).casefold()
        for fact in _projection("credit_line").facts
        if fact.field_path.value.startswith("fee.")
    ]
    assert descriptions
    assert not any(
        word in text.replace("not related to the collateral", "")
        for text in descriptions
        for word in ("collateral", "pledged", "vehicle", "security interest")
    )
    # A consent fee that says it is not about collateral stays.
    assert any("not related to the collateral" in text for text in descriptions)


def test_f17_a_mortgage_keeps_its_collateral_fees() -> None:
    descriptions = [
        str((fact.value or {}).get("description", "")).casefold()
        for fact in _projection("mortgage_express").facts
        if fact.field_path.value.startswith("fee.")
    ]
    assert any("collateral" in text or "pledge" in text for text in descriptions)


# --- F18: one in-run retry of a transient fetch failure ---------------------------------


@pytest.mark.xfail(strict=True, reason="F18")
@pytest.mark.asyncio
async def test_f18_a_transient_browser_failure_is_retried_once() -> None:
    from app.services.acquisition_errors import AcquisitionError, AcquisitionFailure
    from app.services.monitoring_pipeline import acquire_with_retry

    calls = []

    async def acquire(url):
        calls.append(url)
        if len(calls) == 1:
            raise AcquisitionError(
                AcquisitionFailure.BROWSER_FAILED, "navigation timeout"
            )
        return "artifact"

    assert await acquire_with_retry(acquire, "https://x", delay_seconds=0) == "artifact"
    assert len(calls) == 2


# --- F19: pipeline model calls carry the run --------------------------------------------


@pytest.mark.xfail(strict=True, reason="F19")
def test_f19_a_pipeline_call_is_attributed_to_its_run() -> None:
    from app.services.model_call_usage import active_run_id, pipeline_usage_scope

    run_id = uuid4()
    context = SimpleNamespace(state={}, invocation_id="inv-1")
    assert active_run_id(context) is None
    with pipeline_usage_scope(run_id, "overdraft"):
        assert active_run_id(context) == run_id
    assert active_run_id(context) is None


# --- F21: the scheduler can be switched off ---------------------------------------------


@pytest.mark.xfail(strict=True, reason="F21")
def test_f21_schedule_enabled_setting(monkeypatch) -> None:
    from app.config.loader import load_settings

    assert load_settings(_env_file=None).scheduler.enabled is True
    monkeypatch.setenv("SCHEDULE_ENABLED", "false")
    assert load_settings(_env_file=None).scheduler.enabled is False
