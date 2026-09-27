from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.intent import RequestIntent
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    AnswerStatus,
    QuestionCommand,
)
from app.domain.structured_tariffs import (
    FieldPath,
    QueryOperation,
    QueryStatus,
    ResolutionPlan,
)
from app.services.answer_read_model import TariffAnswerRouter
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.fixtures.evaluation_corpus import EvaluationRepository
from tests.fixtures.interpretations import interp, scripted_resolver

NOW = datetime(2026, 9, 22, tzinfo=UTC)
QUESTION = "What is the nominal interest rate of the Overdraft?"
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"


def _plan() -> ResolutionPlan:
    issued = datetime.now(UTC)
    return ResolutionPlan(
        session_id="session-1",
        turn_id="turn-1",
        question_sha256=hashlib.sha256(QUESTION.encode()).hexdigest(),
        issued_at=issued,
        expires_at=issued + timedelta(minutes=5),
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.OVERDRAFT,),
        operation=QueryOperation.SINGLE,
        fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
    )


def _shapes():
    """The interpreter's shape for each typed question (D9), scripted."""
    answer = RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION
    nominal = (FieldPath.NOMINAL_RATE_MINIMUM, FieldPath.NOMINAL_RATE_MAXIMUM)
    return scripted_resolver(
        {
            QUESTION: interp(
                answer,
                offering_ids=(OfferingId.OVERDRAFT,),
                operation=QueryOperation.SINGLE,
                fields=nominal,
            ),
            "What is the nominal interest rate?": interp(
                answer,
                product=ProductType.CONSUMER_LOAN,
                operation=QueryOperation.SINGLE,
                fields=nominal,
            ),
            "What application fee applies to the Express Mortgage?": interp(
                answer,
                offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
                operation=QueryOperation.SINGLE,
                fields=(FieldPath.FEE_APPLICATION,),
            ),
        }
    ).shape_for


def _router() -> TariffAnswerRouter:
    return TariffAnswerRouter(
        StructuredTariffQueryService(EvaluationRepository()), shapes=_shapes()
    )


@pytest.mark.asyncio
async def test_structured_mode_answers_a_plan_from_typed_accepted_facts() -> None:
    router = _router()

    result = await router.answer_plan(_plan(), QUESTION)

    assert result.status is QueryStatus.ANSWERED
    assert result.facts and all(fact.evidence for fact in result.facts)


@pytest.mark.asyncio
async def test_typed_api_question_keeps_citations() -> None:
    router = _router()

    result = await router.answer_question(
        QuestionCommand(
            query=QUESTION,
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.OVERDRAFT,
        )
    )

    assert result.status is AnswerStatus.ANSWERED
    assert result.citations
    assert all(item.evidence_id for item in result.citations)
    assert all(item.excerpt for item in result.citations)
    assert result.audit_metadata["read_model"] == "structured"


@pytest.mark.asyncio
async def test_typed_api_question_without_product_stays_ambiguous() -> None:
    router = _router()

    result = await router.answer_question(QuestionCommand(query=QUESTION))

    assert result.status is AnswerStatus.AMBIGUOUS_PRODUCT


@pytest.mark.asyncio
async def test_unresolvable_family_scope_abstains_instead_of_widening() -> None:
    router = _router()

    result = await router.answer_question(
        QuestionCommand(
            query="What is the nominal interest rate?",
            product=ProductType.CONSUMER_LOAN,
        )
    )

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert "one offering" in str(result.audit_metadata["reason"])


@pytest.mark.asyncio
async def test_structured_abstention_does_not_leak_an_uncited_answer() -> None:
    router = _router()

    result = await router.answer_question(
        QuestionCommand(
            query="What application fee applies to the Express Mortgage?",
            product=ProductType.MORTGAGE,
            offering_id=OfferingId.MORTGAGE_EXPRESS,
        )
    )

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert result.answer is None
    assert result.citations == ()
    assert result.audit_metadata["query_status"] == "missing"
