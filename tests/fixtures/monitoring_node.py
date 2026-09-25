"""In-memory fakes and a scripted ADK runner for monitoring-node tests.

Everything here is deterministic: a scripted `BaseLlm` stands in for Gemini
(the technique `tests/unit/test_cli.py` already uses), and the repositories,
run service and pipeline are small in-memory fakes that keep the same state
transitions as PostgreSQL.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from google.adk.agents import Agent
from google.adk.apps import App, ResumabilityConfig
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types
from pydantic import PrivateAttr

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    AnswerResult,
    AnswerStatus,
    ClaimedRun,
    MonitoringRun,
    OfferingExecution,
    OfferingRunStatus,
    RunCommand,
    RunFailureCode,
    RunStatus,
    RunSubmissionResult,
    RunTrigger,
)
from app.domain.review import (
    ReviewCandidate,
    ReviewDecisionType,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.services.monitoring_node import build_monitoring_node
from app.services.monitoring_progress import PipelineProgress, ProgressKind
from app.services.review_resolution import ReviewResolutionService

NOW = datetime(2026, 9, 25, 10, 0, tzinfo=UTC)
APP_NAME = "node_test"
USER_ID = "cli-user"
SESSION_ID = "default"


class Runs:
    """RunRepository + RunService fake with PostgreSQL's transition rules."""

    def __init__(self) -> None:
        self.runs: dict[UUID, MonitoringRun] = {}
        self.owners: dict[UUID, str] = {}
        self.executions: dict[UUID, list[OfferingExecution]] = {}
        self.submits: list[RunCommand] = []
        self.claims: list[tuple[UUID, str]] = []
        self.audits: list[tuple[UUID, str]] = []

    # --- RunService -------------------------------------------------------
    async def submit(self, command: RunCommand, *, idempotency_key=None):
        self.submits.append(command)
        for run in self.runs.values():
            if (
                run.command.product is command.product
                and run.status
                in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.AWAITING_REVIEW}
                and (
                    command.offering_id is None
                    or run.command.offering_id in {None, command.offering_id}
                )
            ):
                return RunSubmissionResult(run=run, created=False)
        run = MonitoringRun(
            id=uuid4(),
            command=command,
            status=RunStatus.QUEUED,
            queued_at=NOW,
        )
        self.runs[run.id] = run
        return RunSubmissionResult(run=run, created=True)

    def add(self, run: MonitoringRun, owner: str | None = None) -> MonitoringRun:
        self.runs[run.id] = run
        if owner:
            self.owners[run.id] = owner
        return run

    # --- RunRepository ----------------------------------------------------
    async def get(self, run_id: UUID) -> MonitoringRun | None:
        return self.runs.get(run_id)

    async def claim(self, run_id: UUID, owner: str) -> ClaimedRun | None:
        self.claims.append((run_id, owner))
        run = self.runs.get(run_id)
        if run is None or run.status is not RunStatus.QUEUED:
            return None
        run = self.set(run_id, status=RunStatus.RUNNING, started_at=NOW)
        self.owners[run_id] = owner
        return ClaimedRun(run=run, worker_id=owner)

    async def list_by_status(self, status: RunStatus, *, limit: int = 100):
        return tuple(run for run in self.runs.values() if run.status is status)[:limit]

    async def list_offering_executions(self, run_id: UUID):
        return tuple(self.executions.get(run_id, ()))

    async def finish_after_review(self, run_id, status, *, summary):
        run = self.runs[run_id]
        if run.status is not RunStatus.AWAITING_REVIEW:
            raise RuntimeError("run cannot finish after review")
        return self.set(
            run_id,
            status=status,
            summary=summary,
            completed_at=NOW + timedelta(minutes=5),
        )

    async def record_audit(self, run_id, event_type, **kwargs) -> None:
        self.audits.append((run_id, event_type))

    def set(self, run_id: UUID, **update: Any) -> MonitoringRun:
        self.runs[run_id] = self.runs[run_id].model_copy(update=update)
        return self.runs[run_id]

    def execution(
        self,
        run_id: UUID,
        offering_id: OfferingId,
        *,
        status: OfferingRunStatus,
        stage: str | None,
        failure_code: str | None = None,
    ) -> None:
        items = [
            item
            for item in self.executions.get(run_id, [])
            if item.offering_id is not offering_id
        ]
        items.append(
            OfferingExecution(
                id=uuid4(),
                run_id=run_id,
                product=offering_id.product,
                offering_id=offering_id,
                status=status,
                current_stage=stage,
                failure_code=failure_code,
            )
        )
        self.executions[run_id] = items


class Reviews:
    def __init__(self) -> None:
        self.tasks: dict[UUID, ReviewTask] = {}

    async def get(self, review_id: UUID):
        return self.tasks.get(review_id)

    async def list(self, *, status=None, run_id=None, limit=100, offset=0, **_):
        return tuple(
            task
            for task in self.tasks.values()
            if (status is None or task.status is status)
            and (run_id is None or task.run_id == run_id)
        )[offset : offset + limit]

    async def supersede(self, review_id: UUID):
        return self._set(review_id, status=ReviewStatus.SUPERSEDED)

    def _set(self, review_id: UUID, **update: Any) -> ReviewTask:
        self.tasks[review_id] = self.tasks[review_id].model_copy(update=update)
        return self.tasks[review_id]


class Decisions:
    def __init__(self, reviews: Reviews) -> None:
        self.reviews = reviews
        self.applied: list[tuple[UUID, str, str]] = []

    async def apply(self, review_id, decision, *, reviewer):
        self.applied.append((review_id, decision.decision_type.value, reviewer))
        rejected = decision.decision_type is ReviewDecisionType.REJECT_ALL
        return self.reviews._set(
            review_id,
            status=ReviewStatus.REJECTED if rejected else ReviewStatus.APPROVED,
            reviewer=reviewer,
            decision=decision,
            decided_at=NOW,
        )


@dataclass
class Pipeline:
    """Reports three stages, then ends the run as configured."""

    runs: Runs
    reviews: Reviews
    review_scopes: tuple[str, ...] = ()
    fail: bool = False
    block: bool = False
    stage_delay: float = 0.0
    executed: int = 0
    started: asyncio.Event = field(default_factory=asyncio.Event)

    async def execute(self, run: MonitoringRun, *, progress=None) -> MonitoringRun:
        self.executed += 1
        offering = run.command.offering_id or OfferingId.OVERDRAFT
        try:
            await self._report(progress, run, ProgressKind.RUN_STARTED)
            for stage in ("acquisition", "normalization", "semantic_extraction"):
                self.runs.execution(
                    run.id, offering, status=OfferingRunStatus.RUNNING, stage=stage
                )
                await self._report(progress, run, ProgressKind.STAGE_STARTED, stage)
                self.started.set()
                if self.block:
                    await asyncio.Event().wait()
                await asyncio.sleep(self.stage_delay)
                await self._report(progress, run, ProgressKind.STAGE_COMPLETED, stage)
        except asyncio.CancelledError:
            self.runs.execution(
                run.id,
                offering,
                status=OfferingRunStatus.FAILED,
                stage="semantic_extraction",
                failure_code=RunFailureCode.CANCELLED.value,
            )
            self.runs.set(
                run.id,
                status=RunStatus.FAILED,
                failure_code=RunFailureCode.CANCELLED.value,
                completed_at=NOW,
            )
            raise
        if self.fail:
            self.runs.execution(
                run.id,
                offering,
                status=OfferingRunStatus.FAILED,
                stage="semantic_extraction",
                failure_code="source.model_failed",
            )
            return self.runs.set(
                run.id,
                status=RunStatus.FAILED,
                failure_code="source.model_failed",
                completed_at=NOW,
            )
        if self.review_scopes:
            self.runs.execution(
                run.id,
                offering,
                status=OfferingRunStatus.CANDIDATE_REVIEW,
                stage="publication",
            )
            for index, scope in enumerate(self.review_scopes):
                task = review_task(run, offering, scope, order=index)
                self.reviews.tasks[task.id] = task
            return self.runs.set(
                run.id,
                status=RunStatus.AWAITING_REVIEW,
                summary={"succeeded": 0, "failed": 0},
            )
        self.runs.execution(
            run.id, offering, status=OfferingRunStatus.SUCCEEDED, stage="publication"
        )
        return self.runs.set(
            run.id,
            status=RunStatus.SUCCEEDED,
            summary={"succeeded": 1, "failed": 0},
            completed_at=NOW + timedelta(minutes=5),
        )

    @staticmethod
    async def _report(progress, run, kind, stage=None) -> None:
        if progress is None:
            return
        await progress.report(
            PipelineProgress(
                kind=kind,
                run_id=run.id,
                product=run.command.product,
                offering_id=run.command.offering_id,
                stage=stage,
            )
        )


def review_task(
    run: MonitoringRun, offering: OfferingId, scope: str, *, order: int = 0
) -> ReviewTask:
    review_id = uuid4()
    return ReviewTask(
        id=review_id,
        idempotency_key=f"review:{review_id}",
        run_id=run.id,
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=offering.product,
        offering_id=offering,
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
        created_at=NOW + timedelta(seconds=order),
        updated_at=NOW,
    )


class Answers:
    def __init__(self) -> None:
        self.questions: list[str] = []

    async def answer_question(self, command):
        self.questions.append(command.query)
        return AnswerResult(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            product=command.product,
            offering_id=command.offering_id,
        )


class ScriptedModel(BaseLlm):
    """Plays back function calls, then answers with text; counts its calls."""

    _script: list[types.Part] = PrivateAttr(default_factory=list)
    _calls: int = PrivateAttr(default=0)

    def play(self, *parts: types.Part) -> None:
        self._script.extend(parts)

    @property
    def calls(self) -> int:
        return self._calls

    async def generate_content_async(self, llm_request, stream=False):
        self._calls += 1
        part = self._script.pop(0) if self._script else types.Part(text="done")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def call(name: str, **args: Any) -> types.Part:
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


def text(value: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=value)])


def reply(interrupt_id: str, result: Any) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=interrupt_id,
                    name="adk_request_input",
                    response={"result": result},
                )
            )
        ],
    )


@dataclass
class Harness:
    runs: Runs
    reviews: Reviews
    decisions: Decisions
    pipeline: Pipeline
    answers: Answers
    model: ScriptedModel
    runner: Runner
    sessions: InMemorySessionService
    node: Any

    async def turn(self, message: types.Content) -> list:
        return [
            event
            async for event in self.runner.run_async(
                user_id=USER_ID, session_id=SESSION_ID, new_message=message
            )
        ]

    async def persisted(self) -> list:
        session = await self.sessions.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
        return list(session.events)


def interrupts(events: list) -> list[tuple[str, dict]]:
    """(interrupt id, payload) of every `adk_request_input` call in `events`."""
    found = []
    for event in events:
        for part in (event.content.parts if event.content else ()) or ():
            fc = part.function_call
            if fc is not None and fc.name == "adk_request_input":
                found.append((fc.id, dict(fc.args or {}).get("payload")))
    return found


def function_responses(events: list, name: str) -> list[dict]:
    return [
        dict(part.function_response.response or {})
        for event in events
        for part in (event.content.parts if event.content else ()) or ()
        if part.function_response is not None and part.function_response.name == name
    ]


def progress_events(events: list) -> list:
    return [
        event
        for event in events
        if (event.custom_metadata or {}).get("kind") == "monitoring_progress"
    ]


async def build(
    *,
    tools: list | None = None,
    review_scopes: tuple[str, ...] = (),
    fail: bool = False,
    block: bool = False,
    stage_delay: float = 0.0,
    owner: str = "cli:test-host:1",
    follow_timeout_seconds: float = 5.0,
) -> Harness:
    runs = Runs()
    reviews = Reviews()
    decisions = Decisions(reviews)
    pipeline = Pipeline(
        runs,
        reviews,
        review_scopes=review_scopes,
        fail=fail,
        block=block,
        stage_delay=stage_delay,
    )
    answers = Answers()
    resolution = ReviewResolutionService(
        runs=runs, reviews=reviews, decisions=decisions
    )
    node = build_monitoring_node(
        runs=runs,
        run_service=runs,
        pipeline=pipeline,
        resolution=resolution,
        answer_router=answers,
        owner=owner,
        poll_seconds=0.01,
        follow_timeout_seconds=follow_timeout_seconds,
    )

    async def monitor(
        tool_context: ToolContext,
        product: str | None = None,
        offering_id: str | None = None,
        question: str | None = None,
        review_only: bool = False,
    ) -> dict:
        """Run the monitoring node directly (no authorization layer)."""
        return await tool_context.run_node(
            node,
            {
                "product": product,
                "offering_id": offering_id,
                "question": question,
                "review_only": review_only,
            },
        )

    model = ScriptedModel(model="scripted")
    app = App(
        name=APP_NAME,
        root_agent=Agent(name="root", model=model, tools=tools or [monitor]),
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
    sessions = InMemorySessionService()
    await sessions.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(app=app, session_service=sessions)
    return Harness(
        runs=runs,
        reviews=reviews,
        decisions=decisions,
        pipeline=pipeline,
        answers=answers,
        model=model,
        runner=runner,
        sessions=sessions,
        node=node,
    )


def queued_run(offering: OfferingId = OfferingId.OVERDRAFT, **update) -> MonitoringRun:
    return MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=offering.product, offering_id=offering, trigger=RunTrigger.SCHEDULE
        ),
        status=RunStatus.QUEUED,
        queued_at=NOW,
    ).model_copy(update=update)


PRODUCT = ProductType.CONSUMER_LOAN.value
OFFERING = OfferingId.OVERDRAFT.value
