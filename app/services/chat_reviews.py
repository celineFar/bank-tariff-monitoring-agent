from __future__ import annotations

from collections import defaultdict
from typing import Protocol
from uuid import UUID

from app.domain.monitoring import RunStatus
from app.domain.monitoring_workflow import (
    MonitoringReviewRequest,
    MonitoringReviewResponse,
    MonitoringWorkflowResult,
    ReviewResponseItem,
)
from app.domain.review import (
    ReviewDecision,
    ReviewDecisionType,
    ReviewStatus,
    ReviewTask,
)
from app.domain.semantic_extraction import ExtractionField
from app.repositories.contracts import ReviewRepository, RunRepository
from app.services.monitoring_workflow import (
    MONITORING_WORKFLOW_APP_NAME,
    build_review_request,
)
from app.services.review_decisions import coerce_review_candidate_value
from app.services.semantic_extraction import validate_review_field_value


class ReviewResumePort(Protocol):
    async def resume(
        self,
        *,
        user_id: str,
        session_id: str,
        interrupt_id: str,
        response: MonitoringReviewResponse,
        run_id: UUID,
    ) -> MonitoringWorkflowResult: ...


class ReviewNotReadyError(RuntimeError):
    pass


class ChatReviewService:
    """Present business reviews in chat and resume their durable worker invocation."""

    def __init__(
        self,
        *,
        runs: RunRepository,
        reviews: ReviewRepository,
        workflow: ReviewResumePort,
    ) -> None:
        self._runs = runs
        self._reviews = reviews
        self._workflow = workflow

    async def pending_request(self, run_id: UUID) -> MonitoringReviewRequest:
        run = await self._runs.get(run_id)
        if run is None:
            raise LookupError(str(run_id))
        if run.status is not RunStatus.AWAITING_REVIEW:
            raise ReviewNotReadyError(f"run is {run.status.value}")
        tasks = await self._pending(run_id)
        self._correlation(tasks)
        return build_review_request(run_id, tasks)

    async def resume(
        self,
        run_id: UUID,
        response: MonitoringReviewResponse,
        *,
        actor_user_id: str,
        actor_session_id: str,
    ) -> MonitoringWorkflowResult:
        request = await self.pending_request(run_id)
        if {item.review_id for item in response.decisions} != {
            item.review_id for item in request.reviews
        }:
            raise ValueError("every pending review needs exactly one decision")
        tasks = await self._pending(run_id)
        _validate_review_values(tasks, response)
        correlation = self._correlation(tasks)
        await self._runs.record_audit(
            run_id,
            "review.chat_resume_requested",
            payload={
                "actor_user_id": actor_user_id,
                "actor_session_id": actor_session_id,
                "review_ids": [str(item.review_id) for item in response.decisions],
            },
        )
        return await self._workflow.resume(
            user_id=correlation.user_id,
            session_id=correlation.session_id,
            interrupt_id=correlation.interrupt_id,
            response=response,
            run_id=run_id,
        )

    async def abort_all(self) -> dict[str, object]:
        """Reject every ready paused run through ADK, leaving failed runs visible."""
        completed: list[dict[str, object]] = []
        failed: list[dict[str, str]] = []
        pending: list[ReviewTask] = []
        offset = 0
        while True:
            page = await self._reviews.list(
                status=ReviewStatus.PENDING, limit=500, offset=offset
            )
            pending.extend(page)
            if len(page) < 500:
                break
            offset += len(page)
        grouped: dict[UUID, list[ReviewTask]] = defaultdict(list)
        for task in pending:
            grouped[task.run_id].append(task)
        for run_id, tasks in grouped.items():
            try:
                request = await self.pending_request(run_id)
                response = MonitoringReviewResponse(
                    decisions=tuple(
                        ReviewResponseItem(
                            review_id=item.review_id,
                            decision=ReviewDecision(
                                decision_type=ReviewDecisionType.REJECT_ALL
                            ),
                        )
                        for item in request.reviews
                    )
                )
                result = await self.resume(
                    run_id,
                    response,
                    actor_user_id="api-admin",
                    actor_session_id="abort-all-pending",
                )
                remaining = await self._reviews.list(
                    status=ReviewStatus.PENDING, run_id=run_id, limit=1
                )
                if not result.status.is_terminal or remaining:
                    raise ReviewNotReadyError("workflow did not close all reviews")
                completed.append(
                    {
                        "run_id": str(run_id),
                        "status": result.status.value,
                        "review_count": len(tasks),
                    }
                )
            except Exception as exc:
                failed.append({"run_id": str(run_id), "reason": type(exc).__name__})
        return {
            "aborted_runs": completed,
            "failed_runs": failed,
            "aborted_review_count": sum(
                int(item["review_count"]) for item in completed
            ),
        }

    async def _pending(self, run_id: UUID) -> tuple[ReviewTask, ...]:
        tasks = await self._reviews.list(
            status=ReviewStatus.PENDING,
            run_id=run_id,
            limit=20,
        )
        if not tasks:
            raise ReviewNotReadyError("run has no pending review")
        return tasks

    @staticmethod
    def _correlation(tasks: tuple[ReviewTask, ...]):
        correlation = tasks[0].correlation
        if correlation is None or correlation.app_name != MONITORING_WORKFLOW_APP_NAME:
            raise ReviewNotReadyError("review interrupt is still being prepared")
        if any(task.correlation != correlation for task in tasks):
            raise ReviewNotReadyError("review interrupts do not match")
        return correlation


def _validate_review_values(
    tasks: tuple[ReviewTask, ...], response: MonitoringReviewResponse
) -> None:
    by_id = {task.id: task for task in tasks}
    for item in response.decisions:
        task = by_id[item.review_id]
        decision = item.decision
        if decision.decision_type not in {
            ReviewDecisionType.SELECT_CANDIDATE,
            ReviewDecisionType.OVERRIDE,
        }:
            continue
        field = ExtractionField(task.issue_scope)
        if decision.decision_type is ReviewDecisionType.SELECT_CANDIDATE:
            candidate = next(
                (
                    value for value in task.candidates
                    if value.candidate_id == decision.candidate_id
                ),
                None,
            )
            if candidate is None:
                raise ValueError("selected candidate is outside the review scope")
            if candidate.conditions.get("conditions"):
                raise ValueError("candidate conditions require a structured override")
            value = coerce_review_candidate_value(field, candidate.value)
        else:
            value = decision.override_value
        try:
            validate_review_field_value(field, value)
        except ValueError as exc:
            raise ValueError(
                f"review value for {field.value} does not match the field schema"
            ) from exc
