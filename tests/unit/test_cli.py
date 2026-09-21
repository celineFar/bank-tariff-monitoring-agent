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

from app.cli import _wait_for_run, pending_input, start_tariff_monitoring_cli
from app.domain.models import OfferingId
from app.domain.monitoring import OfferingRunStatus, RunStatus


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


@pytest.mark.asyncio
async def test_cli_reports_persisted_pipeline_stages(capsys) -> None:
    run_id = uuid4()

    class _Runs:
        def __init__(self) -> None:
            self.poll = 0

        async def get(self, run_id):
            self.poll += 1
            status = RunStatus.SUCCEEDED if self.poll == 3 else RunStatus.RUNNING
            return SimpleNamespace(status=status)

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

    result = await _wait_for_run(_Runs(), run_id, 0.001)

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

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: (
            '{"decision_type":"override","override_value":'
            '"Indefinite term (until requested back)","reason":"Official term",'
            '"evidence_reference":"evidence-term"}'
        ),
    )
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
    assert (
        reviews.submitted.decisions[0].decision.override_value
        == "Indefinite term (until requested back)"
    )
    output = capsys.readouterr().out
    assert "Continuing here; no new run is needed" in output
    assert "Review completed" in output


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
