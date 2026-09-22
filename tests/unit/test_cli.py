import logging
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from google.adk.agents import Agent
from google.adk.apps import App, ResumabilityConfig
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import LongRunningFunctionTool
from google.genai import types
from pydantic import PrivateAttr

from app import cli
from app.cli import _wait_for_run, pending_input, start_tariff_monitoring_cli
from app.domain.models import OfferingId
from app.domain.monitoring import OfferingRunStatus, RunStatus
from app.services.run_service import RunProgressPort, RunService


class _LocalModel(BaseLlm):
    _calls: int = PrivateAttr(default=0)

    async def generate_content_async(self, llm_request, stream=False):
        self._calls += 1
        if self._calls == 1:
            part = types.Part(
                function_call=types.FunctionCall(
                    name="start_tariff_monitoring_cli",
                    args={"product": "consumer_loan", "offering_id": "overdraft"},
                )
            )
        else:
            part = types.Part(text="The monitoring run failed during embedding.")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


@pytest.mark.asyncio
async def test_cli_long_running_monitoring_pauses_and_resumes_same_invocation(
    monkeypatch,
) -> None:
    run_id = uuid4()
    app = App(
        name="cli_pause_test",
        root_agent=Agent(
            name="cli_agent",
            model=_LocalModel(model="local-test"),
            tools=[LongRunningFunctionTool(start_tariff_monitoring_cli)],
        ),
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
    sessions = InMemorySessionService()
    await sessions.create_session(
        app_name=app.name, user_id="user", session_id="original-chat"
    )

    async def fake_start(product, offering_id, tool_context):
        return {
            "request_satisfied": True,
            "chat_review_available": True,
            "run_id": str(run_id),
        }

    monkeypatch.setattr("app.cli.start_tariff_monitoring", fake_start)
    runner = Runner(app=app, session_service=sessions)
    first = [
        event
        async for event in runner.run_async(
            user_id="user",
            session_id="original-chat",
            new_message=types.Content(
                role="user", parts=[types.Part(text="Start Overdraft monitoring")]
            ),
        )
    ]
    assert any(event.long_running_tool_ids for event in first)
    session = await sessions.get_session(
        app_name=app.name, user_id="user", session_id="original-chat"
    )
    paused = pending_input(session.events)
    assert paused is not None
    assert paused.name == "start_tariff_monitoring_cli"
    assert paused.initial_response is not None
    assert paused.initial_response["run_id"] == str(run_id)

    resumed = [
        event
        async for event in runner.run_async(
            user_id="user",
            session_id="original-chat",
            invocation_id=paused.invocation_id,
            new_message=types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=paused.function_call_id,
                            name=paused.name,
                            response={
                                "run_id": str(run_id),
                                "status": "failed",
                                "failure_code": "indexing.embedding_failed",
                            },
                        )
                    )
                ],
            ),
        )
    ]
    assert any(
        part.text == "The monitoring run failed during embedding."
        for event in resumed
        for part in (event.content.parts if event.content else ())
    )
    session = await sessions.get_session(
        app_name=app.name, user_id="user", session_id="original-chat"
    )
    assert pending_input(session.events) is None


class _StageRepository:
    """Stands in for `PostgresRunRepository`, not for the service above it.

    The CLI narrates progress through `RunService`, so the fake belongs one layer
    lower: a method the service forgets to expose then fails this test instead of
    the live chat.
    """

    def __init__(self) -> None:
        self.poll = 0

    async def get(self, run_id):
        self.poll += 1
        status = RunStatus.SUCCEEDED if self.poll == 3 else RunStatus.RUNNING
        return SimpleNamespace(
            id=run_id,
            status=status,
            failure_code=None,
            failure_detail=None,
        )

    async def list_offering_executions(self, run_id):
        if self.poll == 3:
            return ()
        stage = "acquisition" if self.poll == 1 else "semantic_extraction"
        return (
            SimpleNamespace(
                offering_id=OfferingId.OVERDRAFT,
                current_stage=stage,
                status=OfferingRunStatus.RUNNING,
            ),
        )


def test_run_service_satisfies_the_cli_progress_port() -> None:
    assert isinstance(RunService(_StageRepository()), RunProgressPort)


@pytest.mark.asyncio
async def test_cli_reports_persisted_pipeline_stages(capsys) -> None:
    run_id = uuid4()

    result = await _wait_for_run(RunService(_StageRepository()), run_id, 0.001)

    assert result.status is RunStatus.SUCCEEDED
    output = capsys.readouterr().out
    assert "Acquiring web content" in output
    assert "Extracting tariff fields" in output
    assert "Monitoring succeeded" in output


@pytest.mark.asyncio
async def test_cli_reopens_pending_business_review_without_starting_new_run(
    monkeypatch, capsys
) -> None:
    from app.cli import _recover_review
    from app.domain.review import ReviewDecisionType, ReviewReason

    run_id = uuid4()
    review_id = uuid4()
    session = SimpleNamespace(
        events=[],
        state={
            "monitoring_active_run_id": str(run_id),
            "monitoring_chat_run_ids": [str(run_id)],
        },
    )
    item = SimpleNamespace(
        review_id=review_id,
        offering_id=OfferingId.OVERDRAFT,
        issue_scope="term",
        reason=ReviewReason.MISSING_REQUIRED_FIELD,
        guidance="Supply the evidenced term.",
        allowed_decisions=(
            ReviewDecisionType.OVERRIDE,
            ReviewDecisionType.REJECT_ALL,
        ),
        candidates=(),
        evidence=(
            SimpleNamespace(
                evidence_id="evidence-term",
                source_url="https://ameriabank.am/overdraft.pdf",
                page=2,
                excerpt="Row: Term (months) | Indefinite term (until requested back)",
            ),
        ),
    )

    class _Sessions:
        async def get_session(self, **kwargs):
            return session

    class _Runs:
        async def get(self, saved_id):
            assert saved_id == run_id
            return SimpleNamespace(
                id=run_id,
                status=RunStatus.AWAITING_REVIEW,
                command=SimpleNamespace(
                    offering_id=OfferingId.OVERDRAFT,
                    product=OfferingId.OVERDRAFT.product,
                ),
            )

    class _Reviews:
        def __init__(self):
            self.submitted = None

        async def pending_request(self, saved_id):
            assert saved_id == run_id
            return SimpleNamespace(reviews=(item,))

        async def resume(self, saved_id, response, **kwargs):
            self.submitted = response
            return SimpleNamespace(status=RunStatus.SUCCEEDED)

    monkeypatch.setattr("builtins.input", lambda prompt: "Indefinite term")
    reviews = _Reviews()

    handled = await _recover_review(
        object(),
        _Sessions(),
        _Runs(),
        reviews,
        user_id="cli-user",
        session_id="original-chat",
    )

    assert handled is True
    assert reviews.submitted.decisions[0].review_id == review_id
    assert reviews.submitted.decisions[0].decision.override_value == [
        {"value": {"indefinite": True, "end_condition": "on_demand"}, "conditions": []}
    ]
    assert reviews.submitted.decisions[0].decision.evidence_reference == "evidence-term"
    output = capsys.readouterr().out
    assert "Continuing here; no new run is needed" in output
    assert "Review completed" in output
    assert "Accepted term formats" in output


def test_cli_evidence_ranks_review_field_passage_first() -> None:
    from app.cli import _ordered_evidence

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
    assert _ordered_evidence(item)[0].evidence_id == "term"


def test_cli_bootstrap_hides_adk_experimental_notices() -> None:
    result = subprocess.run(
        [sys.executable, "app/cli_entry.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Durable Ameria tariff ADK chat" in result.stdout
    assert "[EXPERIMENTAL]" not in result.stderr


def test_cli_explains_gemini_402_without_traceback(capsys) -> None:
    from google.genai.errors import ClientError

    from app.cli import _print_api_error

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
    _print_api_error(error)

    output = capsys.readouterr()
    assert "Gemini prepaid credits are depleted" in output.out
    assert "retry in this session" in output.out
    assert "Traceback" not in output.err


@pytest.mark.asyncio
async def test_cli_hides_adk_429_traceback_and_shows_retry_delay(
    capsys, caplog
) -> None:
    from google.genai.errors import ClientError

    from app.cli import _print_api_error, _run_and_print

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
                    "Root node %s failed.", "cli_agent", exc_info=True
                )
                raise
            yield  # pragma: no cover

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ClientError) as raised:
            await _run_and_print(FailingRunner())
    _print_api_error(raised.value)

    output = capsys.readouterr()
    assert "Gemini rate limit reached" in output.out
    assert "about 51s" in output.out
    assert "Traceback" not in output.out + output.err + caplog.text
    assert "Node execution failed" not in caplog.text
    assert "Root node" not in caplog.text


def test_cli_review_shows_field_passages_before_other_context(capsys) -> None:
    from app.cli import _show_review
    from app.domain.review import ReviewReason

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
    _show_review(item, 1, 1)
    output = capsys.readouterr().out
    assert "term-source" not in output  # Reviewers choose the displayed passage number.
    assert "Indefinite term" in output
    assert "Nominal interest rate" not in output
    assert "revision of another loan term" not in output
    assert "2 other captured passages" in output


def test_cli_accepts_bare_indefinite_only_with_matching_end_condition() -> None:
    from app.cli import _review_value
    from app.domain.semantic_extraction import ExtractionField

    passage = SimpleNamespace(
        excerpt="Term (months): Indefinite term (until requested back)"
    )
    assert _review_value(
        ExtractionField.TERM, "Indefinite term", evidence=(passage,)
    ) == [
        {"value": {"indefinite": True, "end_condition": "on_demand"}, "conditions": []}
    ]
    with pytest.raises(ValueError, match="source must state the end condition"):
        _review_value(
            ExtractionField.TERM,
            "Indefinite term",
            evidence=(SimpleNamespace(excerpt="An indefinite term applies"),),
        )


def test_cli_accepts_plain_bounded_term() -> None:
    from app.cli import _review_value
    from app.domain.semantic_extraction import ExtractionField

    assert _review_value(ExtractionField.TERM, "12-24 months") == [
        {"value": {"min_months": 12, "max_months": 24}, "conditions": []}
    ]


@pytest.mark.asyncio
async def test_cli_native_pause_accepts_plain_term_review(monkeypatch) -> None:
    from app.cli import PendingInput, _continue_pending
    from app.domain.review import ReviewDecisionType, ReviewReason

    review_id = uuid4()
    run_id = uuid4()
    item = SimpleNamespace(
        review_id=review_id,
        offering_id=OfferingId.OVERDRAFT,
        issue_scope="term",
        reason=ReviewReason.MISSING_REQUIRED_FIELD,
        guidance="Review the term.",
        allowed_decisions=(ReviewDecisionType.OVERRIDE, ReviewDecisionType.REJECT_ALL),
        candidates=(),
        evidence=(
            SimpleNamespace(
                evidence_id="term-evidence",
                source_url="https://example.com/term.pdf",
                page=2,
                excerpt="Term (months): Indefinite term (until requested back)",
            ),
        ),
    )
    session = SimpleNamespace(
        events=[],
        state={
            "monitoring_active_run_id": str(run_id),
            "monitoring_review_current_id": str(review_id),
        },
    )

    class _Sessions:
        async def get_session(self, **kwargs):
            return session

    class _Reviews:
        async def pending_request(self, saved_id):
            assert saved_id == run_id
            return SimpleNamespace(reviews=(item,))

    pending = PendingInput(
        invocation_id="invocation",
        function_call_id="call",
        name="adk_request_input",
        arguments={},
    )
    calls = iter((pending, None))
    captured = {}

    async def fake_resume(runner, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.cli.pending_input", lambda events: next(calls))
    monkeypatch.setattr("app.cli._resume", fake_resume)
    monkeypatch.setattr(
        "builtins.input", lambda prompt: "Indefinite term (until requested back)"
    )

    await _continue_pending(
        object(),
        _Sessions(),
        object(),
        _Reviews(),
        user_id="cli-user",
        session_id="session",
        poll_seconds=1,
    )

    result = captured["response"]["result"]
    assert result["review_id"] == str(review_id)
    assert result["decision_type"] == "override"
    assert result["evidence_reference"] == "term-evidence"
    assert result["override_value"] == [
        {"value": {"indefinite": True, "end_condition": "on_demand"}, "conditions": []}
    ]


def test_cli_agent_disables_sdk_afc_but_retains_adk_tools() -> None:
    from app.cli import cli_agent

    assert cli_agent.generate_content_config.automatic_function_calling.disable is True
    assert any(
        getattr(tool, "name", None) == "start_tariff_monitoring_cli"
        or getattr(getattr(tool, "func", None), "__name__", None)
        == "start_tariff_monitoring_cli"
        for tool in cli_agent.tools
    )


@pytest.mark.asyncio
async def test_chat_survives_an_unexpected_error_in_one_turn(
    monkeypatch, capsys
) -> None:
    """One broken turn must not end a durable session with a traceback."""
    prompts = iter(["show me the overdraft tariff", "quit"])
    container = SimpleNamespace(
        run_service=None,
        answer_service=None,
        request_resolver=None,
        current_tariff_service=None,
        tariff_history_service=None,
        run_wait_service=None,
        chat_review_service=None,
        structured_query_service=None,
        answer_router=None,
        close=_noop_close,
    )
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(cli, "build_application_container", lambda settings: container)
    monkeypatch.setattr(cli, "configure_services", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "Runner", lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(
        cli.services, "ensure_session_service_ready", _in_memory_session_service
    )
    monkeypatch.setattr(cli.services, "get_artifact_service", lambda: None)
    monkeypatch.setattr(cli, "_input", lambda prompt: next(prompts))
    monkeypatch.setattr(cli, "_recover_review", _never_recovers)
    monkeypatch.setattr(cli, "_run_and_print", _raises_unexpectedly)

    await cli.chat("user", "durable-session", 0.001)

    output = capsys.readouterr().out
    assert "Something went wrong" in output
    assert "durable-session" in output
    assert next(prompts, None) is None


async def _noop_close() -> None:
    return None


async def _in_memory_session_service():
    return InMemorySessionService()


async def _never_recovers(*args, **kwargs) -> bool:
    return False


async def _raises_unexpectedly(*args, **kwargs) -> None:
    raise AttributeError(
        "'RunService' object has no attribute 'list_offering_executions'"
    )


class _PendingThenDoneSessions:
    """Serves the paused session once, then a session with nothing outstanding."""

    def __init__(self, run_id) -> None:
        self.calls = 0
        self._paused = SimpleNamespace(
            state={},
            events=[
                SimpleNamespace(
                    author="ameria_tariff_monitor_cli",
                    invocation_id="invocation-1",
                    long_running_tool_ids=["monitor-1"],
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                function_call=types.FunctionCall(
                                    id="monitor-1",
                                    name="start_tariff_monitoring_cli",
                                    args={},
                                )
                            )
                        ],
                    ),
                ),
                SimpleNamespace(
                    author="ameria_tariff_monitor_cli",
                    invocation_id="invocation-1",
                    long_running_tool_ids=[],
                    content=types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    id="monitor-1",
                                    name="start_tariff_monitoring_cli",
                                    response={
                                        "request_satisfied": True,
                                        "run_id": str(run_id),
                                        "offering_id": "overdraft",
                                    },
                                )
                            )
                        ],
                    ),
                ),
            ],
        )
        self._done = SimpleNamespace(state={}, events=[])

    async def get_session(self, *, app_name, user_id, session_id):
        self.calls += 1
        return self._paused if self.calls == 1 else self._done


@pytest.mark.asyncio
async def test_cli_announces_the_run_before_the_first_stage_line(
    monkeypatch, capsys
) -> None:
    run_id = uuid4()

    async def _no_resume(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(cli, "_resume", _no_resume)

    await cli._continue_pending(
        SimpleNamespace(),
        _PendingThenDoneSessions(run_id),
        RunService(_StageRepository()),
        None,
        user_id="user",
        session_id="durable-session",
        poll_seconds=0.001,
    )

    output = capsys.readouterr().out
    assert output.index(str(run_id)) < output.index("Acquiring web content")
    assert "overdraft" in output
    # The heartbeat carries elapsed time so a slow stage never looks frozen.
    assert "s…" in output
