from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from google.adk.tools import ToolContext
from google.genai import types
from pydantic import SecretStr

from app.api.routes import router
from app.config.models import HitlSettings
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    AnswerResult,
    AnswerStatus,
    MonitoringRun,
    RunCommand,
    RunStatus,
    RunTrigger,
)
from app.domain.monitoring_workflow import MonitoringWorkflowResult
from app.domain.review import (
    ReviewCandidate,
    ReviewCorrelation,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.services.chat_reviews import ChatReviewService
from app.tools import (
    _switch_chat_run,
    configure_services,
    get_next_monitoring_review,
    submit_monitoring_review_input,
)

NOW = datetime(2026, 9, 21, tzinfo=UTC)


def _run(status: RunStatus = RunStatus.AWAITING_REVIEW) -> MonitoringRun:
    return MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.OVERDRAFT,
            trigger=RunTrigger.ADK,
        ),
        status=status,
        queued_at=NOW,
        started_at=NOW,
        completed_at=NOW if status.is_terminal else None,
    )


def _review(run: MonitoringRun, scope: str = "interest_rate") -> ReviewTask:
    review_id = uuid4()
    return ReviewTask(
        id=review_id,
        idempotency_key=f"review:{review_id}",
        run_id=run.id,
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        reason=ReviewReason.OFFICIAL_SOURCE_CONFLICT,
        issue_scope=scope,
        candidates=(
            ReviewCandidate(
                candidate_id="candidate-1",
                field=scope,
                value="12.5%",
                evidence_references=("evidence-1",),
            ),
        ),
        evidence={
            "items": [
                {
                    "evidence_id": "evidence-1",
                    "content": "Official rate is 12.5%",
                    "locator": {
                        "source_url": "https://ameriabank.am/rates.pdf",
                        "pdf_page": 2,
                    },
                }
            ]
        },
        correlation=ReviewCorrelation(
            app_name="tariff_monitoring_workflow",
            user_id="monitoring-adk",
            session_id=f"monitoring-run-{run.id}",
            invocation_id="invocation-1",
            interrupt_id=f"monitoring-review:{run.id}",
        ),
        created_at=NOW,
        updated_at=NOW,
    )


class _Runs:
    def __init__(self, run: MonitoringRun) -> None:
        self.run = run
        self.audits: list[str] = []

    async def get(self, run_id: UUID):
        return self.run if run_id == self.run.id else None

    async def record_audit(self, run_id, event_type, **kwargs):
        self.audits.append(event_type)


class _Reviews:
    def __init__(self, tasks: tuple[ReviewTask, ...]) -> None:
        self.tasks = tasks

    async def list(self, *, status=None, run_id=None, limit=100, offset=0, **kwargs):
        return tuple(
            task
            for task in self.tasks
            if (status is None or task.status is status)
            and (run_id is None or task.run_id == run_id)
        )[offset : offset + limit]


class _Workflow:
    def __init__(
        self, reviews: _Reviews | None = None, status: RunStatus = RunStatus.FAILED
    ) -> None:
        self.calls = []
        self.reviews = reviews
        self.status = status

    async def resume(self, **kwargs):
        self.calls.append(kwargs)
        if self.reviews is not None:
            self.reviews.tasks = tuple(
                task.model_copy(update={"status": ReviewStatus.REJECTED})
                for task in self.reviews.tasks
            )
        return MonitoringWorkflowResult(run_id=kwargs["run_id"], status=self.status)


class _Context:
    def __init__(self, state: dict, response: dict | None = None) -> None:
        self.state = state
        self.user_id = "reviewer-1"
        self.user_content = types.Content(
            role="user", parts=[types.Part(text="original tariff question")]
        )
        latest = (
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id="root-interrupt-1",
                            name="adk_request_input",
                            response={"result": response},
                        )
                    )
                ],
            )
            if response is not None
            else types.Content(role="user", parts=[types.Part(text="reject")])
        )
        self.session = SimpleNamespace(
            id="original-chat-1",
            events=[
                SimpleNamespace(
                    author="review_agent",
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                function_call=types.FunctionCall(
                                    id="root-interrupt-1",
                                    name="adk_request_input",
                                    args={"message": "Review the rate"},
                                )
                            )
                        ],
                    ),
                ),
                SimpleNamespace(author="user", content=latest),
            ],
        )


def test_multiple_chat_runs_keep_separate_review_progress() -> None:
    first = str(uuid4())
    second = str(uuid4())
    context = _Context(
        {
            "monitoring_active_run_id": first,
            "monitoring_review_choices": {"review-a": {"decision_type": "approve"}},
            "monitoring_review_current_id": "review-b",
        }
    )
    _switch_chat_run(context, second)
    assert context.state["monitoring_review_choices"] == {}
    context.state["monitoring_review_choices"] = {
        "review-c": {"decision_type": "reject_all"}
    }
    _switch_chat_run(context, first)
    assert context.state["monitoring_review_current_id"] == "review-b"
    assert "review-a" in context.state["monitoring_review_choices"]
    _switch_chat_run(context, second)
    assert "review-c" in context.state["monitoring_review_choices"]


@pytest.mark.asyncio
async def test_native_chat_review_requires_adk_input_and_resumes_worker() -> None:
    run = _run()
    tasks = (_review(run), _review(run, "fees"))
    runs = _Runs(run)
    workflow = _Workflow()
    service = ChatReviewService(runs=runs, reviews=_Reviews(tasks), workflow=workflow)
    state = {"monitoring_active_run_id": str(run.id), "monitoring_review_choices": {}}
    configure_services(runs, None, chat_review_service=service)
    try:
        first = await get_next_monitoring_review(_Context(state))
        assert first["status"] == "needs_input"
        assert first["review"]["evidence"][0]["excerpt"] == "Official rate is 12.5%"
        assert first["response_schema"]["required"] == ["review_id", "decision_type"]
        assert first["response_schema"]["properties"]["decision_type"]["enum"] == [
            "select_candidate",
            "reject_all",
            "override",
        ]

        untrusted_text = await submit_monitoring_review_input(_Context(state))
        assert untrusted_text["reason_code"] == "review.native_input_required"
        assert workflow.calls == []

        rejected = await submit_monitoring_review_input(
            _Context(
                state,
                {
                    "review_id": first["review"]["review_id"],
                    "decision_type": "reject_all",
                },
            )
        )
    finally:
        configure_services(None, None)

    assert rejected["status"] == "failed"
    assert len(workflow.calls) == 1
    sent = workflow.calls[0]["response"]
    assert {item.review_id for item in sent.decisions} == {task.id for task in tasks}
    assert {item.decision.decision_type.value for item in sent.decisions} == {
        "reject_all"
    }
    assert runs.audits == ["review.chat_resume_requested"]


@pytest.mark.asyncio
async def test_chat_review_rejects_answer_for_another_review() -> None:
    run = _run()
    task = _review(run)
    workflow = _Workflow()
    service = ChatReviewService(
        runs=_Runs(run), reviews=_Reviews((task,)), workflow=workflow
    )
    state = {"monitoring_active_run_id": str(run.id), "monitoring_review_choices": {}}
    configure_services(_Runs(run), None, chat_review_service=service)
    try:
        await get_next_monitoring_review(_Context(state))
        result = await submit_monitoring_review_input(
            _Context(state, {"review_id": str(uuid4()), "decision_type": "approve"})
        )
    finally:
        configure_services(None, None)
    assert result["reason_code"] == "review.input_scope_mismatch"
    assert workflow.calls == []


@pytest.mark.asyncio
async def test_review_response_without_saved_adk_interrupt_is_rejected() -> None:
    run = _run()
    task = _review(run)
    runs = _Runs(run)
    workflow = _Workflow()
    service = ChatReviewService(runs=runs, reviews=_Reviews((task,)), workflow=workflow)
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_review_current_id": str(task.id),
        "monitoring_review_choices": {},
    }
    context = _Context(
        state, {"review_id": str(task.id), "decision_type": "reject_all"}
    )
    context.session.events.pop(0)
    configure_services(runs, None, chat_review_service=service)
    try:
        result = await submit_monitoring_review_input(context)
    finally:
        configure_services(None, None)
    assert result["reason_code"] == "review.native_input_required"
    assert workflow.calls == []


@pytest.mark.asyncio
async def test_chat_reply_after_admin_abort_reports_terminal_run() -> None:
    run = _run(RunStatus.FAILED)
    runs = _Runs(run)
    service = ChatReviewService(runs=runs, reviews=_Reviews(()), workflow=_Workflow())
    review_id = str(uuid4())
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_review_current_id": review_id,
    }
    configure_services(runs, None, chat_review_service=service)
    try:
        result = await submit_monitoring_review_input(
            _Context(
                state,
                {"review_id": review_id, "decision_type": "reject_all"},
            )
        )
    finally:
        configure_services(None, None)
    assert result["status"] == "failed"
    assert result["reason_code"] == "review.no_longer_pending"


@pytest.mark.asyncio
async def test_successful_chat_review_answers_original_question() -> None:
    class _AnswerService:
        def __init__(self) -> None:
            self.commands = []

        async def answer(self, command):
            self.commands.append(command)
            return AnswerResult(
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                product=command.product,
                offering_id=command.offering_id,
            )

    run = _run()
    task = _review(run)
    runs = _Runs(run)
    workflow = _Workflow(status=RunStatus.SUCCEEDED)
    service = ChatReviewService(runs=runs, reviews=_Reviews((task,)), workflow=workflow)
    answer = _AnswerService()
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_review_choices": {},
        "monitoring_original_question": "What is the overdraft rate?",
    }
    configure_services(runs, answer, chat_review_service=service)
    try:
        prompt = await get_next_monitoring_review(_Context(state))
        result = await submit_monitoring_review_input(
            _Context(
                state,
                {
                    "review_id": prompt["review"]["review_id"],
                    "decision_type": "select_candidate",
                    "candidate_id": "candidate-1",
                },
            )
        )
    finally:
        configure_services(None, None)
    assert result["status"] == "succeeded"
    assert result["answer"]["status"] == "insufficient_evidence"
    assert answer.commands[0].query == "What is the overdraft rate?"
    assert answer.commands[0].offering_id is OfferingId.OVERDRAFT


@pytest.mark.asyncio
async def test_abort_all_rejects_each_pending_run_through_workflow() -> None:
    run = _run()
    tasks = (_review(run), _review(run, "fees"))
    reviews = _Reviews(tasks)
    workflow = _Workflow(reviews)
    service = ChatReviewService(runs=_Runs(run), reviews=reviews, workflow=workflow)
    result = await service.abort_all()
    assert result["aborted_review_count"] == 2
    assert result["aborted_runs"][0]["run_id"] == str(run.id)
    assert result["failed_runs"] == []
    assert len(workflow.calls) == 1


@pytest.mark.asyncio
async def test_abort_reports_unprepared_review_as_failed_and_keeps_it_pending() -> None:
    run = _run()
    task = _review(run).model_copy(update={"correlation": None})
    reviews = _Reviews((task,))
    service = ChatReviewService(
        runs=_Runs(run), reviews=reviews, workflow=_Workflow(reviews)
    )
    result = await service.abort_all()
    assert result["aborted_review_count"] == 0
    assert result["failed_runs"] == [
        {"run_id": str(run.id), "reason": "ReviewNotReadyError"}
    ]
    assert reviews.tasks[0].status is ReviewStatus.PENDING


@pytest.mark.asyncio
async def test_abort_api_requires_configured_admin_token() -> None:
    class _AbortService:
        async def abort_all(self):
            return {"aborted_runs": [], "failed_runs": [], "aborted_review_count": 0}

    app = FastAPI()
    app.state.chat_review_service = _AbortService()
    app.state.settings = SimpleNamespace(
        hitl=HitlSettings(review_admin_token=SecretStr("secret-token"))
    )
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        missing = await client.post("/api/v1/reviews/abort-pending")
        wrong = await client.post(
            "/api/v1/reviews/abort-pending", headers={"X-Review-Admin-Token": "wrong"}
        )
        allowed = await client.post(
            "/api/v1/reviews/abort-pending",
            headers={"X-Review-Admin-Token": "secret-token"},
        )
    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["aborted_review_count"] == 0
    app.state.settings = SimpleNamespace(hitl=HitlSettings())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        unconfigured = await client.post(
            "/api/v1/reviews/abort-pending",
            headers={"X-Review-Admin-Token": "secret-token"},
        )
    assert unconfigured.status_code == 503


@pytest.mark.asyncio
async def test_adk_native_input_resumes_original_session_and_is_visible_to_tool() -> (
    None
):
    from google.adk.agents import Agent
    from google.adk.apps import App, ResumabilityConfig
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools import request_input

    from app.tools import _native_input

    class _LocalModel(BaseLlm):
        calls: int = 0

        async def generate_content_async(self, llm_request, stream=False):
            self.calls += 1
            if self.calls == 1:
                part = types.Part(
                    function_call=types.FunctionCall(
                        name="adk_request_input",
                        args={
                            "message": "Review the captured rate",
                            "response_schema": {
                                "type": "object",
                                "properties": {"review_id": {"type": "string"}},
                            },
                        },
                    )
                )
            elif self.calls == 2:
                part = types.Part(
                    function_call=types.FunctionCall(
                        name="capture_native_reply", args={}
                    )
                )
            else:
                part = types.Part(text="Review response received")
            yield LlmResponse(content=types.Content(role="model", parts=[part]))

    async def capture_native_reply(tool_context: ToolContext) -> dict:
        return _native_input(tool_context) or {}

    app = App(
        name="native_review_test",
        root_agent=Agent(
            name="review_agent",
            model=_LocalModel(model="local-test"),
            tools=[request_input, capture_native_reply],
        ),
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
    sessions = InMemorySessionService()
    await sessions.create_session(
        app_name="native_review_test", user_id="reviewer", session_id="original-chat"
    )
    runner = Runner(app=app, session_service=sessions)
    first = [
        event
        async for event in runner.run_async(
            user_id="reviewer",
            session_id="original-chat",
            new_message=types.Content(
                role="user", parts=[types.Part(text="What is the rate?")]
            ),
        )
    ]
    paused = next(event for event in first if event.long_running_tool_ids)
    interrupt_id = next(iter(paused.long_running_tool_ids))
    response = {
        "review_id": "review-1",
        "decision_type": "reject_all",
    }
    resumed = [
        event
        async for event in runner.run_async(
            user_id="reviewer",
            session_id="original-chat",
            invocation_id=paused.invocation_id,
            new_message=types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=interrupt_id,
                            name="adk_request_input",
                            response={"result": response},
                        )
                    )
                ],
            ),
        )
    ]
    captured = [
        part.function_response.response
        for event in resumed
        for part in (event.content.parts if event.content else ())
        if part.function_response
        and part.function_response.name == "capture_native_reply"
    ]
    assert captured == [response]
    assert any(
        part.text == "Review response received"
        for event in resumed
        for part in (event.content.parts if event.content else ())
    )


@pytest.mark.asyncio
async def test_indefinite_term_candidate_resumes_review_workflow() -> None:
    run = _run()
    task = _review(run, "term")
    task = task.model_copy(
        update={
            "candidates": (
                ReviewCandidate(
                    candidate_id="term-text",
                    field="term",
                    value="Indefinite term (until requested back)",
                    evidence_references=("evidence-1",),
                ),
            )
        }
    )
    runs = _Runs(run)
    workflow = _Workflow(status=RunStatus.SUCCEEDED)
    service = ChatReviewService(runs=runs, reviews=_Reviews((task,)), workflow=workflow)
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_review_choices": {},
    }
    configure_services(runs, None, chat_review_service=service)
    try:
        prompt = await get_next_monitoring_review(_Context(state))
        result = await submit_monitoring_review_input(
            _Context(
                state,
                {
                    "review_id": prompt["review"]["review_id"],
                    "decision_type": "select_candidate",
                    "candidate_id": "term-text",
                },
            )
        )
    finally:
        configure_services(None, None)
    assert result["status"] == "succeeded"
    assert state["monitoring_review_choices"] == {}


@pytest.mark.asyncio
async def test_invalid_term_candidate_is_rejected_before_workflow_resume() -> None:
    from app.domain.monitoring_workflow import (
        MonitoringReviewResponse,
        ReviewResponseItem,
    )
    from app.domain.review import ReviewDecision, ReviewDecisionType

    run = _run()
    task = _review(run, "term")
    task = task.model_copy(
        update={
            "candidates": (
                ReviewCandidate(
                    candidate_id="unknown-term",
                    field="term",
                    value="Some indefinite term",
                    evidence_references=("evidence-1",),
                ),
            )
        }
    )
    runs = _Runs(run)
    workflow = _Workflow()
    service = ChatReviewService(runs=runs, reviews=_Reviews((task,)), workflow=workflow)
    response = MonitoringReviewResponse(
        decisions=(
            ReviewResponseItem(
                review_id=task.id,
                decision=ReviewDecision(
                    decision_type=ReviewDecisionType.SELECT_CANDIDATE,
                    candidate_id="unknown-term",
                ),
            ),
        )
    )

    with pytest.raises(ValueError, match="does not match the field schema"):
        await service.resume(
            run.id,
            response,
            actor_user_id="reviewer-1",
            actor_session_id="original-chat-1",
        )

    assert workflow.calls == []
    assert runs.audits == []


@pytest.mark.asyncio
async def test_stale_review_choice_is_reprompted_after_failed_resume() -> None:
    run = _run()
    task = _review(run, "term")
    runs = _Runs(run)
    service = ChatReviewService(
        runs=runs, reviews=_Reviews((task,)), workflow=_Workflow()
    )
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_review_choices": {
            str(task.id): {"decision_type": "override", "override_value": "bad"}
        },
    }
    configure_services(runs, None, chat_review_service=service)
    try:
        prompt = await get_next_monitoring_review(_Context(state))
    finally:
        configure_services(None, None)

    assert prompt["status"] == "needs_input"
    assert prompt["review"]["review_id"] == str(task.id)
    assert state["monitoring_review_choices"] == {}


@pytest.mark.asyncio
async def test_on_demand_text_override_can_resume_review() -> None:
    run = _run()
    task = _review(run, "term").model_copy(
        update={
            "reason": ReviewReason.MISSING_REQUIRED_FIELD,
            "candidates": (),
        }
    )
    runs = _Runs(run)
    workflow = _Workflow(status=RunStatus.SUCCEEDED)
    service = ChatReviewService(runs=runs, reviews=_Reviews((task,)), workflow=workflow)
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_review_choices": {},
    }
    configure_services(runs, None, chat_review_service=service)
    try:
        prompt = await get_next_monitoring_review(_Context(state))
        result = await submit_monitoring_review_input(
            _Context(
                state,
                {
                    "review_id": prompt["review"]["review_id"],
                    "decision_type": "override",
                    "override_value": "Indefinite term (until requested back)",
                    "reason": "The official source says the term ends on demand.",
                    "evidence_reference": "evidence-1",
                },
            )
        )
    finally:
        configure_services(None, None)

    assert result["status"] == "succeeded"
    assert len(workflow.calls) == 1


class _MonitoringContext:
    """A chat whose long-running monitoring call is still unanswered."""

    def __init__(self, state: dict, *, answered: bool) -> None:
        self.state = state
        self.user_id = "reviewer-1"
        self.user_content = types.Content(role="user", parts=[types.Part(text="yes")])
        events = [
            SimpleNamespace(
                author="ameria_tariff_monitor_cli",
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                id="monitor-1",
                                name="start_tariff_monitoring_cli",
                                args={"product": "consumer_loan"},
                            )
                        )
                    ],
                ),
            )
        ]
        if answered:
            events.append(
                SimpleNamespace(
                    author="user",
                    content=types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    id="monitor-1",
                                    name="start_tariff_monitoring_cli",
                                    response={"status": "failed"},
                                )
                            )
                        ],
                    ),
                )
            )
        self.session = SimpleNamespace(id="original-chat-1", events=events)


@pytest.mark.asyncio
async def test_review_tool_refuses_while_the_cli_owes_a_monitoring_result() -> None:
    """The model polled this tool 45 times during one run; it must not pay for that."""
    run = _run(RunStatus.RUNNING)
    runs = _Runs(run)
    service = ChatReviewService(runs=runs, reviews=_Reviews(()), workflow=_Workflow())
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_chat_run_ids": [str(run.id)],
    }
    configure_services(runs, None, chat_review_service=service)
    try:
        answer = await get_next_monitoring_review(
            _MonitoringContext(state, answered=False)
        )
    finally:
        configure_services(None, None, chat_review_service=None)

    assert answer == {
        "status": "rejected",
        "reason_code": "review.awaiting_cli_result",
        "action": "stop_and_wait",
    }


@pytest.mark.asyncio
async def test_review_tool_reports_a_running_run_without_pollable_detail() -> None:
    run = _run(RunStatus.RUNNING)
    runs = _Runs(run)
    service = ChatReviewService(runs=runs, reviews=_Reviews(()), workflow=_Workflow())
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_chat_run_ids": [str(run.id)],
    }
    configure_services(runs, None, chat_review_service=service)
    try:
        answer = await get_next_monitoring_review(
            _MonitoringContext(state, answered=True)
        )
    finally:
        configure_services(None, None, chat_review_service=None)

    assert answer["status"] == "in_progress"
    assert answer["action"] == "stop_and_wait"
    # Nothing here changes between polls, so there is nothing to poll for.
    assert "failure_code" not in answer
    assert "current_stage" not in answer


@pytest.mark.asyncio
async def test_review_tool_explains_a_failed_run_in_words_and_code() -> None:
    run = _run(RunStatus.FAILED).model_copy(
        update={"failure_code": "source.model_failed"}
    )
    runs = _Runs(run)
    service = ChatReviewService(runs=runs, reviews=_Reviews(()), workflow=_Workflow())
    state = {
        "monitoring_active_run_id": str(run.id),
        "monitoring_chat_run_ids": [str(run.id)],
    }
    configure_services(runs, None, chat_review_service=service)
    try:
        answer = await get_next_monitoring_review(
            _MonitoringContext(state, answered=True)
        )
    finally:
        configure_services(None, None, chat_review_service=None)

    assert answer["status"] == "failed"
    assert answer["failure_code"] == "source.model_failed"
    assert "no configured model was available" in answer["failure_summary"]
