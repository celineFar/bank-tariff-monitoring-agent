"""Deterministic accepted-tariff answers over the structured read model.

The answer is the accepted, evidence-backed facts of the plan's fields. Retrieval
only finds the fields when the question named none (the field finder, D4); it
never changes which facts answer a question that names its fields.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol

from pydantic import JsonValue

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotChangeSet
from app.domain.semantic_extraction import ExtractionStatus
from app.domain.structured_tariffs import (
    SOURCE_FIELD_PATHS,
    ComparisonRow,
    FieldPath,
    OfferingDataState,
    OfferingProfile,
    QueryOperation,
    QueryStatus,
    RankDirection,
    ResolutionPlan,
    RetrievalUnitKind,
    TariffFact,
    TariffQueryResult,
)
from app.domain.tariff_comparison import ComparableMeasure, comparison_issue
from app.repositories.structured_tariff_query import RankedUnit
from app.services.retrieval_trace import (
    record,
    record_text,
    retrieval_trace,
    set_outcome,
)
from app.services.structured_query_planning import CORE_FIELDS

logger = logging.getLogger(__name__)
RANK_FUSION_VERSION = "rrf-v1-k60-lex1-vector0.7"
# The field finder loads the facts of at most this many field paths.
FIELD_FINDER_MAX_PATHS = 3
# An overview lists at most this many variants per offering and field, and
# this many facts in all, so a family-wide listing stays a bounded payload.
OVERVIEW_MAX_VARIANTS = 6
OVERVIEW_MAX_FACTS = 240


class StructuredUnitEmbedder(Protocol):
    """Only the query side: units are embedded by the worker's sweep (D10)."""

    model_name: str

    async def embed_query(self, question: str) -> Sequence[float]: ...


class StructuredQueryRepository(Protocol):
    async def active_profiles(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
    ) -> tuple[OfferingProfile, ...]: ...

    async def facts(
        self,
        *,
        snapshots: Sequence,
        fields: Sequence[FieldPath],
        include_inactive: bool = False,
    ) -> tuple[TariffFact, ...]: ...

    async def lexical_units(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        query: str,
        limit: int,
        exclude_terms: Sequence[str] = (),
    ) -> tuple[RankedUnit, ...]: ...

    async def vector_units(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        embedding: Sequence[float],
        model_id: str,
        limit: int,
    ) -> tuple[RankedUnit, ...]: ...

    async def accepted_changes(
        self,
        *,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        limit: int,
    ) -> tuple[SnapshotChangeSet, ...]: ...


def _measure(fact: TariffFact) -> ComparableMeasure:
    return ComparableMeasure(
        field_path=fact.field_path,
        number=fact.number,
        unit=fact.unit or "",
        currency=fact.currency,
        rate_basis=fact.rate_basis,
        fee_scope=fact.fee_scope,
        conditions=tuple(json.dumps(item, sort_keys=True) for item in fact.conditions),
    )


def _condition_match(fact: TariffFact, required: dict) -> bool:
    for dimension, expected in required.items():
        if dimension == "currency":
            # A currency drops a fact only when the fact names another one: a
            # term or a repayment method has no currency and stays (RR24).
            stated = {fact.currency} | {
                item.get("value")
                for item in fact.conditions
                if item.get("dimension") == "currency"
            }
            stated.discard(None)
            if not stated or expected in stated:
                continue
            return False
        if (
            dimension == "rate_basis"
            and fact.rate_basis
            and fact.rate_basis.value == expected
        ):
            continue
        if dimension == "fee_scope" and fact.fee_scope == expected:
            continue
        if any(
            item.get("dimension") == dimension and item.get("value") == expected
            for item in fact.conditions
        ):
            continue
        return False
    return True


def _paths_for_change(field: str) -> tuple[FieldPath, ...]:
    for source, paths in SOURCE_FIELD_PATHS.items():
        if source.value == field:
            return paths
    try:
        return (FieldPath(field),)
    except ValueError:
        return ()


def _display(fact: TariffFact) -> str:
    value = json.dumps(fact.value, ensure_ascii=False, sort_keys=True)
    extras = ", ".join(
        item
        for item in (
            fact.currency,
            fact.unit,
            fact.rate_basis.value if fact.rate_basis else None,
        )
        if item
    )
    conditions = (
        " conditions=" + json.dumps(fact.conditions, ensure_ascii=False, sort_keys=True)
        if fact.conditions
        else ""
    )
    return (
        f"{fact.offering_id.value} {fact.field_path.value}: {value}"
        + (f" ({extras})" if extras else "")
        + conditions
    )


class OfferingStateReader(Protocol):
    async def offering_states(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
    ) -> dict[OfferingId, OfferingDataState]: ...


_FEE_PATHS = tuple(path for path in FieldPath if path.value.startswith("fee."))


def _coverage_entry(
    offering: OfferingId, state: str, data: OfferingDataState | None = None
) -> dict[str, JsonValue]:
    entry: dict[str, JsonValue] = {"offering_id": offering.value, "state": state}
    if data is not None and data.pending_reviews:
        entry["pending_reviews"] = data.pending_reviews
    if data is not None and data.failure_code:
        entry["failure_code"] = data.failure_code
    return entry


class StructuredTariffQueryService:
    def __init__(
        self,
        repository: StructuredQueryRepository,
        unit_embedder: StructuredUnitEmbedder | None = None,
        *,
        offering_states: OfferingStateReader | None = None,
    ) -> None:
        self._repository = repository
        self._unit_embedder = unit_embedder
        self._offering_states = offering_states

    async def _unpublished(
        self,
        plan: ResolutionPlan,
        offering_ids: tuple[OfferingId, ...],
        profiles: tuple[OfferingProfile, ...],
    ) -> dict[OfferingId, OfferingDataState]:
        """In-scope offerings with no active profile, and why (F1, F4).

        The reason is best effort: without a reader, or when it fails, an
        offering is `no_accepted_data`; the answer itself never fails on it.
        """
        published = {item.offering_id for item in profiles}
        missing = tuple(item for item in offering_ids if item not in published)
        if not missing:
            return {}
        states: dict[OfferingId, OfferingDataState] = {}
        if self._offering_states is not None:
            try:
                states = await self._offering_states.offering_states(
                    bank=plan.bank, product=plan.product, offering_ids=missing
                )
            except Exception:
                logger.warning("offering state lookup failed", exc_info=True)
        return {
            item: states.get(item) or OfferingDataState(state="no_accepted_data")
            for item in missing
        }

    async def answer(
        self, plan: ResolutionPlan, question: str, *, now: datetime | None = None
    ) -> TariffQueryResult:
        with retrieval_trace(
            operation=plan.operation.value,
            product=plan.product.value,
            question_sha12=plan.question_sha256[:12],
        ):
            result = await self._answer(plan, question, now=now)
            set_outcome(
                status=result.status.value,
                facts=len(result.facts),
                units=len(result.retrieval_units),
                rows=len(result.comparison_rows),
                reason=result.reason,
            )
            return result

    async def _answer(
        self, plan: ResolutionPlan, question: str, *, now: datetime | None = None
    ) -> TariffQueryResult:
        current = now or datetime.now(UTC)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("current time must be timezone-aware")
        if not plan.issued_at <= current < plan.expires_at:
            raise ValueError("resolution plan is expired or not yet active")
        if hashlib.sha256(question.encode("utf-8")).hexdigest() != plan.question_sha256:
            raise ValueError("question differs from authorized resolution plan")
        if plan.product is None:
            raise ValueError("a tariff answer requires a resolved family")
        offering_ids = plan.offering_ids or tuple(
            item for item in OfferingId if item.product is plan.product
        )
        if any(item.product is not plan.product for item in offering_ids):
            raise ValueError("offering outside authorized family")
        record(
            "plan.authorized",
            offerings=[item.value for item in offering_ids],
            fields=[item.value for item in plan.fields],
            conditions=plan.conditions,
            rank_direction=(plan.rank_direction.value if plan.rank_direction else None),
            expires_at=plan.expires_at.isoformat(),
        )
        if plan.operation is QueryOperation.HISTORY:
            return await self._history(plan, offering_ids)
        profiles = await self._repository.active_profiles(
            bank=plan.bank, product=plan.product, offering_ids=offering_ids
        )
        record(
            "profiles.loaded",
            requested=len(offering_ids),
            active=len(profiles),
            snapshots=[str(item.snapshot_id)[:8] for item in profiles],
        )
        unpublished = await self._unpublished(plan, offering_ids, profiles)
        if unpublished:
            record(
                "coverage.unpublished",
                offerings={
                    item.value: data.state for item, data in unpublished.items()
                },
            )
        if not profiles:
            states = {data.state for data in unpublished.values()}
            return self._empty(
                plan, QueryStatus.MISSING, "no accepted offering projection"
            ).model_copy(
                update={
                    "reason_code": states.pop()
                    if len(states) == 1
                    else "no_accepted_data",
                    "metadata": {
                        "coverage": [
                            _coverage_entry(item, data.state, data)
                            for item, data in unpublished.items()
                        ]
                    },
                }
            )
        fields, fields_source = plan.fields, "question"
        if not fields:
            fields = await self._find_fields(plan, profiles, question)
            fields_source = "retrieval" if fields else "core"
            fields = fields or CORE_FIELDS
        record(
            "fields.selected", source=fields_source, fields=[f.value for f in fields]
        )
        facts = await self._repository.facts(
            snapshots=[item.snapshot_id for item in profiles], fields=fields
        )
        loaded = len(facts)
        facts = tuple(fact for fact in facts if _condition_match(fact, plan.conditions))
        found = tuple(
            fact
            for fact in facts
            if fact.status is ExtractionStatus.FOUND and fact.evidence
        )
        record(
            "facts.loaded",
            loaded=loaded,
            after_conditions=len(facts),
            evidence_backed=len(found),
            citations=sum(len(fact.evidence) for fact in found),
        )
        if not found:
            return await self._not_found(
                plan, profiles, facts, fields, fields_source, unpublished
            )
        record("branch.selected", branch=plan.operation.value)
        if plan.operation is QueryOperation.FAMILY_RANK:
            result = self._rank(plan, profiles, found, offering_ids, unpublished)
        elif plan.operation is QueryOperation.COMPARE:
            result = self._compare(plan, profiles, found, fields)
        elif plan.operation is QueryOperation.OVERVIEW:
            result = self._overview(plan, profiles, found)
        else:
            result = self._single(plan, profiles[0], found)
        if unpublished and "coverage" not in result.metadata:
            result = result.model_copy(
                update={
                    "metadata": {
                        **result.metadata,
                        "coverage": [
                            _coverage_entry(
                                item,
                                "published"
                                if item not in unpublished
                                else unpublished[item].state,
                                unpublished.get(item),
                            )
                            for item in offering_ids
                        ],
                    }
                }
            )
        return result.model_copy(
            update={
                "metadata": {
                    **result.metadata,
                    "fields": [item.value for item in fields],
                    "fields_source": fields_source,
                }
            }
        )

    async def _find_fields(
        self,
        plan: ResolutionPlan,
        profiles: tuple[OfferingProfile, ...],
        question: str,
    ) -> tuple[FieldPath, ...]:
        """The field finder (D4): which fields a question that named none is about.

        Ranks the scoped offerings' retrieval units against the question, with
        the offerings' own names left out (they match every unit), and returns
        the field paths of the best units. Only this path embeds the question.
        """
        offerings = tuple(item.offering_id for item in profiles)
        names = tuple(
            name
            for profile in profiles
            for name in (
                profile.display_name,
                *profile.aliases,
                *profile.formal_names,
                profile.extracted_name or "",
            )
            if name
        )
        lexical = await self._repository.lexical_units(
            bank=plan.bank,
            product=plan.product,
            offering_ids=offerings,
            query=question,
            limit=8,
            exclude_terms=names,
        )
        record(
            "lexical.result",
            hits=len(lexical),
            top=[(hit.unit.unit_id[:8], round(hit.score, 4)) for hit in lexical[:3]],
        )
        vector: tuple[RankedUnit, ...] = ()
        if self._unit_embedder is not None:
            try:
                query_vector = await self._unit_embedder.embed_query(question)
                vector = await self._repository.vector_units(
                    bank=plan.bank,
                    product=plan.product,
                    offering_ids=offerings,
                    embedding=query_vector,
                    model_id=self._unit_embedder.model_name,
                    limit=8,
                )
                record("vector.result", hits=len(vector))
            except Exception as exc:
                logger.warning(
                    "field finder vector retrieval unavailable error=%s",
                    type(exc).__name__,
                )
        scores: dict[str, float] = {}
        units = {}
        for weight, hits in ((1.0, lexical), (0.7, vector)):
            for rank, hit in enumerate(hits, start=1):
                scores[hit.unit.unit_id] = scores.get(hit.unit.unit_id, 0) + weight / (
                    60 + rank
                )
                units[hit.unit.unit_id] = hit.unit
        ranked = sorted(scores, key=lambda key: (-scores[key], key))
        paths: list[FieldPath] = []
        for unit_id in ranked:
            unit = units[unit_id]
            if unit.kind is not RetrievalUnitKind.FIELD_DETAIL:
                continue
            record_text(
                "unit.content",
                unit=unit.unit_id[:8],
                kind=unit.kind.value,
                renderer=unit.renderer_version,
                content=repr(unit.content),
            )
            for path in unit.field_paths:
                if path not in paths:
                    paths.append(path)
            if len(paths) >= FIELD_FINDER_MAX_PATHS:
                break
        record(
            "fusion.ranked",
            version=RANK_FUSION_VERSION,
            candidates=len(ranked),
            fields=[item.value for item in paths],
        )
        return tuple(paths[:FIELD_FINDER_MAX_PATHS])

    def _single(
        self,
        plan: ResolutionPlan,
        profile: OfferingProfile,
        facts: tuple[TariffFact, ...],
    ) -> TariffQueryResult:
        return TariffQueryResult(
            status=QueryStatus.ANSWERED,
            operation=plan.operation,
            product=plan.product,
            offering_ids=(profile.offering_id,),
            facts=facts,
            answer="\n".join(_display(fact) for fact in facts),
            as_of=profile.accepted_at,
        )

    def _overview(
        self,
        plan: ResolutionPlan,
        profiles: tuple[OfferingProfile, ...],
        facts: tuple[TariffFact, ...],
    ) -> TariffQueryResult:
        """A listing: each offering's values side by side, with no verdict."""
        kept: list[TariffFact] = []
        per_key: dict[tuple, int] = {}
        for fact in facts:
            key = (fact.offering_id, fact.field_path)
            if per_key.get(key, 0) >= OVERVIEW_MAX_VARIANTS:
                continue
            per_key[key] = per_key.get(key, 0) + 1
            kept.append(fact)
        truncated = len(kept) > OVERVIEW_MAX_FACTS or len(kept) < len(facts)
        kept = kept[:OVERVIEW_MAX_FACTS]
        with_facts = {fact.offering_id for fact in kept}
        record(
            "overview.offerings", with_facts=len(with_facts), requested=len(profiles)
        )
        return TariffQueryResult(
            status=QueryStatus.ANSWERED,
            operation=plan.operation,
            product=plan.product,
            offering_ids=plan.offering_ids,
            facts=tuple(kept),
            answer="\n".join(_display(fact) for fact in kept),
            as_of=max(item.accepted_at for item in profiles),
            metadata={
                "offerings_with_facts": sorted(item.value for item in with_facts),
                # Requested offerings with no accepted fact, including those
                # with no accepted projection at all.
                "offerings_without_facts": sorted(
                    item.value for item in plan.offering_ids if item not in with_facts
                ),
                "truncated": truncated,
            },
        )

    def _compare(
        self,
        plan: ResolutionPlan,
        profiles: tuple[OfferingProfile, ...],
        facts: tuple[TariffFact, ...],
        fields: tuple[FieldPath, ...],
    ) -> TariffQueryResult:
        present = {fact.offering_id for fact in facts}
        record("compare.offerings", with_facts=len(present), requested=len(profiles))
        if len(present) < 2:
            return self._empty(
                plan,
                QueryStatus.INSUFFICIENT_EVIDENCE,
                "fewer than two offerings have evidence-backed requested facts",
            )
        rows: list[ComparisonRow] = []
        for path in fields:
            entries = tuple(fact for fact in facts if fact.field_path is path)
            shared = len({fact.offering_id for fact in entries}) >= 2
            numeric = any(fact.number is not None for fact in entries)
            formula = any(fact.unit == "formula" for fact in entries)
            comparable = (
                False
                if formula
                else (
                    any(
                        left.offering_id is not right.offering_id
                        and comparison_issue(_measure(left), _measure(right)) is None
                        for index, left in enumerate(entries)
                        for right in entries[index + 1 :]
                    )
                    if numeric
                    else shared
                )
            )
            rows.append(
                ComparisonRow(
                    field_path=path,
                    facts=entries,
                    comparable=comparable,
                    reason=(
                        "formula values require their disclosed conditions"
                        if shared and formula
                        else "no common comparable numeric basis"
                        if shared and numeric and not comparable
                        else None
                    ),
                )
            )
        if not any(len({fact.offering_id for fact in row.facts}) >= 2 for row in rows):
            return self._empty(
                plan,
                QueryStatus.INSUFFICIENT_EVIDENCE,
                "no requested field has evidence from two offerings",
            )
        quantitative_rows = [
            row
            for row in rows
            if any(
                fact.number is not None or fact.unit == "formula" for fact in row.facts
            )
        ]
        if quantitative_rows and not any(row.comparable for row in quantitative_rows):
            return TariffQueryResult(
                status=QueryStatus.INCOMPARABLE,
                operation=plan.operation,
                product=plan.product,
                offering_ids=plan.offering_ids,
                facts=facts,
                comparison_rows=tuple(rows),
                reason="requested numeric variants have no shared comparable basis",
                as_of=max(item.accepted_at for item in profiles),
            )
        return TariffQueryResult(
            status=QueryStatus.ANSWERED,
            operation=plan.operation,
            product=plan.product,
            offering_ids=plan.offering_ids,
            facts=facts,
            comparison_rows=tuple(rows),
            answer="\n".join(_display(fact) for fact in facts),
            as_of=max(item.accepted_at for item in profiles),
            metadata={"comparable_fields": sum(row.comparable for row in rows)},
        )

    async def _not_found(
        self,
        plan: ResolutionPlan,
        profiles: tuple[OfferingProfile, ...],
        facts: tuple[TariffFact, ...],
        fields: tuple[FieldPath, ...],
        fields_source: str,
        unpublished: dict[OfferingId, OfferingDataState],
    ) -> TariffQueryResult:
        """No evidence-backed fact: say whether the source omits it (F5).

        A fee the offering's published fee list does not name is
        `not_stated_in_source`, with the listed fees returned so the answer can
        cite the list it checked. A field extraction recorded as `not_stated` is
        the same. Anything else is `field_not_extracted`.
        """
        result = self._empty(
            plan,
            QueryStatus.INSUFFICIENT_EVIDENCE,
            "no accepted evidence-backed fact for requested fields",
            fields_source=fields_source,
        )
        coverage = (
            {
                "coverage": [
                    _coverage_entry(item, data.state, data)
                    for item, data in unpublished.items()
                ]
            }
            if unpublished
            else {}
        )
        if fields and all(item in _FEE_PATHS for item in fields):
            listed = tuple(
                fact
                for fact in await self._repository.facts(
                    snapshots=[item.snapshot_id for item in profiles],
                    fields=_FEE_PATHS,
                )
                if fact.status is ExtractionStatus.FOUND and fact.evidence
            )
            if listed:
                return result.model_copy(
                    update={
                        "reason_code": "not_stated_in_source",
                        "reason": (
                            "the offering's published fee list names no "
                            + ", ".join(
                                item.value.removeprefix("fee.") for item in fields
                            )
                            + " fee"
                        ),
                        "facts": listed,
                        "metadata": {
                            **result.metadata,
                            **coverage,
                            "fees_checked": len(listed),
                        },
                    }
                )
        stated_absent = any(
            fact.status is ExtractionStatus.NOT_STATED for fact in facts
        )
        return result.model_copy(
            update={
                "reason_code": (
                    "not_stated_in_source" if stated_absent else "field_not_extracted"
                ),
                "metadata": {**result.metadata, **coverage},
            }
        )

    def _rank(
        self,
        plan: ResolutionPlan,
        profiles: tuple[OfferingProfile, ...],
        facts: tuple[TariffFact, ...],
        offering_ids: tuple[OfferingId, ...] = (),
        unpublished: dict[OfferingId, OfferingDataState] | None = None,
    ) -> TariffQueryResult:
        """Rank by group (D3): offerings compete only on a shared numeric basis.

        Values are grouped by unit, currency, rate basis and fee scope. In each
        group every offering is represented by its best variant, whatever that
        variant's conditions, and the conditions are reported with the value.
        """
        if len(plan.fields) != 1:
            raise ValueError("family rank requires exactly one canonical field")
        field_path = plan.fields[0]
        candidates = [
            fact
            for fact in facts
            if fact.number is not None and fact.field_path is field_path
        ]
        offerings = {fact.offering_id for fact in candidates}
        record(
            "rank.candidates",
            numeric=len(candidates),
            offerings=len(offerings),
            direction=plan.rank_direction.value if plan.rank_direction else None,
        )
        if len(offerings) < 2:
            return self._empty(
                plan,
                QueryStatus.INSUFFICIENT_EVIDENCE,
                "fewer than two offerings have a numeric disclosed value",
            )
        lowest = plan.rank_direction is RankDirection.LOWEST
        groups: dict[tuple, list[TariffFact]] = {}
        for fact in candidates:
            key = (
                fact.unit or "",
                fact.currency,
                fact.rate_basis.value if fact.rate_basis else None,
                fact.fee_scope,
            )
            groups.setdefault(key, []).append(fact)
        ranked_groups: list[dict[str, object]] = []
        ordered_facts: list[TariffFact] = []
        for key, items in sorted(groups.items(), key=lambda item: str(item[0])):
            best: dict[OfferingId, TariffFact] = {}
            for fact in items:
                held = best.get(fact.offering_id)
                if held is None or (
                    fact.number < held.number if lowest else fact.number > held.number
                ):
                    best[fact.offering_id] = fact
            if len(best) < 2:
                continue
            ordered = sorted(
                best.values(),
                key=lambda item: (
                    item.number if lowest else -item.number,
                    item.offering_id.value,
                ),
            )
            ordered_facts.extend(ordered)
            ranked_groups.append(
                {
                    "unit": key[0] or None,
                    "currency": key[1],
                    "rate_basis": key[2],
                    "fee_scope": key[3],
                    "winner": ordered[0].offering_id.value,
                    "ranking": [
                        {
                            "offering_id": item.offering_id.value,
                            "value": str(item.number),
                            "conditions": list(item.conditions),
                        }
                        for item in ordered
                    ],
                }
            )
        record("rank.groups", groups=len(groups), ranked=len(ranked_groups))
        as_of = max(item.accepted_at for item in profiles)
        if not ranked_groups:
            return TariffQueryResult(
                status=QueryStatus.INCOMPARABLE,
                operation=plan.operation,
                product=plan.product,
                offering_ids=tuple(item.offering_id for item in profiles),
                facts=tuple(candidates),
                reason=_incomparable_reason(groups),
                as_of=as_of,
            )
        # Every in-scope offering, ranked or not, with the reason (F1).
        unpublished = unpublished or {}
        scope = offering_ids or tuple(item.offering_id for item in profiles)
        ranked_ids = {fact.offering_id for fact in ordered_facts}
        with_value = {fact.offering_id for fact in candidates}
        coverage: list[dict[str, JsonValue]] = []
        for offering in scope:
            if offering in ranked_ids:
                coverage.append(_coverage_entry(offering, "ranked"))
            elif offering in unpublished:
                data = unpublished[offering]
                coverage.append(_coverage_entry(offering, data.state, data))
            elif offering in with_value:
                coverage.append(_coverage_entry(offering, "not_comparable"))
            else:
                coverage.append(_coverage_entry(offering, "no_value"))
        not_ranked = [
            {"offering_id": entry["offering_id"], "reason": entry["state"]}
            for entry in coverage
            if entry["state"] != "ranked"
        ]
        metadata: dict[str, object] = {
            "direction": "lowest" if lowest else "highest",
            "groups": ranked_groups,
            "not_ranked": not_ranked,
            "coverage": coverage,
        }
        if len(ranked_groups) == 1:
            metadata["winner"] = ranked_groups[0]["winner"]
        headline = f"ranked {len(ranked_ids)} of {len(scope)} offerings"
        if not_ranked:
            headline += "; not ranked: " + ", ".join(
                f"{item['offering_id']} ({item['reason']})" for item in not_ranked
            )
        return TariffQueryResult(
            status=QueryStatus.ANSWERED,
            operation=plan.operation,
            product=plan.product,
            offering_ids=tuple(item.offering_id for item in profiles),
            facts=tuple(ordered_facts),
            answer=headline
            + "\n"
            + "\n".join(
                f"[{group['unit']} {group['currency'] or ''}] winner "
                f"{group['winner']}: "
                + "; ".join(
                    f"{entry['offering_id']} {entry['value']}"
                    for entry in group["ranking"]
                )
                for group in ranked_groups
            ),
            as_of=as_of,
            metadata=metadata,
        )

    async def _history(
        self,
        plan: ResolutionPlan,
        offering_ids: tuple[OfferingId, ...],
    ) -> TariffQueryResult:
        changes = await self._repository.accepted_changes(
            product=plan.product, offering_ids=offering_ids, limit=50
        )
        record("history.changes", accepted_change_sets=len(changes))
        relevant = tuple(
            change
            for change in changes
            # An initial accepted snapshot records no change.
            if change.changes
            and (
                not plan.fields
                or any(
                    set(_paths_for_change(item.field)) & set(plan.fields)
                    for item in change.changes
                )
            )
        )
        if not relevant:
            return self._empty(
                plan, QueryStatus.MISSING, "no accepted change in available history"
            )
        paths = tuple(
            dict.fromkeys(
                path
                for change in relevant
                for item in change.changes
                for path in _paths_for_change(item.field)
            )
        )
        snapshot_ids = tuple(
            dict.fromkeys(
                snapshot_id
                for change in relevant
                for snapshot_id in (
                    change.previous_snapshot_id,
                    change.current_snapshot_id,
                )
                if snapshot_id is not None
            )
        )
        historical = await self._repository.facts(
            snapshots=snapshot_ids,
            fields=paths,
            include_inactive=True,
        )
        enriched = []
        omitted: list[dict[str, object]] = []
        for change in relevant:
            updated_items = []
            for item in change.changes:
                item_paths = set(_paths_for_change(item.field))
                previous_evidence = tuple(
                    evidence.model_dump(mode="json")
                    for fact in historical
                    if fact.snapshot_id == change.previous_snapshot_id
                    and fact.offering_id is change.offering_id
                    and fact.field_path in item_paths
                    for evidence in fact.evidence
                )
                current_evidence = tuple(
                    evidence.model_dump(mode="json")
                    for fact in historical
                    if fact.snapshot_id == change.current_snapshot_id
                    and fact.offering_id is change.offering_id
                    and fact.field_path in item_paths
                    for evidence in fact.evidence
                )
                # Evidence is required only for a side that has a value: an
                # added field has no previous value, a removed one no current
                # value (RR26). An item missing it is left out and listed.
                missing = [
                    side
                    for side, value, evidence in (
                        ("previous", item.previous, previous_evidence),
                        ("current", item.current, current_evidence),
                    )
                    if value is not None and not evidence
                ]
                if missing:
                    omitted.append(
                        {
                            "offering_id": change.offering_id.value,
                            "field": item.field,
                            "reason": f"no verified evidence for the {missing[0]} value",
                        }
                    )
                    continue
                updated_items.append(
                    item.model_copy(
                        update={
                            "previous_evidence": previous_evidence,
                            "current_evidence": current_evidence,
                        }
                    )
                )
            if updated_items:
                enriched.append(
                    change.model_copy(update={"changes": tuple(updated_items)})
                )
        record(
            "history.items",
            kept=sum(len(c.changes) for c in enriched),
            omitted=len(omitted),
        )
        if not enriched:
            result = self._empty(
                plan,
                QueryStatus.INSUFFICIENT_EVIDENCE,
                "no accepted change has verified source evidence",
            )
            return result.model_copy(update={"metadata": {"omitted": omitted}})
        return TariffQueryResult(
            status=QueryStatus.ANSWERED,
            operation=plan.operation,
            product=plan.product,
            offering_ids=offering_ids,
            as_of=max(item.created_at for item in enriched),
            metadata={
                "changes": [item.model_dump(mode="json") for item in enriched],
                "omitted": omitted,
            },
        )

    @staticmethod
    def _empty(
        plan: ResolutionPlan,
        status: QueryStatus,
        reason: str,
        *,
        fields_source: str | None = None,
    ) -> TariffQueryResult:
        return TariffQueryResult(
            status=status,
            operation=plan.operation,
            product=plan.product,
            offering_ids=plan.offering_ids,
            reason=reason,
            metadata={"fields_source": fields_source} if fields_source else {},
        )


def _incomparable_reason(groups: dict[tuple, list[TariffFact]]) -> str:
    """Name what actually differs between the offerings' values."""
    dimensions = ("units", "currencies", "rate bases", "fee scopes")
    differing = [
        name
        for index, name in enumerate(dimensions)
        if len({key[index] for key in groups}) > 1
    ]
    return (
        "no two offerings share a numeric basis: their values differ in "
        + ", ".join(differing or ["basis"])
    )
