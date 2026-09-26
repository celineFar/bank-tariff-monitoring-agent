from __future__ import annotations

import logging
from typing import Protocol

from app.config import AcquisitionSettings
from app.domain.acquisition import AcquisitionInventory, PageArtifact
from app.repositories.contracts import AcquisitionBaselineRepository
from app.services.acquisition_errors import AcquisitionError, AcquisitionFailure

logger = logging.getLogger(__name__)

_RESET_HINT = (
    "if the bank redesigned the page, accept it with "
    "`python -m scripts.reset_acquisition_baseline <offering_id>`"
)


class AcquisitionPort(Protocol):
    async def acquire(self, url: str) -> PageArtifact: ...


def compare_inventory(
    baseline: AcquisitionInventory,
    current: AcquisitionInventory,
    settings: AcquisitionSettings,
) -> tuple[str, ...]:
    """Why `current` is a sharp drop from the last good acquisition, or ().

    A structure the page had and no longer has -- tables, PDF links, data
    payloads -- always fails: that is what a half-rendered page looks like.
    PDF links and main content also fail on a large relative drop. Growth never
    fails; small shrinkage is ordinary editing.
    """
    reasons: list[str] = []
    for name in ("tables", "pdf_links", "payloads"):
        before, after = getattr(baseline, name), getattr(current, name)
        if before and not after:
            reasons.append(f"{name} {before} -> 0")
    for name, allowed in (
        ("pdf_links", settings.baseline_max_pdf_link_drop),
        ("main_chars", settings.baseline_max_main_content_drop),
    ):
        before, after = getattr(baseline, name), getattr(current, name)
        if before and after and (before - after) / before >= allowed:
            reasons.append(
                f"{name} {before} -> {after} (-{round(100 * (before - after) / before)}%)"
            )
    return tuple(reasons)


class CompletenessGatedAcquisitionService:
    """Fail an acquisition that lost much of what the same page had last time.

    `AcquisitionService` already refuses a page below the absolute floor. This
    adds the page-specific check: each fresh acquisition is compared with the
    last one of the same URL that passed, and a sharp drop fails the offering.
    Only a passing acquisition updates the baseline, so a degraded one can never
    become the reference. A drop keeps failing until an operator resets the
    baseline -- the bank may simply have redesigned the page, and that is a
    human's call, not the pipeline's.
    """

    def __init__(
        self,
        acquisition: AcquisitionPort,
        baselines: AcquisitionBaselineRepository,
        settings: AcquisitionSettings,
    ) -> None:
        self._acquisition = acquisition
        self._baselines = baselines
        self._settings = settings

    async def acquire(self, url: str) -> PageArtifact:
        artifact = await self._acquisition.acquire(url)
        baseline = await self._baselines.get(url)
        if baseline is not None:
            reasons = compare_inventory(baseline, artifact.inventory, self._settings)
            if reasons:
                raise AcquisitionError(
                    AcquisitionFailure.INCOMPLETE_CONTENT,
                    "Acquired page lost content since the last good acquisition "
                    f"({'; '.join(reasons)}); {_RESET_HINT}",
                    reasons=reasons,
                )
        try:
            await self._baselines.record(
                url, artifact.inventory, recorded_at=artifact.retrieved_at
            )
        except Exception:
            # The acquisition passed; failing to move the baseline forward
            # only means the next run compares against an older good one.
            logger.warning(
                "Could not record the acquisition baseline of %s", url, exc_info=True
            )
        return artifact
