from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotChangeSet, validate_offering_product


class ReviewModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ReviewReason(StrEnum):
    LARGE_RATE_CHANGE = "large_rate_change"
    OFFICIAL_SOURCE_CONFLICT = "official_source_conflict"
    SOURCE_APPLICABILITY = "source_applicability"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    OCR_EVIDENCE = "ocr_evidence"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self is not ReviewStatus.PENDING


class ReviewDecisionType(StrEnum):
    APPROVE = "approve"
    SELECT_CANDIDATE = "select_candidate"
    REJECT_ALL = "reject_all"
    OVERRIDE = "override"


class ReviewCandidate(ReviewModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    field: str = Field(min_length=1, max_length=200)
    value: JsonValue
    evidence_references: tuple[str, ...] = Field(min_length=1, max_length=20)
    conditions: dict[str, JsonValue] = Field(default_factory=dict)


class ReviewDecision(ReviewModel):
    decision_type: ReviewDecisionType
    candidate_id: str | None = Field(default=None, min_length=1, max_length=200)
    override_value: JsonValue = None
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    evidence_reference: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_decision(self) -> ReviewDecision:
        if self.decision_type is ReviewDecisionType.SELECT_CANDIDATE:
            if self.candidate_id is None:
                raise ValueError("candidate selection requires candidate_id")
        elif self.candidate_id is not None:
            raise ValueError("candidate_id is valid only for candidate selection")
        if self.decision_type is ReviewDecisionType.OVERRIDE:
            if (
                self.override_value is None
                or self.reason is None
                or self.evidence_reference is None
            ):
                raise ValueError(
                    "override requires value, reason, and evidence reference"
                )
        elif any(
            value is not None
            for value in (
                self.override_value,
                self.evidence_reference,
            )
        ):
            raise ValueError("override fields are valid only for override decisions")
        return self


class ReviewDecisionInput(ReviewModel):
    """The wire shape of one reviewer reply: the `RequestInput` response schema.

    Deliberately permissive: only field types are checked here. ADK validates a
    resumed reply against this schema *after* persisting it, and a reply that
    fails there can never be retried (plan §5, E11). Business rules therefore
    live in `ReviewResolutionService.validate`, which re-asks instead of failing.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    decision_type: ReviewDecisionType
    candidate_id: str | None = Field(default=None, max_length=200)
    override_value: JsonValue = None
    reason: str | None = Field(default=None, max_length=2000)
    evidence_reference: str | None = Field(default=None, max_length=500)

    def to_decision(self) -> ReviewDecision:
        """Raises `ValueError` when the reply is not a coherent decision."""
        return ReviewDecision(
            decision_type=self.decision_type,
            candidate_id=self.candidate_id or None,
            override_value=self.override_value,
            reason=self.reason or None,
            evidence_reference=self.evidence_reference or None,
        )


class ReviewEvidenceView(ReviewModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    source_url: str = Field(min_length=1, max_length=2000)
    source_type: str | None = Field(default=None, max_length=100)
    document_id: str | None = Field(default=None, max_length=500)
    page: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, max_length=1000)
    excerpt: str = Field(min_length=1, max_length=1500)


class ReviewCandidateView(ReviewModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    field: str = Field(min_length=1, max_length=200)
    value: JsonValue
    evidence_references: tuple[str, ...] = Field(min_length=1, max_length=20)
    conditions: dict[str, JsonValue] = Field(default_factory=dict)


class ReviewPromptView(ReviewModel):
    review_id: UUID
    reason: ReviewReason
    product: ProductType
    offering_id: OfferingId
    issue_scope: str
    guidance: str = Field(min_length=1, max_length=2000)
    allowed_decisions: tuple[ReviewDecisionType, ...] = Field(min_length=1)
    candidates: tuple[ReviewCandidateView, ...] = Field(max_length=20)
    evidence: tuple[ReviewEvidenceView, ...] = Field(max_length=20)


class ReviewTask(ReviewModel):
    id: UUID
    idempotency_key: str = Field(min_length=1, max_length=500)
    run_id: UUID
    offering_execution_id: UUID
    snapshot_id: UUID
    product: ProductType
    offering_id: OfferingId
    reason: ReviewReason
    issue_scope: str = Field(min_length=1, max_length=500)
    candidates: tuple[ReviewCandidate, ...] = Field(max_length=20)
    evidence: dict[str, JsonValue] = Field(default_factory=dict)
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer: str | None = Field(default=None, min_length=1, max_length=200)
    decision: ReviewDecision | None = None
    comment: str | None = Field(default=None, max_length=2000)
    failure_detail: str | None = Field(default=None, max_length=2000)
    created_at: datetime
    updated_at: datetime
    decided_at: datetime | None = None

    @model_validator(mode="after")
    def validate_task(self) -> ReviewTask:
        validate_offering_product(self.product, self.offering_id)
        for value in (self.created_at, self.updated_at, self.decided_at):
            if value is not None and (
                value.tzinfo is None or value.utcoffset() is None
            ):
                raise ValueError("review timestamps must be timezone-aware")
        if self.status is ReviewStatus.PENDING:
            if self.reviewer is not None or self.decision is not None:
                raise ValueError("pending review cannot contain a decision")
        elif self.status in {ReviewStatus.APPROVED, ReviewStatus.REJECTED}:
            if (
                self.reviewer is None
                or self.decision is None
                or self.decided_at is None
            ):
                raise ValueError("decided review requires reviewer, decision, and time")
        return self


class ReviewSnapshotUpdate(ReviewModel):
    snapshot_id: UUID
    expected_canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    normalized_tariff: dict[str, JsonValue]
    semantic_extraction: dict[str, JsonValue]
    validation: dict[str, JsonValue]
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ready_for_activation: bool
    changes: SnapshotChangeSet | None = None
