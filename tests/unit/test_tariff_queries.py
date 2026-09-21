from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.config.models import TariffQuerySettings
from app.config.seed_catalog import load_seed_catalog
from app.domain.intent import HistoryQuery, HistoryRequestKind
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    MonitoringRun,
    RunCommand,
    RunStatus,
    RunTrigger,
    SnapshotAttempt,
    SnapshotChange,
    SnapshotChangeSet,
    SnapshotStatus,
)
from app.domain.review import ReviewCorrelation, ReviewReason, ReviewStatus, ReviewTask
from app.domain.tariff_queries import HistoryResultStatus, RunWaitState
from app.services.tariff_queries import (
    CurrentTariffService,
    RunWaitService,
    TariffHistoryService,
)

NOW = datetime(2026, 9, 20, 12, tzinfo=UTC)


def _snapshot(
    offering_id: OfferingId,
    *,
    accepted_at: datetime,
    previous: UUID | None = None,
) -> SnapshotAttempt:
    return SnapshotAttempt(
        id=uuid4(),
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=offering_id.product,
        offering_id=offering_id,
        status=SnapshotStatus.ACCEPTED,
        normalized_tariff={"nominal_rate": "12.5%"},
        evidence=({"url": "https://ameriabank.am/tariff", "excerpt": "12.5%"},),
        canonical_sha256="a" * 64,
        previous_accepted_snapshot_id=previous,
        created_at=accepted_at,
        accepted_at=accepted_at,
    )


def _change(created_at: datetime) -> SnapshotChangeSet:
    return SnapshotChangeSet(
        id=uuid4(),
        run_id=uuid4(),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_EXPRESS,
        previous_snapshot_id=uuid4(),
        current_snapshot_id=uuid4(),
        changes=(
            SnapshotChange(field="nominal_rate", previous="11%", current="12.5%"),
        ),
        created_at=created_at,
    )


class _Snapshots:
    def __init__(self) -> None:
        self.latest: tuple[SnapshotAttempt, ...] = ()
        self.history: tuple[SnapshotAttempt, ...] = ()
        self.changes: tuple[SnapshotChangeSet, ...] = ()
        self.older: SnapshotChangeSet | None = None
        self.pending: set[OfferingId] = set()
        self.history_calls: list[dict[str, object]] = []
        self.change_calls: list[dict[str, object]] = []

    async def list_latest_accepted(self, **kwargs):
        product = kwargs.get("product")
        offering_id = kwargs.get("offering_id")
        return tuple(
            item
            for item in self.latest
            if (product is None or item.product is product)
            and (offering_id is None or item.offering_id is offering_id)
        )

    async def has_newer_pending_review(self, **kwargs):
        return kwargs["offering_id"] in self.pending

    async def list_accepted_history(self, **kwargs):
        self.history_calls.append(kwargs)
        return self.history

    async def list_changes(self, **kwargs):
        self.change_calls.append(kwargs)
        return self.changes

    async def get_latest_change_before(self, **kwargs):
        return self.older


@pytest.mark.asyncio
async def test_current_tariffs_classify_fresh_stale_missing_and_hide_pending() -> None:
    repository = _Snapshots()
    repository.latest = (
        _snapshot(
            OfferingId.CONSUMER_STANDARD,
            accepted_at=NOW - timedelta(days=7),
        ),
        _snapshot(
            OfferingId.CREDIT_LINE,
            accepted_at=NOW - timedelta(days=8),
        ),
    )
    repository.pending.add(OfferingId.CREDIT_LINE)
    service = CurrentTariffService(
        load_seed_catalog(),
        repository,
        TariffQuerySettings(),
        clock=lambda: NOW,
    )

    result = await service.get_current(product=ProductType.CONSUMER_LOAN)
    items = {item.offering_id: item for item in result.items}

    assert items[OfferingId.CONSUMER_STANDARD].freshness.value == "fresh"
    assert items[OfferingId.CREDIT_LINE].freshness.value == "stale"
    assert items[OfferingId.CREDIT_LINE].pending_newer_review is True
    assert items[OfferingId.OVERDRAFT].freshness.value == "missing"
    assert items[OfferingId.OVERDRAFT].normalized_tariff is None
    assert len(result.items) == 4


@pytest.mark.asyncio
async def test_what_changed_uses_sixty_days_and_reports_changes() -> None:
    repository = _Snapshots()
    repository.changes = (_change(NOW - timedelta(days=5)),)
    result = await TariffHistoryService(
        repository,
        TariffQuerySettings(),
        clock=lambda: NOW,
    ).query(
        HistoryQuery(
            kind=HistoryRequestKind.WHAT_CHANGED,
            product=ProductType.MORTGAGE,
        )
    )

    assert result.status is HistoryResultStatus.CHANGES_FOUND
    assert result.window_start == NOW - timedelta(days=60)
    assert result.changes == repository.changes
    assert repository.change_calls[0]["limit"] == 20


@pytest.mark.asyncio
async def test_what_changed_distinguishes_first_unchanged_old_and_unavailable() -> None:
    repository = _Snapshots()
    first = _snapshot(OfferingId.MORTGAGE_EXPRESS, accepted_at=NOW)
    repository.latest = (first,)
    service = TariffHistoryService(repository, TariffQuerySettings(), clock=lambda: NOW)
    query = HistoryQuery(kind=HistoryRequestKind.WHAT_CHANGED)

    first_result = await service.query(query)
    repository.latest = (
        first.model_copy(update={"previous_accepted_snapshot_id": uuid4()}),
    )
    repository.older = _change(NOW - timedelta(days=90))
    unchanged = await service.query(query)
    repository.latest = ()
    unavailable = await service.query(query)

    assert first_result.status is HistoryResultStatus.FIRST_OBSERVATION
    assert unchanged.status is HistoryResultStatus.UNCHANGED_IN_WINDOW
    assert unchanged.last_change_before_window_at == NOW - timedelta(days=90)
    assert unavailable.status is HistoryResultStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_show_history_defaults_to_thirty_days() -> None:
    repository = _Snapshots()
    repository.history = (
        _snapshot(OfferingId.MORTGAGE_EXPRESS, accepted_at=NOW - timedelta(days=1)),
    )

    result = await TariffHistoryService(
        repository,
        TariffQuerySettings(),
        clock=lambda: NOW,
    ).query(HistoryQuery(kind=HistoryRequestKind.SHOW_HISTORY))

    assert result.window_start == NOW - timedelta(days=30)
    assert result.status is HistoryResultStatus.FIRST_OBSERVATION


def _run(status: RunStatus) -> MonitoringRun:
    return MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.MORTGAGE,
            trigger=RunTrigger.ADK,
        ),
        status=status,
        queued_at=NOW,
        started_at=NOW if status is not RunStatus.QUEUED else None,
        completed_at=NOW if status.is_terminal else None,
    )


class _Runs:
    def __init__(self, values: list[MonitoringRun | None]) -> None:
        self.values = values

    async def get(self, run_id: UUID) -> MonitoringRun | None:
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


class _Timer:
    def __init__(self) -> None:
        self.value = 0.0

    def now(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        self.value += seconds


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("final_status", "expected"),
    [
        (RunStatus.SUCCEEDED, RunWaitState.TERMINAL),
        (RunStatus.AWAITING_REVIEW, RunWaitState.AWAITING_REVIEW),
    ],
)
async def test_run_wait_stops_on_terminal_or_review(
    final_status: RunStatus,
    expected: RunWaitState,
) -> None:
    timer = _Timer()
    service = RunWaitService(
        _Runs([_run(RunStatus.RUNNING), _run(final_status)]),
        TariffQuerySettings(run_poll_seconds=1),
        monotonic_clock=timer.now,
        sleep=timer.sleep,
    )

    result = await service.wait(uuid4())

    assert result.state is expected
    assert result.waited_seconds == 1


@pytest.mark.asyncio
async def test_run_wait_delivers_attached_review_session_and_scopes() -> None:
    run = _run(RunStatus.AWAITING_REVIEW)
    review = ReviewTask(
        id=uuid4(),
        idempotency_key="review:test:1",
        run_id=run.id,
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        reason=ReviewReason.MISSING_REQUIRED_FIELD,
        issue_scope="interest_rate",
        candidates=(),
        status=ReviewStatus.PENDING,
        correlation=ReviewCorrelation(
            app_name="tariff_monitoring_workflow",
            user_id="monitoring-adk",
            session_id=f"monitoring-run-{run.id}",
            invocation_id="invocation-1",
            interrupt_id=f"monitoring-review:{run.id}",
        ),
        created_at=NOW,
        updated_at=NOW,
    )
    run = run.model_copy(update={"summary": {"review_ids": [str(review.id)]}})

    class _Reviews:
        def __init__(self) -> None:
            self.calls = 0

        async def list(self, **kwargs):
            assert kwargs["run_id"] == run.id
            self.calls += 1
            if self.calls == 1:
                return (review.model_copy(update={"correlation": None}),)
            return (review,)

    timer = _Timer()
    reviews = _Reviews()
    result = await RunWaitService(
        _Runs([run]),
        TariffQuerySettings(run_poll_seconds=1),
        reviews=reviews,
        monotonic_clock=timer.now,
        sleep=timer.sleep,
    ).wait(run.id)

    assert reviews.calls == 2
    assert result.waited_seconds == 1
    assert result.state is RunWaitState.AWAITING_REVIEW
    assert result.review_handoff is not None
    assert result.review_handoff.ready is True
    assert result.review_handoff.pending[0].issue_scope == "interest_rate"
    assert result.review_handoff.review_url == (
        "/dev-ui/?app=tariff_monitoring_workflow&userId=monitoring-adk&"
        f"session=monitoring-run-{run.id}"
    )
    assert result.review_handoff.reviews_url == (
        f"/api/v1/reviews?run_id={run.id}"
    )


@pytest.mark.asyncio
async def test_run_wait_returns_incomplete_envelope_at_timeout() -> None:
    timer = _Timer()
    service = RunWaitService(
        _Runs([_run(RunStatus.RUNNING)]),
        TariffQuerySettings(run_wait_seconds=2, run_poll_seconds=1),
        monotonic_clock=timer.now,
        sleep=timer.sleep,
    )

    result = await service.wait(uuid4())

    assert result.state is RunWaitState.TIMED_OUT
    assert result.run is not None
    assert result.run.status is RunStatus.RUNNING
    assert result.waited_seconds == 2


@pytest.mark.asyncio
async def test_current_and_history_http_endpoints_have_typed_parity() -> None:
    repository = _Snapshots()
    repository.latest = (_snapshot(OfferingId.MORTGAGE_EXPRESS, accepted_at=NOW),)
    app = FastAPI()
    app.state.current_tariff_service = CurrentTariffService(
        load_seed_catalog(),
        repository,
        TariffQuerySettings(),
        clock=lambda: NOW,
    )
    app.state.tariff_history_service = TariffHistoryService(
        repository,
        TariffQuerySettings(),
        clock=lambda: NOW,
    )
    app.include_router(router)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        current = await client.get(
            "/api/v1/tariffs/current",
            params={"product": "mortgage", "offering_id": "mortgage_express"},
        )
        history = await client.get(
            "/api/v1/tariffs/history",
            params={"kind": "what_changed", "product": "mortgage"},
        )

    assert current.status_code == 200
    assert current.json()["items"][0]["freshness"] == "fresh"
    assert history.status_code == 200
    assert history.json()["status"] == "first_observation"
