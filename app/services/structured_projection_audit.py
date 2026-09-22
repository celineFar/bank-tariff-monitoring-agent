"""Read-only checks of stored facts against accepted canonical extraction."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.structured_tariffs import FieldPath, TariffFact
from app.repositories.monitoring import _snapshot_from_row
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
)
from app.services.structured_projection import StructuredTariffProjector


def _comparable_fact(fact: TariffFact) -> dict:
    data = fact.model_dump(mode="json")
    if fact.number is not None:
        data["number"] = str(fact.number.normalize())
    for evidence in data["evidence"]:
        evidence.pop("document_id", None)
        evidence.pop("document_checksum", None)
    return data


@dataclass(frozen=True)
class ProjectionAuditResult:
    snapshot_id: UUID
    status: str
    expected_facts: int
    stored_facts: int
    missing_fact_ids: tuple[str, ...] = ()
    extra_fact_ids: tuple[str, ...] = ()
    altered_fact_ids: tuple[str, ...] = ()
    reason: str | None = None


class StructuredProjectionAuditor:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions
        self._reader = PostgresStructuredTariffQueryRepository(sessions)
        self._projector = StructuredTariffProjector()

    async def audit_snapshot(self, snapshot_id: UUID) -> ProjectionAuditResult:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT * FROM tariff_snapshots "
                        "WHERE id = :id AND status = 'accepted'"
                    ),
                    {"id": snapshot_id},
                )
            ).first()
        if row is None:
            raise ValueError("accepted snapshot not found")
        snapshot = _snapshot_from_row(row)
        try:
            expected = self._projector.project(
                snapshot,
                display_name=snapshot.offering_id.value.replace("_", " ").title(),
            )
        except ValueError as exc:
            return ProjectionAuditResult(
                snapshot_id=snapshot_id,
                status="unprojectable",
                expected_facts=0,
                stored_facts=0,
                reason=str(exc),
            )
        try:
            actual = await self._reader.facts(
                snapshots=(snapshot_id,),
                fields=tuple(FieldPath),
                include_inactive=True,
            )
        except ValueError as exc:
            return ProjectionAuditResult(
                snapshot_id=snapshot_id,
                status="evidence_mismatch",
                expected_facts=len(expected.facts),
                stored_facts=0,
                reason=str(exc),
            )
        expected_by_id = {
            fact.fact_id: _comparable_fact(fact) for fact in expected.facts
        }
        actual_by_id = {fact.fact_id: _comparable_fact(fact) for fact in actual}
        missing = tuple(sorted(set(expected_by_id) - set(actual_by_id)))
        extra = tuple(sorted(set(actual_by_id) - set(expected_by_id)))
        altered = tuple(
            sorted(
                fact_id
                for fact_id in set(expected_by_id) & set(actual_by_id)
                if expected_by_id[fact_id] != actual_by_id[fact_id]
            )
        )
        return ProjectionAuditResult(
            snapshot_id=snapshot_id,
            status="matched" if not (missing or extra or altered) else "mismatch",
            expected_facts=len(expected.facts),
            stored_facts=len(actual),
            missing_fact_ids=missing,
            extra_fact_ids=extra,
            altered_fact_ids=altered,
        )
