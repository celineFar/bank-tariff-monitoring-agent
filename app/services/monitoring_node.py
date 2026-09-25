"""The monitoring run as seen from the conversation: one idempotent ADK node.

A chat tool calls `tool_context.run_node(monitoring_node, …)`. The node submits
or finds the run, executes it in this process (streaming progress as partial
events), pauses the *same* invocation on a native `RequestInput` for each
pending review, applies each decision on resume, and finally yields the result
the tool returns to the model.

ADK re-runs the node from the top on every resume (plan §5, E3/E5), so every
branch re-derives its position from PostgreSQL and from `ctx.resume_inputs`,
and the node always returns right after yielding a `RequestInput` (E6).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Protocol
from uuid import UUID

from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import FunctionNode
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    MonitoringRun,
    OfferingExecution,
    QuestionCommand,
    RunCommand,
    RunStatus,
    RunTrigger,
)
from app.domain.review import ReviewDecisionInput, ReviewDecisionType, ReviewTask
from app.repositories.contracts import RunRepository
from app.services.contracts import TariffPipeline
from app.services.failure_mapping import explain_failure_code
from app.services.monitoring_progress import (
    PipelineProgress,
    ProgressKind,
    progress_label,
    stream_progress,
)
from app.services.review_resolution import (
    ReviewInputRejected,
    ReviewResolutionService,
)
from app.services.run_service import RunServicePort, run_covers_command

logger = logging.getLogger(__name__)

MONITORING_NODE_NAME = "monitoring"
PROGRESS_KIND = "monitoring_progress"
REVIEW_INTERRUPT_PREFIX = "review"
# Following a run another process owns is bounded; the user can ask again.
DEFAULT_FOLLOW_TIMEOUT_SECONDS = 1800.0


class AnswerPort(Protocol):
    async def answer_question(self, command: QuestionCommand) -> Any: ...


class NodeModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class MonitoringNodeInput(NodeModel):
    product: ProductType | None = None
    offering_id: OfferingId | None = None
    question: str | None = None
    review_only: bool = False


class OfferingOutcome(NodeModel):
    offering_id: OfferingId
    status: str
    stage: str | None = None
    failure_code: str | None = None
    failure_summary: str | None = None


class MonitoringResult(NodeModel):
    """What the tool returns to the model; it carries no identifiers to relay."""

    # A RunStatus value, or blocked / no_pending_reviews / still_running.
    status: str
    product: ProductType | None = None
    offering_id: OfferingId | None = None
    elapsed_seconds: int = Field(default=0, ge=0)
    offerings: tuple[OfferingOutcome, ...] = ()
    reviews_applied: int = Field(default=0, ge=0)
    created: bool = False
    followed: bool = False
    answer: dict[str, JsonValue] | None = None
    answer_status: str | None = None
    failure_code: str | None = None
    failure_summary: str | None = None
    message: str | None = None


def review_interrupt_id(run_id: UUID, review_id: UUID, attempt: int = 1) -> str:
    """`review:<run>:<review>[:<attempt>]` — the run id makes re-runs idempotent."""
    base = f"{REVIEW_INTERRUPT_PREFIX}:{run_id}:{review_id}"
    return base if attempt == 1 else f"{base}:{attempt}"


def parse_review_interrupt_id(value: str) -> tuple[UUID, UUID, int] | None:
    parts = value.split(":")
    if len(parts) not in {3, 4} or parts[0] != REVIEW_INTERRUPT_PREFIX:
        return None
    try:
        attempt = int(parts[3]) if len(parts) == 4 else 1
        return UUID(parts[1]), UUID(parts[2]), attempt
    except ValueError:
        return None


def build_monitoring_node(
    *,
    runs: RunRepository,
    run_service: RunServicePort,
    pipeline: TariffPipeline,
    resolution: ReviewResolutionService,
    answer_router: AnswerPort | None,
    owner: str,
    poll_seconds: float,
    follow_timeout_seconds: float = DEFAULT_FOLLOW_TIMEOUT_SECONDS,
    clock: Callable[[], float] = monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> FunctionNode:
    async def monitoring(
        ctx: Context,
        product: str | None = None,
        offering_id: str | None = None,
        question: str | None = None,
        review_only: bool = False,
    ) -> AsyncIterator[Any]:
        """Runs or resumes one tariff monitoring run."""
        request = MonitoringNodeInput(
            product=product,
            offering_id=offering_id,
            question=question,
            review_only=review_only,
        )
        resume = _resume_inputs(ctx)
        created = False

        # 1. Find the run. A resumed node goes back to the run it paused on and
        #    never submits again; that keeps a replay from starting a new run.
        run = await _resumed_run(runs, resume)
        if run is None and request.review_only:
            run = await _oldest_awaiting_review(runs, request)
            if run is None:
                yield _result(
                    status="no_pending_reviews",
                    request=request,
                    message="No monitoring run is waiting for a review.",
                ).model_dump(mode="json")
                return
        elif run is None:
            if request.product is None:
                raise ValueError("a monitoring run needs a product family")
            command = RunCommand(
                product=request.product,
                offering_id=request.offering_id,
                trigger=RunTrigger.ADK,
            )
            submission = await run_service.submit(command)
            run, created = submission.run, submission.created
            if not run_covers_command(run, command):
                yield _result(
                    status="blocked",
                    request=request,
                    run=run,
                    message=(
                        "Another monitoring run for "
                        f"{_scope_label(run)} is already in progress, so this "
                        "offering was not started. Ask again once it finishes."
                    ),
                ).model_dump(mode="json")
                return

        # 2. Execute it here if nobody has claimed it yet.
        if run.status is RunStatus.QUEUED:
            claimed = await runs.claim(run.id, owner)
            if claimed is not None:
                stream = stream_progress(
                    lambda sink: pipeline.execute(claimed.run, progress=sink)
                )
                async for item in stream:
                    yield _progress_event(item)
                run = await _reload(runs, run.id)

        # 3. Otherwise follow the process that owns it (the one remaining poll).
        followed = False
        if run.status in {RunStatus.QUEUED, RunStatus.RUNNING}:
            followed = True
            async for event in _follow(
                runs,
                run,
                poll_seconds=poll_seconds,
                timeout_seconds=follow_timeout_seconds,
                clock=clock,
                sleep=sleep,
            ):
                yield event
            run = await _reload(runs, run.id)
            if run.status in {RunStatus.QUEUED, RunStatus.RUNNING}:
                yield (
                    await _outcome(
                        runs,
                        run,
                        request,
                        status="still_running",
                        created=created,
                        followed=True,
                        message=(
                            "The run started elsewhere is still going; ask for "
                            "its status later."
                        ),
                    )
                ).model_dump(mode="json")
                return

        # 4. Ask for each pending review, one pause per review.
        if run.status is RunStatus.AWAITING_REVIEW:
            pending = await resolution.pending(run.id)
            # Position among all of the run's reviews, so "2/2" stays "2/2"
            # when the node re-runs with the first one already decided.
            ordered = [item.id for item in await resolution.all_reviews(run.id)]
            total = len(ordered)
            for task in pending:
                position = ordered.index(task.id) + 1 if task.id in ordered else 1
                attempt, reply = _latest_reply(resume, run.id, task.id)
                if reply is None:
                    yield _review_request(
                        resolution,
                        task,
                        run_id=run.id,
                        attempt=1,
                        position=position,
                        total=total,
                    )
                    return
                try:
                    decision = resolution.validate(
                        task, ReviewDecisionInput.model_validate(reply)
                    )
                    await resolution.apply(task, decision, reviewer=ctx.user_id)
                except ValidationError as exc:
                    rejected = ReviewInputRejected(
                        "review.invalid_input",
                        str(exc.errors()[0].get("msg", "The reply is not valid.")),
                        resolution.input_format(task),
                    )
                    yield _review_request(
                        resolution,
                        task,
                        run_id=run.id,
                        attempt=attempt + 1,
                        position=position,
                        total=total,
                        rejected=rejected,
                    )
                    return
                except ReviewInputRejected as rejected:
                    yield _review_request(
                        resolution,
                        task,
                        run_id=run.id,
                        attempt=attempt + 1,
                        position=position,
                        total=total,
                        rejected=rejected,
                    )
                    return
                if decision.decision_type is ReviewDecisionType.REJECT_ALL:
                    break
            run = await resolution.complete_run(run.id)

        # 5. Report, and answer the original question from accepted facts.
        result = await _outcome(runs, run, request, created=created, followed=followed)
        if request.question and run.status in {
            RunStatus.SUCCEEDED,
            RunStatus.PARTIAL_SUCCESS,
        }:
            result = await _with_answer(answer_router, result, run, request)
        yield result.model_dump(mode="json")

    node = FunctionNode(
        func=monitoring,
        name=MONITORING_NODE_NAME,
        rerun_on_resume=True,
        parameter_binding="node_input",
    )
    node.description = "Runs or resumes one tariff monitoring run."
    return node


def _resume_inputs(ctx: Context) -> dict[str, Any]:
    raw = dict(getattr(ctx, "resume_inputs", None) or {})
    return {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in raw.items()
    }


async def _resumed_run(
    runs: RunRepository, resume: dict[str, Any]
) -> MonitoringRun | None:
    run_ids = {
        parsed[0]
        for key in resume
        if (parsed := parse_review_interrupt_id(key)) is not None
    }
    if not run_ids:
        return None
    if len(run_ids) > 1:
        raise ValueError("one monitoring invocation cannot span several runs")
    return await _reload(runs, next(iter(run_ids)))


async def _reload(runs: RunRepository, run_id: UUID) -> MonitoringRun:
    run = await runs.get(run_id)
    if run is None:
        raise LookupError(str(run_id))
    return run


async def _oldest_awaiting_review(
    runs: RunRepository, request: MonitoringNodeInput
) -> MonitoringRun | None:
    for run in await runs.list_by_status(RunStatus.AWAITING_REVIEW, limit=100):
        if request.product is not None and run.command.product is not request.product:
            continue
        if (
            request.offering_id is not None
            and run.command.offering_id is not None
            and run.command.offering_id is not request.offering_id
        ):
            continue
        return run
    return None


def _latest_reply(
    resume: dict[str, Any], run_id: UUID, review_id: UUID
) -> tuple[int, Any]:
    """The highest attempt answered for this review, and its reply."""
    latest = 0
    reply: Any = None
    for key, value in resume.items():
        parsed = parse_review_interrupt_id(key)
        if parsed is None or parsed[0] != run_id or parsed[1] != review_id:
            continue
        if parsed[2] > latest:
            latest, reply = parsed[2], value
    return latest, reply


def _review_request(
    resolution: ReviewResolutionService,
    task: ReviewTask,
    *,
    run_id: UUID,
    attempt: int,
    position: int,
    total: int,
    rejected: ReviewInputRejected | None = None,
) -> RequestInput:
    view = resolution.prompt_view(task)
    payload: dict[str, Any] = {
        "kind": "tariff_review",
        "view": view.model_dump(mode="json"),
        "input_format": resolution.input_format(task),
        "position": position,
        "total": total,
        "attempt": attempt,
    }
    if rejected is not None:
        payload["rejected"] = rejected.as_payload()
    field = task.issue_scope.replace("_", " ")
    return RequestInput(
        interrupt_id=review_interrupt_id(run_id, task.id, attempt),
        message=(
            f"Review {position}/{total}: {task.offering_id.value} · {field} "
            f"({task.reason.value})"
        ),
        payload=payload,
        response_schema=ReviewDecisionInput,
    )


def _progress_event(item: PipelineProgress) -> Event:
    """Partial: streamed to the caller, never persisted, never in model context.

    Renderers read `custom_metadata["progress"]` (a `PipelineProgress`), never
    the text, which is only a fallback label.
    """
    return Event(
        message=progress_label(item),
        partial=True,
        custom_metadata={
            "kind": PROGRESS_KIND,
            "progress": item.model_dump(mode="json"),
        },
    )


async def _follow(
    runs: RunRepository,
    run: MonitoringRun,
    *,
    poll_seconds: float,
    timeout_seconds: float,
    clock: Callable[[], float],
    sleep: Callable[[float], Awaitable[None]],
) -> AsyncIterator[Event]:
    """Stream the persisted stages of a run another process is executing."""
    yield _progress_event(
        PipelineProgress(
            kind=ProgressKind.FOLLOWING,
            run_id=run.id,
            product=run.command.product,
            offering_id=run.command.offering_id,
            detail=f"A run for {_scope_label(run)} started by "
            f"{_origin(run)} is already in progress — following it.",
        )
    )
    seen: dict[OfferingId, str | None] = {}
    started = clock()
    while clock() - started < timeout_seconds:
        current = await _reload(runs, run.id)
        for execution in await runs.list_offering_executions(run.id):
            if seen.get(execution.offering_id) == execution.current_stage:
                continue
            seen[execution.offering_id] = execution.current_stage
            if execution.current_stage:
                yield _progress_event(
                    PipelineProgress(
                        kind=ProgressKind.STAGE_STARTED,
                        run_id=run.id,
                        product=execution.product,
                        offering_id=execution.offering_id,
                        stage=execution.current_stage,
                    )
                )
        if current.status not in {RunStatus.QUEUED, RunStatus.RUNNING}:
            return
        await sleep(poll_seconds)


async def _outcome(
    runs: RunRepository,
    run: MonitoringRun,
    request: MonitoringNodeInput,
    *,
    status: str | None = None,
    created: bool = False,
    followed: bool = False,
    message: str | None = None,
) -> MonitoringResult:
    executions = await runs.list_offering_executions(run.id)
    summary = run.summary or {}
    reviews_applied = int(summary.get("reviews_approved", 0) or 0) + int(
        summary.get("reviews_rejected", 0) or 0
    )
    return _result(
        status=status or run.status.value,
        request=request,
        run=run,
        offerings=tuple(_offering_outcome(item) for item in executions),
        reviews_applied=reviews_applied,
        created=created,
        followed=followed,
        failure_code=run.failure_code if run.status is RunStatus.FAILED else None,
        message=message,
    )


def _result(
    *,
    status: str,
    request: MonitoringNodeInput,
    run: MonitoringRun | None = None,
    offerings: tuple[OfferingOutcome, ...] = (),
    reviews_applied: int = 0,
    created: bool = False,
    followed: bool = False,
    failure_code: str | None = None,
    message: str | None = None,
) -> MonitoringResult:
    return MonitoringResult(
        status=status,
        product=run.command.product if run is not None else request.product,
        offering_id=(
            run.command.offering_id if run is not None else request.offering_id
        ),
        elapsed_seconds=_elapsed(run) if run is not None else 0,
        offerings=offerings,
        reviews_applied=reviews_applied,
        created=created,
        followed=followed,
        failure_code=failure_code,
        failure_summary=explain_failure_code(failure_code) if failure_code else None,
        message=message,
    )


def _offering_outcome(execution: OfferingExecution) -> OfferingOutcome:
    return OfferingOutcome(
        offering_id=execution.offering_id,
        status=execution.status.value,
        stage=execution.current_stage,
        failure_code=execution.failure_code,
        failure_summary=(
            explain_failure_code(execution.failure_code)
            if execution.failure_code
            else None
        ),
    )


async def _with_answer(
    answer_router: AnswerPort | None,
    result: MonitoringResult,
    run: MonitoringRun,
    request: MonitoringNodeInput,
) -> MonitoringResult:
    if answer_router is None or not request.question:
        return result
    try:
        answer = await answer_router.answer_question(
            QuestionCommand(
                query=request.question,
                product=run.command.product,
                offering_id=run.command.offering_id,
            )
        )
    except Exception:
        logger.warning("post-monitoring answer failed run_id=%s", run.id, exc_info=True)
        return result.model_copy(update={"answer_status": "temporarily_unavailable"})
    dumped = answer.model_dump(mode="json") if isinstance(answer, BaseModel) else answer
    return result.model_copy(update={"answer": dumped, "answer_status": "answered"})


def _elapsed(run: MonitoringRun) -> int:
    if run.started_at is None:
        return 0
    end = run.completed_at or datetime.now(UTC)
    return max(0, int((end - run.started_at).total_seconds()))


def _scope_label(run: MonitoringRun) -> str:
    if run.command.offering_id is not None:
        return run.command.offering_id.value
    return f"the whole {run.command.product.value} family"


def _origin(run: MonitoringRun) -> str:
    return {
        RunTrigger.SCHEDULE: "the daily scheduler",
        RunTrigger.API: "the API",
        RunTrigger.ADK: "another chat",
        RunTrigger.USER: "a user",
    }.get(run.command.trigger, "another process")
