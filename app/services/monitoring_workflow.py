from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.events.request_input import RequestInput
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.workflow import Workflow
from google.genai import types

from app.domain.monitoring import MonitoringRun, RunStatus
from app.domain.monitoring_workflow import (
    MonitoringReviewResponse,
    MonitoringWorkflowInput,
    MonitoringWorkflowResult,
    MonitoringWorkflowState,
)
from app.domain.review import (
    ReviewCorrelation,
    ReviewDecision,
    ReviewStatus,
    ReviewTask,
)
from app.repositories.contracts import ReviewRepository, RunRepository
from app.services.contracts import TariffPipeline

MONITORING_WORKFLOW_APP_NAME = "tariff_monitoring_workflow"


class ReviewDecisionPort(Protocol):
    async def apply(
        self,
        review_id,
        decision: ReviewDecision,
        *,
        reviewer: str,
    ) -> ReviewTask: ...


def build_monitoring_workflow(
    *,
    runs: RunRepository,
    pipeline: TariffPipeline,
    reviews: ReviewRepository,
    decisions: ReviewDecisionPort,
) -> Workflow:
    async def execute_monitoring(
        node_input: MonitoringWorkflowInput,
    ) -> MonitoringRun:
        run = await runs.get(node_input.run_id)
        if run is None:
            raise LookupError(str(node_input.run_id))
        if run.status is RunStatus.RUNNING:
            return await pipeline.execute(run)
        if run.status is RunStatus.AWAITING_REVIEW or run.status.is_terminal:
            return run
        raise ValueError(f"run {run.id} cannot enter workflow from {run.status.value}")

    def route_outcome(node_input: MonitoringRun) -> Event:
        route = (
            "review"
            if node_input.status is RunStatus.AWAITING_REVIEW
            else "finished"
        )
        return Event(
            output=node_input.model_dump(mode="json"),
            actions=EventActions(route=route),
        )

    async def request_human_input(
        ctx: Context,
        node_input: MonitoringRun,
    ) -> AsyncIterator[RequestInput]:
        pending = await reviews.list(
            status=ReviewStatus.PENDING,
            run_id=node_input.id,
            limit=20,
        )
        if not pending:
            raise RuntimeError("awaiting-review run has no pending review tasks")
        interrupt_id = f"monitoring-review:{node_input.id}"
        session = ctx.session
        correlation = ReviewCorrelation(
            app_name=MONITORING_WORKFLOW_APP_NAME,
            user_id=str(getattr(session, "user_id", "reviewer")),
            session_id=str(session.id),
            invocation_id=str(ctx.invocation_id),
            interrupt_id=interrupt_id,
        )
        attached = tuple(
            [
                await reviews.attach_workflow(review.id, correlation)
                for review in pending
            ]
        )
        await runs.record_audit(
            node_input.id,
            "review.paused",
            payload={
                "review_ids": [str(item.id) for item in attached],
                "session_id": correlation.session_id,
                "invocation_id": correlation.invocation_id,
                "interrupt_id": correlation.interrupt_id,
            },
        )
        yield RequestInput(
            interrupt_id=interrupt_id,
            message=(
                f"{len(attached)} tariff review decision(s) are required. "
                "Use only the captured candidate and evidence references shown."
            ),
            payload={
                "run_id": str(node_input.id),
                "reviews": [item.model_dump(mode="json") for item in attached],
            },
            response_schema=MonitoringReviewResponse,
        )

    async def apply_review_decision(
        ctx: Context,
        node_input: MonitoringReviewResponse,
    ) -> MonitoringRun:
        reviewer = str(getattr(ctx.session, "user_id", "reviewer"))
        current = []
        for item in node_input.decisions:
            task = await reviews.get(item.review_id)
            if task is None:
                raise LookupError(str(item.review_id))
            current.append(task)
        run_ids = {item.run_id for item in current}
        if len(run_ids) != 1:
            raise ValueError("all review decisions must belong to one run")
        run_id = next(iter(run_ids))
        await runs.record_audit(
            run_id,
            "review.resume_attempt",
            payload={
                "review_ids": [str(item.review_id) for item in node_input.decisions]
            },
        )
        pending = await reviews.list(
            status=ReviewStatus.PENDING,
            run_id=run_id,
            limit=20,
        )
        if {item.id for item in pending} != {
            item.review_id for item in node_input.decisions
        }:
            await runs.record_audit(
                run_id,
                "review.resume_failed",
                reason_code="review_set_mismatch",
            )
            raise ValueError("response must decide every current pending review exactly once")
        try:
            decided = tuple(
                [
                    await decisions.apply(
                        item.review_id,
                        item.decision,
                        reviewer=reviewer,
                    )
                    for item in node_input.decisions
                ]
            )
        except Exception as exc:
            await runs.record_audit(
                run_id,
                "review.resume_failed",
                reason_code=type(exc).__name__,
            )
            raise
        approved = sum(item.status is ReviewStatus.APPROVED for item in decided)
        rejected = sum(item.status is ReviewStatus.REJECTED for item in decided)
        run = await runs.get(run_id)
        if run is None:
            raise LookupError(str(run_id))
        prior_succeeded = int(run.summary.get("succeeded", 0))
        prior_failed = int(run.summary.get("failed", 0))
        status = terminal_review_status(
            approved=approved,
            rejected=rejected,
            prior_succeeded=prior_succeeded,
            prior_failed=prior_failed,
        )
        completed = await runs.finish_after_review(
            run_id,
            status,
            summary={
                **run.summary,
                "reviews_approved": approved,
                "reviews_rejected": rejected,
            },
        )
        await runs.record_audit(
            run_id,
            "review.approved" if rejected == 0 else "review.rejected",
            payload={"approved": approved, "rejected": rejected},
        )
        return completed

    def build_final_result(node_input: MonitoringRun) -> MonitoringWorkflowResult:
        raw_review_ids = node_input.summary.get("review_ids", [])
        return MonitoringWorkflowResult(
            run_id=node_input.id,
            status=node_input.status,
            review_ids=tuple(raw_review_ids),
            paused=node_input.status is RunStatus.AWAITING_REVIEW,
            summary=node_input.summary,
        )

    return Workflow(
        name="tariff_monitoring_workflow",
        input_schema=MonitoringWorkflowInput,
        output_schema=MonitoringWorkflowResult,
        state_schema=MonitoringWorkflowState,
        edges=[
            ("START", execute_monitoring),
            (execute_monitoring, route_outcome),
            (
                route_outcome,
                {
                    "finished": build_final_result,
                    "review": request_human_input,
                },
            ),
            (request_human_input, apply_review_decision),
            (apply_review_decision, build_final_result),
        ],
    )


def build_monitoring_app(workflow: Workflow) -> App:
    return App(
        name=MONITORING_WORKFLOW_APP_NAME,
        root_agent=workflow,
        resumability_config=ResumabilityConfig(is_resumable=True),
    )


class MonitoringWorkflowRunner:
    """Starts and resumes one durable ADK workflow invocation per business run."""

    def __init__(
        self,
        *,
        app: App,
        session_service: BaseSessionService,
        artifact_service=None,
    ) -> None:
        self._runner = Runner(
            app=app,
            session_service=session_service,
            artifact_service=artifact_service,
            auto_create_session=True,
        )

    async def start(self, run: MonitoringRun) -> MonitoringWorkflowResult:
        user_id, session_id = workflow_identity(run)
        content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=MonitoringWorkflowInput(run_id=run.id).model_dump_json()
                )
            ],
        )
        return await self._run(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            fallback_run_id=run.id,
        )

    async def resume(
        self,
        *,
        user_id: str,
        session_id: str,
        interrupt_id: str,
        response: MonitoringReviewResponse,
        run_id: UUID,
    ) -> MonitoringWorkflowResult:
        content = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=interrupt_id,
                        name="adk_request_input",
                        response=response.model_dump(mode="json"),
                    )
                )
            ],
        )
        return await self._run(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            fallback_run_id=run_id,
        )

    async def _run(
        self,
        *,
        user_id: str,
        session_id: str,
        new_message: types.Content,
        fallback_run_id: UUID,
    ) -> MonitoringWorkflowResult:
        final: MonitoringWorkflowResult | None = None
        latest_run: MonitoringRun | None = None
        paused = False
        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
        ):
            if event.long_running_tool_ids:
                paused = True
            if event.output is not None:
                try:
                    final = MonitoringWorkflowResult.model_validate(event.output)
                except (TypeError, ValueError):
                    try:
                        latest_run = MonitoringRun.model_validate(event.output)
                    except (TypeError, ValueError):
                        continue
        if final is not None:
            return final
        if paused:
            raw_review_ids = (
                latest_run.summary.get("review_ids", []) if latest_run else []
            )
            return MonitoringWorkflowResult(
                run_id=fallback_run_id,
                status=RunStatus.AWAITING_REVIEW,
                review_ids=tuple(raw_review_ids),
                paused=True,
                summary=latest_run.summary if latest_run else {},
            )
        raise RuntimeError("monitoring workflow completed without a final result")


def workflow_identity(run: MonitoringRun) -> tuple[str, str]:
    """Return stable origin-scoped identity without treating it as a person."""
    origin = run.command.trigger.value
    return f"monitoring-{origin}", f"monitoring-run-{run.id}"


def terminal_review_status(
    *,
    approved: int,
    rejected: int,
    prior_succeeded: int,
    prior_failed: int,
) -> RunStatus:
    if rejected == 0 and prior_failed == 0:
        return RunStatus.SUCCEEDED
    if approved or prior_succeeded:
        return RunStatus.PARTIAL_SUCCESS
    return RunStatus.FAILED
