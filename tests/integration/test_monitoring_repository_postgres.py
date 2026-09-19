import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.domain.knowledge import (
    EMBEDDING_DIMENSIONS,
    EmbeddedKnowledgeChunk,
    EmbeddedKnowledgeDocument,
)
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    ManifestItemStatus,
    OfferingPublication,
    OfferingRunStatus,
    RunCommand,
    RunStatus,
    RunTrigger,
    SnapshotAttempt,
    SnapshotStatus,
    SourceManifestItem,
)
from app.repositories.monitoring import (
    PostgresOfferingPublicationRepository,
    PostgresRunRepository,
    PostgresSnapshotRepository,
)

pytestmark = pytest.mark.postgres


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    database_name = make_url(database_url).database or ""
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must target a database ending in '_test'")
    return database_url


@pytest_asyncio.fixture(scope="session")
async def monitoring_database_engine() -> AsyncIterator[AsyncEngine]:
    database_url = _test_database_url()
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        await connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        for migration in sorted(Path("migrations").glob("*.sql")):
            await connection.execute(migration.read_text(encoding="utf-8"))
    finally:
        await connection.close()

    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def monitoring_session_factory(
    monitoring_database_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    async with monitoring_database_engine.begin() as connection:
        await connection.execute(text("TRUNCATE monitoring_runs CASCADE"))
    yield async_sessionmaker(monitoring_database_engine, expire_on_commit=False)


def _command(
    product: ProductType = ProductType.CONSUMER_LOAN,
    offering_id: OfferingId | None = None,
) -> RunCommand:
    return RunCommand(
        product=product,
        offering_id=offering_id,
        trigger=RunTrigger.API,
    )


def _document(
    run_id,
    *,
    checksum: str = "a" * 64,
    document_key: str = "consumer-standard-page",
    dimensions: int = EMBEDDING_DIMENSIONS,
) -> EmbeddedKnowledgeDocument:
    return EmbeddedKnowledgeDocument(
        run_id=run_id,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        document_key=document_key,
        document_name="Consumer Loans",
        source_url="https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
        final_url="https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
        mime_type="text/html",
        content_sha256=checksum,
        retrieved_at=datetime.now(UTC),
        extraction_method="browser",
        quality_score=0.99,
        chunks=(
            EmbeddedKnowledgeChunk(
                ordinal=0,
                content="Nominal interest rate: 13.5%",
                section="Rates",
                language="en",
                extraction_method="browser",
                quality_score=0.99,
                embedding=tuple(0.01 for _ in range(dimensions)),
            ),
        ),
    )


async def _running_offering(
    session_factory: async_sessionmaker[AsyncSession],
):
    repository = PostgresRunRepository(session_factory)
    submitted = await repository.submit(
        _command(offering_id=OfferingId.CONSUMER_STANDARD)
    )
    claimed = await repository.claim_next("test-worker")
    assert claimed is not None
    execution = await repository.create_offering_execution(
        submitted.run.id,
        ProductType.CONSUMER_LOAN,
        OfferingId.CONSUMER_STANDARD,
    )
    execution = await repository.start_offering_execution(execution.id)
    return repository, claimed.run, execution


def _snapshot(run_id, execution_id) -> SnapshotAttempt:
    now = datetime.now(UTC)
    return SnapshotAttempt(
        id=uuid4(),
        run_id=run_id,
        offering_execution_id=execution_id,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        status=SnapshotStatus.ACCEPTED,
        normalized_tariff={"nominal_interest_rate": "13.5%"},
        evidence=(
            {
                "source_url": "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
                "excerpt": "Nominal interest rate: 13.5%",
            },
        ),
        semantic_extraction={"status": "completed"},
        validation={"decision": "accept"},
        canonical_sha256="c" * 64,
        created_at=now,
        accepted_at=now,
    )


def _manifest(run_id, execution_id) -> SourceManifestItem:
    return SourceManifestItem(
        id=uuid4(),
        run_id=run_id,
        offering_execution_id=execution_id,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        source_url="https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
        final_url="https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
        document_key="consumer-standard-page",
        content_sha256="a" * 64,
        status=ManifestItemStatus.INDEXED,
        selected=True,
    )


@pytest.mark.asyncio
async def test_submission_is_idempotent_and_reuses_active_family_run(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = PostgresRunRepository(monitoring_session_factory)

    first, repeated = await asyncio.gather(
        repository.submit(_command(), idempotency_key="same-request"),
        repository.submit(_command(), idempotency_key="same-request"),
    )
    active = await repository.submit(_command(), idempotency_key="new-request")
    mortgage = await repository.submit(
        _command(ProductType.MORTGAGE),
        idempotency_key="mortgage-request",
    )

    with pytest.raises(ValueError, match="must not be blank"):
        await repository.submit(_command(), idempotency_key="   ")

    assert {first.run.id, repeated.run.id} == {first.run.id}
    assert first.created != repeated.created
    assert active.created is False
    assert active.run.id == first.run.id
    assert mortgage.created is True
    assert mortgage.run.id != first.run.id


@pytest.mark.asyncio
async def test_queue_claim_is_skip_locked_and_restart_safe(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    submitter = PostgresRunRepository(monitoring_session_factory)
    consumer = await submitter.submit(_command())
    mortgage = await submitter.submit(_command(ProductType.MORTGAGE))

    restarted_worker = PostgresRunRepository(monitoring_session_factory)
    first, second = await asyncio.gather(
        restarted_worker.claim_next("worker-a"),
        restarted_worker.claim_next("worker-b"),
    )

    assert first is not None
    assert second is not None
    assert {first.run.id, second.run.id} == {consumer.run.id, mortgage.run.id}
    assert await restarted_worker.claim_next("worker-c") is None


@pytest.mark.asyncio
async def test_abandoned_running_run_is_failed_and_family_can_restart(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = PostgresRunRepository(monitoring_session_factory)
    submitted = await repository.submit(_command())
    claimed = await repository.claim_next("lost-worker")
    assert claimed is not None
    async with monitoring_session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                UPDATE monitoring_runs
                SET claimed_at = now() - interval '2 hours'
                WHERE id = :id
                """
            ),
            {"id": submitted.run.id},
        )

    recovered = await repository.recover_abandoned(
        before=datetime.now(UTC) - timedelta(minutes=30)
    )
    failed = await repository.get(submitted.run.id)
    replacement = await repository.submit(_command())

    assert recovered == 1
    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.failure_code == "run.abandoned"
    assert replacement.created is True
    assert replacement.run.id != submitted.run.id


@pytest.mark.asyncio
async def test_latest_accepted_snapshot_is_offering_scoped(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_repository, run, execution = await _running_offering(monitoring_session_factory)
    snapshot_repository = PostgresSnapshotRepository(monitoring_session_factory)
    snapshot = _snapshot(run.id, execution.id)
    await snapshot_repository.save_attempt(snapshot)
    await run_repository.finish(run.id, RunStatus.SUCCEEDED)

    next_run = await run_repository.submit(
        _command(offering_id=OfferingId.CONSUMER_STANDARD)
    )
    latest = await snapshot_repository.get_latest_accepted(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        before_run_id=next_run.run.id,
    )

    assert latest is not None
    assert latest.id == snapshot.id
    assert latest.offering_id is OfferingId.CONSUMER_STANDARD


@pytest.mark.asyncio
async def test_atomic_publication_commits_documents_snapshot_and_manifest(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, run, execution = await _running_offering(monitoring_session_factory)
    snapshot = _snapshot(run.id, execution.id)
    publication = OfferingPublication(
        offering_execution_id=execution.id,
        documents=(_document(run.id),),
        snapshot=snapshot,
        manifests=(_manifest(run.id, execution.id),),
        audit_metadata={
            "provenance_changed": True,
            "timings": [{"stage": "publication", "duration_ms": 4}],
        },
    )

    result = await PostgresOfferingPublicationRepository(
        monitoring_session_factory
    ).publish(publication)

    assert result.snapshot_id == snapshot.id
    assert result.offering_status is OfferingRunStatus.SUCCEEDED
    assert result.document_results[0].document_created is True
    async with monitoring_session_factory() as session:
        counts = (
            await session.execute(
                text(
                    """
                    SELECT
                        (SELECT count(*) FROM knowledge_documents),
                        (SELECT count(*) FROM knowledge_chunks),
                        (SELECT count(*) FROM tariff_snapshots),
                        (SELECT count(*) FROM source_manifests)
                    """
                )
            )
        ).one()
        status = await session.scalar(
            text("SELECT status FROM offering_executions WHERE id = :id"),
            {"id": execution.id},
        )
        audit_payload = await session.scalar(
            text(
                """
                SELECT payload
                FROM audit_events
                WHERE offering_execution_id = :id
                  AND event_type = 'offering.published'
                """
            ),
            {"id": execution.id},
        )
    assert tuple(counts) == (1, 1, 1, 1)
    assert status == "succeeded"
    assert audit_payload["metadata"]["provenance_changed"] is True
    assert audit_payload["metadata"]["timings"][0]["stage"] == "publication"


@pytest.mark.asyncio
async def test_atomic_publication_rolls_back_everything_on_index_failure(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, run, execution = await _running_offering(monitoring_session_factory)
    publication = OfferingPublication(
        offering_execution_id=execution.id,
        documents=(
            _document(run.id),
            _document(
                run.id,
                checksum="b" * 64,
                document_key="invalid-embedding",
                dimensions=1,
            ),
        ),
        snapshot=_snapshot(run.id, execution.id),
        manifests=(_manifest(run.id, execution.id),),
    )

    with pytest.raises(ValueError, match="embedding"):
        await PostgresOfferingPublicationRepository(monitoring_session_factory).publish(
            publication
        )

    async with monitoring_session_factory() as session:
        counts = (
            await session.execute(
                text(
                    """
                    SELECT
                        (SELECT count(*) FROM knowledge_documents),
                        (SELECT count(*) FROM knowledge_chunks),
                        (SELECT count(*) FROM tariff_snapshots),
                        (SELECT count(*) FROM source_manifests)
                    """
                )
            )
        ).one()
        status = await session.scalar(
            text("SELECT status FROM offering_executions WHERE id = :id"),
            {"id": execution.id},
        )
    assert tuple(counts) == (0, 0, 0, 0)
    assert status == "running"
