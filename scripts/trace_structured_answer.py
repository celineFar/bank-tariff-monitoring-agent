"""Print every stage of the structured tariff answer path for one question.

Read-only. It shows resolution, the issued authorization plan, the typed facts
with their verified citations, and the bounded explanatory units. No model call
is made unless lexical recall is sparse enough to trigger the bounded vector
fallback, which needs one query embedding; `--no-vector` forbids even that.

Usage:
    uv run python -m scripts.trace_structured_answer \
        "What is the nominal interest rate of the Overdraft?"
"""

from __future__ import annotations

import argparse
import asyncio
import json
from uuid import uuid4

from app.config import get_settings
from app.domain.structured_tariffs import QueryOperation, QueryStatus
from app.runtime import build_application_container
from app.services.structured_query_planning import issue_resolution_plan


def _line(title: str) -> None:
    print(f"\n{title}\n" + "-" * len(title), flush=True)


async def _trace(question: str, *, allow_vector: bool) -> int:
    container = build_application_container(get_settings())
    try:
        _line("[1] Deterministic resolution")
        resolution = (
            await container.request_resolver.resolve_turn(question)
        ).resolution
        print(
            f"intent={resolution.intent} product={resolution.product} "
            f"offering={resolution.offering_id} "
            f"offerings={[item.value for item in resolution.offering_ids]} "
            f"method={resolution.method} clarify={resolution.needs_clarification}"
        )
        if resolution.needs_clarification or resolution.product is None:
            print("Scope is unresolved; the service would not read any tariff data.")
            return 1

        _line("[2] Per-turn authorization plan")
        plan = issue_resolution_plan(
            question,
            resolution,
            session_id=f"trace-{uuid4()}",
            turn_id=str(uuid4()),
        )
        print(
            f"operation={plan.operation.value} "
            f"direction={plan.rank_direction} "
            f"offerings={[item.value for item in plan.offering_ids]}\n"
            f"fields={[item.value for item in plan.fields]}\n"
            f"conditions={plan.conditions} expires_at={plan.expires_at.isoformat()}"
        )

        _line("[3] Read model")
        service = container.structured_query_service
        if not allow_vector:
            service._unit_embedder = None
        result = await service.answer(plan, question)
        print(
            f"status={result.status.value} as_of={result.as_of} "
            f"facts={len(result.facts)} rows={len(result.comparison_rows)} "
            f"units={len(result.retrieval_units)} reason={result.reason}"
        )

        _line("[4] Typed accepted facts and verified citations")
        for fact in result.facts:
            print(
                f"{fact.offering_id.value} {fact.field_path.value} = "
                f"{json.dumps(fact.value, ensure_ascii=False)}"
                + (f" {fact.currency}" if fact.currency else "")
                + (f" ({fact.unit})" if fact.unit else "")
            )
            for condition in fact.conditions:
                print(f"    condition {json.dumps(condition, ensure_ascii=False)}")
            for evidence in fact.evidence:
                print(
                    f"    cite {evidence.evidence_id} {evidence.authority} "
                    f"{evidence.source_url} locator={json.dumps(evidence.locator)}"
                )
        if result.operation is QueryOperation.HISTORY:
            print(json.dumps(result.metadata.get("changes"), indent=2)[:4000])

        _line("[5] Bounded explanatory units admitted to the evidence packet")
        for unit in result.retrieval_units:
            print(f"{unit.kind.value} v{unit.renderer_version} {unit.content}")
        if not result.retrieval_units:
            print("(none admitted; every unit must be backed by the answered facts)")

        _line("[6] Ranking")
        print(json.dumps(result.metadata, ensure_ascii=False, default=str)[:2000])
        return 0 if result.status is QueryStatus.ANSWERED else 2
    finally:
        await container.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument(
        "--no-vector",
        action="store_true",
        help="forbid the bounded vector fallback, so no model call can happen",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(_trace(args.question, allow_vector=not args.no_vector))
    )


if __name__ == "__main__":
    main()
