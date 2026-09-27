"""Phase 0 baseline: the pre-fix keyword resolver over the interpretation case set.

Runs on the code at 180ea9f (before Phase 2). The Gemini fallback is a stub that
fails, which is the production behaviour when the classifier errors. Operation
and fields come from the old keyword planner; `spend` follows the old tool
rules (exact affirmative reply, or any same-family spend grant after a scope
question). Writes the per-case result to stdout.
"""

from __future__ import annotations

import asyncio
from collections import Counter

from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.domain.catalog import normalize_catalog_term
from app.domain.intent import RequestIntent, ResolutionScope
from app.services.intent_resolution import RequestResolver
from app.services.structured_query_planning import issue_read_grant
from tests.fixtures.interpretation_cases import INTERPRETATION_CASES
from tests.fixtures.interpretation_scoring import TurnOutcome, score_turn

AFFIRMATIVE = {"yes", "yes please", "refresh", "go ahead", "yes go ahead", "confirm", "այո", "թարմացրու"}


class _Stub:
    async def classify(self, **_):
        raise RuntimeError("no gemini in the baseline")


def _outcome(message, resolution, offer) -> TurnOutcome:
    intent = resolution.continuation_intent or resolution.intent
    offerings = frozenset(
        resolution.offering_ids
        or ((resolution.offering_id,) if resolution.offering_id else ())
    )
    operation = fields = rank_field = direction = currency = None
    if intent in {
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        RequestIntent.GET_CURRENT_TARIFFS,
        RequestIntent.GET_CHANGE_HISTORY,
    } and not resolution.needs_clarification:
        try:
            plan = issue_read_grant(
                message, resolution,
                history=intent is RequestIntent.GET_CHANGE_HISTORY,
                session_id="s", turn_id="t",
            )
            operation, fields = plan.operation, frozenset(plan.fields)
            direction = plan.rank_direction
            rank_field = plan.fields[0] if plan.rank_direction else None
            currency = plan.conditions.get("currency")
        except Exception:  # noqa: BLE001
            pass
    spend = False
    if offer is not None:
        if offer.kind == "monitoring":
            spend = normalize_catalog_term(message) in AFFIRMATIVE
        else:
            spend = (
                normalize_catalog_term(message) in AFFIRMATIVE
                or (intent is RequestIntent.START_MONITORING_RUN
                    and resolution.product is offer.product)
            )
    levels = {c.scope for c in resolution.candidates} if resolution.needs_clarification else set()
    return TurnOutcome(
        intent=intent,
        product=resolution.product,
        offerings=offerings,
        clarify=resolution.needs_clarification,
        option_products=frozenset(c.product for c in resolution.candidates)
        if resolution.needs_clarification else frozenset(),
        option_level=(
            "mixed" if len(levels) > 1
            else "family" if levels == {ResolutionScope.FAMILY}
            else "offering" if levels else None
        ),
        operation=operation,
        fields=fields or frozenset(),
        rank_field=rank_field,
        rank_direction=direction,
        currency=currency,
        language=resolution.language,
        spend=spend,
    )


async def main() -> None:
    resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings(), classifier=_Stub())
    passed = 0
    checks: Counter[str] = Counter()
    safety_failed = 0
    for case in INTERPRETATION_CASES:
        state = None
        failures = []
        for index, turn in enumerate(case.turns):
            try:
                result = await resolver.resolve_turn(turn.message, state)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"turn {index}: CRASH {type(exc).__name__}")
                checks["crash"] += 1
                if turn.expect.safety:
                    safety_failed += 1
                break
            state = result.state
            mismatches = score_turn(case.case_id, index, turn.expect, _outcome(turn.message, result.resolution, turn.offer))
            for item in mismatches:
                failures.append(f"turn {index}: {item.check} ({item.detail})")
                checks[item.check] += 1
            safety_failed += sum(1 for item in mismatches if item.safety)
        if failures:
            print(f"FAIL {case.case_id}: " + "; ".join(failures))
        else:
            passed += 1
    total = len(INTERPRETATION_CASES)
    print(f"\npassed {passed}/{total} cases ({passed / total:.0%}); safety mismatches: {safety_failed}")
    print("failed checks:", dict(checks.most_common()))


if __name__ == "__main__":
    asyncio.run(main())
