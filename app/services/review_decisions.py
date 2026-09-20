from __future__ import annotations

from uuid import UUID

from app.domain.review import (
    ReviewDecision,
    ReviewDecisionType,
    ReviewReason,
    ReviewTask,
)
from app.repositories.contracts import ReviewRepository


class ReviewDecisionService:
    """Validate bounded reviewer input before changing a review's durable state."""

    def __init__(self, reviews: ReviewRepository) -> None:
        self._reviews = reviews

    async def apply(
        self,
        review_id: UUID,
        decision: ReviewDecision,
        *,
        reviewer: str,
    ) -> ReviewTask:
        task = await self._reviews.get(review_id)
        if task is None:
            raise LookupError(str(review_id))
        if decision.decision_type is ReviewDecisionType.REJECT_ALL:
            return await self._reviews.reject(review_id, reviewer=reviewer)

        evidence_items = task.evidence.get("items", [])
        if not isinstance(evidence_items, list):
            evidence_items = []
        available_evidence = {
            str(item.get("evidence_id"))
            for item in evidence_items
            if isinstance(item, dict) and item.get("evidence_id") is not None
        }
        if decision.decision_type is ReviewDecisionType.SELECT_CANDIDATE:
            candidate = next(
                (
                    item
                    for item in task.candidates
                    if item.candidate_id == decision.candidate_id
                ),
                None,
            )
            if candidate is None:
                raise ValueError("selected candidate is outside the review scope")
            if not set(candidate.evidence_references) <= available_evidence:
                raise ValueError("selected candidate references unavailable evidence")
        elif decision.decision_type is ReviewDecisionType.OVERRIDE:
            if decision.evidence_reference not in available_evidence:
                raise ValueError("override evidence is outside the review scope")
        elif (
            decision.decision_type is ReviewDecisionType.APPROVE
            and task.reason is not ReviewReason.LARGE_RATE_CHANGE
        ):
            raise ValueError("approve is valid only for a complete large-change candidate")

        return await self._reviews.approve(
            review_id,
            decision,
            reviewer=reviewer,
        )
