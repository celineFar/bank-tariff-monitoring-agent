"""Superseding pending reviews that a newer accepted snapshot made moot (IX4).

Shared by the offering publication repository (an accepted run) and the review
repository; runs inside the caller's transaction, under the offering's
publication lock.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge_publication import discard_snapshot_documents


async def supersede_reviews_older_than(
    session: AsyncSession, snapshot_id: UUID, now: datetime
) -> tuple[UUID, ...]:
    """Supersede pending reviews of the offering's snapshots older than this one.

    Approving one of them would roll the offering back to older values, so they
    are closed as the existing supersede path closes a review: status
    `superseded`, a `review.superseded` audit event, and the old snapshot's
    never-published documents discarded. Returns the superseded review ids.
    """
    rows = (
        await session.execute(
            text(
                """
                WITH current AS (
                    SELECT lower(bank) AS bank, product, offering_id, created_at
                    FROM tariff_snapshots
                    WHERE id = :snapshot_id
                )
                UPDATE human_reviews AS review
                SET status = 'superseded', updated_at = :now
                FROM tariff_snapshots AS older, current
                WHERE review.snapshot_id = older.id
                  AND review.status = 'pending'
                  AND older.id <> :snapshot_id
                  AND lower(older.bank) = current.bank
                  AND older.product = current.product
                  AND older.offering_id = current.offering_id
                  AND older.created_at < current.created_at
                RETURNING review.id, review.run_id, review.offering_execution_id,
                          review.snapshot_id
                """
            ),
            {"snapshot_id": snapshot_id, "now": now},
        )
    ).all()
    for row in rows:
        await session.execute(
            text(
                """
                INSERT INTO audit_events (
                    run_id, offering_execution_id, event_type, payload
                )
                VALUES (
                    :run_id, :offering_execution_id, 'review.superseded',
                    CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "run_id": row.run_id,
                "offering_execution_id": row.offering_execution_id,
                "payload": json.dumps(
                    {
                        "review_id": str(row.id),
                        "replacement_snapshot_id": str(snapshot_id),
                        "reason": "newer_accepted_snapshot",
                    }
                ),
            },
        )
    for older_snapshot_id in dict.fromkeys(row.snapshot_id for row in rows):
        await discard_snapshot_documents(session, older_snapshot_id)
    return tuple(row.id for row in rows)


async def newer_accepted_snapshot_exists(
    session: AsyncSession, snapshot_id: UUID
) -> bool:
    """An accepted snapshot of the same offering was created after this one."""
    return bool(
        await session.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM tariff_snapshots AS newer
                    JOIN tariff_snapshots AS current ON current.id = :snapshot_id
                    WHERE newer.status = 'accepted'
                      AND newer.id <> current.id
                      AND lower(newer.bank) = lower(current.bank)
                      AND newer.product = current.product
                      AND newer.offering_id = current.offering_id
                      AND newer.created_at > current.created_at
                )
                """
            ),
            {"snapshot_id": snapshot_id},
        )
    )
