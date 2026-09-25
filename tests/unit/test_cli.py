"""The CLI attach loop, driven by a real ADK Runner and the monitoring node.

The scripted model and in-memory fakes come from tests/fixtures/monitoring_node;
only the terminal input is replaced.
"""

import asyncio
import logging
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService

from app import cli
from app.domain.models import OfferingId
from app.domain.monitoring import RunStatus
from app.domain.review import ReviewDecisionType, ReviewReason
from app.services.monitoring_node import parse_review_interrupt_id
from tests.fixtures.monitoring_node import (
    APP_NAME,
    OFFERING,
    PRODUCT,
    SESSION_ID,
    USER_ID,
    build,
    call,
    function_responses,
    interrupts,
    text,
)

QUESTION = "What is the overdraft rate?"


def _monitor():
    return call(
        "run_tariff_monitoring",
        product=PRODUCT,
        offering_id=OFFERING,
        question=QUESTION,
    )


def _session(harness, *, owner="cli:test-host:1:aaaa") -> cli.ChatSession:
    return cli.ChatSession(
        runner=harness.runner,
        sessions=harness.sessions,
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        owner=owner,
        runs=harness.runs,
    )


def _answers(monkeypatch, *values):
    """Script the terminal: each prompt takes the next value."""
    remaining = list(values)
    asked = []

    async def fake_input(prompt):
        asked.append(prompt)
        if not remaining:
            raise AssertionError(f"unexpected prompt: {prompt}")
        return remaining.pop(0)

    monkeypatch.setattr(cli, "_ainput", fake_input)
    return asked


def _review_replies(events) -> list[dict]:
    return function_responses(events, "adk_request_input")


# --- progress ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_progress_lines_come_from_streamed_node_events(capsys) -> None:
    harness = await build()
    harness.model.play(_monitor())

    await _session(harness).converse("monitor overdraft")

    output = capsys.readouterr().out
    assert "Monitoring overdraft" in output
    assert "✓ Acquiring web content" in output
    assert "✓ Extracting tariff fields" in output
    assert "Monitoring finished" in output
    assert "done" in output  # the model's answer panel
    # No identifiers in normal output.
    (run_id,) = harness.runs.runs
    assert str(run_id) not in output


@pytest.mark.asyncio
async def test_verbose_mode_shows_the_run_id_and_tool_calls(capsys) -> None:
    harness = await build()
    harness.model.play(_monitor())
    session = _session(harness)
    session.renderer.verbose = True

    await session.converse("monitor overdraft")

    output = capsys.readouterr().out
    (run_id,) = harness.runs.runs
    assert str(run_id) in output
    assert "call run_tariff_monitoring" in output


def test_renderer_reads_only_structured_metadata(capsys) -> None:
    renderer = cli.ProgressRenderer()
    renderer.render(
        Event(
            message="Totally different text",
            partial=True,
            custom_metadata={
                "kind": "monitoring_progress",
                "progress": {
                    "kind": "offering_failed",
                    "run_id": str(uuid4()),
                    "product": "consumer_loan",
                    "offering_id": "overdraft",
                    "stage": "normalization",
                    "failure_code": "source.pdf_extraction_failed",
                },
            },
        )
    )

    output = capsys.readouterr().out
    assert "Reading source documents" in output
    assert "source.pdf_extraction_failed" in output
    assert "Totally different text" not in output


# --- reviews ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_paused_turn_prompts_once_and_resumes_with_a_valid_reply(
    monkeypatch, capsys
) -> None:
    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(_monitor())
    asked = _answers(monkeypatch, "1")

    await _session(harness).converse("monitor overdraft")

    assert len(asked) == 1
    replies = _review_replies(await harness.persisted())
    assert replies == [
        {"result": {"decision_type": "select_candidate", "candidate_id": "candidate-1"}}
    ]
    assert harness.decisions.applied[0][1:] == ("select_candidate", "cli-user")
    output = capsys.readouterr().out
    assert "Review 1/1 · overdraft · interest_rate" in output
    assert harness.model.calls == 2


@pytest.mark.asyncio
async def test_a_malformed_typed_reply_is_reprompted_locally_and_never_sent(
    monkeypatch, capsys
) -> None:
    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(_monitor())
    asked = _answers(monkeypatch, "quite high", "1")

    await _session(harness).converse("monitor overdraft")

    assert len(asked) == 2
    assert len(_review_replies(await harness.persisted())) == 1
    assert "Invalid interest rate" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_a_rejected_reply_shows_why_and_asks_again(monkeypatch, capsys) -> None:
    harness = await build(review_scopes=("fees",))  # "12.5%" is not a valid fee
    harness.model.play(_monitor())
    _answers(monkeypatch, "1", "reject_all")

    await _session(harness).converse("monitor overdraft")

    output = capsys.readouterr().out
    assert "The previous answer was not applied" in output
    assert "cannot be stored as a valid fees value" in output
    (run,) = harness.runs.runs.values()
    assert run.status is RunStatus.FAILED


@pytest.mark.asyncio
async def test_two_reviews_are_asked_in_order(monkeypatch, capsys) -> None:
    harness = await build(review_scopes=("interest_rate", "effective_rate"))
    harness.model.play(_monitor())
    _answers(monkeypatch, "1", "1")

    await _session(harness).converse("monitor overdraft")

    output = capsys.readouterr().out
    assert output.index("Review 1/2") < output.index("Review 2/2")
    assert len(harness.decisions.applied) == 2


def _term_view(review_id, excerpt, scope="term"):
    return {
        "review_id": str(review_id),
        "reason": ReviewReason.MISSING_REQUIRED_FIELD.value,
        "product": "consumer_loan",
        "offering_id": "overdraft",
        "issue_scope": scope,
        "guidance": "Review the value.",
        "allowed_decisions": [
            ReviewDecisionType.OVERRIDE.value,
            ReviewDecisionType.REJECT_ALL.value,
        ],
        "candidates": [],
        "evidence": [
            {
                "evidence_id": f"{scope}-evidence",
                "source_url": "https://example.com/overdraft.pdf",
                "page": 2,
                "excerpt": excerpt,
            }
        ],
    }


def _pending(view) -> cli.PendingReview:
    return cli.PendingReview(
        invocation_id="invocation",
        interrupt_id="review:x",
        message=None,
        payload={"kind": "tariff_review", "view": view, "position": 1, "total": 1},
    )


@pytest.mark.asyncio
async def test_native_pause_accepts_a_plain_term_review(monkeypatch) -> None:
    _answers(monkeypatch, "Indefinite term (until requested back)")
    session = cli.ChatSession(
        runner=None,
        sessions=None,
        app_name="a",
        user_id="u",
        session_id="s",
        owner="o",
    )

    reply = await session.ask(
        _pending(
            _term_view(uuid4(), "Term (months): Indefinite term (until requested back)")
        )
    )

    assert reply["decision_type"] == "override"
    assert reply["evidence_reference"] == "term-evidence"
    assert reply["override_value"] == [
        {"value": {"indefinite": True, "end_condition": "on_demand"}, "conditions": []}
    ]


@pytest.mark.asyncio
async def test_native_pause_accepts_a_plain_repayment_review(
    monkeypatch, capsys
) -> None:
    """A structured field must be answerable in the words the passage uses."""
    excerpt = (
        "METHOD AND FREQUENCY OF PAYMENTS Repayment Interest accrued on overdraft "
        "is repaid on monthly basis and the utilized amounts are repaid at the end "
        "of the term."
    )
    _answers(monkeypatch, "Interest is repaid monthly, the principal at the end", "1")
    session = cli.ChatSession(
        runner=None,
        sessions=None,
        app_name="a",
        user_id="u",
        session_id="s",
        owner="o",
    )

    reply = await session.ask(_pending(_term_view(uuid4(), excerpt, "repayment")))

    assert reply["decision_type"] == "override"
    assert reply["evidence_reference"] == "repayment-evidence"
    assert reply["override_value"] == [
        {
            "value": {"method": "Interest is repaid monthly, the principal at the end"},
            "conditions": [],
        }
    ]
    # The accepted format is stated before the reviewer types, not after a rejection.
    assert "Enter each repayment method" in capsys.readouterr().out


# --- Ctrl-C and recovery -------------------------------------------------------------


@pytest.mark.asyncio
async def test_ctrl_c_cancels_the_run_and_rewinds_the_turn(capsys) -> None:
    harness = await build(block=True)
    harness.model.play(_monitor())
    session = _session(harness)

    converse = asyncio.create_task(session.converse("monitor overdraft"))
    await harness.pipeline.started.wait()
    converse.cancel()  # what the SIGINT handler does to the running turn
    await converse  # the turn absorbs the cancellation and returns

    (run,) = harness.runs.runs.values()
    assert run.status is RunStatus.FAILED
    assert run.failure_code == "run.cancelled"
    assert "Monitoring cancelled." in capsys.readouterr().out
    assert cli.dangling_monitoring_invocation(await harness.persisted()) is None

    harness.model.play()  # next turn: the model just answers
    await session.converse("hello")
    assert "done" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_ctrl_c_during_a_review_postpones_it(monkeypatch, capsys) -> None:
    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(_monitor())
    reached = asyncio.Event()

    async def wait_forever(prompt):
        reached.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(cli, "_ainput", wait_forever)
    converse = asyncio.create_task(_session(harness).converse("monitor overdraft"))
    await reached.wait()
    converse.cancel()
    await converse

    assert "Review postponed" in capsys.readouterr().out
    assert cli.pending_review(await harness.persisted()) is None
    (run,) = harness.runs.runs.values()
    assert run.status is RunStatus.AWAITING_REVIEW  # still reviewable later


@pytest.mark.asyncio
async def test_startup_continues_an_unanswered_review(monkeypatch, capsys) -> None:
    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(_monitor())
    # The previous CLI paused on the review and was closed before answering.
    ((interrupt_id, _),) = interrupts(await harness.turn(text("monitor overdraft")))
    _answers(monkeypatch, "1")

    await _session(harness).open()

    output = capsys.readouterr().out
    assert "Continuing the review of overdraft · interest rate" in output
    assert harness.decisions.applied
    run_id = parse_review_interrupt_id(interrupt_id)[0]
    assert harness.runs.runs[run_id].status is RunStatus.SUCCEEDED
    assert harness.pipeline.executed == 1


@pytest.mark.asyncio
async def test_startup_closes_a_run_the_dead_cli_left_running(capsys) -> None:
    harness = await build(block=True)
    harness.model.play(_monitor())
    session = await harness.sessions.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    await harness.sessions.append_event(
        session,
        Event(
            author="user",
            invocation_id="cli-open-1",
            actions=EventActions(state_delta={"cli_owner": "cli:test-host:1:dead"}),
        ),
    )
    turn = asyncio.create_task(harness.turn(text("monitor overdraft")))
    await harness.pipeline.started.wait()
    turn.cancel()  # the process dies: no cleanup, no rewind
    with pytest.raises(asyncio.CancelledError):
        await turn
    (run_id,) = harness.runs.runs
    harness.runs.set(run_id, status=RunStatus.RUNNING, failure_code=None)
    harness.runs.owners[run_id] = "cli:test-host:1:dead"
    assert cli.dangling_monitoring_invocation(await harness.persisted()) is not None

    await _session(harness, owner="cli:test-host:2:live").open()

    assert harness.runs.interrupted_prefixes == ["cli:test-host:1:dead"]
    assert harness.runs.runs[run_id].failure_code == "run.interrupted"
    assert cli.dangling_monitoring_invocation(await harness.persisted()) is None
    assert "interrupted when the chat closed" in capsys.readouterr().out
    state = (
        await harness.sessions.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
    ).state
    assert state["cli_owner"] == "cli:test-host:2:live"


def test_every_cli_process_gets_a_distinct_owner() -> None:
    first, second = cli.process_owner(), cli.process_owner()

    assert first.startswith("cli:") and second.startswith("cli:")
    assert first != second
    assert not second.startswith(first) and not first.startswith(second)


# --- kept from the pre-redesign CLI -----------------------------------------------


def test_cli_evidence_ranks_review_field_passage_first() -> None:
    item = SimpleNamespace(
        issue_scope="term",
        candidates=(),
        evidence=(
            SimpleNamespace(evidence_id="generic", excerpt="General conditions"),
            SimpleNamespace(
                evidence_id="term",
                excerpt="Row: Term (months) | Indefinite term",
            ),
        ),
    )
    assert cli._ordered_evidence(item)[0].evidence_id == "term"


def test_cli_bootstrap_hides_adk_experimental_notices() -> None:
    result = subprocess.run(
        [sys.executable, "app/cli_entry.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Durable Ameria tariff ADK chat" in result.stdout
    assert "--session" in result.stdout and "--new" in result.stdout
    assert "--poll-seconds" not in result.stdout
    assert "[EXPERIMENTAL]" not in result.stderr


def test_cli_explains_gemini_402_without_traceback(capsys) -> None:
    from google.genai.errors import ClientError

    error = ClientError(
        402,
        {
            "error": {
                "code": 402,
                "status": "RESOURCE_EXHAUSTED",
                "message": "Your prepaid credits are depleted.",
            }
        },
    )
    cli._print_api_error(error)

    output = capsys.readouterr()
    assert "Gemini prepaid credits are depleted" in output.out
    assert "retry in this session" in output.out
    assert "Traceback" not in output.err


@pytest.mark.asyncio
async def test_cli_hides_adk_429_traceback_and_shows_retry_delay(
    capsys, caplog
) -> None:
    from google.genai.errors import ClientError

    error = ClientError(
        429,
        {
            "error": {
                "code": 429,
                "status": "RESOURCE_EXHAUSTED",
                "message": "Input token quota exceeded",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "51s",
                    }
                ],
            }
        },
    )

    class FailingRunner:
        async def run_async(self, **kwargs):
            try:
                raise error
            except ClientError:
                logging.getLogger("google.adk.workflow._node_runner").exception(
                    "Node execution failed with exception"
                )
                logging.getLogger("google.adk.runners").error(
                    "Root node %s failed.", "root", exc_info=True
                )
                raise
            yield  # pragma: no cover

    session = cli.ChatSession(
        runner=FailingRunner(),
        sessions=None,
        app_name="a",
        user_id="u",
        session_id="s",
        owner="o",
    )
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ClientError) as raised:
            await session._stream(text("hi"))
    cli._print_api_error(raised.value)

    output = capsys.readouterr()
    assert "Gemini rate limit reached" in output.out
    assert "about 51s" in output.out
    assert "Traceback" not in output.out + output.err + caplog.text
    assert "Node execution failed" not in caplog.text
    assert "Root node" not in caplog.text


def test_cli_review_shows_field_passages_before_other_context(capsys) -> None:
    item = SimpleNamespace(
        offering_id=OfferingId.OVERDRAFT,
        issue_scope="term",
        reason=ReviewReason.MISSING_REQUIRED_FIELD,
        guidance="Provide a structured override.",
        candidates=(),
        evidence=(
            SimpleNamespace(
                evidence_id="term-source",
                source_url="https://example.com/term.pdf",
                page=2,
                excerpt="Row: Term (months) | Indefinite term",
            ),
            SimpleNamespace(
                evidence_id="rate-source",
                source_url="https://example.com/rate.pdf",
                page=3,
                excerpt="Nominal interest rate 15%",
            ),
            SimpleNamespace(
                evidence_id="fee-source",
                source_url="https://example.com/fees.pdf",
                page=4,
                excerpt="Fee for revision of another loan term: 0.1%",
            ),
        ),
    )
    cli._show_review(item, 1, 1)
    output = capsys.readouterr().out
    assert "term-source" not in output  # Reviewers choose the displayed passage number.
    assert "Indefinite term" in output
    assert "Nominal interest rate" not in output
    assert "revision of another loan term" not in output
    assert "2 other captured passages" in output


def test_cli_accepts_bare_indefinite_only_with_matching_end_condition() -> None:
    from app.domain.semantic_extraction import ExtractionField

    passage = SimpleNamespace(
        excerpt="Term (months): Indefinite term (until requested back)"
    )
    assert cli._review_value(
        ExtractionField.TERM, "Indefinite term", evidence=(passage,)
    ) == [
        {"value": {"indefinite": True, "end_condition": "on_demand"}, "conditions": []}
    ]
    with pytest.raises(ValueError, match="source must state the end condition"):
        cli._review_value(
            ExtractionField.TERM,
            "Indefinite term",
            evidence=(SimpleNamespace(excerpt="An indefinite term applies"),),
        )


def test_cli_accepts_plain_bounded_term() -> None:
    from app.domain.semantic_extraction import ExtractionField

    assert cli._review_value(ExtractionField.TERM, "12-24 months") == [
        {"value": {"min_months": 12, "max_months": 24}, "conditions": []}
    ]


def test_cli_states_the_entry_format_for_every_reviewable_field() -> None:
    from app.domain.semantic_extraction import ExtractionField

    for field in ExtractionField:
        assert "For example" in cli._entry_format(field.value)
    assert "JSON" in cli._entry_format("unknown_scope")


@pytest.mark.asyncio
async def test_chat_survives_an_unexpected_error_in_one_turn(
    monkeypatch, capsys
) -> None:
    """One broken turn must not end a durable conversation with a traceback."""
    prompts = iter(["show me the overdraft tariff", "quit"])
    container = SimpleNamespace(
        run_service=None,
        answer_service=None,
        request_resolver=None,
        current_tariff_service=None,
        tariff_history_service=None,
        structured_query_service=None,
        answer_router=None,
        monitoring_node=None,
        runs=None,
        reviews=None,
        close=_noop_close,
    )
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        cli, "build_application_container", lambda settings, **kwargs: container
    )
    monkeypatch.setattr(cli, "configure_services", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "Runner", lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(
        cli.services, "ensure_session_service_ready", _in_memory_session_service
    )
    monkeypatch.setattr(cli.services, "get_artifact_service", lambda: None)

    async def next_prompt(prompt):
        return next(prompts)

    monkeypatch.setattr(cli, "_ainput", next_prompt)
    monkeypatch.setattr(cli.ChatSession, "converse", _raises_unexpectedly)

    await cli.chat("user", "durable-session")

    output = capsys.readouterr().out
    assert "Something went wrong" in output
    assert 'Reopen it later with: ./tariff-chat --session "durable-session"' in output
    assert next(prompts, None) is None


async def _noop_close() -> None:
    return None


async def _in_memory_session_service():
    return InMemorySessionService()


async def _raises_unexpectedly(*args, **kwargs) -> None:
    raise AttributeError("'NoneType' object has no attribute 'run_async'")
