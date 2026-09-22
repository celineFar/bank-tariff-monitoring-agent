"""Deliverable 10 — tariff change detection between monitoring runs."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from app.domain.models import OfferingId
from app.domain.structured_tariffs import QueryOperation, QueryStatus
from app.repositories.monitoring import PostgresSnapshotRepository
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
)
from app.services.snapshot_lifecycle import compare_accepted_snapshots
from app.services.structured_backfill import StructuredProjectionBackfill
from app.services.structured_query_planning import issue_typed_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from scripts.demonstrations import ScenarioResult
from scripts.demonstrations.support import accept_snapshot, demonstration_sessions
from tests.fixtures.evaluation_corpus import CORPUS_SPECS
from tests.fixtures.structured_tariffs import build_snapshot

QUESTION = "What changed in the Primary Market Mortgage tariff?"


async def run() -> ScenarioResult:
    result = ScenarioResult(
        deliverable="Deliverable 10",
        title="Tariff change detection across two monitoring runs",
    )
    base = next(
        spec for spec in CORPUS_SPECS if spec.offering_id is OfferingId.MORTGAGE_PRIMARY
    )
    first = replace(
        base,
        case="demo_mortgage_run_1",
        nominal_min_amd=Decimal("10"),
        nominal_max_amd=Decimal("12"),
        extra_evidence_salt=":run1",
    )
    second = replace(
        base,
        case="demo_mortgage_run_2",
        nominal_min_amd=Decimal("11"),
        nominal_max_amd=Decimal("12"),
        extra_evidence_salt=":run2",
    )

    # Same disclosed amount written two ways must not raise a false alert.
    formatting_only = replace(
        second, case="demo_mortgage_formatting", extra_evidence_salt=":run2"
    )
    identical = compare_accepted_snapshots(
        build_snapshot(second), build_snapshot(formatting_only)
    )

    async with demonstration_sessions() as sessions:
        previous = await accept_snapshot(sessions, first)
        result.step(
            "Monitoring run 1 accepted a snapshot with a 10% minimum nominal "
            f"rate (snapshot {str(previous.id)[:8]})."
        )
        current = await accept_snapshot(sessions, second, previous=previous)
        result.step(
            "Monitoring run 2 accepted a snapshot with an 11% minimum nominal "
            f"rate (snapshot {str(current.id)[:8]})."
        )

        change_set = compare_accepted_snapshots(previous, current)
        result.step(
            "Deterministic comparison of the two canonical payloads found "
            f"{len(change_set.changes)} changed field(s)."
        )
        for item in change_set.changes:
            result.step(
                f"    {item.field}: {item.previous_display} -> {item.current_display}"
            )
        await PostgresSnapshotRepository(sessions).save_changes(change_set)
        result.step("Persisted the accepted change set for audit and history reads.")

        backfill = StructuredProjectionBackfill(sessions)
        await backfill.run_scope(
            "ameria", base.product.value, base.offering_id.value, apply=True
        )
        result.step("Reprojected the offering so history can cite old and new values.")

        plan = issue_typed_resolution_plan(
            QUESTION,
            product=base.product,
            offering_ids=(base.offering_id,),
            session_id="demo-change",
            turn_id="turn-1",
        )
        service = StructuredTariffQueryService(
            PostgresStructuredTariffQueryRepository(sessions)
        )
        answer = await service.answer(plan, QUESTION)
        reported = answer.metadata.get("changes") or []
        result.step(
            f"History query returned status={answer.status.value} with "
            f"{len(reported)} accepted change set(s)."
        )

    changed_fields = {item.field for item in change_set.changes}
    evidence_pairs = [
        item
        for entry in reported
        for item in (entry.get("changes") or [])
        if item.get("previous_evidence") and item.get("current_evidence")
    ]

    result.check(
        "a real change is detected",
        "the rate change between the two accepted runs is reported",
        "interest_rate" in changed_fields,
        f"changed fields = {sorted(changed_fields)}",
    )
    result.check(
        "only meaningful fields change",
        "unchanged fields are not reported as changes",
        len(changed_fields) == 1,
        f"{len(changed_fields)} field(s) reported changed",
    )
    result.check(
        "no false alert on formatting",
        "two snapshots with the same disclosed values report no change",
        identical is not None and not identical.changes,
        f"{0 if identical is None else len(identical.changes)} changes between "
        "two equal-value snapshots",
    )
    result.check(
        "history is answerable",
        "a history question returns the accepted change set",
        answer.status is QueryStatus.ANSWERED
        and answer.operation is QueryOperation.HISTORY,
        f"status={answer.status.value}, operation={answer.operation.value}",
    )
    result.check(
        "old and new values are both cited",
        "each reported change carries previous and current source evidence",
        bool(evidence_pairs),
        f"{len(evidence_pairs)} change item(s) with both-sided evidence",
    )
    return result
