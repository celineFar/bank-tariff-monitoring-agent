from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.review import (
    ReviewDecision,
    ReviewDecisionType,
    ReviewReason,
    ReviewSnapshotUpdate,
    ReviewTask,
)
from app.domain.semantic_extraction import (
    EvidenceCitation,
    ExtractionField,
    ExtractionStatus,
    PartialLoanProduct,
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
    ValidatedFieldResult,
)
from app.repositories.contracts import MonitoringSnapshotRepository, ReviewRepository
from app.services.semantic_extraction import (
    assemble_reviewed_loan_product,
    validate_review_field_value,
)
from app.services.snapshot_lifecycle import (
    canonical_sha256,
    canonical_tariff_payload,
    compare_accepted_snapshots,
    extraction_is_acceptable,
)


class ReviewDecisionService:
    """Validate native reviewer input and atomically update candidate publication."""

    def __init__(
        self,
        reviews: ReviewRepository,
        snapshots: MonitoringSnapshotRepository,
    ) -> None:
        self._reviews = reviews
        self._snapshots = snapshots

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

        evidence_items = _evidence_items(task)
        selected = None
        if decision.decision_type is ReviewDecisionType.SELECT_CANDIDATE:
            selected = next(
                (
                    item
                    for item in task.candidates
                    if item.candidate_id == decision.candidate_id
                ),
                None,
            )
            if selected is None:
                raise ValueError("selected candidate is outside the review scope")
            if not set(selected.evidence_references) <= evidence_items.keys():
                raise ValueError("selected candidate references unavailable evidence")
        elif decision.decision_type is ReviewDecisionType.OVERRIDE:
            if decision.evidence_reference not in evidence_items:
                raise ValueError("override evidence is outside the review scope")
        elif (
            decision.decision_type is ReviewDecisionType.APPROVE
            and task.reason is not ReviewReason.LARGE_RATE_CHANGE
        ):
            raise ValueError(
                "approve is valid only for a complete large-change candidate"
            )

        snapshot = await self._snapshots.get(task.snapshot_id)
        if snapshot is None:
            raise LookupError(str(task.snapshot_id))
        if snapshot.status is not SnapshotStatus.REVIEW_REQUIRED:
            raise ValueError("candidate snapshot is no longer reviewable")

        if decision.decision_type is ReviewDecisionType.APPROVE:
            update = await self._approve_unchanged(task, snapshot)
        else:
            update = await self._resolve_field(
                task,
                snapshot,
                decision,
                evidence_items,
                selected,
            )
        return await self._reviews.approve_with_snapshot(
            review_id,
            decision,
            update,
            reviewer=reviewer,
        )

    async def _approve_unchanged(
        self,
        task: ReviewTask,
        snapshot: SnapshotAttempt,
    ) -> ReviewSnapshotUpdate:
        validation = _without_review_signal(snapshot.validation, task.issue_scope)
        validation["accepted"] = not validation["review_signals"]
        return await self._build_update(
            task,
            snapshot,
            normalized_tariff=snapshot.normalized_tariff,
            semantic_extraction=snapshot.semantic_extraction,
            validation=validation,
        )

    async def _resolve_field(
        self,
        task: ReviewTask,
        snapshot: SnapshotAttempt,
        decision: ReviewDecision,
        evidence_items: dict[str, dict[str, Any]],
        selected: Any,
    ) -> ReviewSnapshotUpdate:
        try:
            field = ExtractionField(task.issue_scope)
        except ValueError as exc:
            raise ValueError(
                "review issue scope is not a supported tariff field"
            ) from exc

        if decision.decision_type is ReviewDecisionType.SELECT_CANDIDATE:
            raw_value = selected.value
            evidence_id = selected.evidence_references[0]
            if selected.conditions.get("conditions"):
                raise ValueError(
                    "candidate conditions require an explicit structured override"
                )
            raw_value = coerce_review_candidate_value(field, raw_value)
            explanation = "Reviewer selected a captured official-source candidate."
        else:
            raw_value = decision.override_value
            evidence_id = decision.evidence_reference
            explanation = decision.reason
        assert evidence_id is not None
        try:
            validated_value = validate_review_field_value(field, raw_value)
        except ValueError as exc:
            raise ValueError(
                f"review value for {field.value} does not match the required structured field"
            ) from exc

        extraction = SemanticExtractionResult.model_validate(
            snapshot.semantic_extraction
        )
        replacement = ValidatedFieldResult(
            field=field,
            status=ExtractionStatus.FOUND,
            value=validated_value,
            evidence=(_citation(evidence_items[evidence_id], evidence_id, selected),),
            explanation=explanation,
            batch_id=f"review:{task.id}",
        )
        fields = tuple(
            replacement if item.field is field else item
            for item in extraction.validated_fields
        )
        if not any(item.field is field for item in extraction.validated_fields):
            fields = (*fields, replacement)
        remaining_items = tuple(
            item for item in extraction.review_items if item.field is not field
        )
        product = assemble_reviewed_loan_product(extraction, fields)
        updated_extraction = extraction.model_copy(
            update={
                "status": SemanticExtractionRunStatus.COMPLETED,
                "loan_product": product,
                "partial_product": PartialLoanProduct(
                    canonical_url=product.canonical_url,
                    retrieved_at=product.retrieved_at,
                    category=product.category,
                    fields=fields,
                ),
                "validated_fields": fields,
                "review_items": remaining_items,
            }
        )
        if not extraction_is_acceptable(updated_extraction):
            raise ValueError(
                "review decision does not produce a complete valid snapshot"
            )
        validation = _without_review_signal(snapshot.validation, task.issue_scope)
        validation.update(
            {
                "accepted": not validation["review_signals"],
                "review_count": len(remaining_items),
                "validated_field_count": len(fields),
            }
        )
        return await self._build_update(
            task,
            snapshot,
            normalized_tariff=canonical_tariff_payload(product),
            semantic_extraction=updated_extraction.model_dump(mode="json"),
            validation=validation,
        )

    async def _build_update(
        self,
        task: ReviewTask,
        snapshot: SnapshotAttempt,
        *,
        normalized_tariff: dict,
        semantic_extraction: dict,
        validation: dict,
    ) -> ReviewSnapshotUpdate:
        payload = canonical_tariff_payload(normalized_tariff)
        candidate = snapshot.model_copy(
            update={
                "status": SnapshotStatus.ACCEPTED,
                "normalized_tariff": payload,
                "semantic_extraction": semantic_extraction,
                "validation": validation,
                "canonical_sha256": canonical_sha256(payload),
                "accepted_at": snapshot.created_at,
            }
        )
        previous = await self._snapshots.get_latest_accepted(
            bank=snapshot.bank,
            product=task.product,
            offering_id=task.offering_id,
            before_run_id=snapshot.run_id,
        )
        return ReviewSnapshotUpdate(
            snapshot_id=snapshot.id,
            expected_canonical_sha256=snapshot.canonical_sha256,
            normalized_tariff=payload,
            semantic_extraction=semantic_extraction,
            validation=validation,
            canonical_sha256=candidate.canonical_sha256,
            ready_for_activation=bool(validation.get("accepted")),
            changes=compare_accepted_snapshots(previous, candidate),
        )


def _evidence_items(task: ReviewTask) -> dict[str, dict[str, Any]]:
    raw_items = task.evidence.get("items", [])
    if not isinstance(raw_items, list):
        return {}
    return {
        str(item["evidence_id"]): item
        for item in raw_items
        if isinstance(item, dict) and item.get("evidence_id") is not None
    }


def _without_review_signal(validation: dict, issue_scope: str) -> dict:
    updated = dict(validation)
    signals = validation.get("review_signals", [])
    signal_items = signals if isinstance(signals, list) else []
    updated["review_signals"] = [
        signal
        for signal in signal_items
        if not isinstance(signal, dict) or signal.get("issue_scope") != issue_scope
    ]
    return updated


def coerce_review_candidate_value(field: ExtractionField, value: Any) -> Any:
    if field is ExtractionField.TERM and isinstance(value, str):
        if re.fullmatch(
            r"\s*indefinite\s+term\s*\(\s*until\s+requested\s+back\s*\)\s*",
            value,
            flags=re.IGNORECASE,
        ):
            return [
                {
                    "value": {"indefinite": True, "end_condition": "on_demand"},
                    "conditions": [],
                }
            ]
    if field not in {ExtractionField.INTEREST_RATE, ExtractionField.EFFECTIVE_RATE}:
        return value
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*%?\s*", value)
        if match is None:
            return value
        value = match.group(1)
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return [
            {
                "value": {
                    "min": value,
                    "max": value,
                    "rate_type": "unknown",
                    "basis": "annual",
                    "formula": None,
                },
                "conditions": [],
            }
        ]
    return value


def _citation(
    raw: dict[str, Any],
    evidence_id: str,
    selected: Any,
) -> EvidenceCitation:
    content = raw.get("content")
    if not isinstance(content, str) or not content:
        raise ValueError("review evidence has no captured content")
    quote = None
    if selected is not None:
        candidate_quote = selected.conditions.get("quote")
        if isinstance(candidate_quote, str) and candidate_quote in content:
            quote = candidate_quote
    return EvidenceCitation(
        evidence_id=evidence_id,
        source_item_id=raw["source_item_id"],
        source_url=raw["locator"]["source_url"],
        source_type=raw["locator"]["source_type"],
        quote=quote or content[:1500],
        section=raw.get("section"),
        locator=raw["locator"],
        authority=raw["authority"],
    )
