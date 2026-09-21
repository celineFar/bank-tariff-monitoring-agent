from __future__ import annotations

from typing import Protocol
from uuid import UUID

from google.adk.sessions.base_session_service import BaseSessionService

from app.domain.monitoring import MonitoringRun, RunStatus, RunTrigger
from app.domain.monitoring_workflow import (
    ReconciliationIssueCode,
    ReconciliationItem,
    ReconciliationReport,
)
from app.domain.review import ReviewStatus, ReviewTask
from app.repositories.contracts import ReviewRepository, RunRepository
from app.services.monitoring_workflow import (
    MONITORING_WORKFLOW_APP_NAME,
    terminal_review_status,
    workflow_identity,
)


class MonitoringWorkflowStartPort(Protocol):
    async def start(self, run: MonitoringRun): ...


class WorkflowReconciliationService:
    """Repair business/workflow linkage without making reviewer decisions."""

    def __init__(
        self,
        *,
        runs: RunRepository,
        reviews: ReviewRepository,
        sessions: BaseSessionService,
        workflow: MonitoringWorkflowStartPort,
        limit: int = 100,
    ) -> None:
        if not 1 <= limit <= 500:
            raise ValueError("reconciliation limit must be between 1 and 500")
        self._runs = runs
        self._reviews = reviews
        self._sessions = sessions
        self._workflow = workflow
        self._limit = limit

    async def reconcile(self) -> ReconciliationReport:
        runs = await self._runs.list_by_status(
            RunStatus.AWAITING_REVIEW,
            limit=self._limit,
        )
        items: list[ReconciliationItem] = []
        reviewed_interrupt_ids: set[str] = set()
        for run in runs:
            tasks = await self._reviews.list(run_id=run.id, limit=500)
            reviewed_interrupt_ids.update(
                task.correlation.interrupt_id
                for task in tasks
                if task.correlation is not None
            )
            pending = tuple(
                task for task in tasks if task.status is ReviewStatus.PENDING
            )
            if not tasks:
                orphan_interrupts = await self._run_open_interrupts(run)
                if orphan_interrupts:
                    item = ReconciliationItem(
                        run_id=run.id,
                        issue=(
                            ReconciliationIssueCode.INTERRUPT_WITHOUT_PENDING_REVIEW
                        ),
                        repaired=False,
                        detail="stale input remains fail-closed and cannot publish",
                    )
                    await self._audit(item)
                    items.append(item)
                items.append(await self._finish_orphaned_run(run))
                continue
            if not pending:
                stale = await self._terminal_interrupt_item(run, tasks)
                if stale is not None:
                    items.append(stale)
                items.append(await self._finish_terminal_run(run, tasks))
                continue

            missing_items: list[ReviewTask] = []
            for task in pending:
                if not await self._has_open_interrupt(task):
                    missing_items.append(task)
            missing = tuple(missing_items)
            if missing:
                repaired = False
                detail = None
                try:
                    await self._workflow.start(run)
                    refreshed = tuple(
                        await self._reviews.get(task.id) for task in missing
                    )
                    repaired = True
                    for refreshed_task in refreshed:
                        if refreshed_task is None or not await self._has_open_interrupt(
                            refreshed_task
                        ):
                            repaired = False
                            break
                    if not repaired:
                        detail = "workflow did not recreate every missing interrupt"
                except Exception as exc:
                    detail = type(exc).__name__
                item = ReconciliationItem(
                    run_id=run.id,
                    issue=ReconciliationIssueCode.PENDING_WITHOUT_INTERRUPT,
                    repaired=repaired,
                    review_ids=tuple(task.id for task in missing),
                    detail=detail,
                )
                await self._audit(item)
                items.append(item)

            stale = await self._terminal_interrupt_item(run, tasks)
            if stale is not None:
                items.append(stale)
        terminal_tasks: list[ReviewTask] = []
        for status in (
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED,
            ReviewStatus.SUPERSEDED,
            ReviewStatus.FAILED,
        ):
            terminal_tasks.extend(
                await self._reviews.list(status=status, limit=self._limit)
            )
        seen_terminal = {
            review_id
            for item in items
            if item.issue is ReconciliationIssueCode.INTERRUPT_WITHOUT_PENDING_REVIEW
            for review_id in item.review_ids
        }
        for task in terminal_tasks:
            if task.id in seen_terminal or not await self._has_open_interrupt(task):
                continue
            if task.correlation is not None:
                reviewed_interrupt_ids.add(task.correlation.interrupt_id)
            item = ReconciliationItem(
                run_id=task.run_id,
                issue=ReconciliationIssueCode.INTERRUPT_WITHOUT_PENDING_REVIEW,
                repaired=False,
                review_ids=(task.id,),
                detail="terminal or superseded review remains fail-closed",
            )
            await self._audit(item)
            items.append(item)
        items.extend(await self._find_unlinked_interrupts(reviewed_interrupt_ids))
        return ReconciliationReport(scanned_runs=len(runs), items=tuple(items))

    async def _has_open_interrupt(self, task: ReviewTask) -> bool:
        correlation = task.correlation
        if correlation is None:
            return False
        session = await self._sessions.get_session(
            app_name=correlation.app_name,
            user_id=correlation.user_id,
            session_id=correlation.session_id,
        )
        if session is None:
            return False
        return correlation.interrupt_id in self._open_interrupt_ids(session.events)

    async def _run_open_interrupts(self, run: MonitoringRun) -> set[str]:
        user_id, session_id = workflow_identity(run)
        session = await self._sessions.get_session(
            app_name=MONITORING_WORKFLOW_APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        return (
            self._open_interrupt_ids(session.events) if session is not None else set()
        )

    async def _find_unlinked_interrupts(
        self,
        known_interrupt_ids: set[str],
    ) -> tuple[ReconciliationItem, ...]:
        items: list[ReconciliationItem] = []
        remaining = self._limit
        for trigger in (
            RunTrigger.API,
            RunTrigger.SCHEDULE,
            RunTrigger.ADK,
            RunTrigger.USER,
        ):
            if remaining <= 0:
                break
            user_id = f"monitoring-{trigger.value}"
            response = await self._sessions.list_sessions(
                app_name=MONITORING_WORKFLOW_APP_NAME,
                user_id=user_id,
            )
            for summary in response.sessions[:remaining]:
                session = await self._sessions.get_session(
                    app_name=MONITORING_WORKFLOW_APP_NAME,
                    user_id=user_id,
                    session_id=summary.id,
                )
                if session is None:
                    continue
                unknown = self._open_interrupt_ids(session.events) - known_interrupt_ids
                if not unknown:
                    continue
                prefix = "monitoring-run-"
                if not summary.id.startswith(prefix):
                    continue
                try:
                    run_id = UUID(summary.id.removeprefix(prefix))
                except ValueError:
                    continue
                if await self._runs.get(run_id) is None:
                    continue
                item = ReconciliationItem(
                    run_id=run_id,
                    issue=ReconciliationIssueCode.INTERRUPT_WITHOUT_PENDING_REVIEW,
                    repaired=False,
                    detail="ADK interrupt has no live business review",
                )
                await self._audit(item)
                items.append(item)
                remaining -= 1
                if remaining <= 0:
                    break
        return tuple(items)

    @staticmethod
    def _open_interrupt_ids(events) -> set[str]:
        calls: set[str] = set()
        responses: set[str] = set()
        for event in events:
            parts = event.content.parts if event.content and event.content.parts else ()
            for part in parts:
                if part.function_call and part.function_call.id:
                    calls.add(part.function_call.id)
                if part.function_response and part.function_response.id:
                    responses.add(part.function_response.id)
        return calls - responses

    async def _finish_terminal_run(
        self,
        run: MonitoringRun,
        tasks: tuple[ReviewTask, ...],
    ) -> ReconciliationItem:
        approved = sum(task.status is ReviewStatus.APPROVED for task in tasks)
        rejected = len(tasks) - approved
        status = terminal_review_status(
            approved=approved,
            rejected=rejected,
            prior_succeeded=int(run.summary.get("succeeded", 0)),
            prior_failed=int(run.summary.get("failed", 0)),
        )
        await self._runs.finish_after_review(
            run.id,
            status,
            summary={
                **run.summary,
                "reviews_approved": approved,
                "reviews_rejected": rejected,
                "reconciled": True,
            },
        )
        item = ReconciliationItem(
            run_id=run.id,
            issue=ReconciliationIssueCode.TERMINAL_REVIEWS_WITH_PAUSED_RUN,
            repaired=True,
            review_ids=tuple(task.id for task in tasks),
        )
        await self._audit(item)
        return item

    async def _terminal_interrupt_item(
        self,
        run: MonitoringRun,
        tasks: tuple[ReviewTask, ...],
    ) -> ReconciliationItem | None:
        terminal_with_open_interrupt: list[ReviewTask] = []
        for task in tasks:
            if task.status.is_terminal and await self._has_open_interrupt(task):
                terminal_with_open_interrupt.append(task)
        if not terminal_with_open_interrupt:
            return None
        item = ReconciliationItem(
            run_id=run.id,
            issue=ReconciliationIssueCode.INTERRUPT_WITHOUT_PENDING_REVIEW,
            repaired=False,
            review_ids=tuple(task.id for task in terminal_with_open_interrupt),
            detail="stale input remains fail-closed and cannot publish",
        )
        await self._audit(item)
        return item

    async def _finish_orphaned_run(
        self,
        run: MonitoringRun,
    ) -> ReconciliationItem:
        await self._runs.finish_after_review(
            run.id,
            RunStatus.FAILED,
            summary={**run.summary, "reconciled": True, "review_link_missing": True},
        )
        item = ReconciliationItem(
            run_id=run.id,
            issue=ReconciliationIssueCode.AWAITING_RUN_WITHOUT_REVIEW,
            repaired=True,
            detail="failed safely because no reviewer task exists",
        )
        await self._audit(item)
        return item

    async def _audit(self, item: ReconciliationItem) -> None:
        await self._runs.record_audit(
            item.run_id,
            "review.reconciled",
            reason_code=item.issue.value,
            payload={
                "repaired": item.repaired,
                "review_ids": [str(review_id) for review_id in item.review_ids],
                "detail": item.detail,
            },
        )
