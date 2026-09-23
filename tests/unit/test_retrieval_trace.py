from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import OfferingId, ProductType
from app.domain.structured_tariffs import (
    FieldPath,
    QueryOperation,
    ResolutionPlan,
)
from app.services.retrieval_trace import (
    RETRIEVAL_LOGGER_NAME,
    RetrievalTraceLevel,
    configure_retrieval_trace,
    current_level,
)
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.fixtures.evaluation_corpus import EvaluationRepository

QUESTION = "What is the nominal interest rate of the Overdraft?"


@pytest.fixture(autouse=True)
def _restore_level():
    previous = current_level()
    yield
    configure_retrieval_trace(previous)


def _plan() -> ResolutionPlan:
    issued = datetime.now(UTC)
    return ResolutionPlan(
        session_id="trace-session",
        turn_id="trace-turn",
        question_sha256=hashlib.sha256(QUESTION.encode()).hexdigest(),
        issued_at=issued,
        expires_at=issued + timedelta(minutes=5),
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.OVERDRAFT,),
        operation=QueryOperation.SINGLE,
        fields=(FieldPath.NOMINAL_RATE_MINIMUM, FieldPath.NOMINAL_RATE_MAXIMUM),
    )


async def _answer(caplog, level: RetrievalTraceLevel):
    configure_retrieval_trace(level)
    with caplog.at_level("INFO", logger=RETRIEVAL_LOGGER_NAME):
        await StructuredTariffQueryService(EvaluationRepository()).answer(
            _plan(), QUESTION
        )
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == RETRIEVAL_LOGGER_NAME
    ]


@pytest.mark.asyncio
async def test_off_emits_nothing(caplog) -> None:
    assert await _answer(caplog, RetrievalTraceLevel.OFF) == []


@pytest.mark.asyncio
async def test_summary_emits_one_closing_line_with_the_outcome(caplog) -> None:
    lines = await _answer(caplog, RetrievalTraceLevel.SUMMARY)

    assert len(lines) == 1
    assert "status=answered" in lines[0]
    assert "elapsed_ms=" in lines[0]
    assert "trace=" in lines[0]


@pytest.mark.asyncio
async def test_steps_records_every_stage_in_call_order(caplog) -> None:
    lines = await _answer(caplog, RetrievalTraceLevel.STEPS)

    stages = [
        part.removeprefix("stage=")
        for line in lines
        for part in line.split()
        if part.startswith("stage=")
    ]
    assert stages == [
        "begin",
        "plan.authorized",
        "profiles.loaded",
        "facts.loaded",
        "branch.selected",
        "lexical.query",
        "lexical.result",
        "vector.skipped",
        "fusion.ranked",
        "units.admitted",
    ]
    trace_ids = {
        part for line in lines for part in line.split() if part.startswith("trace=")
    }
    assert len(trace_ids) == 1, "every stage of one answer shares a trace ID"


@pytest.mark.asyncio
async def test_steps_keeps_question_and_unit_text_out_of_the_log(caplog) -> None:
    lines = await _answer(caplog, RetrievalTraceLevel.STEPS)

    logged = "\n".join(lines)
    assert QUESTION not in logged
    assert "nominal interest rate (rate.nominal.minimum)" not in logged
    # The question is still correlatable by its hash prefix.
    assert hashlib.sha256(QUESTION.encode()).hexdigest()[:12] in logged


@pytest.mark.asyncio
async def test_verbose_adds_derived_terms_and_unit_text(caplog) -> None:
    lines = await _answer(caplog, RetrievalTraceLevel.VERBOSE)

    logged = "\n".join(lines)
    assert "stage=lexical.terms" in logged
    assert '"nominal" or "interest" or "rate" or "overdraft"' in logged
    assert "stage=unit.content" in logged
    assert "minimum nominal interest rate (rate.nominal.minimum)" in logged


@pytest.mark.asyncio
async def test_a_failing_answer_still_closes_its_trace(caplog) -> None:
    class _Broken(EvaluationRepository):
        async def facts(self, **kwargs):
            raise RuntimeError("projection unavailable")

    configure_retrieval_trace(RetrievalTraceLevel.STEPS)
    with caplog.at_level("INFO", logger=RETRIEVAL_LOGGER_NAME):
        with pytest.raises(RuntimeError):
            await StructuredTariffQueryService(_Broken()).answer(_plan(), QUESTION)

    closing = [
        record.getMessage()
        for record in caplog.records
        if record.name == RETRIEVAL_LOGGER_NAME and "elapsed_ms=" in record.getMessage()
    ]
    assert closing
    assert "outcome=error" in closing[-1]
    assert "error_type=RuntimeError" in closing[-1]
