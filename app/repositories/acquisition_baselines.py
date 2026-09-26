from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.acquisition import AcquisitionInventory
from app.repositories.acquisition_snapshots import acquisition_url_key


class PostgresAcquisitionBaselineRepository:
    """The last inventory per seed URL that passed the completeness gate."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, url: str) -> AcquisitionInventory | None:
        async with self._session_factory() as session:
            value = await session.scalar(
                text(
                    "SELECT inventory FROM acquisition_baselines WHERE url_key = :key"
                ),
                {"key": acquisition_url_key(url)},
            )
        return AcquisitionInventory.model_validate(value) if value is not None else None

    async def record(
        self, url: str, inventory: AcquisitionInventory, *, recorded_at: datetime
    ) -> None:
        # A reset stamp on the row survives: it is the history of why the
        # baseline before this one was cleared.
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text(
                    """
                    INSERT INTO acquisition_baselines
                        (url_key, source_url, inventory, recorded_at)
                    VALUES (:key, :url, CAST(:inventory AS jsonb), :recorded_at)
                    ON CONFLICT (url_key) DO UPDATE SET
                        source_url = EXCLUDED.source_url,
                        inventory = EXCLUDED.inventory,
                        recorded_at = EXCLUDED.recorded_at,
                        updated_at = now()
                    """
                ),
                {
                    "key": acquisition_url_key(url),
                    "url": url,
                    "inventory": json.dumps(inventory.model_dump(mode="json")),
                    "recorded_at": recorded_at,
                },
            )

    async def reset(
        self,
        url: str,
        *,
        reset_by: str,
        offering_id: str,
        reset_at: datetime | None = None,
    ) -> AcquisitionInventory | None:
        """Clear the baseline so the next passing run records a new one.

        Returns the inventory that was cleared, and writes an audit event in the
        same transaction, so a reset is never silent.
        """
        reset_at = reset_at or datetime.now(UTC)
        key = acquisition_url_key(url)
        async with self._session_factory() as session, session.begin():
            previous = await session.scalar(
                text(
                    "SELECT inventory FROM acquisition_baselines "
                    "WHERE url_key = :key FOR UPDATE"
                ),
                {"key": key},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO acquisition_baselines
                        (url_key, source_url, reset_by, reset_at)
                    VALUES (:key, :url, :reset_by, :reset_at)
                    ON CONFLICT (url_key) DO UPDATE SET
                        inventory = NULL,
                        recorded_at = NULL,
                        reset_by = EXCLUDED.reset_by,
                        reset_at = EXCLUDED.reset_at,
                        updated_at = now()
                    """
                ),
                {"key": key, "url": url, "reset_by": reset_by, "reset_at": reset_at},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO audit_events (event_type, reason_code, payload)
                    VALUES (
                        'acquisition.baseline_reset',
                        'operator_reset',
                        CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "payload": json.dumps(
                        {
                            "offering_id": offering_id,
                            "source_url": url,
                            "reset_by": reset_by,
                            "previous_inventory": previous,
                        }
                    )
                },
            )
        return (
            AcquisitionInventory.model_validate(previous)
            if previous is not None
            else None
        )
