from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from app.domain.intent import FreshnessStatus, HistoryQuery
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    SnapshotAttempt,
    SnapshotChangeSet,
    validate_offering_product,
)


class QueryModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class CurrentTariffItem(QueryModel):
    product: ProductType
    offering_id: OfferingId
    freshness: FreshnessStatus
    snapshot_id: UUID | None = None
    accepted_at: datetime | None = None
    age_seconds: float | None = Field(default=None, ge=0)
    normalized_tariff: dict[str, JsonValue] | None = None
    evidence: tuple[dict[str, JsonValue], ...] = ()
    pending_newer_review: bool = False

    @model_validator(mode="after")
    def validate_state(self) -> CurrentTariffItem:
        validate_offering_product(self.product, self.offering_id)
        accepted_fields = (
            self.snapshot_id,
            self.accepted_at,
            self.age_seconds,
            self.normalized_tariff,
        )
        if self.freshness is FreshnessStatus.MISSING:
            if any(value is not None for value in accepted_fields) or self.evidence:
                raise ValueError("missing current tariff cannot expose snapshot values")
        elif any(value is None for value in accepted_fields):
            raise ValueError(
                "fresh or stale current tariff requires accepted snapshot data"
            )
        return self


class CurrentTariffResult(QueryModel):
    bank: str = Field(default="ameria", min_length=1, max_length=100)
    as_of: datetime
    items: tuple[CurrentTariffItem, ...]


class HistoryResultStatus(StrEnum):
    CHANGES_FOUND = "changes_found"
    HISTORY_FOUND = "history_found"
    FIRST_OBSERVATION = "first_observation"
    UNCHANGED_IN_WINDOW = "unchanged_in_window"
    UNAVAILABLE = "unavailable"


class TariffHistoryResult(QueryModel):
    query: HistoryQuery
    status: HistoryResultStatus
    window_start: datetime
    window_end: datetime
    snapshots: tuple[SnapshotAttempt, ...] = ()
    changes: tuple[SnapshotChangeSet, ...] = ()
    last_change_before_window_at: datetime | None = None
