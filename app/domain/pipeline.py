from __future__ import annotations

from pydantic import Field, model_validator

from app.domain.monitoring import (
    MonitoringModel,
    PublicationResult,
    SnapshotAttempt,
    SourceManifestItem,
)


class StageTiming(MonitoringModel):
    stage: str = Field(min_length=1, max_length=100)
    duration_ms: int = Field(ge=0)


class SourceManifest(MonitoringModel):
    items: tuple[SourceManifestItem, ...]
    source_count: int = Field(ge=0)
    selected_count: int = Field(ge=0)
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    warning_codes: tuple[str, ...] = ()
    failure_codes: tuple[str, ...] = ()
    timings: tuple[StageTiming, ...] = ()

    @model_validator(mode="after")
    def validate_counts(self) -> SourceManifest:
        if self.source_count != len(self.items):
            raise ValueError("source_count must match manifest items")
        if self.selected_count != sum(item.selected for item in self.items):
            raise ValueError("selected_count must match selected manifest items")
        return self


class IndexingRefreshResult(MonitoringModel):
    manifest: SourceManifest
    snapshot: SnapshotAttempt
    publication: PublicationResult
    provenance_changed: bool = False
