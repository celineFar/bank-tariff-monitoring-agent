from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.domain.acquisition import (
    AcquisitionWarningCode,
    PageArtifact,
    StoredArtifact,
)
from app.repositories.contracts import AcquisitionSnapshotRepository
from app.services.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer()


class AcquisitionPort(Protocol):
    async def acquire(self, url: str) -> PageArtifact: ...


class ArtifactReader(Protocol):
    async def read(self, artifact: StoredArtifact) -> bytes: ...


class FreshnessGatedAcquisitionService:
    """Reuse a recent acquisition instead of fetching the bank again.

    A monitoring run re-asked minutes after the last one is asking about the
    same published page. Within the configured window this serves the stored
    page artifact, so the run skips the fetch, the browser render and the linked
    downloads. Only acquisition is skipped: normalization, discovery, extraction
    and indexing still execute, and because the reused artifact carries the same
    content hashes as before, each of them resolves from its own
    content-addressed cache rather than calling a model.

    Outside the window, or when the stored artifact's downloads are no longer on
    disk, this acquires normally. Reuse is never a fallback for a failed
    acquisition: a fetch that fails must fail the offering, because serving
    yesterday's tariffs as today's is the one outcome this system may not have.
    Nor is a partial one stored for reuse: an acquisition whose linked PDFs
    failed to download is used once and fetched again next time.
    """

    def __init__(
        self,
        acquisition: AcquisitionPort,
        snapshots: AcquisitionSnapshotRepository,
        *,
        freshness_hours: float,
        artifact_reader: ArtifactReader | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._acquisition = acquisition
        self._snapshots = snapshots
        self._window = timedelta(hours=freshness_hours)
        self._artifact_reader = artifact_reader
        self._now = now

    async def acquire(self, url: str) -> PageArtifact:
        with tracer.start_as_current_span("acquisition freshness") as span:
            span.set_attribute(
                "tariff.acquisition.freshness_hours",
                self._window.total_seconds() / 3600,
            )
            reusable = await self._reusable(url)
            span.set_attribute("tariff.acquisition.reused", reusable is not None)
            if reusable is not None:
                span.set_attribute(
                    "tariff.acquisition.content_hash", reusable.content_hash
                )
                return reusable.model_copy(update={"reused": True})
            artifact = await self._acquisition.acquire(url)
            span.set_attribute("tariff.acquisition.content_hash", artifact.content_hash)
        if self._reusable_later(artifact):
            await self._remember(url, artifact)
        return artifact

    @staticmethod
    def _reusable_later(artifact: PageArtifact) -> bool:
        """Whether serving this artifact again would repeat a complete fetch.

        An acquisition reaching here passed the completeness gate, but one whose
        linked PDFs failed to download is still partial: reusing it would carry
        the gap into every run in the window instead of retrying the download.
        A link that is simply dead (`linked_document_missing`, HTTP 404) does
        not count: it is the same on every fetch, and refusing reuse over it
        would refetch the page and all its PDFs on every run for nothing.
        """
        partial = any(
            warning.code is AcquisitionWarningCode.LINKED_DOCUMENT_FAILED
            for warning in artifact.warnings
        )
        if partial:
            logger.info(
                "Not storing the acquisition of %s for reuse: "
                "some linked documents failed to download",
                artifact.url,
            )
        return not partial

    async def _reusable(self, url: str) -> PageArtifact | None:
        if not self._window:
            return None
        try:
            stored = await self._snapshots.get_latest(url)
        except Exception:
            # Reuse is an optimisation. A lookup that fails must cost a fetch,
            # never the run.
            logger.warning(
                "Acquisition freshness lookup failed for %s", url, exc_info=True
            )
            return None
        if stored is None:
            return None
        age = self._now() - stored.retrieved_at
        if age < timedelta(0) or age > self._window:
            logger.info(
                "Re-acquiring %s: stored acquisition is %s old, window is %s",
                url,
                age,
                self._window,
            )
            return None
        if not await self._downloads_readable(stored):
            logger.info(
                "Re-acquiring %s: stored linked documents are no longer readable", url
            )
            return None
        logger.info(
            "Reusing the acquisition of %s from %s (%s old, content hash %s)",
            url,
            stored.retrieved_at.isoformat(),
            age,
            stored.content_hash[:12],
        )
        return stored

    async def _downloads_readable(self, artifact: PageArtifact) -> bool:
        """Confirm normalization can still read what the stored artifact cites.

        The page's own markup travels inside the artifact, but its linked PDFs
        live in the artifact store, which is temporary storage. Reusing an
        artifact whose downloads have been swept would silently normalize the
        page without its tariff documents.
        """
        if self._artifact_reader is None:
            return not artifact.downloadable_documents
        for document in artifact.downloadable_documents:
            try:
                await self._artifact_reader.read(document.artifact)
            except Exception:
                return False
        return True

    async def _remember(self, url: str, artifact: PageArtifact) -> None:
        try:
            await self._snapshots.save(url, artifact)
        except Exception:
            # The acquisition succeeded; failing to record it for reuse costs a
            # future fetch, not this run.
            logger.warning(
                "Could not store the acquisition of %s for reuse", url, exc_info=True
            )
