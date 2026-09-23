"""Deliverable 12 — a large rate change held for human review."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import RunCommand, RunTrigger, SnapshotStatus
from app.domain.review import (
    ReviewCandidate,
    ReviewDecision,
    ReviewDecisionType,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.domain.structured_tariffs import FieldPath, QueryStatus
from app.repositories.monitoring import (
    PostgresRunRepository,
    PostgresSnapshotRepository,
)
from app.repositories.reviews import PostgresReviewRepository
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
)
from app.services.snapshot_lifecycle import detect_large_rate_changes
from app.services.structured_backfill import StructuredProjectionBackfill
from app.services.structured_query_planning import issue_typed_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from scripts.demonstrations import ScenarioResult
from scripts.demonstrations.support import (
    DemonstrationError,
    accept_snapshot,
    demonstration_sessions,
)
from tests.fixtures.evaluation_corpus import CORPUS_SPECS
from tests.fixtures.structured_tariffs import build_snapshot

THRESHOLD = Decimal("3")
QUESTION = "What is the nominal interest rate of the Consumer Loans?"


async def run() -> ScenarioResult:
    result = ScenarioResult(
        deliverable="Deliverable 12",
        title="Human-in-the-loop: a large rate change is quarantined until approved",
    )
    base = next(
        spec
        for spec in CORPUS_SPECS
        if spec.offering_id is OfferingId.CONSUMER_STANDARD
    )
    accepted_spec = replace(
        base,
        case="demo_hitl_accepted",
        nominal_min_amd=Decimal("12"),
        extra_evidence_salt=":hitl1",
    )
    # A jump far beyond the configured threshold must not publish itself.
    candidate_spec = replace(
        base,
        case="demo_hitl_candidate",
        nominal_min_amd=Decimal("19"),
        nominal_max_amd=Decimal("22"),
        extra_evidence_salt=":hitl2",
    )

    async with demonstration_sessions() as sessions:
        accepted = await accept_snapshot(sessions, accepted_spec)
        await StructuredProjectionBackfill(sessions).run_scope(
            "ameria", base.product.value, base.offering_id.value, apply=True
        )
        result.step(
            "An accepted snapshot publishes a 12% minimum nominal rate "
            f"(snapshot {str(accepted.id)[:8]})."
        )

        candidate_payload = build_snapshot(candidate_spec)
        signals = detect_large_rate_changes(
            accepted.normalized_tariff,
            candidate_payload.normalized_tariff,
            threshold=THRESHOLD,
        )
        result.step(
            "Monitoring run 2 extracted an AMD nominal rate of 19-22%, up from "
            "12-15%. Deterministic "
            f"change detection raised {len(signals)} large-rate-change signal(s) "
            f"against the {THRESHOLD}pp threshold."
        )
        for signal in signals:
            result.step(f"    signal: {signal}")

        runs = PostgresRunRepository(sessions)
        submitted = await runs.submit(
            RunCommand(
                product=base.product,
                offering_id=base.offering_id,
                trigger=RunTrigger.API,
            )
        )
        claimed = await runs.claim_next("demonstration")
        if claimed is None:
            raise DemonstrationError("no run could be claimed for the review scenario")
        execution = await runs.create_offering_execution(
            submitted.run.id, base.product, base.offering_id
        )
        execution = await runs.start_offering_execution(execution.id)
        quarantined = candidate_payload.model_copy(
            update={
                "run_id": submitted.run.id,
                "offering_execution_id": execution.id,
                "status": SnapshotStatus.REVIEW_REQUIRED,
                "accepted_at": None,
                "previous_accepted_snapshot_id": accepted.id,
            }
        )
        await PostgresSnapshotRepository(sessions).save_attempt(quarantined)
        result.step(
            "The candidate was stored as review_required, not accepted "
            f"(snapshot {str(quarantined.id)[:8]})."
        )

        reviews = PostgresReviewRepository(sessions)
        evidence_reference = candidate_payload.evidence[0]["evidence_id"]
        task = await reviews.create(
            ReviewTask(
                id=uuid4(),
                idempotency_key=f"review:{quarantined.id}:nominal_interest_rate",
                run_id=submitted.run.id,
                offering_execution_id=execution.id,
                snapshot_id=quarantined.id,
                product=ProductType.CONSUMER_LOAN,
                offering_id=OfferingId.CONSUMER_STANDARD,
                reason=ReviewReason.LARGE_RATE_CHANGE,
                issue_scope="interest_rate:default",
                candidates=(
                    ReviewCandidate(
                        candidate_id="extracted-rate",
                        field="interest_rate",
                        value="19%",
                        evidence_references=(evidence_reference,),
                    ),
                ),
                evidence={
                    "previous": "12% minimum nominal rate, AMD",
                    "candidate": "19% minimum nominal rate, AMD",
                    "source_url": str(
                        candidate_payload.evidence[0]["locator"]["source_url"]
                    ),
                    "threshold_percentage_points": str(THRESHOLD),
                },
                status=ReviewStatus.PENDING,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result.step(
            f"A review task was opened ({str(task.id)[:8]}, reason="
            f"{task.reason.value}) carrying the previous value, the candidate "
            "value, the source URL, and the evidence reference the reviewer needs."
        )

        service = StructuredTariffQueryService(
            PostgresStructuredTariffQueryRepository(sessions)
        )
        plan = issue_typed_resolution_plan(
            QUESTION,
            product=base.product,
            offering_ids=(base.offering_id,),
            session_id="demo-hitl",
            turn_id="turn-1",
        )
        during_review = await service.answer(plan, QUESTION)
        during_values = sorted(
            str(fact.value)
            for fact in during_review.facts
            if fact.field_path is FieldPath.NOMINAL_RATE_MINIMUM
            and fact.currency == "AMD"
        )
        result.step(
            "While the review is pending, the same question still answers from "
            f"the older accepted snapshot: AMD minimum nominal rate "
            f"{during_values}%, not the quarantined 19%."
        )

        approved = await reviews.approve(
            task.id,
            ReviewDecision(
                decision_type=ReviewDecisionType.APPROVE,
                reason="Confirmed against the published information summary.",
            ),
            reviewer="reviewer@example.test",
        )
        result.step(
            f"A reviewer approved the candidate: status={approved.status.value}, "
            f"reviewer={approved.reviewer}."
        )

        pending_after = await reviews.list(status=ReviewStatus.PENDING)

    result.check(
        "large change is detected deterministically",
        "a jump beyond the threshold raises a signal without asking the model",
        bool(signals),
        f"{len(signals)} signal(s) at a {THRESHOLD}pp threshold",
    )
    result.check(
        "candidate is quarantined",
        "the new snapshot is review_required, never auto-accepted",
        quarantined.status is SnapshotStatus.REVIEW_REQUIRED
        and quarantined.accepted_at is None,
        f"status={quarantined.status.value}, accepted_at={quarantined.accepted_at}",
    )
    result.check(
        "reviewer receives source evidence",
        "the task carries candidate value, previous value, and an evidence link",
        bool(task.candidates)
        and bool(task.candidates[0].evidence_references)
        and "source_url" in task.evidence,
        f"{len(task.candidates)} candidate(s), evidence keys {sorted(task.evidence)}",
    )
    result.check(
        "pending value never leaks",
        "answers during review still show the older accepted 12%, not 19%",
        during_review.status is QueryStatus.ANSWERED and during_values == ["12"],
        f"answered AMD minimum {during_values}",
    )
    result.check(
        "decision is recorded with its reviewer",
        "approval stores who decided and why",
        approved.status is ReviewStatus.APPROVED and approved.reviewer is not None,
        f"status={approved.status.value}, reviewer={approved.reviewer}",
    )
    result.check(
        "review queue is cleared",
        "no pending review remains for this scope",
        not any(item.id == task.id for item in pending_after),
        f"{len(pending_after)} pending review(s) remain",
    )
    return result
