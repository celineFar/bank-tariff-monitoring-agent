"""The monitoring node through a real ADK Runner (plan §14: the executable spec).

A scripted model calls a thin tool that runs the node; everything else is the
real ADK runtime: partial progress events, the native `RequestInput` pause, the
replay of the original tool call on resume, and cancellation.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.domain.models import OfferingId
from app.domain.monitoring import OfferingRunStatus, RunStatus
from app.domain.review import ReviewStatus
from app.services.monitoring_node import (
    parse_review_interrupt_id,
    review_interrupt_id,
)
from tests.fixtures.monitoring_node import (
    OFFERING,
    PRODUCT,
    build,
    call,
    function_responses,
    interrupts,
    progress_events,
    queued_run,
    reply,
    text,
)

QUESTION = "What is the overdraft rate?"
SELECT = {"decision_type": "select_candidate", "candidate_id": "candidate-1"}


def _monitor(**args):
    return call(
        "run_tariff_monitoring",
        **{"product": PRODUCT, "offering_id": OFFERING, "question": QUESTION, **args},
    )


@pytest.mark.asyncio
async def test_progress_streams_as_partial_events_that_are_never_persisted() -> None:
    harness = await build()
    harness.model.play(_monitor())

    events = await harness.turn(text("monitor overdraft"))

    streamed = progress_events(events)
    stages = [
        (item["kind"], item["stage"])
        for item in (event.custom_metadata["progress"] for event in streamed)
    ]
    assert stages[0] == ("run_started", None)
    assert stages[1:3] == [
        ("stage_started", "acquisition"),
        ("stage_completed", "acquisition"),
    ]
    assert all(event.partial for event in streamed)
    persisted = await harness.persisted()
    assert not progress_events(persisted)
    result = function_responses(events, "run_tariff_monitoring")[0]
    assert result["status"] == "succeeded"
    assert harness.pipeline.executed == 1
    assert harness.runs.claims[0][1] == "cli:test-host:1"


@pytest.mark.asyncio
async def test_successful_run_answers_the_original_question_in_the_same_turn() -> None:
    harness = await build()
    harness.model.play(_monitor())

    events = await harness.turn(text("monitor overdraft"))

    result = function_responses(events, "run_tariff_monitoring")[0]
    assert result["answer_status"] == "answered"
    assert result["answer"]["status"] == "insufficient_evidence"
    assert harness.answers.questions == [QUESTION]
    assert harness.model.calls == 2  # choose the tool, then answer


@pytest.mark.asyncio
async def test_a_pause_is_a_native_request_input_and_the_model_is_not_called() -> None:
    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(_monitor())

    events = await harness.turn(text("monitor overdraft"))

    ((interrupt_id, payload),) = interrupts(events)
    run_id, review_id, attempt = parse_review_interrupt_id(interrupt_id)
    assert harness.runs.runs[run_id].status is RunStatus.AWAITING_REVIEW
    assert attempt == 1
    assert payload["kind"] == "tariff_review"
    assert payload["view"]["review_id"] == str(review_id)
    assert payload["view"]["evidence"][0]["excerpt"] == "Official rate is 12.5%"
    assert payload["input_format"]["field"] == "interest_rate"
    assert (payload["position"], payload["total"]) == (1, 1)
    assert harness.model.calls == 1
    assert function_responses(events, "run_tariff_monitoring") == []


@pytest.mark.asyncio
async def test_resume_replays_the_tool_applies_the_decision_and_answers() -> None:
    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(_monitor())
    ((interrupt_id, _),) = interrupts(await harness.turn(text("monitor overdraft")))

    events = await harness.turn(reply(interrupt_id, SELECT))

    result = function_responses(events, "run_tariff_monitoring")[0]
    assert result["status"] == "succeeded"
    assert result["reviews_applied"] == 1
    assert result["answer"]["status"] == "insufficient_evidence"
    assert harness.pipeline.executed == 1  # resume never re-runs the pipeline
    assert len(harness.runs.submits) == 1  # nor submits a second run
    assert [item[1:] for item in harness.decisions.applied] == [
        ("select_candidate", "cli-user")
    ]
    assert harness.model.calls == 2


@pytest.mark.asyncio
async def test_two_reviews_pause_twice_in_one_tool_call() -> None:
    harness = await build(review_scopes=("interest_rate", "effective_rate"))
    harness.model.play(_monitor())
    ((first, first_payload),) = interrupts(await harness.turn(text("monitor")))

    second_events = await harness.turn(reply(first, SELECT))
    ((second, second_payload),) = interrupts(second_events)
    final = await harness.turn(reply(second, SELECT))

    assert (first_payload["position"], first_payload["total"]) == (1, 2)
    assert (second_payload["position"], second_payload["total"]) == (2, 2)
    assert first != second
    assert function_responses(second_events, "run_tariff_monitoring") == []
    assert (
        function_responses(final, "run_tariff_monitoring")[0]["status"] == "succeeded"
    )
    assert len(harness.decisions.applied) == 2
    assert harness.pipeline.executed == 1
    assert harness.model.calls == 2


@pytest.mark.asyncio
async def test_a_rejected_reply_is_asked_again_under_a_new_interrupt() -> None:
    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(_monitor())
    ((interrupt_id, _),) = interrupts(await harness.turn(text("monitor")))

    events = await harness.turn(
        reply(interrupt_id, {"decision_type": "select_candidate", "candidate_id": "x"})
    )

    ((again, payload),) = interrupts(events)
    assert parse_review_interrupt_id(again)[2] == 2
    assert payload["rejected"]["reason_code"] == "review.invalid_input"
    assert harness.decisions.applied == []  # nothing was written

    final = await harness.turn(reply(again, SELECT))
    assert (
        function_responses(final, "run_tariff_monitoring")[0]["status"] == "succeeded"
    )


@pytest.mark.asyncio
async def test_reject_all_supersedes_the_rest_and_fails_the_run() -> None:
    harness = await build(review_scopes=("interest_rate", "effective_rate"))
    harness.model.play(_monitor())
    ((interrupt_id, _),) = interrupts(await harness.turn(text("monitor")))

    events = await harness.turn(reply(interrupt_id, {"decision_type": "reject_all"}))

    result = function_responses(events, "run_tariff_monitoring")[0]
    assert result["status"] == "failed"
    assert "answer" not in result or result["answer"] is None
    statuses = sorted(task.status.value for task in harness.reviews.tasks.values())
    assert statuses == ["rejected", "superseded"]
    assert interrupts(events) == []


@pytest.mark.asyncio
async def test_a_run_closed_elsewhere_while_paused_is_reported_not_restarted() -> None:
    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(_monitor())
    ((interrupt_id, _),) = interrupts(await harness.turn(text("monitor")))
    run_id = parse_review_interrupt_id(interrupt_id)[0]
    # An admin rejects every pending review while the chat is paused.
    for task in harness.reviews.tasks.values():
        harness.reviews._set(task.id, status=ReviewStatus.SUPERSEDED)
    harness.runs.set(run_id, status=RunStatus.FAILED)

    events = await harness.turn(reply(interrupt_id, SELECT))

    assert function_responses(events, "run_tariff_monitoring")[0]["status"] == "failed"
    assert len(harness.runs.submits) == 1
    assert harness.pipeline.executed == 1


@pytest.mark.asyncio
async def test_cancelling_the_consumer_cancels_the_run() -> None:
    harness = await build(block=True)
    harness.model.play(_monitor())

    async def consume():
        return await harness.turn(text("monitor"))

    task = asyncio.create_task(consume())
    await harness.pipeline.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    (run,) = harness.runs.runs.values()
    assert run.status is RunStatus.FAILED
    assert run.failure_code == "run.cancelled"


@pytest.mark.asyncio
async def test_a_run_owned_by_another_process_is_followed_not_executed() -> None:
    harness = await build()
    other = harness.runs.add(
        queued_run().model_copy(
            update={"status": RunStatus.RUNNING, "started_at": queued_run().queued_at}
        ),
        owner="worker-1",
    )
    harness.runs.execution(
        other.id,
        OfferingId.OVERDRAFT,
        status=OfferingRunStatus.RUNNING,
        stage="acquisition",
    )
    harness.model.play(_monitor())

    async def finish_later():
        await asyncio.sleep(0.05)
        harness.runs.set(
            other.id, status=RunStatus.SUCCEEDED, completed_at=other.queued_at
        )

    finisher = asyncio.create_task(finish_later())
    events = await harness.turn(text("monitor"))
    await finisher

    progress = [event.custom_metadata["progress"] for event in progress_events(events)]
    assert progress[0]["kind"] == "following"
    assert "daily scheduler" in progress[0]["detail"]
    assert ("stage_started", "acquisition") in [
        (item["kind"], item["stage"]) for item in progress
    ]
    result = function_responses(events, "run_tariff_monitoring")[0]
    assert result["status"] == "succeeded"
    assert result["followed"] is True
    assert harness.pipeline.executed == 0


@pytest.mark.asyncio
async def test_review_only_never_submits_or_claims() -> None:
    harness = await build()
    paused = harness.runs.add(
        queued_run().model_copy(
            update={
                "status": RunStatus.AWAITING_REVIEW,
                "started_at": queued_run().queued_at,
            }
        )
    )
    from tests.fixtures.monitoring_node import review_task

    task = review_task(paused, OfferingId.OVERDRAFT, "interest_rate")
    harness.reviews.tasks[task.id] = task
    harness.model.play(call("run_tariff_monitoring", review_only=True))

    ((interrupt_id, _),) = interrupts(await harness.turn(text("review them")))
    events = await harness.turn(reply(interrupt_id, SELECT))

    assert (
        function_responses(events, "run_tariff_monitoring")[0]["status"] == "succeeded"
    )
    assert harness.runs.submits == []
    assert harness.runs.claims == []


@pytest.mark.asyncio
async def test_review_only_without_a_paused_run_says_so() -> None:
    harness = await build()
    harness.model.play(call("run_tariff_monitoring", review_only=True))

    events = await harness.turn(text("review them"))

    assert (
        function_responses(events, "run_tariff_monitoring")[0]["status"]
        == "no_pending_reviews"
    )


@pytest.mark.asyncio
async def test_an_active_run_for_another_offering_blocks_without_starting() -> None:
    harness = await build()
    harness.runs.add(
        queued_run(OfferingId.CONSUMER_STANDARD).model_copy(
            update={"status": RunStatus.RUNNING, "started_at": queued_run().queued_at}
        )
    )
    harness.model.play(_monitor(offering_id=None))

    events = await harness.turn(text("monitor all consumer loans"))

    result = function_responses(events, "run_tariff_monitoring")[0]
    assert result["status"] == "blocked"
    assert harness.pipeline.executed == 0
    assert harness.runs.claims == []


@pytest.mark.asyncio
async def test_a_failed_run_reports_its_code_in_words() -> None:
    harness = await build(fail=True)
    harness.model.play(_monitor())

    events = await harness.turn(text("monitor"))

    result = function_responses(events, "run_tariff_monitoring")[0]
    assert result["status"] == "failed"
    assert result["failure_code"] == "source.model_failed"
    assert "no configured model was available" in result["failure_summary"]
    assert result["offerings"][0]["failure_code"] == "source.model_failed"
    assert result.get("answer") is None


def test_interrupt_ids_round_trip() -> None:
    run_id, review_id = uuid4(), uuid4()

    assert parse_review_interrupt_id(review_interrupt_id(run_id, review_id)) == (
        run_id,
        review_id,
        1,
    )
    assert parse_review_interrupt_id(review_interrupt_id(run_id, review_id, 3))[2] == 3
    assert parse_review_interrupt_id("adk-123") is None
    assert parse_review_interrupt_id("review:not-a-uuid:x") is None
