from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    AnswerFailureCode,
    AnswerResult,
    AnswerStatus,
    MonitoringRun,
    QuestionCommand,
    RunCommand,
    RunStatus,
    RunTrigger,
    SnapshotAttempt,
    SnapshotStatus,
)


def test_offering_ids_map_to_their_product_family() -> None:
    assert OfferingId.CONSUMER_STANDARD.product is ProductType.CONSUMER_LOAN
    assert OfferingId.OVERDRAFT.product is ProductType.CONSUMER_LOAN
    assert OfferingId.MORTGAGE_PRIMARY.product is ProductType.MORTGAGE
    assert OfferingId.MORTGAGE_CONSTRUCTION.product is ProductType.MORTGAGE


def test_run_command_rejects_offering_from_another_family() -> None:
    with pytest.raises(ValidationError, match="does not belong"):
        RunCommand(
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.MORTGAGE_PRIMARY,
            trigger=RunTrigger.API,
        )


def test_run_statuses_are_typed_and_terminal_state_requires_completion() -> None:
    queued_at = datetime(2026, 9, 19, tzinfo=UTC)
    queued = MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            trigger=RunTrigger.API,
        ),
        status=RunStatus.QUEUED,
        queued_at=queued_at,
    )
    assert queued.status.is_terminal is False

    with pytest.raises(ValidationError, match="terminal run requires"):
        MonitoringRun(
            id=uuid4(),
            command=queued.command,
            status=RunStatus.SUCCEEDED,
            queued_at=queued_at,
        )


def test_accepted_snapshot_requires_acceptance_time() -> None:
    now = datetime(2026, 9, 19, tzinfo=UTC)
    with pytest.raises(ValidationError, match="accepted snapshot requires"):
        SnapshotAttempt(
            id=uuid4(),
            run_id=uuid4(),
            offering_execution_id=uuid4(),
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.CONSUMER_STANDARD,
            status=SnapshotStatus.ACCEPTED,
            normalized_tariff={"interest_rate": "13.5%"},
            canonical_sha256="a" * 64,
            created_at=now,
        )


def test_question_contract_requires_product_for_offering() -> None:
    with pytest.raises(ValidationError, match="offering_id requires product"):
        QuestionCommand(
            query="What is the rate?",
            offering_id=OfferingId.CONSUMER_STANDARD,
        )


@pytest.mark.parametrize("model", [RunCommand, QuestionCommand])
def test_query_contracts_reject_whitespace_only_input(model) -> None:
    values = {"query": "   "}
    if model is RunCommand:
        values.update(product=ProductType.CONSUMER_LOAN, trigger=RunTrigger.API)
    with pytest.raises(ValidationError, match="non-whitespace"):
        model(**values)


def test_non_answered_result_cannot_smuggle_answer_or_citations() -> None:
    with pytest.raises(ValidationError, match="non-answered"):
        AnswerResult(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            answer="Unsupported answer",
            failure_code=AnswerFailureCode.INSUFFICIENT_EVIDENCE,
        )
