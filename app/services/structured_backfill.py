"""Rebuild accepted tariff projections by offering, without model calls."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.monitoring import SnapshotAttempt
from app.repositories.monitoring import _snapshot_from_row
from app.repositories.structured_projection import publish_structured_projection
from app.services.structured_projection import StructuredTariffProjector


@dataclass(frozen=True)
class BackfillIssue:
    snapshot_id: UUID
    reason: str


@dataclass(frozen=True)
class BackfillScopeResult:
    bank: str
    product: str
    offering_id: str
    examined: int
    projectable: int
    published: int
    active_snapshot_id: UUID | None
    issues: tuple[BackfillIssue, ...]


class StructuredProjectionBackfill:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions
        self._projector = StructuredTariffProjector()

    async def scopes(self) -> tuple[tuple[str, str, str], ...]:
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    text(
                        """SELECT DISTINCT bank, product, offering_id
                        FROM tariff_snapshots WHERE status = 'accepted'
                        ORDER BY bank, product, offering_id"""
                    )
                )
            ).all()
        return tuple((row.bank, row.product, row.offering_id) for row in rows)

    async def run_scope(
        self,
        bank: str,
        product: str,
        offering_id: str,
        *,
        batch_size: int = 50,
        apply: bool = False,
    ) -> BackfillScopeResult:
        if not 1 <= batch_size <= 500:
            raise ValueError("batch_size must be 1..500")
        scope = {
            "bank": bank.lower(),
            "product": product,
            "offering_id": offering_id,
        }
        examined = projectable = published = 0
        latest_id: UUID | None = None
        latest_projectable = False
        issues: list[BackfillIssue] = []
        async with self._sessions() as session, session.begin():
            if apply:
                await session.execute(
                    text(
                        "SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"
                    ),
                    {
                        "lock_key": (
                            f"publication:{scope['bank']}:{product}:{offering_id}"
                        )
                    },
                )
            offset = 0
            while True:
                rows = (
                    await session.execute(
                        text(
                            """SELECT * FROM tariff_snapshots
                            WHERE bank = :bank AND product = :product
                              AND offering_id = :offering_id AND status = 'accepted'
                            ORDER BY accepted_at, created_at, id
                            LIMIT :batch_size OFFSET :offset"""
                        ),
                        {**scope, "batch_size": batch_size, "offset": offset},
                    )
                ).all()
                if not rows:
                    break
                for row in rows:
                    snapshot: SnapshotAttempt = _snapshot_from_row(row)
                    examined += 1
                    latest_id = snapshot.id
                    try:
                        self._projector.project(
                            snapshot,
                            display_name=snapshot.offering_id.value.replace(
                                "_", " "
                            ).title(),
                        )
                    except ValueError as exc:
                        latest_projectable = False
                        issues.append(
                            BackfillIssue(
                                snapshot_id=snapshot.id,
                                reason=type(exc).__name__ + ": " + str(exc),
                            )
                        )
                        continue
                    projectable += 1
                    latest_projectable = True
                    if apply:
                        await publish_structured_projection(session, snapshot)
                        published += 1
                offset += len(rows)
            if apply and examined:
                # Repeated publication above is invisible outside this transaction.
                # Leave only the newest accepted snapshot active, or none if its
                # extraction cannot pass the current evidence contract.
                for table in ("retrieval_units", "tariff_facts"):
                    await session.execute(
                        text(
                            f"""UPDATE {table} SET is_active = false
                            WHERE snapshot_id IN (
                                SELECT snapshot_id FROM offering_profiles
                                WHERE bank = :bank AND product = :product
                                  AND offering_id = :offering_id
                            )"""
                        ),
                        scope,
                    )
                await session.execute(
                    text(
                        """UPDATE offering_profiles SET is_active = false
                        WHERE bank = :bank AND product = :product
                          AND offering_id = :offering_id"""
                    ),
                    scope,
                )
                if latest_projectable and latest_id is not None:
                    for table in (
                        "offering_profiles",
                        "tariff_facts",
                        "retrieval_units",
                    ):
                        await session.execute(
                            text(
                                f"UPDATE {table} SET is_active = true "
                                "WHERE snapshot_id = :snapshot_id"
                            ),
                            {"snapshot_id": latest_id},
                        )
        return BackfillScopeResult(
            bank=scope["bank"],
            product=product,
            offering_id=offering_id,
            examined=examined,
            projectable=projectable,
            published=published,
            active_snapshot_id=(latest_id if latest_projectable else None),
            issues=tuple(issues),
        )
