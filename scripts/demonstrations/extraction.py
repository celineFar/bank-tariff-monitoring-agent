"""Deliverable 9 — normal tariff extraction with evidence."""

from __future__ import annotations

from app.config import load_seed_catalog
from app.config.models import IntentResolutionSettings
from app.domain.models import OfferingId
from app.domain.structured_tariffs import QueryStatus
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
)
from app.services.intent_resolution import RequestResolver
from app.services.structured_backfill import StructuredProjectionBackfill
from app.services.structured_query_planning import issue_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from scripts.demonstrations import ScenarioResult
from scripts.demonstrations.support import accept_snapshot, demonstration_sessions
from tests.fixtures.evaluation_corpus import CORPUS_SPECS

QUESTION = "What is the nominal interest rate of the Overdraft?"
REQUIRED_FIELDS = {"rate.nominal.minimum", "rate.nominal.maximum"}


async def run() -> ScenarioResult:
    result = ScenarioResult(
        deliverable="Deliverable 9",
        title="Normal tariff extraction, stored with source evidence",
    )
    async with demonstration_sessions() as sessions:
        overdraft = next(
            spec for spec in CORPUS_SPECS if spec.offering_id is OfferingId.OVERDRAFT
        )
        snapshot = await accept_snapshot(sessions, overdraft)
        result.step(
            f"Accepted a monitoring snapshot for {overdraft.offering_id.value} "
            f"through the real run lifecycle (snapshot {str(snapshot.id)[:8]})."
        )

        projected = await StructuredProjectionBackfill(sessions).run_scope(
            "ameria",
            overdraft.product.value,
            overdraft.offering_id.value,
            apply=True,
        )
        result.step(
            "Projected the accepted snapshot into typed facts, verified citations, "
            f"and retrieval units ({projected.published} version published, "
            f"{len(projected.issues)} unprojectable)."
        )

        resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings())
        resolution = (await resolver.resolve_turn(QUESTION)).resolution
        result.step(
            f'Resolved "{QUESTION}" deterministically to '
            f"{resolution.product.value}/{resolution.offering_id.value} "
            f"by {resolution.method.value} match, with no model call."
        )

        plan = issue_resolution_plan(
            QUESTION, resolution, session_id="demo-extraction", turn_id="turn-1"
        )
        result.step(
            f"Issued a per-turn authorization plan: operation={plan.operation.value}, "
            f"fields={len(plan.fields)}, expires {plan.expires_at.isoformat()}."
        )

        service = StructuredTariffQueryService(
            PostgresStructuredTariffQueryRepository(sessions)
        )
        answer = await service.answer(plan, QUESTION)
        result.step(
            f"Answered from accepted typed facts: status={answer.status.value}, "
            f"{len(answer.facts)} facts, as of {answer.as_of}."
        )
        for fact in answer.facts:
            citation = fact.evidence[0]
            result.step(
                f"    {fact.field_path.value} = {fact.value}"
                + (f" {fact.currency}" if fact.currency else "")
                + f"  <- {citation.source_url} "
                f"({citation.locator.get('block_id', 'n/a')}, {citation.authority})"
            )

    returned_fields = {fact.field_path.value for fact in answer.facts}
    currencies = {fact.currency for fact in answer.facts if fact.currency}
    uncited = [fact for fact in answer.facts if not fact.evidence]
    unlocated = [
        item
        for fact in answer.facts
        for item in fact.evidence
        if not item.quote or not item.locator
    ]

    result.check(
        "answered",
        "the query is answered from accepted data, not abstained",
        answer.status is QueryStatus.ANSWERED,
        f"status={answer.status.value}",
    )
    result.check(
        "requested fields returned",
        "both the minimum and maximum nominal rate come back",
        REQUIRED_FIELDS <= returned_fields,
        f"returned {sorted(returned_fields)}",
    )
    result.check(
        "every value is cited",
        "no returned fact lacks source evidence",
        not uncited,
        f"{len(answer.facts)} facts, {len(uncited)} without evidence",
    )
    result.check(
        "evidence is verifiable",
        "each citation carries an exact quote and a source locator",
        not unlocated,
        f"{sum(len(f.evidence) for f in answer.facts)} citations, "
        f"{len(unlocated)} missing quote or locator",
    )
    result.check(
        "currencies stay separate",
        "AMD and USD variants are not merged into one number",
        currencies == {"AMD", "USD"},
        f"currencies={sorted(currencies)}",
    )
    result.check(
        "freshness is reported",
        "the answer carries the accepted-snapshot as-of time",
        answer.as_of is not None,
        f"as_of={answer.as_of}",
    )
    result.note(
        "This is the read side. The live acquisition pipeline that produces the "
        "snapshot needs the bank website and Gemini; run "
        "`scripts/demonstrate_end_to_end.py` for that path."
    )
    return result
