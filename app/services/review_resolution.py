"""One deterministic place that turns a reviewer's reply into a run outcome.

The monitoring node, the API's abort route and the worker's startup check all
call this service, so a review is validated, applied and closed the same way no
matter who asked. It has no ADK dependency.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from app.domain.monitoring import MonitoringRun, RunStatus
from app.domain.review import (
    ReviewCandidateView,
    ReviewDecision,
    ReviewDecisionInput,
    ReviewDecisionType,
    ReviewEvidenceView,
    ReviewPromptView,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.domain.semantic_extraction import ExtractionField
from app.repositories.contracts import ReviewRepository, RunRepository
from app.services.review_decisions import coerce_review_candidate_value
from app.services.review_input import (
    ReviewInputError,
    parse_review_field_text,
    review_field_format,
)
from app.services.semantic_extraction import validate_review_field_value

logger = logging.getLogger(__name__)

# One run never carries more reviews than this; a family run creates at most a
# handful per offering.
_REVIEW_PAGE = 100
_EVIDENCE_LIMIT = 20


class ReviewDecisionPort(Protocol):
    async def apply(
        self,
        review_id: UUID,
        decision: ReviewDecision,
        *,
        reviewer: str,
    ) -> ReviewTask: ...


class ReviewInputRejected(ValueError):
    """A reply that is well-formed but cannot be applied to this review.

    The caller shows `message` and asks again; nothing was written.
    """

    def __init__(
        self,
        reason_code: str,
        message: str,
        input_format: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message
        self.input_format = input_format

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "reason_code": self.reason_code,
            "message": self.message,
        }
        if self.input_format is not None:
            payload["input_format"] = self.input_format
        return payload


class ReviewResolutionService:
    def __init__(
        self,
        *,
        runs: RunRepository,
        reviews: ReviewRepository,
        decisions: ReviewDecisionPort,
    ) -> None:
        self._runs = runs
        self._reviews = reviews
        self._decisions = decisions

    async def pending(self, run_id: UUID) -> tuple[ReviewTask, ...]:
        """Pending reviews of one run, in a stable order."""
        tasks = await self._reviews.list(
            status=ReviewStatus.PENDING, run_id=run_id, limit=_REVIEW_PAGE
        )
        return tuple(sorted(tasks, key=lambda task: (task.created_at, str(task.id))))

    def prompt_view(self, task: ReviewTask) -> ReviewPromptView:
        return build_review_view(task)

    def input_format(self, task: ReviewTask) -> dict[str, object]:
        return review_input_format(task.issue_scope)

    def validate(
        self,
        task: ReviewTask,
        reply: ReviewDecision | ReviewDecisionInput,
    ) -> ReviewDecision:
        """Return the decision to apply, or raise `ReviewInputRejected`.

        Checks: the decision type is allowed for this review's reason; a
        selected candidate belongs to this review, carries no conditions and
        fits the field schema; an override cites evidence inside this review and
        its value (JSON or plain words) parses against that passage.
        """
        if isinstance(reply, ReviewDecisionInput):
            try:
                decision = reply.to_decision()
            except ValueError as exc:
                raise ReviewInputRejected(
                    "review.invalid_input",
                    _first_line(exc),
                    self.input_format(task),
                ) from exc
        else:
            decision = reply
        allowed, _ = review_policy(task.reason)
        if decision.decision_type not in allowed:
            raise ReviewInputRejected(
                "review.invalid_input",
                f"{decision.decision_type.value} is not allowed for this review; "
                f"choose one of: {', '.join(item.value for item in allowed)}.",
            )
        if decision.decision_type is ReviewDecisionType.SELECT_CANDIDATE:
            return self._validate_candidate(task, decision)
        if decision.decision_type is ReviewDecisionType.OVERRIDE:
            return self._validate_override(task, decision)
        return decision

    async def apply(
        self,
        task: ReviewTask,
        decision: ReviewDecision,
        *,
        reviewer: str,
    ) -> ReviewTask:
        """Apply one validated decision; `reject_all` supersedes the run's rest.

        Idempotent: a review that is no longer pending is returned unchanged, so
        a node that re-runs after a crash never applies a decision twice.
        """
        current = await self._reviews.get(task.id)
        if current is None:
            raise LookupError(str(task.id))
        if current.status is not ReviewStatus.PENDING:
            return current
        await self._runs.record_audit(
            task.run_id,
            "review.resume_attempt",
            payload={
                "review_ids": [str(task.id)],
                "decision_type": decision.decision_type.value,
            },
        )
        try:
            decided = await self._decisions.apply(task.id, decision, reviewer=reviewer)
            if decision.decision_type is ReviewDecisionType.REJECT_ALL:
                for sibling in await self.pending(task.run_id):
                    if sibling.id != task.id:
                        await self._reviews.supersede(sibling.id)
        except ValueError as exc:
            await self._runs.record_audit(
                task.run_id,
                "review.resume_failed",
                reason_code=type(exc).__name__,
                payload={"review_ids": [str(task.id)]},
            )
            raise ReviewInputRejected(
                "review.decision_failed",
                f"The decision could not be applied: {_first_line(exc)}",
            ) from exc
        except Exception as exc:
            await self._runs.record_audit(
                task.run_id,
                "review.resume_failed",
                reason_code=type(exc).__name__,
                payload={"review_ids": [str(task.id)]},
            )
            raise
        return decided

    async def complete_run(self, run_id: UUID) -> MonitoringRun:
        """Finish a paused run once none of its reviews is pending.

        Returns the run unchanged while a review is still pending or when the
        run is not paused. A paused run with no review at all fails closed: no
        candidate can be activated without a decision.
        """
        run = await self._runs.get(run_id)
        if run is None:
            raise LookupError(str(run_id))
        if run.status is not RunStatus.AWAITING_REVIEW:
            return run
        tasks = await self._reviews.list(run_id=run_id, limit=_REVIEW_PAGE)
        if any(task.status is ReviewStatus.PENDING for task in tasks):
            return run
        if not tasks:
            status = RunStatus.FAILED
            summary = {**run.summary, "review_link_missing": True}
            approved = rejected = 0
        else:
            approved = sum(task.status is ReviewStatus.APPROVED for task in tasks)
            # Superseded and failed reviews activated nothing either.
            rejected = len(tasks) - approved
            status = terminal_review_status(
                approved=approved,
                rejected=rejected,
                prior_succeeded=int(run.summary.get("succeeded", 0)),
                prior_failed=int(run.summary.get("failed", 0)),
            )
            summary = {
                **run.summary,
                "reviews_approved": approved,
                "reviews_rejected": rejected,
            }
        try:
            completed = await self._runs.finish_after_review(
                run_id, status, summary=summary
            )
        except Exception:
            # Another process closed it first; report what is stored.
            latest = await self._runs.get(run_id)
            if latest is not None and latest.status.is_terminal:
                return latest
            raise
        await self._runs.record_audit(
            run_id,
            "review.approved" if rejected == 0 and tasks else "review.rejected",
            payload={"approved": approved, "rejected": rejected},
        )
        return completed

    async def complete_runs_without_pending_reviews(self, *, limit: int = 100) -> int:
        """Worker startup: close paused runs whose reviews were all decided."""
        completed = 0
        for run in await self._runs.list_by_status(
            RunStatus.AWAITING_REVIEW, limit=limit
        ):
            try:
                closed = await self.complete_run(run.id)
            except Exception:
                logger.warning(
                    "could not complete reviewed run %s", run.id, exc_info=True
                )
                continue
            if closed.status.is_terminal:
                completed += 1
        return completed

    async def reject_all_pending(self, *, reviewer: str) -> dict[str, object]:
        """Reject every pending review, run by run, and close those runs."""
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
        completed: list[dict[str, object]] = []
        failed: list[dict[str, str]] = []
        for run_id, tasks in grouped.items():
            try:
                await self.apply(
                    tasks[0],
                    ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL),
                    reviewer=reviewer,
                )
                run = await self.complete_run(run_id)
                if not run.status.is_terminal or await self.pending(run_id):
                    raise RuntimeError("run still has pending reviews")
                completed.append(
                    {
                        "run_id": str(run_id),
                        "status": run.status.value,
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

    def _validate_candidate(
        self, task: ReviewTask, decision: ReviewDecision
    ) -> ReviewDecision:
        candidate = next(
            (
                item
                for item in task.candidates
                if item.candidate_id == decision.candidate_id
            ),
            None,
        )
        if candidate is None:
            raise ReviewInputRejected(
                "review.invalid_input",
                "That candidate is not part of this review.",
            )
        if candidate.conditions.get("conditions"):
            raise ReviewInputRejected(
                "review.candidate_requires_override",
                "This candidate has conditions; provide a structured override "
                "with evidence or reject the review.",
                self.input_format(task),
            )
        field = _field(task)
        try:
            value = coerce_review_candidate_value(field, candidate.value)
            validate_review_field_value(field, value)
        except ValueError as exc:
            raise ReviewInputRejected(
                "review.candidate_value_invalid",
                "The captured candidate is text that cannot be stored as a valid "
                f"{task.issue_scope} value. Provide a structured override with "
                "evidence or reject the review.",
                self.input_format(task),
            ) from exc
        return decision

    def _validate_override(
        self, task: ReviewTask, decision: ReviewDecision
    ) -> ReviewDecision:
        excerpt = _evidence_excerpt(task, decision.evidence_reference)
        if excerpt is None:
            raise ReviewInputRejected(
                "review.invalid_input",
                "The cited evidence is not part of this review; cite one of the "
                "passages shown.",
            )
        field = _field(task)
        try:
            value = reviewed_value(field, decision.override_value, excerpt)
        except ReviewInputError as exc:
            raise ReviewInputRejected(
                "review.override_value_invalid",
                str(exc),
                self.input_format(task),
            ) from exc
        except ValueError as exc:
            raise ReviewInputRejected(
                "review.override_value_invalid",
                f"The override does not match the {task.issue_scope} field schema. "
                "Correct the structured value and try again.",
                self.input_format(task),
            ) from exc
        return decision.model_copy(update={"override_value": value})


def _field(task: ReviewTask) -> ExtractionField:
    try:
        return ExtractionField(task.issue_scope)
    except ValueError as exc:
        raise ReviewInputRejected(
            "review.invalid_input",
            f"{task.issue_scope} cannot take a candidate or an override; approve "
            "or reject the review instead.",
        ) from exc


def _evidence_excerpt(task: ReviewTask, evidence_id: str | None) -> str | None:
    raw_items = task.evidence.get("items", [])
    for raw in raw_items if isinstance(raw_items, list) else ():
        if isinstance(raw, dict) and raw.get("evidence_id") == evidence_id:
            content = raw.get("content")
            return content if isinstance(content, str) else ""
    return None


def _first_line(exc: Exception) -> str:
    """The part of an error a reviewer can act on."""
    if isinstance(exc, ValidationError) and exc.errors():
        message = str(exc.errors()[0].get("msg", ""))
        return message.removeprefix("Value error, ") or type(exc).__name__
    text = str(exc).strip()
    return text.splitlines()[0] if text else type(exc).__name__


def reviewed_value(field: ExtractionField, value: object, excerpt: str) -> object:
    """Accept a plain-language override exactly as the guided CLI prompt does."""
    if isinstance(value, str):
        return parse_review_field_text(field, value, excerpts=(excerpt,))
    coerced = coerce_review_candidate_value(field, value)
    validate_review_field_value(field, coerced)
    return coerced


def review_input_format(issue_scope: str) -> dict[str, object]:
    """Describe a valid answer, so the human is asked for one before typing."""
    try:
        field_format = review_field_format(ExtractionField(issue_scope))
    except (KeyError, ValueError):
        return {
            "field": issue_scope,
            "instruction": "Provide the value as JSON matching the stored field "
            "structure, or choose a candidate.",
            "examples": [],
        }
    return {
        "field": issue_scope,
        "instruction": field_format.instruction,
        "examples": list(field_format.examples),
    }


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


def build_review_view(task: ReviewTask) -> ReviewPromptView:
    """The bounded, reason-specific view a reviewer decides from.

    Evidence is ranked so candidate passages come first, then passages that
    name the field, before the 20-passage limit applies.
    """
    allowed, guidance = review_policy(task.reason)
    raw_items = task.evidence.get("items", [])
    raw_items = raw_items if isinstance(raw_items, list) else []
    candidate_references = {
        reference
        for candidate in task.candidates
        for reference in candidate.evidence_references
    }

    def rank(raw: object) -> int:
        if not isinstance(raw, dict):
            return 4
        if raw.get("evidence_id") in candidate_references:
            return 0
        content = str(raw.get("content", "")).casefold()
        field = task.issue_scope.replace("_", " ").casefold()
        if field == "term" and re.search(
            r"\bterm\s*\(months?\)|\bindefinite term\b",
            content,
        ):
            return 1
        if field in content:
            return 2
        return 3

    evidence = tuple(
        view
        for raw in sorted(raw_items, key=rank)
        if isinstance(raw, dict)
        if (view := evidence_view(raw)) is not None
    )
    return ReviewPromptView(
        review_id=task.id,
        reason=task.reason,
        product=task.product,
        offering_id=task.offering_id,
        issue_scope=task.issue_scope,
        guidance=guidance,
        allowed_decisions=allowed,
        candidates=tuple(
            ReviewCandidateView.model_validate(candidate.model_dump(mode="json"))
            for candidate in task.candidates
        ),
        evidence=evidence[:_EVIDENCE_LIMIT],
    )


def review_policy(
    reason: ReviewReason,
) -> tuple[tuple[ReviewDecisionType, ...], str]:
    if reason is ReviewReason.LARGE_RATE_CHANGE:
        return (
            (
                ReviewDecisionType.APPROVE,
                ReviewDecisionType.REJECT_ALL,
                ReviewDecisionType.OVERRIDE,
            ),
            "Confirm the evidence-backed large rate change, reject the candidate "
            "snapshot, or provide an evidence-linked structured override.",
        )
    if reason is ReviewReason.OFFICIAL_SOURCE_CONFLICT:
        return (
            (
                ReviewDecisionType.SELECT_CANDIDATE,
                ReviewDecisionType.REJECT_ALL,
                ReviewDecisionType.OVERRIDE,
            ),
            "Select one captured official-source candidate, reject all candidates, "
            "or provide a structured override tied to captured evidence.",
        )
    if reason is ReviewReason.OCR_EVIDENCE:
        return (
            (
                ReviewDecisionType.APPROVE,
                ReviewDecisionType.REJECT_ALL,
                ReviewDecisionType.OVERRIDE,
            ),
            "This value was read off a scanned page by OCR, not from a text "
            "layer. Check the quoted text against the cited page, then approve "
            "it, reject the candidate snapshot, or provide an evidence-linked "
            "structured override.",
        )
    return (
        (ReviewDecisionType.REJECT_ALL, ReviewDecisionType.OVERRIDE),
        "Reject the candidate snapshot or provide a structured value with a reason "
        "and reference to captured official evidence.",
    )


def evidence_view(raw: dict) -> ReviewEvidenceView | None:
    evidence_id = raw.get("evidence_id")
    content = raw.get("content")
    locator = raw.get("locator")
    if not isinstance(evidence_id, str) or not isinstance(content, str):
        return None
    locator = locator if isinstance(locator, dict) else {}
    source_url = locator.get("source_url")
    if not isinstance(source_url, str):
        return None
    page = locator.get("pdf_page")
    return ReviewEvidenceView(
        evidence_id=evidence_id,
        source_url=source_url,
        source_type=(
            str(locator["source_type"]) if locator.get("source_type") else None
        ),
        document_id=(str(raw["document_id"]) if raw.get("document_id") else None),
        page=page if isinstance(page, int) else None,
        section=str(raw["section"]) if raw.get("section") else None,
        excerpt=content[:1500],
    )
