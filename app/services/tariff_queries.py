from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import UUID

from app.config.models import TariffQuerySettings
from app.domain.catalog import SeedCatalog
from app.domain.intent import FreshnessStatus, HistoryQuery, HistoryRequestKind
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import RunStatus
from app.domain.tariff_queries import (
    CurrentTariffItem,
    CurrentTariffResult,
    HistoryResultStatus,
    RunWaitResult,
    RunWaitState,
    TariffHistoryResult,
)
from app.repositories.contracts import MonitoringSnapshotRepository
from app.services.run_service import RunServicePort

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
    ) -> CurrentTariffResult:
        if offering_id is not None and product is None:
            raise ValueError("offering_id requires product")
        if offering_id is not None and offering_id.product is not product:
            raise ValueError("offering does not belong to product")
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
            offering_id=query.offering_id,
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
            offering_id=query.offering_id,
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
            offering_id=query.offering_id,
        )
        if not latest:
            status = HistoryResultStatus.UNAVAILABLE
        elif all(item.previous_accepted_snapshot_id is None for item in latest):
            status = HistoryResultStatus.FIRST_OBSERVATION
        else:
            status = HistoryResultStatus.UNCHANGED_IN_WINDOW
        older = await self._snapshots.get_latest_change_before(
            product=query.product,
            offering_id=query.offering_id,
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


class RunWaitService:
    def __init__(
        self,
        runs: RunServicePort,
        settings: TariffQuerySettings,
        *,
        monotonic_clock: MonotonicClock = monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._runs = runs
        self._settings = settings
        self._monotonic = monotonic_clock
        self._sleep = sleep

    async def wait(
        self,
        run_id: UUID,
        *,
        timeout_seconds: float | None = None,
    ) -> RunWaitResult:
        requested_timeout = (
            self._settings.run_wait_seconds
            if timeout_seconds is None
            else timeout_seconds
        )
        timeout = min(
            requested_timeout,
            self._settings.run_wait_seconds,
        )
        if timeout <= 0:
            raise ValueError("timeout_seconds must be positive")
        started = self._monotonic()
        while True:
            run = await self._runs.get(run_id)
            elapsed = max(0.0, self._monotonic() - started)
            if run is None:
                return RunWaitResult(
                    state=RunWaitState.NOT_FOUND,
                    waited_seconds=elapsed,
                )
            if run.status.is_terminal:
                return RunWaitResult(
                    state=RunWaitState.TERMINAL,
                    run=run,
                    waited_seconds=elapsed,
                )
            if run.status is RunStatus.AWAITING_REVIEW:
                return RunWaitResult(
                    state=RunWaitState.AWAITING_REVIEW,
                    run=run,
                    waited_seconds=elapsed,
                )
            if elapsed >= timeout:
                return RunWaitResult(
                    state=RunWaitState.TIMED_OUT,
                    run=run,
                    waited_seconds=elapsed,
                )
            await self._sleep(min(self._settings.run_poll_seconds, timeout - elapsed))


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
