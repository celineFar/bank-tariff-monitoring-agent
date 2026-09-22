"""Deterministic accepted-tariff answers over the structured read model."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotChangeSet
from app.domain.semantic_extraction import ExtractionStatus
from app.domain.structured_tariffs import (
    SOURCE_FIELD_PATHS,
    ComparisonRow,
    FieldPath,
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

logger = logging.getLogger(__name__)
RANK_FUSION_VERSION = "rrf-v1-k60-lex1-vector0.7"


class StructuredUnitEmbedder(Protocol):
    model_name: str

    async def ensure(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        limit: int,
    ) -> int: ...

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
        if dimension == "currency" and fact.currency == expected:
            continue
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


class StructuredTariffQueryService:
    def __init__(
        self,
        repository: StructuredQueryRepository,
        unit_embedder: StructuredUnitEmbedder | None = None,
    ) -> None:
        self._repository = repository
        self._unit_embedder = unit_embedder

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
        if not profiles:
            return self._empty(
                plan, QueryStatus.MISSING, "no accepted offering projection"
            )
        facts = await self._repository.facts(
            snapshots=[item.snapshot_id for item in profiles], fields=plan.fields
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
            return self._empty(
                plan,
                QueryStatus.INSUFFICIENT_EVIDENCE,
                "no accepted evidence-backed fact for requested fields",
            )
        record("branch.selected", branch=plan.operation.value)
        if plan.operation is QueryOperation.FAMILY_RANK:
            return self._rank(plan, profiles, found)
        if plan.operation is QueryOperation.COMPARE:
            return self._compare(plan, profiles, found)
        return await self._single(plan, question, profiles[0], found)

    async def _single(
        self,
        plan: ResolutionPlan,
        question: str,
        profile: OfferingProfile,
        facts: tuple[TariffFact, ...],
    ) -> TariffQueryResult:
        lexical = await self._repository.lexical_units(
            bank=plan.bank,
            product=plan.product,
            offering_ids=(profile.offering_id,),
            query=question,
            limit=8,
        )
        record(
            "lexical.result",
            hits=len(lexical),
            top=[(hit.unit.unit_id[:8], round(hit.score, 4)) for hit in lexical[:3]],
        )
        vector: tuple[RankedUnit, ...] = ()
        if len(lexical) >= 4 or self._unit_embedder is None:
            record(
                "vector.skipped",
                reason=(
                    "lexical recall sufficient"
                    if len(lexical) >= 4
                    else "no embedder configured"
                ),
            )
        if len(lexical) < 4 and self._unit_embedder is not None:
            try:
                await self._unit_embedder.ensure(
                    bank=plan.bank,
                    product=plan.product,
                    offering_ids=(profile.offering_id,),
                    limit=100,
                )
                query_vector = await self._unit_embedder.embed_query(question)
                vector = await self._repository.vector_units(
                    bank=plan.bank,
                    product=plan.product,
                    offering_ids=(profile.offering_id,),
                    embedding=query_vector,
                    model_id=self._unit_embedder.model_name,
                    limit=8,
                )
                record(
                    "vector.result",
                    model=self._unit_embedder.model_name,
                    hits=len(vector),
                    top=[
                        (hit.unit.unit_id[:8], round(hit.score, 4))
                        for hit in vector[:3]
                    ],
                )
            except Exception as exc:
                logger.warning(
                    "supplemental vector retrieval unavailable error=%s",
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
        hits = tuple(
            units[unit_id]
            for unit_id in sorted(scores, key=lambda key: (-scores[key], key))
        )
        record(
            "fusion.ranked",
            version=RANK_FUSION_VERSION,
            candidates=len(hits),
            fused=[
                (unit.unit_id[:8], round(scores[unit.unit_id], 6)) for unit in hits[:5]
            ],
        )
        fact_ids = {fact.fact_id for fact in facts}
        evidence_ids = {item.evidence_id for fact in facts for item in fact.evidence}
        supported = tuple(
            unit
            for unit in hits
            if unit.fact_ids
            and unit.evidence_ids
            and set(unit.fact_ids) <= fact_ids
            and set(unit.evidence_ids) <= evidence_ids
        )
        selected = tuple(
            [unit for unit in supported if unit.kind is RetrievalUnitKind.PROFILE][:2]
            + [
                unit
                for unit in supported
                if unit.kind is RetrievalUnitKind.FIELD_DETAIL
            ][:6]
        )
        record(
            "units.admitted",
            candidates=len(hits),
            supported=len(supported),
            rejected_unsupported=len(hits) - len(supported),
            selected=len(selected),
            rule="a unit needs every fact and citation inside the answer",
        )
        for unit in selected:
            record_text(
                "unit.content",
                unit=unit.unit_id[:8],
                kind=unit.kind.value,
                renderer=unit.renderer_version,
                content=repr(unit.content),
            )
        return TariffQueryResult(
            status=QueryStatus.ANSWERED,
            operation=plan.operation,
            product=plan.product,
            offering_ids=(profile.offering_id,),
            facts=facts,
            retrieval_units=selected,
            answer="\n".join(_display(fact) for fact in facts),
            as_of=profile.accepted_at,
            metadata={
                "retrieval_units": len(selected),
                "ranking_version": RANK_FUSION_VERSION,
            },
        )

    def _compare(
        self,
        plan: ResolutionPlan,
        profiles: tuple[OfferingProfile, ...],
        facts: tuple[TariffFact, ...],
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
        for path in plan.fields:
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

    def _rank(
        self,
        plan: ResolutionPlan,
        profiles: tuple[OfferingProfile, ...],
        facts: tuple[TariffFact, ...],
    ) -> TariffQueryResult:
        if len(plan.fields) != 1:
            raise ValueError("family rank requires exactly one canonical field")
        candidates = [fact for fact in facts if fact.number is not None]
        record(
            "rank.candidates",
            numeric=len(candidates),
            offerings=len({fact.offering_id for fact in candidates}),
            direction=plan.rank_direction.value if plan.rank_direction else None,
        )
        if len({fact.offering_id for fact in candidates}) < 2:
            return self._empty(
                plan,
                QueryStatus.INSUFFICIENT_EVIDENCE,
                "fewer than two offerings have a numeric disclosed value",
            )
        reference = _measure(candidates[0])
        if any(comparison_issue(reference, _measure(item)) for item in candidates[1:]):
            return TariffQueryResult(
                status=QueryStatus.INCOMPARABLE,
                operation=plan.operation,
                product=plan.product,
                offering_ids=tuple(item.offering_id for item in profiles),
                facts=tuple(candidates),
                reason="numeric variants have different currencies, units, rate bases or fee scopes",
                as_of=max(item.accepted_at for item in profiles),
            )
        ascending = plan.rank_direction is RankDirection.LOWEST
        ordered = tuple(
            sorted(
                candidates,
                key=lambda item: (
                    item.number if ascending else -item.number,
                    item.offering_id.value,
                ),
            )
        )
        winner = ordered[0]
        return TariffQueryResult(
            status=QueryStatus.ANSWERED,
            operation=plan.operation,
            product=plan.product,
            offering_ids=tuple(item.offering_id for item in profiles),
            facts=ordered,
            answer=_display(winner),
            as_of=max(item.accepted_at for item in profiles),
            metadata={
                "winner": winner.offering_id.value,
                "direction": "lowest" if ascending else "highest",
            },
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
            if not plan.fields
            or any(
                set(_paths_for_change(item.field)) & set(plan.fields)
                for item in change.changes
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
                if not previous_evidence or not current_evidence:
                    return self._empty(
                        plan,
                        QueryStatus.INSUFFICIENT_EVIDENCE,
                        "accepted change lacks old or new verified source evidence",
                    )
                updated_items.append(
                    item.model_copy(
                        update={
                            "previous_evidence": previous_evidence,
                            "current_evidence": current_evidence,
                        }
                    )
                )
            enriched.append(change.model_copy(update={"changes": tuple(updated_items)}))
        return TariffQueryResult(
            status=QueryStatus.ANSWERED,
            operation=plan.operation,
            product=plan.product,
            offering_ids=offering_ids,
            as_of=max(item.created_at for item in enriched),
            metadata={"changes": [item.model_dump(mode="json") for item in enriched]},
        )

    @staticmethod
    def _empty(
        plan: ResolutionPlan, status: QueryStatus, reason: str
    ) -> TariffQueryResult:
        return TariffQueryResult(
            status=status,
            operation=plan.operation,
            product=plan.product,
            offering_ids=plan.offering_ids,
            reason=reason,
        )
