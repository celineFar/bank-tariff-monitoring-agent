from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config.models import TariffQuerySettings
from app.domain.catalog import SeedCatalog
from app.domain.intent import FreshnessStatus, HistoryQuery, HistoryRequestKind
from app.domain.models import OfferingId, ProductType
from app.domain.tariff_queries import (
    CurrentTariffItem,
    CurrentTariffResult,
    HistoryResultStatus,
    TariffHistoryResult,
)
from app.repositories.contracts import MonitoringSnapshotRepository

Clock = Callable[[], datetime]
MonotonicClock = Callable[[], float]
Sleep = Callable[[float], Awaitable[None]]


class CurrentTariffService:
    def __init__(
        self,
        catalog: SeedCatalog,
        snapshots: MonitoringSnapshotRepository,
        settings: TariffQuerySettings,
        *,
        clock: Clock = lambda: datetime.now(UTC),
    ) -> None:
        self._catalog = catalog
        self._snapshots = snapshots
        self._settings = settings
        self._clock = clock

    async def get_current(
        self,
        *,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
        offering_ids: tuple[OfferingId, ...] = (),
    ) -> CurrentTariffResult:
        if (offering_id is not None or offering_ids) and product is None:
            raise ValueError("offering_id requires product")
        if offering_id is not None and offering_id.product is not product:
            raise ValueError("offering does not belong to product")
        if any(item.product is not product for item in offering_ids):
            raise ValueError("offering does not belong to product")
        if offering_id is not None and offering_ids:
            raise ValueError("use offering_id or offering_ids, not both")
        if len(offering_ids) == 1:
            offering_id, offering_ids = offering_ids[0], ()
        subset = frozenset(offering_ids)
        now = self._clock()
        _require_aware(now, "current tariff clock")
        latest = {
            snapshot.offering_id: snapshot
            for snapshot in await self._snapshots.list_latest_accepted(
                bank="ameria",
                product=product,
                offering_id=offering_id,
            )
        }
        offerings = tuple(
            entry
            for entry in self._catalog.offerings
            if entry.enabled
            and (product is None or entry.product is product)
            and (offering_id is None or entry.offering_id is offering_id)
            and (not subset or entry.offering_id in subset)
        )
        items: list[CurrentTariffItem] = []
        for entry in offerings:
            snapshot = latest.get(entry.offering_id)
            accepted_at = snapshot.accepted_at if snapshot is not None else None
            pending = await self._snapshots.has_newer_pending_review(
                bank="ameria",
                product=entry.product,
                offering_id=entry.offering_id,
                accepted_at=accepted_at,
            )
            if snapshot is None:
                items.append(
                    CurrentTariffItem(
                        product=entry.product,
                        offering_id=entry.offering_id,
                        freshness=FreshnessStatus.MISSING,
                        pending_newer_review=pending,
                    )
                )
                continue
            assert snapshot.accepted_at is not None
            age = max(timedelta(), now - snapshot.accepted_at)
            freshness = (
                FreshnessStatus.FRESH
                if age <= timedelta(days=self._settings.freshness_days)
                else FreshnessStatus.STALE
            )
            items.append(
                CurrentTariffItem(
                    product=entry.product,
                    offering_id=entry.offering_id,
                    freshness=freshness,
                    snapshot_id=snapshot.id,
                    accepted_at=snapshot.accepted_at,
                    age_seconds=age.total_seconds(),
                    normalized_tariff=snapshot.normalized_tariff,
                    evidence=snapshot.evidence,
                    pending_newer_review=pending,
                )
            )
        return CurrentTariffResult(as_of=now, items=tuple(items))


class TariffHistoryService:
    def __init__(
        self,
        snapshots: MonitoringSnapshotRepository,
        settings: TariffQuerySettings,
        *,
        clock: Clock = lambda: datetime.now(UTC),
    ) -> None:
        self._snapshots = snapshots
        self._settings = settings
        self._clock = clock

    async def query(self, query: HistoryQuery) -> TariffHistoryResult:
        """Read one scope, with a compact citation on every changed value (RR28)."""
        result = await self._query(query)
        if not result.changes:
            return result
        return result.model_copy(
            update={"changes": await self._cited_changes(result.changes)}
        )

    async def _cited_changes(self, changes):
        """Each changed value's citations, from the snapshot that accepted it."""
        get = getattr(self._snapshots, "get", None)
        if get is None:
            return changes
        loaded: dict = {}

        async def snapshot(snapshot_id):
            if snapshot_id is None:
                return None
            if snapshot_id not in loaded:
                loaded[snapshot_id] = await get(snapshot_id)
            return loaded[snapshot_id]

        cited = []
        for change in changes:
            previous = await snapshot(change.previous_snapshot_id)
            current = await snapshot(change.current_snapshot_id)
            cited.append(
                change.model_copy(
                    update={
                        "changes": tuple(
                            item.model_copy(
                                update={
                                    "previous_evidence": (
                                        field_citations(previous, item.field)
                                        if previous is not None
                                        else ()
                                    ),
                                    "current_evidence": (
                                        field_citations(current, item.field)
                                        if current is not None
                                        else ()
                                    ),
                                }
                            )
                            for item in change.changes
                        )
                    }
                )
            )
        return tuple(cited)

    async def _query(self, query: HistoryQuery) -> TariffHistoryResult:
        """Read one scope; a subset of offerings is read per offering and merged."""
        family = (
            frozenset(item for item in OfferingId if item.product is query.product)
            if query.product is not None
            else frozenset()
        )
        if len(query.offering_ids) == 1:
            query = query.model_copy(
                update={"offering_id": query.offering_ids[0], "offering_ids": ()}
            )
        elif query.offering_ids and frozenset(query.offering_ids) >= family:
            query = query.model_copy(update={"offering_ids": ()})
        if not query.offering_ids:
            return await self._query_one(query, query.offering_id)
        return await self._query_subset(query)

    async def _query_subset(self, query: HistoryQuery) -> TariffHistoryResult:
        parts = [
            await self._query_one(query, offering) for offering in query.offering_ids
        ]
        limit = min(query.limit, self._settings.max_history_results)
        snapshots = tuple(
            sorted(
                (item for part in parts for item in part.snapshots),
                key=lambda item: (item.accepted_at or item.created_at, str(item.id)),
                reverse=True,
            )[:limit]
        )
        changes = tuple(
            sorted(
                (item for part in parts for item in part.changes),
                key=lambda item: (item.created_at, str(item.id)),
                reverse=True,
            )[:limit]
        )
        statuses = {part.status for part in parts}
        for status in (
            HistoryResultStatus.CHANGES_FOUND,
            HistoryResultStatus.HISTORY_FOUND,
            HistoryResultStatus.UNCHANGED_IN_WINDOW,
            HistoryResultStatus.FIRST_OBSERVATION,
            HistoryResultStatus.UNAVAILABLE,
        ):
            if status in statuses:
                break
        older = [
            part.last_change_before_window_at
            for part in parts
            if part.last_change_before_window_at is not None
        ]
        return TariffHistoryResult(
            query=query,
            status=status,
            window_start=parts[0].window_start,
            window_end=parts[0].window_end,
            snapshots=snapshots,
            changes=changes,
            last_change_before_window_at=max(older) if older else None,
        )

    async def _query_one(
        self, query: HistoryQuery, offering_id: OfferingId | None
    ) -> TariffHistoryResult:
        end_at = query.end_at or self._clock()
        _require_aware(end_at, "history clock")
        default_days = (
            self._settings.recent_change_days
            if query.kind is HistoryRequestKind.WHAT_CHANGED
            else self._settings.default_history_days
        )
        start_at = query.start_at or end_at - timedelta(days=default_days)
        limit = min(query.limit, self._settings.max_history_results)
        snapshots = await self._snapshots.list_accepted_history(
            bank="ameria",
            product=query.product,
            offering_id=offering_id,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
        )
        if query.kind is HistoryRequestKind.SHOW_HISTORY:
            status = (
                HistoryResultStatus.HISTORY_FOUND
                if snapshots
                else HistoryResultStatus.UNAVAILABLE
            )
            if snapshots and all(
                item.previous_accepted_snapshot_id is None for item in snapshots
            ):
                status = HistoryResultStatus.FIRST_OBSERVATION
            return TariffHistoryResult(
                query=query,
                status=status,
                window_start=start_at,
                window_end=end_at,
                snapshots=snapshots,
            )

        changes = await self._snapshots.list_changes(
            product=query.product,
            offering_id=offering_id,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
        )
        if changes:
            return TariffHistoryResult(
                query=query,
                status=HistoryResultStatus.CHANGES_FOUND,
                window_start=start_at,
                window_end=end_at,
                changes=changes,
            )
        latest = await self._snapshots.list_latest_accepted(
            bank="ameria",
            product=query.product,
            offering_id=offering_id,
        )
        if not latest:
            status = HistoryResultStatus.UNAVAILABLE
        elif all(item.previous_accepted_snapshot_id is None for item in latest):
            status = HistoryResultStatus.FIRST_OBSERVATION
        else:
            status = HistoryResultStatus.UNCHANGED_IN_WINDOW
        older = await self._snapshots.get_latest_change_before(
            product=query.product,
            offering_id=offering_id,
            before=start_at,
        )
        return TariffHistoryResult(
            query=query,
            status=status,
            window_start=start_at,
            window_end=end_at,
            changes=(),
            last_change_before_window_at=(older.created_at if older else None),
        )


CITATIONS_PER_FIELD = 3
QUOTE_CHARS = 300


def field_citations(snapshot, field: str) -> tuple[dict[str, object], ...]:
    """Compact citations of one accepted field (D15): URL, section, page, quote.

    Read from the snapshot's own extraction, so a history value carries the
    evidence it was accepted with, at a bounded size (the RV8 payload bound).
    """
    product = (snapshot.semantic_extraction or {}).get("loan_product") or {}
    value = product.get(field)
    if value is None:
        # Category-specific fields (down payment, credit limit, ...) are nested.
        details = product.get("details")
        value = details.get(field) if isinstance(details, dict) else None
    if not isinstance(value, dict) or value.get("status") != "found":
        return ()
    citations: list[dict[str, object]] = []
    for item in value.get("evidence") or ():
        if not isinstance(item, dict):
            continue
        locator = item.get("locator") or {}
        url = item.get("source_url") or locator.get("source_url")
        quote = str(item.get("quote") or "").strip()
        if not url or not quote:
            continue
        citations.append(
            {
                "source_url": str(url),
                "section": item.get("section"),
                "page": locator.get("pdf_page"),
                "quote": quote[:QUOTE_CHARS],
            }
        )
        if len(citations) >= CITATIONS_PER_FIELD:
            break
    return tuple(citations)


_MODEL_FACT_KEYS = (
    "offering_id",
    "field_path",
    "status",
    "value",
    "unit",
    "currency",
    "rate_basis",
    "fee_scope",
    "conditions",
)


def model_facing_query_result(result: dict[str, Any]) -> dict[str, Any]:
    """A structured query result as the model sees it (F16).

    Each fact keeps its value and conditions; its evidence becomes at most
    three compact citations (URL, section, page, quote of at most 300
    characters). Internal ids and locators (XPath, CSS, block and row ids) are
    not shown, so an answer cites what a person can find.
    """
    if "facts" not in result:
        return result
    facts = []
    for fact in result.get("facts") or ():
        if not isinstance(fact, dict):
            continue
        compact = {
            key: fact[key]
            for key in _MODEL_FACT_KEYS
            if fact.get(key) not in (None, [], ())
        }
        citations: list[dict[str, object]] = []
        for evidence in fact.get("evidence") or ():
            locator = evidence.get("locator") or {}
            url = evidence.get("source_url") or locator.get("source_url")
            quote = str(evidence.get("quote") or "").strip()
            if not url or not quote:
                continue
            citation: dict[str, object] = {"source_url": str(url)}
            if locator.get("section"):
                citation["section"] = locator["section"]
            if locator.get("pdf_page"):
                citation["page"] = locator["pdf_page"]
            citation["quote"] = quote[:QUOTE_CHARS]
            if citation not in citations:
                citations.append(citation)
            if len(citations) >= CITATIONS_PER_FIELD:
                break
        compact["evidence"] = citations
        facts.append(compact)
    return {**result, "facts": facts}


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
