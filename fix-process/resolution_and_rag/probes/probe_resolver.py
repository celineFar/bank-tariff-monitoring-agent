"""Probe resolve_turn + issue_read_grant without any Gemini call.

The classifier stub records that Gemini *would* have been called and then
raises, which the resolver treats as "ambiguous" (its production fallback).
"""

import asyncio
import sys

from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.services.intent_resolution import RequestResolver
from app.services.structured_query_planning import issue_read_grant


class Stub:
    def __init__(self):
        self.calls = []

    async def classify(self, *, query, language, allowed_intents, candidates):
        self.calls.append(
            (
                [i.value for i in allowed_intents],
                [c.candidate_id for c in candidates],
            )
        )
        raise RuntimeError("stub: no gemini")


def fmt_plan(query, res):
    try:
        plan = issue_read_grant(
            query,
            res,
            history=(res.continuation_intent or res.intent).value
            == "get_change_history",
            session_id="s",
            turn_id="t",
        )
    except Exception as exc:  # noqa: BLE001
        return f"grant ERR {type(exc).__name__}: {exc}"
    return (
        f"plan op={plan.operation.value} ids={[i.value for i in plan.offering_ids]} "
        f"fields={[f.value for f in plan.fields]} cond={plan.conditions} "
        f"rank={plan.rank_direction.value if plan.rank_direction else None}"
    )


async def main(queries):
    stub = Stub()
    resolver = RequestResolver(
        load_seed_catalog(), IntentResolutionSettings(), classifier=stub
    )
    state = None
    for q in queries:
        chained = q.startswith(">")
        q = q.lstrip(">").strip()
        stub.calls.clear()
        try:
            turn = await resolver.resolve_turn(q, state if chained else None)
        except Exception as exc:  # noqa: BLE001
            print(f"\nQ: {q!r}\n  CRASH {type(exc).__name__}: {str(exc)[:200]}")
            continue
        state = turn.state
        r = turn.resolution
        print(f"\nQ: {q!r}" + ("  [follow-up]" if chained else ""))
        print(
            f"  intent={r.intent.value} cont={r.continuation_intent.value if r.continuation_intent else None} "
            f"method={r.method.value} product={r.product.value if r.product else None} "
            f"offering={r.offering_id.value if r.offering_id else None} "
            f"ids={[i.value for i in r.offering_ids]} single={r.expects_single_value} "
            f"clarify={r.needs_clarification}"
        )
        if r.needs_clarification:
            print(f"  options={[c.candidate_id for c in r.candidates]}")
        if stub.calls:
            print(f"  GEMINI-WOULD-RUN allowed={stub.calls[0][0]} cands={stub.calls[0][1]}")
        intent = r.continuation_intent or r.intent
        if intent.value in {
            "answer_indexed_tariff_question",
            "get_current_tariffs",
            "get_change_history",
        } and not r.needs_clarification:
            print("  " + fmt_plan(q, r))


if __name__ == "__main__":
    asyncio.run(main([line.rstrip("\n") for line in sys.stdin if line.strip()]))
