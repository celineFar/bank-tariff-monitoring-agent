from __future__ import annotations

import logging
import re
from typing import Any, Protocol
from uuid import UUID

from app.domain.knowledge import EmbeddedKnowledgeDocument, KnowledgeDocument
from app.domain.models import OfferingId
from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.review import (
    ReviewDecision,
    ReviewDecisionType,
    ReviewEvidenceSet,
    ReviewReason,
    ReviewSnapshotUpdate,
    ReviewTask,
)
from app.domain.semantic_extraction import (
    EvidenceCitation,
    ExtractionField,
    ExtractionStatus,
    PartialLoanProduct,
    RememberedReviewDecision,
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
    ValidatedFieldResult,
)
from app.repositories.contracts import MonitoringSnapshotRepository, ReviewRepository
from app.repositories.review_memory import ReviewDecisionMemory
from app.services.review_evidence import PASSAGE_MAX_CHARS, review_passages
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

logger = logging.getLogger(__name__)


class OfferingSummaries(Protocol):
    def project(self, snapshot: SnapshotAttempt) -> KnowledgeDocument: ...


class MissingVectors(Protocol):
    async def embed_missing(
        self, *, offering_id: OfferingId | None = None, limit: int = 200
    ) -> int: ...


class ReviewDecisionService:
    """Validate native reviewer input and atomically update candidate publication."""

    def __init__(
        self,
        reviews: ReviewRepository,
        snapshots: MonitoringSnapshotRepository,
        memory: ReviewDecisionMemory | None = None,
        summaries: OfferingSummaries | None = None,
        vectors: MissingVectors | None = None,
    ) -> None:
        self._reviews = reviews
        self._snapshots = snapshots
        self._memory = memory
        # Builds the approved snapshot's offering summary (IX6). Without it an
        # approval activates the source documents only.
        self._summaries = summaries
        # Embeds what an approval activated (stored text only, IX5).
        self._vectors = vectors

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
        elif (
            decision.decision_type is ReviewDecisionType.APPROVE
            and task.reason
            not in (ReviewReason.LARGE_RATE_CHANGE, ReviewReason.OCR_EVIDENCE)
        ):
            # OCR evidence is approvable because the reviewer is confirming a
            # reading against a page they were shown, not inventing a value.
            raise ValueError(
                "approve is valid only for a complete large-change or OCR candidate"
            )

        snapshot = await self._snapshots.get(task.snapshot_id)
        if snapshot is None:
            raise LookupError(str(task.snapshot_id))
        evidence_items = _evidence_items(task, snapshot)
        if selected is not None and not (
            set(selected.evidence_references) <= evidence_items.keys()
        ):
            raise ValueError("selected candidate references unavailable evidence")
        if (
            decision.decision_type is ReviewDecisionType.OVERRIDE
            and decision.evidence_reference not in evidence_items
        ):
            raise ValueError("override evidence is outside the review scope")
        if snapshot.status is not SnapshotStatus.REVIEW_REQUIRED:
            raise ValueError("candidate snapshot is no longer reviewable")

        remembered = None
        if decision.decision_type is ReviewDecisionType.APPROVE:
            update = await self._approve_unchanged(task, snapshot)
            remembered = _remembered_approval(task, snapshot)
        else:
            update, remembered = await self._resolve_field(
                task,
                snapshot,
                decision,
                evidence_items,
                selected,
            )
        miss = _citation_outside_shown_units(task, decision)
        if miss is not None:
            update = update.model_copy(update={"audit_events": (miss,)})
        approved = await self._reviews.approve_with_snapshot(
            review_id,
            decision,
            update,
            reviewer=reviewer,
        )
        if remembered is not None and self._memory is not None:
            # Only a committed decision is remembered (SE12).
            await self._memory.remember(
                remembered.model_copy(update={"reviewer": reviewer})
            )
        if update.ready_for_activation and self._vectors is not None:
            await self._embed_activated(task)
        return approved

    async def _embed_activated(self, task: ReviewTask) -> None:
        """Embed the approved documents, now active and text only (IX5).

        Best effort after the commit: mostly embedding-cache hits (an unchanged
        page was embedded by earlier accepted runs). A failure leaves the chunks
        to the worker's sweep; lexical search serves them meanwhile.
        """
        assert self._vectors is not None
        try:
            filled = await self._vectors.embed_missing(offering_id=task.offering_id)
        except Exception:
            logger.warning(
                "could not embed the approved documents of %s; the embedding "
                "sweep will retry",
                task.offering_id.value,
                exc_info=True,
            )
            return
        logger.info("embedded %s approved chunks of %s", filled, task.offering_id.value)

    async def _approve_unchanged(
        self,
        task: ReviewTask,
        snapshot: SnapshotAttempt,
    ) -> ReviewSnapshotUpdate:
        validation = _without_review_signal(
            snapshot.validation, task.issue_scope, task.reason
        )
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
    ) -> tuple[ReviewSnapshotUpdate, RememberedReviewDecision | None]:
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
            explanation = "Reviewer selected a captured official-source candidate."
        else:
            raw_value = decision.override_value
            evidence_id = decision.evidence_reference
            explanation = decision.reason
        assert evidence_id is not None
        raw_value = coerce_review_candidate_value(field, raw_value)
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
        remembered = _remembered(task, field, extraction, replacement)
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
        # One extraction can raise several field reviews, and they are decided
        # one at a time. Resolving one of them leaves its siblings open, so the
        # extraction is not yet acceptable -- that is the normal intermediate
        # state of a multi-review batch, not a reviewer error. Treating it as
        # one made every such run impossible to approve: the first decision
        # raised, nothing was recorded, and the reviewer was asked again.
        #
        # The publication gate lives in the repository, which holds the snapshot
        # at review_required until a decision arrives ready_for_activation with
        # no unresolved review left, so the last decision of the batch is the one
        # that publishes and an incomplete batch still publishes nothing.
        validation = _without_review_signal(
            snapshot.validation, task.issue_scope, task.reason
        )
        validation.update(
            {
                "accepted": (
                    extraction_is_acceptable(updated_extraction)
                    and not validation["review_signals"]
                ),
                "review_count": len(remaining_items),
                "validated_field_count": len(fields),
            }
        )
        return (
            await self._build_update(
                task,
                snapshot,
                normalized_tariff=canonical_tariff_payload(product),
                semantic_extraction=updated_extraction.model_dump(mode="json"),
                validation=validation,
            ),
            remembered,
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
        ready = bool(validation.get("accepted"))
        # Only the decision that activates the snapshot carries its summary,
        # built from the final values (overrides included). It is text only:
        # vectors are made after the approval commits (IX5, IX6).
        summary = (
            EmbeddedKnowledgeDocument.text_only(self._summaries.project(candidate))
            if ready and self._summaries is not None
            else None
        )
        return ReviewSnapshotUpdate(
            snapshot_id=snapshot.id,
            expected_canonical_sha256=snapshot.canonical_sha256,
            normalized_tariff=payload,
            semantic_extraction=semantic_extraction,
            validation=validation,
            canonical_sha256=candidate.canonical_sha256,
            ready_for_activation=ready,
            changes=compare_accepted_snapshots(previous, candidate),
            summary=summary,
        )


def _remembered(
    task: ReviewTask,
    field: ExtractionField,
    extraction: SemanticExtractionResult,
    replacement: ValidatedFieldResult,
) -> RememberedReviewDecision | None:
    """What to remember of a field decision: keyed on the model's own result for
    the field -- the review item when validation failed, else the validated
    field a signal flagged -- so the same result next run gets this answer."""
    source = next(
        (item for item in extraction.review_items if item.field is field), None
    ) or next(
        (item for item in extraction.validated_fields if item.field is field), None
    )
    if source is None or not source.result_fingerprint:
        return None
    return RememberedReviewDecision(
        offering_id=task.offering_id.value,
        field=field,
        prompt_fingerprint=source.prompt_fingerprint,
        result_fingerprint=source.result_fingerprint,
        decision=replacement.model_copy(update={"batch_id": f"memory:{task.id}"}),
        review_id=str(task.id),
    )


def _remembered_approval(
    task: ReviewTask, snapshot: SnapshotAttempt
) -> RememberedReviewDecision | None:
    """An approved OCR reading, remembered as read (the value is unchanged).

    A large rate change is approved once: the new value becomes the baseline
    the next run compares against. An OCR reading is raised again for as long
    as the scan is there, so the confirmation is kept for the same result.
    """
    if task.reason is not ReviewReason.OCR_EVIDENCE:
        return None
    try:
        field = ExtractionField(task.issue_scope)
    except ValueError:
        return None
    extraction = SemanticExtractionResult.model_validate(snapshot.semantic_extraction)
    confirmed = next(
        (item for item in extraction.validated_fields if item.field is field), None
    )
    if confirmed is None or confirmed.status is not ExtractionStatus.FOUND:
        return None
    return _remembered(task, field, extraction, confirmed)


def _evidence_items(
    task: ReviewTask, snapshot: SnapshotAttempt
) -> dict[str, dict[str, Any]]:
    """Every passage a decision may cite: the snapshot's evidence (RV7), or the
    copy a review row written before this change carries."""
    return {
        str(item["evidence_id"]): item
        for item in review_passages(task, snapshot.evidence)
        if item.get("evidence_id") is not None
    }


def _citation_outside_shown_units(
    task: ReviewTask, decision: ReviewDecision
) -> dict[str, Any] | None:
    """An override citing a passage the review's units did not show: a direct
    measure of the evidence set missing what the reviewer needed (RV13).

    Only for reviews that store their set; rows written before it showed a
    ranked copy of everything, so "outside" has no meaning there.
    """
    if decision.decision_type is not ReviewDecisionType.OVERRIDE:
        return None
    raw = task.evidence.get("set")
    if not isinstance(raw, dict):
        return None
    evidence_set = ReviewEvidenceSet.model_validate(raw)
    if decision.evidence_reference in evidence_set.shown_ids:
        return None
    return {
        "event_type": "review_citation_outside_shown_units",
        "payload": {
            "review_id": str(task.id),
            "reason": task.reason.value,
            "field": task.issue_scope,
            "evidence_id": decision.evidence_reference,
            "shown_units": [unit.key for unit in evidence_set.units],
        },
    }


def _without_review_signal(
    validation: dict, issue_scope: str, reason: ReviewReason
) -> dict:
    """The validation without the decided review's own signal.

    Matched on reason *and* scope: approving the OCR review of `interest_rate`
    must leave that field's `large_rate_change` signal pending (RV6/B4).
    """
    updated = dict(validation)
    signals = validation.get("review_signals", [])
    signal_items = signals if isinstance(signals, list) else []
    updated["review_signals"] = [
        signal
        for signal in signal_items
        if not isinstance(signal, dict)
        or signal.get("issue_scope") != issue_scope
        or signal.get("reason") != reason.value
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
        quote=quote or content[:PASSAGE_MAX_CHARS],
        section=raw.get("section"),
        locator=raw["locator"],
        authority=raw["authority"],
    )
