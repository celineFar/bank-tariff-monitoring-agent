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
        miss(
            "intent",
            f"{outcome.intent.value} not in {[i.value for i in expect.intents]}",
        )
    if outcome.intent in expect.forbid_intents:
        miss("forbidden_intent", outcome.intent.value)
    if expect.clarify is not None and outcome.clarify != expect.clarify:
        miss("clarify", f"got {outcome.clarify}")
    if outcome.clarify:
        if expect.clarify_level and outcome.option_level != expect.clarify_level:
            miss("clarify_level", f"got {outcome.option_level}")
        if expect.product is not None and outcome.option_products - {expect.product}:
            miss(
                "option_products", str(sorted(p.value for p in outcome.option_products))
            )
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
            miss(
                "fields",
                f"missing {sorted(f.value for f in set(expect.fields) - outcome.fields)}",
            )
        if expect.fields_any and not set(expect.fields_any) & outcome.fields:
            miss("fields_any", f"got {sorted(f.value for f in outcome.fields)}")
        if set(expect.fields_none) & outcome.fields:
            miss(
                "fields_none",
                f"got {sorted(f.value for f in set(expect.fields_none) & outcome.fields)}",
            )
        if expect.rank_fields and outcome.rank_field not in expect.rank_fields:
            miss(
                "rank_field",
                f"{outcome.rank_field.value if outcome.rank_field else None}",
            )
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


def outcome_from_resolution(resolution, offer=None) -> TurnOutcome:
    """The new resolver's `IntentResolution` in the terms the cases check."""
    from app.domain.intent import ResolutionScope
    from app.services.interpretation_validation import offer_accepted

    shape = resolution.query
    levels = (
        {candidate.scope for candidate in resolution.candidates}
        if resolution.needs_clarification
        else set()
    )
    return TurnOutcome(
        intent=resolution.continuation_intent or resolution.intent,
        product=resolution.product,
        offerings=frozenset(
            resolution.offering_ids
            or ((resolution.offering_id,) if resolution.offering_id else ())
        ),
        clarify=resolution.needs_clarification,
        option_products=frozenset(c.product for c in resolution.candidates)
        if resolution.needs_clarification
        else frozenset(),
        option_level=(
            "mixed"
            if len(levels) > 1
            else "family"
            if levels == {ResolutionScope.FAMILY}
            else "offering"
            if levels
            else None
        ),
        operation=shape.operation if shape is not None else None,
        fields=frozenset(shape.fields) if shape is not None else frozenset(),
        rank_field=shape.rank_field if shape is not None else None,
        rank_direction=shape.rank_direction if shape is not None else None,
        currency=shape.currency.value if shape is not None and shape.currency else None,
        language=resolution.language,
        spend=offer_accepted(resolution, offer),
    )


def pending_offer(offer):
    """A case `Offer` as the `PendingOffer` the tools would pass."""
    from app.domain.interpretation import OfferKind, PendingOffer

    if offer is None:
        return None
    return PendingOffer(
        kind=OfferKind(offer.kind), product=offer.product, offering_id=offer.offering_id
    )


async def run_case(resolver, case) -> list[Mismatch]:
    """Replay one case turn by turn, carrying state; score every turn."""
    state = None
    found: list[Mismatch] = []
    for index, turn in enumerate(case.turns):
        offer = pending_offer(turn.offer)
        try:
            result = await resolver.resolve_turn(
                turn.message, state, pending_offer=offer
            )
        except Exception as exc:
            found.append(
                Mismatch(
                    case.case_id, index, "error", repr(exc)[:200], turn.expect.safety
                )
            )
            break
        state = result.state
        found.extend(
            score_turn(
                case.case_id,
                index,
                turn.expect,
                outcome_from_resolution(result.resolution, offer),
            )
        )
    return found
