from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.models import KnowledgeDocumentKind, OfferingId, ProductType
from app.domain.monitoring import (
    AnswerCitation,
    AnswerFailureCode,
    AnswerResult,
    AnswerStatus,
)
from app.domain.structured_tariffs import QueryStatus
from app.services.intent_resolution import RequestResolver
from app.services.structured_shadow_read import (
    DEFAULT_SHADOW_CASES,
    ShadowCase,
    StructuredShadowReader,
)
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.fixtures.evaluation_corpus import EvaluationRepository

NOW = datetime(2026, 9, 22, tzinfo=UTC)
CONSUMER_URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
OTHER_URL = "https://ameriabank.am/en/personal/loans/other"


def _resolver() -> RequestResolver:
    from app.config import load_seed_catalog
    from app.config.models import IntentResolutionSettings

    return RequestResolver(load_seed_catalog(), IntentResolutionSettings())


class _Legacy:
    def __init__(self, result: AnswerResult) -> None:
        self.result = result
        self.commands = []

    async def answer(self, command):
        self.commands.append(command)
        return self.result


def _legacy_answered(url: str = CONSUMER_URL) -> AnswerResult:
    return AnswerResult(
        status=AnswerStatus.ANSWERED,
        answer="The nominal rate is 14%.",
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        citations=(
            AnswerCitation(
                chunk_id="chunk-1",
                source_url=url,
                document_name="Overdraft terms",
                excerpt="Nominal rate schedule",
                page=1,
                section="Rates",
            ),
        ),
        as_of=NOW,
    )


def _legacy_abstained() -> AnswerResult:
    return AnswerResult(
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        product=ProductType.MORTGAGE,
        failure_code=AnswerFailureCode.INSUFFICIENT_EVIDENCE,
    )


OVERDRAFT_CASE = ShadowCase(
    case_id="single_overdraft_rate",
    question="What is the nominal interest rate of the Overdraft?",
    product=ProductType.CONSUMER_LOAN,
    offering_id=OfferingId.OVERDRAFT,
)
MISSING_CASE = ShadowCase(
    case_id="missing_express_mortgage_fee",
    question="What application fee applies to the Express Mortgage?",
    product=ProductType.MORTGAGE,
    offering_id=OfferingId.MORTGAGE_EXPRESS,
)


@pytest.mark.asyncio
async def test_structured_only_run_makes_no_legacy_call_and_records_counts() -> None:
    reader = StructuredShadowReader(
        _resolver(), StructuredTariffQueryService(EvaluationRepository())
    )

    report = await reader.run((OVERDRAFT_CASE, MISSING_CASE))

    assert not report.legacy_enabled
    assert report.agreement_counts == {"structured_only_run": 2}
    assert report.structured_status_counts == {"answered": 1, "missing": 1}
    assert report.legacy_status_counts == {"not_run": 2}
    assert report.structured_answer_rate == 0.5
    assert not report.gate_passed
    assert report.gate_reason == "the legacy path was not run, so no comparison exists"
    answered = report.observations[0]
    assert answered.structured_facts > 0
    assert answered.structured_citations > 0
    assert answered.legacy_citations == 0


@pytest.mark.asyncio
async def test_observation_logs_no_question_source_or_answer_text(caplog) -> None:
    legacy = _Legacy(_legacy_answered())
    reader = StructuredShadowReader(
        _resolver(),
        StructuredTariffQueryService(EvaluationRepository()),
        legacy,
    )

    with caplog.at_level("INFO"):
        observation = await reader.observe(OVERDRAFT_CASE)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert OVERDRAFT_CASE.question not in logged
    assert "Nominal rate schedule" not in logged
    assert "The nominal rate is 14%." not in logged
    assert observation.question_sha256[:12] in logged
    assert observation.agreement == "both_answered"


@pytest.mark.asyncio
async def test_legacy_answer_over_structured_abstention_is_an_audited_mismatch() -> (
    None
):
    reader = StructuredShadowReader(
        _resolver(),
        StructuredTariffQueryService(EvaluationRepository()),
        _Legacy(_legacy_answered()),
    )

    report = await reader.run((MISSING_CASE,))

    assert report.observations[0].agreement == "legacy_only"
    assert report.mismatches
    assert (
        report.mismatches[0].mismatch_reason
        == "legacy answered where the structured read model abstains"
    )
    assert not report.gate_passed


@pytest.mark.asyncio
async def test_legacy_citation_outside_structured_evidence_is_flagged() -> None:
    reader = StructuredShadowReader(
        _resolver(),
        StructuredTariffQueryService(EvaluationRepository()),
        _Legacy(_legacy_answered(OTHER_URL)),
    )

    observation = await reader.observe(OVERDRAFT_CASE)

    assert observation.agreement == "both_answered"
    assert observation.legacy_only_evidence_sources == 1
    assert observation.shared_evidence_sources == 0
    assert (
        observation.mismatch_reason
        == "legacy cited a source the structured evidence does not cover"
    )


@pytest.mark.asyncio
async def test_both_abstained_is_agreement_not_mismatch() -> None:
    reader = StructuredShadowReader(
        _resolver(),
        StructuredTariffQueryService(EvaluationRepository()),
        _Legacy(_legacy_abstained()),
    )

    report = await reader.run((MISSING_CASE,))

    assert report.observations[0].agreement == "both_abstained"
    assert not report.gate_passed
    assert (
        report.gate_reason
        == "the structured read model answered no representative query"
    )


@pytest.mark.asyncio
async def test_reader_reports_errors_instead_of_raising() -> None:
    class _Broken:
        async def answer(self, plan, question):
            raise RuntimeError("projection unavailable")

    reader = StructuredShadowReader(_resolver(), _Broken())

    observation = await reader.observe(OVERDRAFT_CASE)

    assert observation.agreement == "structured_error"
    assert observation.structured_error == "RuntimeError"
    assert observation.mismatch_reason == "structured path raised RuntimeError"


@pytest.mark.asyncio
async def test_default_cases_cover_every_deterministic_branch() -> None:
    reader = StructuredShadowReader(
        _resolver(), StructuredTariffQueryService(EvaluationRepository())
    )

    report = await reader.run(DEFAULT_SHADOW_CASES)

    operations = {item.structured_operation for item in report.observations}
    assert operations == {"single", "compare", "family_rank", "history"}
    assert QueryStatus.MISSING.value in report.structured_status_counts
    assert not report.mismatches
    assert report.gate_reason == "the legacy path was not run, so no comparison exists"
    assert KnowledgeDocumentKind.SOURCE  # legacy kinds stay importable for rollback


@pytest.mark.asyncio
async def test_cutover_gate_opens_only_after_a_clean_two_path_comparison() -> None:
    reader = StructuredShadowReader(
        _resolver(),
        StructuredTariffQueryService(EvaluationRepository()),
        _Legacy(_legacy_answered()),
    )

    report = await reader.run((OVERDRAFT_CASE,))

    assert report.legacy_enabled
    assert report.observations[0].shared_evidence_sources == 1
    assert report.gate_reason is None
    assert report.gate_passed
