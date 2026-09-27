"""Score one resolved turn against its case expectation (RRS01/RRS02)."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.intent import RequestIntent, RequestLanguage
from app.domain.models import OfferingId, ProductType
from app.domain.structured_tariffs import FieldPath, QueryOperation, RankDirection
from tests.fixtures.interpretation_cases import Expect, Mismatch


@dataclass(frozen=True)
class TurnOutcome:
    """What a resolver produced for one turn, in the terms the cases check."""

    intent: RequestIntent
    product: ProductType | None
    offerings: frozenset[OfferingId]
    clarify: bool
    # The products and level ("offering"/"family") of the clarification options.
    option_products: frozenset[ProductType] = frozenset()
    option_level: str | None = None
    operation: QueryOperation | None = None
    fields: frozenset[FieldPath] = frozenset()
    rank_field: FieldPath | None = None
    rank_direction: RankDirection | None = None
    currency: str | None = None
    language: RequestLanguage | None = None
    spend: bool = False


def score_turn(
    case_id: str, index: int, expect: Expect, outcome: TurnOutcome
) -> list[Mismatch]:
    found: list[Mismatch] = []

    def miss(check: str, detail: str) -> None:
        found.append(Mismatch(case_id, index, check, detail, expect.safety))

    if expect.intents and outcome.intent not in expect.intents:
        miss("intent", f"{outcome.intent.value} not in {[i.value for i in expect.intents]}")
    if outcome.intent in expect.forbid_intents:
        miss("forbidden_intent", outcome.intent.value)
    if expect.clarify is not None and outcome.clarify != expect.clarify:
        miss("clarify", f"got {outcome.clarify}")
    if outcome.clarify:
        if expect.clarify_level and outcome.option_level != expect.clarify_level:
            miss("clarify_level", f"got {outcome.option_level}")
        if expect.product is not None and outcome.option_products - {expect.product}:
            miss("option_products", str(sorted(p.value for p in outcome.option_products)))
    else:
        if expect.product is not None and outcome.product is not expect.product:
            miss("product", f"got {outcome.product.value if outcome.product else None}")
        if expect.offerings is not None and outcome.offerings != frozenset(
            expect.offerings
        ):
            miss("offerings", str(sorted(o.value for o in outcome.offerings)))
        if expect.operations and outcome.operation not in expect.operations:
            miss(
                "operation",
                f"{outcome.operation.value if outcome.operation else None}",
            )
        if set(expect.fields) - outcome.fields:
            miss("fields", f"missing {sorted(f.value for f in set(expect.fields) - outcome.fields)}")
        if expect.fields_any and not set(expect.fields_any) & outcome.fields:
            miss("fields_any", f"got {sorted(f.value for f in outcome.fields)}")
        if set(expect.fields_none) & outcome.fields:
            miss("fields_none", f"got {sorted(f.value for f in set(expect.fields_none) & outcome.fields)}")
        if expect.rank_fields and outcome.rank_field not in expect.rank_fields:
            miss("rank_field", f"{outcome.rank_field.value if outcome.rank_field else None}")
        if (
            expect.rank_direction is not None
            and outcome.rank_direction is not expect.rank_direction
        ):
            miss("rank_direction", f"{outcome.rank_direction}")
        if expect.currency is not None and outcome.currency != expect.currency:
            miss("currency", f"got {outcome.currency}")
    if expect.language is not None and outcome.language is not expect.language:
        miss("language", f"got {outcome.language.value if outcome.language else None}")
    if expect.spend is not None and outcome.spend != expect.spend:
        miss("spend", f"got {outcome.spend}")
    return found
