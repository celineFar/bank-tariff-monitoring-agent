"""Regression tests for fix/review-and-publication, on PostgreSQL.

Each test names the review finding it covers (P*, see
tests/unit/test_review_publication_fixes.py). They need TEST_DATABASE_URL, like
the other PostgreSQL integration tests, and skip without it.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.reviews import PostgresReviewRepository
from tests.integration import test_monitoring_repository_postgres as repository_tests
from tests.integration.test_indexing_fixes_postgres import _doc, _publish, _review

monitoring_database_engine = repository_tests.monitoring_database_engine
monitoring_session_factory = repository_tests.monitoring_session_factory

pytestmark = pytest.mark.postgres


async def _states(session_factory, snapshot_id: UUID) -> tuple[str, str, str | None]:
    """(snapshot status, execution status, execution stage) of one snapshot."""
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT s.status, e.status, e.current_stage
                    FROM tariff_snapshots AS s
                    JOIN offering_executions AS e ON e.id = s.offering_execution_id
                    WHERE s.id = :id
                    """
                ),
                {"id": snapshot_id},
            )
        ).one()
    return row[0], row[1], row[2]


@pytest.mark.asyncio
async def test_p3_superseding_the_last_review_closes_the_candidate(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    candidate = await _publish(
        monitoring_session_factory, lambda run_id: [_doc(run_id)], accepted=False
    )
    review = await _review(monitoring_session_factory, candidate, "p3-direct")

    await PostgresReviewRepository(monitoring_session_factory).supersede(review.id)

    assert await _states(monitoring_session_factory, candidate.id) == (
        "rejected",
        "failed",
        "review_superseded",
    )


@pytest.mark.asyncio
async def test_p3_a_newer_review_of_the_field_closes_the_older_candidate(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    older = await _publish(
        monitoring_session_factory, lambda run_id: [_doc(run_id)], accepted=False
    )
    await _review(monitoring_session_factory, older, "p3-older")
    newer = await _publish(
        monitoring_session_factory, lambda run_id: [_doc(run_id)], accepted=False
    )

    await _review(monitoring_session_factory, newer, "p3-newer")

    assert (await _states(monitoring_session_factory, older.id))[0] == "rejected"
    assert (await _states(monitoring_session_factory, newer.id))[0] == (
        "review_required"
    )


@pytest.mark.asyncio
async def test_p3_a_newer_accepted_publication_closes_the_waiting_candidate(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    older = await _publish(
        monitoring_session_factory, lambda run_id: [_doc(run_id)], accepted=False
    )
    await _review(monitoring_session_factory, older, "p3-accepted")

    await _publish(monitoring_session_factory, lambda run_id: [_doc(run_id)])

    assert await _states(monitoring_session_factory, older.id) == (
        "rejected",
        "failed",
        "review_superseded",
    )
