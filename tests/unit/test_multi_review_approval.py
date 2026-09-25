"""A run that raises several field reviews must still be approvable.

Reviews are decided one at a time. Resolving the first of two leaves the second
open, which used to raise `review decision does not produce a complete valid
snapshot` and record nothing: the reviewer answered, the batch vanished, and the
CLI asked again from the top. Only the last decision of a batch may publish, and
an incomplete batch must publish nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.review import (
    ReviewDecision,
    ReviewDecisionType,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.domain.semantic_extraction import (
    EvidenceCitation,
    EvidenceItem,
    ExtractionField,
    ExtractionReviewItem,
    ExtractionStatus,
    LoanCategory,
    PartialLoanProduct,
    SemanticExtractionResult,
    ValidatedFieldResult,
    ValidationIssue,
)
from app.domain.source_discovery import Authority, InformationRole, TemporalStatus
from app.services.review_decisions import ReviewDecisionService
from app.services.review_input import parse_review_field_text

NOW = datetime(2026, 9, 23, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/overdraft"
OPEN_FIELDS = (ExtractionField.PRODUCT_NAME, ExtractionField.COLLATERAL)


def _evidence(index: int) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"ev_{index:024x}",
        document_id="doc-1",
        source_item_id=f"block-{index}",
        content="Overdrafts via Cards not secured with property (unsecured)",
        role=InformationRole.PRODUCT_TERMS,
        authority=Authority.OFFICIAL_TERMS,
        temporal_status=TemporalStatus.CURRENT,
        precedence=1,
        locator=SourceLocator(source_url=URL, source_type=SourceType.PAGE),
    )


def _extraction(open_fields=OPEN_FIELDS) -> SemanticExtractionResult:
    """An extraction complete but for the fields under review."""
    catalog = tuple(_evidence(index) for index in (1, 2))
    first = catalog[0]
    citation = EvidenceCitation(
        evidence_id=first.evidence_id,
        source_item_id=first.source_item_id,
        source_url=URL,
        source_type=SourceType.PAGE,
        quote=first.content,
        locator=first.locator,
        authority=first.authority,
    )
    fields = [
        ValidatedFieldResult(
            field=ExtractionField.CATEGORY,
            status=ExtractionStatus.FOUND,
            value=LoanCategory.OVERDRAFT.value,
            evidence=(citation,),
            batch_id="batch-1",
        )
    ]
    fields.extend(
        ValidatedFieldResult(
            field=field,
            status=ExtractionStatus.NOT_STATED,
            batch_id="batch-1",
        )
        for field in open_fields
    )
    return SemanticExtractionResult(
        product=ProductType.CONSUMER_LOAN,
        model_name="test-model",
        partial_product=PartialLoanProduct(
            canonical_url=URL,
            retrieved_at=NOW,
            category=LoanCategory.OVERDRAFT,
            fields=tuple(fields),
        ),
        evidence_catalog=catalog,
        batch_results=(),
        validated_fields=tuple(fields),
        review_items=tuple(
            ExtractionReviewItem(
                review_id=f"review_{index:024x}",
                batch_id="batch-1",
                field=field,
                model_name="test-model",
                validation_issues=(
                    ValidationIssue(
                        message="required field was not stated",
                        error_type="missing_required_field",
                    ),
                ),
            )
            for index, field in enumerate(open_fields, start=1)
        ),
        reused_batch_count=0,
    )


def _task(
    snapshot_id,
    field: ExtractionField,
    reason: ReviewReason = ReviewReason.MISSING_REQUIRED_FIELD,
) -> ReviewTask:
    return ReviewTask(
        id=uuid4(),
        idempotency_key=f"review-{reason.value}-{field.value}",
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        snapshot_id=snapshot_id,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        reason=reason,
        issue_scope=field.value,
        candidates=(),
        evidence={"items": [item.model_dump(mode="json") for item in (_evidence(1),)]},
        status=ReviewStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )


class _Reviews:
    """Applies each decision to the stored snapshot, as the database does."""

    def __init__(self, tasks, snapshots) -> None:
        self._tasks = {task.id: task for task in tasks}
        self._snapshots = snapshots
        self.updates = []

    async def get(self, review_id):
        return self._tasks.get(review_id)

    async def approve_with_snapshot(self, review_id, decision, update, *, reviewer):
        self.updates.append(update)
        snapshot = self._snapshots.snapshot
        self._snapshots.snapshot = snapshot.model_copy(
            update={
                "normalized_tariff": update.normalized_tariff,
                "semantic_extraction": update.semantic_extraction,
                "validation": update.validation,
                "canonical_sha256": update.canonical_sha256,
            }
        )
        task = self._tasks[review_id]
        return task.model_copy(
            update={
                "status": ReviewStatus.APPROVED,
                "reviewer": reviewer,
                "decision": decision,
                "decided_at": NOW,
            }
        )


class _Snapshots:
    def __init__(self, snapshot) -> None:
        self.snapshot = snapshot

    async def get(self, snapshot_id):
        return self.snapshot if snapshot_id == self.snapshot.id else None

    async def get_latest_accepted(self, **_):
        return None


def _decision(field: ExtractionField, typed: str) -> ReviewDecision:
    """Build the decision the CLI builds, parsing what a reviewer types."""
    return ReviewDecision(
        decision_type=ReviewDecisionType.OVERRIDE,
        override_value=parse_review_field_text(field, typed),
        reason="Read from the official information guide.",
        evidence_reference=f"ev_{1:024x}",
    )


@pytest.mark.asyncio
async def test_two_field_reviews_publish_only_on_the_last_decision() -> None:
    extraction = _extraction()
    snapshot_id = uuid4()
    snapshot = SnapshotAttempt(
        id=snapshot_id,
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        status=SnapshotStatus.REVIEW_REQUIRED,
        normalized_tariff={},
        semantic_extraction=extraction.model_dump(mode="json"),
        validation={"accepted": False, "review_signals": []},
        canonical_sha256="a" * 64,
        created_at=NOW,
    )
    snapshots = _Snapshots(snapshot)
    tasks = [_task(snapshot_id, field) for field in OPEN_FIELDS]
    reviews = _Reviews(tasks, snapshots)
    service = ReviewDecisionService(reviews, snapshots)

    # The first decision must be recorded, not refused, even though its sibling
    # review is still open -- and it must not publish on its own.
    first = await service.apply(
        tasks[0].id,
        _decision(
            ExtractionField.PRODUCT_NAME,
            "Overdrafts via Cards not secured with property",
        ),
        reviewer="reviewer-1",
    )
    assert first.status is ReviewStatus.APPROVED
    assert reviews.updates[0].ready_for_activation is False
    assert reviews.updates[0].validation["accepted"] is False
    assert reviews.updates[0].validation["review_count"] == 1

    second = await service.apply(
        tasks[1].id,
        _decision(ExtractionField.COLLATERAL, "none"),
        reviewer="reviewer-1",
    )
    assert second.status is ReviewStatus.APPROVED
    assert reviews.updates[1].validation["review_count"] == 0


_RATE_SIGNAL = {
    "reason": "large_rate_change",
    "issue_scope": "interest_rate",
    "field": "interest_rate",
    "previous": "21.0",
    "current": "25.0",
    "absolute_percentage_point_change": "4.0",
}
_FIELD_SIGNAL = {
    "reason": "missing_required_field",
    "issue_scope": "product_name",
    "field": "product_name",
}


def _rate_and_field_review_service():
    extraction = _extraction(open_fields=(ExtractionField.PRODUCT_NAME,))
    snapshot_id = uuid4()
    snapshot = SnapshotAttempt(
        id=snapshot_id,
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        status=SnapshotStatus.REVIEW_REQUIRED,
        normalized_tariff={},
        semantic_extraction=extraction.model_dump(mode="json"),
        validation={
            "accepted": False,
            "review_signals": [dict(_RATE_SIGNAL), dict(_FIELD_SIGNAL)],
        },
        canonical_sha256="a" * 64,
        created_at=NOW,
    )
    snapshots = _Snapshots(snapshot)
    rate = _task(
        snapshot_id, ExtractionField.INTEREST_RATE, ReviewReason.LARGE_RATE_CHANGE
    )
    field = _task(snapshot_id, ExtractionField.PRODUCT_NAME)
    reviews = _Reviews([rate, field], snapshots)
    return ReviewDecisionService(reviews, snapshots), reviews, rate, field


_APPROVE = ReviewDecision(decision_type=ReviewDecisionType.APPROVE)
_NAME = "Overdrafts via Cards not secured with property"


@pytest.mark.asyncio
async def test_a_rate_review_and_a_field_review_publish_on_the_last_decision() -> None:
    """The batch a clip-10 reviewer submits: confirm the jump, supply the field."""
    service, reviews, rate, field = _rate_and_field_review_service()

    await service.apply(rate.id, _APPROVE, reviewer="reviewer-1")
    assert reviews.updates[-1].ready_for_activation is False

    await service.apply(
        field.id,
        _decision(ExtractionField.PRODUCT_NAME, _NAME),
        reviewer="reviewer-1",
    )
    assert reviews.updates[-1].ready_for_activation is True
    assert reviews.updates[-1].validation["review_signals"] == []


@pytest.mark.asyncio
async def test_the_same_batch_in_the_other_order_also_waits_for_both() -> None:
    service, reviews, rate, field = _rate_and_field_review_service()

    await service.apply(
        field.id,
        _decision(ExtractionField.PRODUCT_NAME, _NAME),
        reviewer="reviewer-1",
    )
    # The field is answered, but the jump has not been confirmed yet.
    assert reviews.updates[-1].ready_for_activation is False

    await service.apply(rate.id, _APPROVE, reviewer="reviewer-1")
    assert reviews.updates[-1].ready_for_activation is True


def test_a_rate_review_tells_the_reviewer_the_size_of_the_jump() -> None:
    """Confirming a change you are not told the size of is not a review."""
    from app.services.monitoring_pipeline import _review_tasks
    from app.services.review_resolution import build_review_view

    snapshot = SnapshotAttempt(
        id=uuid4(),
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        status=SnapshotStatus.REVIEW_REQUIRED,
        normalized_tariff={},
        validation={"accepted": False, "review_signals": [dict(_RATE_SIGNAL)]},
        canonical_sha256="a" * 64,
        created_at=NOW,
    )

    tasks = _review_tasks(snapshot)
    prompt = build_review_view(tasks[0])

    assert prompt.guidance.startswith(
        "Previous accepted value 21.0, candidate 25.0: "
        "a change of 4.0 percentage points."
    )
    # Field reviews carry no rate change and keep their guidance unchanged.
    field_snapshot = snapshot.model_copy(
        update={"validation": {"accepted": False, "review_signals": [_FIELD_SIGNAL]}}
    )
    field_prompt = build_review_view(_review_tasks(field_snapshot)[0])
    assert "Previous accepted value" not in field_prompt.guidance
