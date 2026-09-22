import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import asyncpg
import pytest
import pytest_asyncio
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import DatabaseSessionService
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import load_seed_catalog
from app.config.models import IntentResolutionSettings
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
    SnapshotChange,
    SnapshotChangeSet,
    SnapshotStatus,
    SourceManifestItem,
)
from app.domain.monitoring_workflow import (
    MonitoringReviewResponse,
    ReviewResponseItem,
)
from app.domain.review import (
    ReviewCandidate,
    ReviewDecision,
    ReviewDecisionType,
    ReviewReason,
    ReviewSnapshotUpdate,
    ReviewStatus,
    ReviewTask,
)
from app.domain.structured_tariffs import FieldPath, QueryOperation
from app.repositories.monitoring import (
    PostgresOfferingPublicationRepository,
    PostgresRunRepository,
    PostgresSnapshotRepository,
)
from app.repositories.reviews import PostgresReviewRepository, ReviewConflictError
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
    PostgresStructuredUnitEmbeddingRepository,
)
from app.services.evidence_retention_audit import EvidenceRetentionAuditor
from app.services.intent_resolution import RequestResolver
from app.services.monitoring_workflow import (
    MonitoringWorkflowRunner,
    build_monitoring_app,
    build_monitoring_workflow,
    workflow_identity,
)
from app.services.review_decisions import ReviewDecisionService
from app.services.structured_backfill import StructuredProjectionBackfill
from app.services.structured_projection import RENDERER_VERSION
from app.services.structured_projection_audit import StructuredProjectionAuditor
from app.services.structured_query_planning import issue_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.fixtures.evaluation_corpus import CORPUS_SPECS, PREVIOUS_MORTGAGE_SPEC
from tests.fixtures.structured_tariffs import accepted_snapshot, build_snapshot
from tests.fixtures.target_questions import TARGET_QUESTIONS

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
    product: ProductType | None = None,
    offering_id: OfferingId | None = None,
) -> RunCommand:
    return RunCommand(
        product=product or ProductType.CONSUMER_LOAN,
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
    return accepted_snapshot("consumer").model_copy(
        update={
            "id": uuid4(),
            "run_id": run_id,
            "offering_execution_id": execution_id,
            "created_at": now,
            "accepted_at": now,
        }
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
async def test_project_timestamps_store_yerevan_wall_time_and_aware_instant(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = PostgresRunRepository(monitoring_session_factory)
    submitted = await repository.submit(_command())
    async with monitoring_session_factory() as session:
        row = (
            await session.execute(
                text("""
                    SELECT queued_at, queued_at_yerevan, created_at, created_at_yerevan
                    FROM monitoring_runs WHERE id = :run_id
                """),
                {"run_id": submitted.run.id},
            )
        ).one()
        for instant, wall_time in (
            (row.queued_at, row.queued_at_yerevan),
            (row.created_at, row.created_at_yerevan),
        ):
            assert instant.tzinfo is not None
            assert wall_time.tzinfo is None
            assert wall_time == instant.astimezone(ZoneInfo("Asia/Yerevan")).replace(
                tzinfo=None
            )

        missing = (
            await session.execute(
                text("""
                SELECT base.table_name, base.column_name
                FROM information_schema.columns AS base
                LEFT JOIN information_schema.columns AS companion
                  ON companion.table_schema = base.table_schema
                 AND companion.table_name = base.table_name
                 AND companion.column_name = base.column_name || '_yerevan'
                WHERE base.table_schema = 'public'
                  AND base.table_name IN (
                    'audit_events', 'human_reviews', 'knowledge_chunks',
                    'knowledge_documents', 'monitoring_runs', 'offering_executions',
                    'pdf_extraction_cache', 'semantic_extraction_batches',
                    'source_discovery_assessments', 'source_documents',
                    'source_manifests', 'tariff_changes', 'tariff_snapshots'
                  )
                  AND base.data_type = 'timestamp with time zone'
                  AND companion.column_name IS NULL
            """)
            )
        ).all()
        assert missing == []


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
async def test_different_offering_can_start_while_another_awaits_review(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = PostgresRunRepository(monitoring_session_factory)
    overdraft = await repository.submit(_command(offering_id=OfferingId.OVERDRAFT))
    claimed = await repository.claim_next("review-worker")
    assert claimed is not None
    assert claimed.run.id == overdraft.run.id
    await repository.pause_for_review(overdraft.run.id, summary={"review_ids": []})

    credit_line = await repository.submit(_command(offering_id=OfferingId.CREDIT_LINE))
    repeated = await repository.submit(_command(offering_id=OfferingId.OVERDRAFT))
    family_wide = await repository.submit(_command())

    assert credit_line.created is True
    assert credit_line.run.id != overdraft.run.id
    assert credit_line.run.command.offering_id is OfferingId.CREDIT_LINE
    assert repeated.created is False
    assert repeated.run.id == overdraft.run.id
    assert family_wide.created is False
    assert family_wide.run.command.offering_id is OfferingId.OVERDRAFT


@pytest.mark.asyncio
async def test_family_wide_active_run_covers_targeted_requests(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = PostgresRunRepository(monitoring_session_factory)
    family_wide = await repository.submit(_command())
    targeted = await repository.submit(_command(offering_id=OfferingId.CREDIT_LINE))

    assert targeted.created is False
    assert targeted.run.id == family_wide.run.id
    assert targeted.run.command.offering_id is None


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
async def test_snapshot_reads_exclude_pending_values_and_report_newer_review(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_repository, run, execution = await _running_offering(monitoring_session_factory)
    snapshots = PostgresSnapshotRepository(monitoring_session_factory)
    accepted = _snapshot(run.id, execution.id)
    assert accepted.accepted_at is not None
    await snapshots.save_attempt(accepted)
    await run_repository.finish(run.id, RunStatus.SUCCEEDED)

    _, pending_run, pending_execution = await _running_offering(
        monitoring_session_factory
    )
    pending = accepted.model_copy(
        update={
            "id": uuid4(),
            "run_id": pending_run.id,
            "offering_execution_id": pending_execution.id,
            "status": SnapshotStatus.REVIEW_REQUIRED,
            "normalized_tariff": {"nominal_interest_rate": "99%"},
            "created_at": accepted.created_at + timedelta(seconds=1),
            "accepted_at": None,
        }
    )
    await snapshots.save_attempt(pending)

    latest = await snapshots.list_latest_accepted(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
    )
    history = await snapshots.list_accepted_history(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        start_at=accepted.accepted_at - timedelta(days=1),
        end_at=accepted.accepted_at + timedelta(days=1),
        limit=10,
    )
    has_pending = await snapshots.has_newer_pending_review(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        accepted_at=accepted.accepted_at,
    )

    assert [item.id for item in latest] == [accepted.id]
    assert [item.id for item in history] == [accepted.id]
    assert has_pending is True


@pytest.mark.asyncio
async def test_change_reads_are_scope_time_and_limit_bounded(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_repository, first_run, first_execution = await _running_offering(
        monitoring_session_factory
    )
    repository = PostgresSnapshotRepository(monitoring_session_factory)
    first = _snapshot(first_run.id, first_execution.id)
    assert first.accepted_at is not None
    await repository.save_attempt(first)
    await run_repository.finish(first_run.id, RunStatus.SUCCEEDED)

    _, second_run, second_execution = await _running_offering(
        monitoring_session_factory
    )
    second_time = first.accepted_at + timedelta(seconds=1)
    second = first.model_copy(
        update={
            "id": uuid4(),
            "run_id": second_run.id,
            "offering_execution_id": second_execution.id,
            "normalized_tariff": {"nominal_interest_rate": "14.0%"},
            "previous_accepted_snapshot_id": first.id,
            "created_at": second_time,
            "accepted_at": second_time,
        }
    )
    await repository.save_attempt(second)
    change_set = SnapshotChangeSet(
        id=uuid4(),
        run_id=second_run.id,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        previous_snapshot_id=first.id,
        current_snapshot_id=second.id,
        changes=(
            SnapshotChange(
                field="nominal_interest_rate",
                previous="13.5%",
                current="14.0%",
            ),
        ),
        created_at=second_time,
    )
    await repository.save_changes(change_set)

    changes = await repository.list_changes(
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        start_at=first.accepted_at,
        end_at=second_time + timedelta(seconds=1),
        limit=1,
    )
    older = await repository.get_latest_change_before(
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        before=second_time + timedelta(seconds=1),
    )

    assert [item.id for item in changes] == [change_set.id]
    assert older is not None
    assert older.id == change_set.id
    structured_history = await PostgresStructuredTariffQueryRepository(
        monitoring_session_factory
    ).accepted_changes(
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
        limit=10,
    )
    assert [item.id for item in structured_history] == [change_set.id]


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


@pytest.mark.asyncio
async def test_review_candidate_documents_remain_hidden_and_keep_prior_active(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_repository, first_run, first_execution = await _running_offering(
        monitoring_session_factory
    )
    publisher = PostgresOfferingPublicationRepository(monitoring_session_factory)
    first_snapshot = _snapshot(first_run.id, first_execution.id)
    await publisher.publish(
        OfferingPublication(
            offering_execution_id=first_execution.id,
            documents=(_document(first_run.id),),
            snapshot=first_snapshot,
        )
    )
    await run_repository.finish(first_run.id, RunStatus.SUCCEEDED)

    _, candidate_run, candidate_execution = await _running_offering(
        monitoring_session_factory
    )
    candidate_snapshot = _snapshot(candidate_run.id, candidate_execution.id).model_copy(
        update={
            "status": SnapshotStatus.REVIEW_REQUIRED,
            "accepted_at": None,
        }
    )
    result = await publisher.publish(
        OfferingPublication(
            offering_execution_id=candidate_execution.id,
            documents=(_document(candidate_run.id, checksum="b" * 64),),
            snapshot=candidate_snapshot,
        )
    )

    async with monitoring_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT content_sha256, is_active, publication_state
                    FROM knowledge_documents
                    ORDER BY content_sha256
                    """
                )
            )
        ).all()
        candidate_active_chunks = await session.scalar(
            text(
                """
                SELECT count(*)
                FROM knowledge_chunks AS chunk
                JOIN knowledge_documents AS document ON document.id = chunk.document_id
                WHERE document.content_sha256 = :checksum AND chunk.is_active
                """
            ),
            {"checksum": "b" * 64},
        )

    assert result.offering_status is OfferingRunStatus.CANDIDATE_REVIEW
    assert [tuple(row) for row in rows] == [
        ("a" * 64, True, "active"),
        ("b" * 64, False, "pending_review"),
    ]
    assert candidate_active_chunks == 0
    reviews = PostgresReviewRepository(monitoring_session_factory)
    review = await reviews.create(
        _review_task(
            candidate_run.id,
            candidate_execution.id,
            candidate_snapshot.id,
            idempotency_key="candidate-rejection",
            created_at=candidate_snapshot.created_at,
        )
    )
    await reviews.reject(review.id, reviewer="reviewer@example.test")
    async with monitoring_session_factory() as session:
        active = (
            (
                await session.execute(
                    text("SELECT snapshot_id FROM offering_profiles WHERE is_active")
                )
            )
            .scalars()
            .all()
        )
    assert active == [first_snapshot.id]


def _review_task(
    run_id,
    execution_id,
    snapshot_id,
    *,
    idempotency_key: str,
    created_at: datetime,
) -> ReviewTask:
    return ReviewTask(
        id=uuid4(),
        idempotency_key=idempotency_key,
        run_id=run_id,
        offering_execution_id=execution_id,
        snapshot_id=snapshot_id,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        reason=ReviewReason.OFFICIAL_SOURCE_CONFLICT,
        issue_scope="nominal_interest_rate:default",
        candidates=(
            ReviewCandidate(
                candidate_id="web-rate",
                field="nominal_interest_rate",
                value="13.5%",
                evidence_references=("evidence:web:rates:1",),
            ),
        ),
        status=ReviewStatus.PENDING,
        created_at=created_at,
        updated_at=created_at,
    )


@pytest.mark.asyncio
async def test_review_create_decide_and_supersession_are_idempotent(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, run, execution = await _running_offering(monitoring_session_factory)
    snapshot = _snapshot(run.id, execution.id).model_copy(
        update={"status": SnapshotStatus.REVIEW_REQUIRED, "accepted_at": None}
    )
    await PostgresSnapshotRepository(monitoring_session_factory).save_attempt(snapshot)
    reviews = PostgresReviewRepository(monitoring_session_factory)
    first_input = _review_task(
        run.id,
        execution.id,
        snapshot.id,
        idempotency_key="review:first",
        created_at=snapshot.created_at,
    )

    first, repeated = await asyncio.gather(
        reviews.create(first_input),
        reviews.create(first_input.model_copy(update={"id": uuid4()})),
    )
    approved = await reviews.approve(
        first.id,
        ReviewDecision(decision_type=ReviewDecisionType.APPROVE),
        reviewer="reviewer@example.test",
    )
    duplicate = await reviews.approve(
        first.id,
        ReviewDecision(decision_type=ReviewDecisionType.APPROVE),
        reviewer="reviewer@example.test",
    )

    assert repeated.id == first.id
    assert approved.status is ReviewStatus.APPROVED
    assert duplicate.id == approved.id

    competing = await reviews.create(
        first_input.model_copy(
            update={
                "id": uuid4(),
                "idempotency_key": "review:competing",
                "issue_scope": "effective_interest_rate:default",
            }
        )
    )
    outcomes = await asyncio.gather(
        reviews.approve(
            competing.id,
            ReviewDecision(decision_type=ReviewDecisionType.APPROVE),
            reviewer="reviewer-a",
        ),
        reviews.reject(competing.id, reviewer="reviewer-b"),
        return_exceptions=True,
    )
    assert sum(isinstance(item, ReviewTask) for item in outcomes) == 1
    assert sum(isinstance(item, ReviewConflictError) for item in outcomes) == 1


@pytest.mark.asyncio
async def test_newer_same_scope_review_supersedes_pending_review(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_repository, first_run, first_execution = await _running_offering(
        monitoring_session_factory
    )
    snapshots = PostgresSnapshotRepository(monitoring_session_factory)
    first_snapshot = _snapshot(first_run.id, first_execution.id).model_copy(
        update={"status": SnapshotStatus.REVIEW_REQUIRED, "accepted_at": None}
    )
    await snapshots.save_attempt(first_snapshot)
    await run_repository.finish(first_run.id, RunStatus.FAILED)
    reviews = PostgresReviewRepository(monitoring_session_factory)
    first = await reviews.create(
        _review_task(
            first_run.id,
            first_execution.id,
            first_snapshot.id,
            idempotency_key="review:old",
            created_at=first_snapshot.created_at,
        )
    )

    _, second_run, second_execution = await _running_offering(
        monitoring_session_factory
    )
    second_snapshot = _snapshot(second_run.id, second_execution.id).model_copy(
        update={
            "status": SnapshotStatus.REVIEW_REQUIRED,
            "accepted_at": None,
            "created_at": first_snapshot.created_at + timedelta(seconds=1),
        }
    )
    await snapshots.save_attempt(second_snapshot)
    second = await reviews.create(
        _review_task(
            second_run.id,
            second_execution.id,
            second_snapshot.id,
            idempotency_key="review:new",
            created_at=second_snapshot.created_at,
        )
    )

    old = await reviews.get(first.id)
    assert old is not None
    assert old.status is ReviewStatus.SUPERSEDED
    assert second.status is ReviewStatus.PENDING
    with pytest.raises(ReviewConflictError):
        await reviews.reject(first.id, reviewer="late-reviewer")


@pytest.mark.asyncio
async def test_postgres_session_restart_resumes_same_workflow_invocation(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    runs, running, execution = await _running_offering(monitoring_session_factory)
    snapshots = PostgresSnapshotRepository(monitoring_session_factory)
    snapshot = _snapshot(running.id, execution.id).model_copy(
        update={"status": SnapshotStatus.REVIEW_REQUIRED, "accepted_at": None}
    )
    await snapshots.save_attempt(snapshot)
    reviews = PostgresReviewRepository(monitoring_session_factory)
    review = await reviews.create(
        _review_task(
            running.id,
            execution.id,
            snapshot.id,
            idempotency_key=f"restart:{running.id}",
            created_at=snapshot.created_at,
        ).model_copy(
            update={"reason": ReviewReason.LARGE_RATE_CHANGE, "candidates": ()}
        )
    )

    class _Pipeline:
        calls = 0

        async def execute(self, run):
            self.calls += 1
            return await runs.pause_for_review(
                run.id,
                summary={
                    "succeeded": 0,
                    "failed": 0,
                    "review_ids": [str(review.id)],
                },
            )

    pipeline = _Pipeline()
    workflow = build_monitoring_workflow(
        runs=runs,
        pipeline=pipeline,
        reviews=reviews,
        decisions=ReviewDecisionService(reviews, snapshots),
    )
    first_sessions = DatabaseSessionService(db_url=_test_database_url())
    await first_sessions.prepare_tables()
    first_runner = MonitoringWorkflowRunner(
        app=build_monitoring_app(workflow),
        session_service=first_sessions,
        artifact_service=InMemoryArtifactService(),
    )

    paused = await first_runner.start(running)
    attached = await reviews.get(review.id)
    assert paused.status is RunStatus.AWAITING_REVIEW
    assert attached is not None and attached.correlation is not None
    correlation = attached.correlation
    await first_sessions.db_engine.dispose()

    second_sessions = DatabaseSessionService(db_url=_test_database_url())
    await second_sessions.prepare_tables()
    second_runner = MonitoringWorkflowRunner(
        app=build_monitoring_app(workflow),
        session_service=second_sessions,
        artifact_service=InMemoryArtifactService(),
    )
    user_id, session_id = workflow_identity(running)

    completed = await second_runner.resume(
        user_id=user_id,
        session_id=session_id,
        interrupt_id=correlation.interrupt_id,
        response=MonitoringReviewResponse(
            decisions=(
                ReviewResponseItem(
                    review_id=review.id,
                    decision=ReviewDecision(decision_type=ReviewDecisionType.APPROVE),
                ),
            )
        ),
        run_id=running.id,
    )

    assert completed.status is RunStatus.SUCCEEDED
    assert pipeline.calls == 1
    persisted = await runs.get(running.id)
    assert persisted is not None and persisted.status is RunStatus.SUCCEEDED
    async with monitoring_session_factory() as session:
        active_projection = await session.scalar(
            text(
                "SELECT count(*) FROM offering_profiles WHERE snapshot_id = :id AND is_active"
            ),
            {"id": snapshot.id},
        )
    assert active_projection == 1
    await second_sessions.db_engine.dispose()


@pytest.mark.asyncio
async def test_structured_projection_is_atomic_and_supersedes_only_accepted_scope(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    runs, first_run, first_execution = await _running_offering(
        monitoring_session_factory
    )
    publisher = PostgresOfferingPublicationRepository(monitoring_session_factory)
    first = _snapshot(first_run.id, first_execution.id)
    await publisher.publish(
        OfferingPublication(
            offering_execution_id=first_execution.id,
            documents=(_document(first_run.id),),
            snapshot=first,
        )
    )
    async with monitoring_session_factory() as session:
        first_counts = (
            await session.execute(
                text(
                    """SELECT
                        (SELECT count(*) FROM offering_profiles WHERE is_active),
                        (SELECT count(*) FROM tariff_facts WHERE is_active),
                        (SELECT count(*) FROM fact_evidence),
                        (SELECT count(*) FROM retrieval_units WHERE is_active)
                    """
                )
            )
        ).one()
    assert first_counts[0] == 1
    assert first_counts[1] > 0
    assert first_counts[2] > 0
    assert first_counts[3] > 0
    await runs.finish(first_run.id, RunStatus.SUCCEEDED)

    _, second_run, second_execution = await _running_offering(
        monitoring_session_factory
    )
    candidate = _snapshot(second_run.id, second_execution.id).model_copy(
        update={"status": SnapshotStatus.REVIEW_REQUIRED, "accepted_at": None}
    )
    await publisher.publish(
        OfferingPublication(
            offering_execution_id=second_execution.id,
            documents=(_document(second_run.id, checksum="b" * 64),),
            snapshot=candidate,
        )
    )
    async with monitoring_session_factory() as session:
        pending_count = await session.scalar(
            text("SELECT count(*) FROM offering_profiles")
        )
    assert pending_count == 1
    query = PostgresStructuredTariffQueryRepository(monitoring_session_factory)
    pending_visible = await query.active_profiles(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
    )
    assert [item.snapshot_id for item in pending_visible] == [first.id]
    await runs.finish(second_run.id, RunStatus.FAILED)

    _, third_run, third_execution = await _running_offering(monitoring_session_factory)
    third = _snapshot(third_run.id, third_execution.id)
    await publisher.publish(
        OfferingPublication(
            offering_execution_id=third_execution.id,
            documents=(_document(third_run.id, checksum="d" * 64),),
            snapshot=third,
        )
    )
    async with monitoring_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """SELECT snapshot_id, is_active FROM offering_profiles
                    ORDER BY accepted_at"""
                )
            )
        ).all()
        active_facts = await session.scalar(
            text(
                "SELECT count(*) FROM tariff_facts WHERE is_active AND snapshot_id = :id"
            ),
            {"id": third.id},
        )
        old_active_units = await session.scalar(
            text(
                "SELECT count(*) FROM retrieval_units WHERE is_active AND snapshot_id = :id"
            ),
            {"id": first.id},
        )
    assert {row.snapshot_id for row in rows if row.is_active} == {third.id}
    assert active_facts > 0
    assert old_active_units == 0
    latest = await query.active_profiles(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
    )
    assert [item.snapshot_id for item in latest] == [third.id]
    assert (
        await query.facts(
            snapshots=(first.id,),
            fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
        )
        == ()
    )


@pytest.mark.asyncio
async def test_projection_failure_rolls_back_snapshot_and_index(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, run, execution = await _running_offering(monitoring_session_factory)
    broken = _snapshot(run.id, execution.id).model_copy(
        update={"semantic_extraction": {"status": "completed"}}
    )
    with pytest.raises(ValueError):
        await PostgresOfferingPublicationRepository(monitoring_session_factory).publish(
            OfferingPublication(
                offering_execution_id=execution.id,
                documents=(_document(run.id),),
                snapshot=broken,
            )
        )
    async with monitoring_session_factory() as session:
        counts = (
            await session.execute(
                text(
                    """SELECT
                        (SELECT count(*) FROM tariff_snapshots),
                        (SELECT count(*) FROM knowledge_documents),
                        (SELECT count(*) FROM offering_profiles)
                    """
                )
            )
        ).one()
    assert tuple(counts) == (0, 0, 0)


@pytest.mark.asyncio
async def test_review_approval_activates_final_projection_atomically(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, run, execution = await _running_offering(monitoring_session_factory)
    accepted = _snapshot(run.id, execution.id)
    pending = accepted.model_copy(
        update={"status": SnapshotStatus.REVIEW_REQUIRED, "accepted_at": None}
    )
    await PostgresOfferingPublicationRepository(monitoring_session_factory).publish(
        OfferingPublication(
            offering_execution_id=execution.id,
            documents=(_document(run.id),),
            snapshot=pending,
        )
    )
    reviews = PostgresReviewRepository(monitoring_session_factory)
    review = await reviews.create(
        _review_task(
            run.id,
            execution.id,
            pending.id,
            idempotency_key="projection-approval",
            created_at=pending.created_at,
        )
    )
    update = ReviewSnapshotUpdate(
        snapshot_id=pending.id,
        expected_canonical_sha256=pending.canonical_sha256,
        normalized_tariff=pending.normalized_tariff,
        semantic_extraction=pending.semantic_extraction,
        validation={"accepted": True, "review_signals": []},
        canonical_sha256=pending.canonical_sha256,
        ready_for_activation=True,
    )
    await reviews.approve_with_snapshot(
        review.id,
        ReviewDecision(decision_type=ReviewDecisionType.APPROVE),
        update,
        reviewer="reviewer@example.test",
    )
    async with monitoring_session_factory() as session:
        snapshot_status = await session.scalar(
            text("SELECT status FROM tariff_snapshots WHERE id = :id"),
            {"id": pending.id},
        )
        profile_count = await session.scalar(
            text(
                "SELECT count(*) FROM offering_profiles WHERE snapshot_id = :id AND is_active"
            ),
            {"id": pending.id},
        )
        fact_count = await session.scalar(
            text(
                "SELECT count(*) FROM tariff_facts WHERE snapshot_id = :id AND is_active"
            ),
            {"id": pending.id},
        )
    assert snapshot_status == "accepted"
    assert profile_count == 1
    assert fact_count > 0


@pytest.mark.asyncio
async def test_concurrent_accepted_publications_leave_one_active_projection(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    runs, first_run, first_execution = await _running_offering(
        monitoring_session_factory
    )
    await runs.finish(first_run.id, RunStatus.SUCCEEDED)
    _, second_run, second_execution = await _running_offering(
        monitoring_session_factory
    )
    first = _snapshot(first_run.id, first_execution.id)
    second = _snapshot(second_run.id, second_execution.id)
    publisher = PostgresOfferingPublicationRepository(monitoring_session_factory)
    await asyncio.gather(
        publisher.publish(
            OfferingPublication(
                offering_execution_id=first_execution.id,
                documents=(_document(first_run.id),),
                snapshot=first,
            )
        ),
        publisher.publish(
            OfferingPublication(
                offering_execution_id=second_execution.id,
                documents=(_document(second_run.id, checksum="b" * 64),),
                snapshot=second,
            )
        ),
    )
    async with monitoring_session_factory() as session:
        active = (
            (
                await session.execute(
                    text("SELECT snapshot_id FROM offering_profiles WHERE is_active")
                )
            )
            .scalars()
            .all()
        )
        active_fact_scopes = (
            (
                await session.execute(
                    text(
                        "SELECT DISTINCT snapshot_id FROM tariff_facts WHERE is_active"
                    )
                )
            )
            .scalars()
            .all()
        )
        active_unit_scopes = (
            (
                await session.execute(
                    text(
                        "SELECT DISTINCT snapshot_id FROM retrieval_units WHERE is_active"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(active) == 1
    assert active[0] in {first.id, second.id}
    assert active_fact_scopes == active
    assert active_unit_scopes == active


@pytest.mark.asyncio
async def test_structured_query_reads_only_active_accepted_evidence(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, run, execution = await _running_offering(monitoring_session_factory)
    snapshot = _snapshot(run.id, execution.id)
    source_document = _document(run.id).model_copy(
        update={
            "document_key": "synthetic-page",
            "source_url": "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
            "final_url": "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
        }
    )
    await PostgresOfferingPublicationRepository(monitoring_session_factory).publish(
        OfferingPublication(
            offering_execution_id=execution.id,
            documents=(source_document,),
            snapshot=snapshot,
        )
    )
    query = PostgresStructuredTariffQueryRepository(monitoring_session_factory)
    profiles = await query.active_profiles(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
    )
    facts = await query.facts(
        snapshots=(snapshot.id,),
        fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
    )
    lexical = await query.lexical_units(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
        query="consumer",
        limit=5,
    )
    assert len(profiles) == 1
    assert len(facts) == 2
    assert len({fact.variant_key for fact in facts}) == 2
    assert all(fact.conditions for fact in facts)
    assert all(fact.evidence[0].quote for fact in facts)
    assert all(fact.evidence[0].document_id for fact in facts)
    assert all(fact.evidence[0].document_checksum == "a" * 64 for fact in facts)
    assert lexical and all(hit.unit.snapshot_id == snapshot.id for hit in lexical)
    assert lexical[0].score > 0
    # PostgreSQL simple tokenization must preserve Armenian terms.
    async with monitoring_session_factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE retrieval_units SET alias_purpose_text = "
                "alias_purpose_text || ' սպառողական վարկ' "
                "WHERE snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": snapshot.id},
        )
    armenian = await query.lexical_units(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
        query="սպառողական վարկ",
        limit=5,
    )
    assert armenian and armenian[0].score > 0
    assert (
        await query.vector_units(
            bank="ameria",
            product=ProductType.CONSUMER_LOAN,
            offering_ids=(OfferingId.CONSUMER_STANDARD,),
            embedding=[0.1] * 768,
            model_id="gemini-embedding-001",
        )
        == ()
    )
    vector_index = PostgresStructuredUnitEmbeddingRepository(monitoring_session_factory)
    missing = await vector_index.missing(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
        model_id="test-model",
    )
    assert missing
    assert (
        await vector_index.save(
            model_id="test-model", vectors=((missing[0], [0.1] * 768),)
        )
        == 1
    )
    vector_hits = await query.vector_units(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
        embedding=[0.1] * 768,
        model_id="test-model",
        limit=5,
    )
    assert len(vector_hits) == 1
    assert vector_hits[0].unit.unit_id == missing[0].unit_id
    async with monitoring_session_factory() as session, session.begin():
        await session.execute(
            text("UPDATE retrieval_units SET content = 'tampered' WHERE id = :unit_id"),
            {"unit_id": lexical[0].unit.unit_id},
        )
    with pytest.raises(ValueError, match="stored retrieval text differs"):
        await query.lexical_units(
            bank="ameria",
            product=ProductType.CONSUMER_LOAN,
            offering_ids=(OfferingId.CONSUMER_STANDARD,),
            query="consumer",
            limit=5,
        )
    with pytest.raises(ValueError, match="outside requested product family"):
        await query.active_profiles(
            bank="ameria",
            product=ProductType.CONSUMER_LOAN,
            offering_ids=(OfferingId.MORTGAGE_PRIMARY,),
        )
    async with monitoring_session_factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE fact_evidence SET quote = 'tampered' WHERE fact_id = :fact_id"
            ),
            {"fact_id": facts[0].fact_id},
        )
    with pytest.raises(ValueError, match="differs from accepted capture"):
        await query.facts(
            snapshots=(snapshot.id,),
            fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
        )


@pytest.mark.asyncio
async def test_structured_backfill_is_atomic_idempotent_and_flags_legacy_bad_evidence(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    runs, first_run, first_execution = await _running_offering(
        monitoring_session_factory
    )
    snapshots = PostgresSnapshotRepository(monitoring_session_factory)
    old = _snapshot(first_run.id, first_execution.id)
    await snapshots.save_attempt(old)
    await runs.finish(first_run.id, RunStatus.SUCCEEDED)

    _, second_run, second_execution = await _running_offering(
        monitoring_session_factory
    )
    newer = accepted_snapshot("reviewed_consumer").model_copy(
        update={
            "id": uuid4(),
            "run_id": second_run.id,
            "offering_execution_id": second_execution.id,
            "created_at": old.created_at + timedelta(seconds=1),
            "accepted_at": old.accepted_at + timedelta(seconds=1),
            "previous_accepted_snapshot_id": old.id,
        }
    )
    await snapshots.save_attempt(newer)
    backfill = StructuredProjectionBackfill(monitoring_session_factory)
    dry = await backfill.run_scope(
        "ameria", "consumer_loan", "consumer_standard", batch_size=1
    )
    assert dry.examined == dry.projectable == 2
    assert dry.published == 0
    applied = await backfill.run_scope(
        "ameria", "consumer_loan", "consumer_standard", batch_size=1, apply=True
    )
    assert applied.published == 2
    assert applied.active_snapshot_id == newer.id
    repeated = await backfill.run_scope(
        "ameria", "consumer_loan", "consumer_standard", batch_size=1, apply=True
    )
    assert repeated.active_snapshot_id == newer.id
    query = PostgresStructuredTariffQueryRepository(monitoring_session_factory)
    profiles = await query.active_profiles(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
    )
    historical = await query.facts(
        snapshots=(old.id,),
        fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
        include_inactive=True,
    )
    assert [profile.snapshot_id for profile in profiles] == [newer.id]
    assert historical and all(fact.evidence for fact in historical)
    auditor = StructuredProjectionAuditor(monitoring_session_factory)
    old_audit = await auditor.audit_snapshot(old.id)
    assert old_audit.status == "matched", old_audit
    assert (await auditor.audit_snapshot(newer.id)).status == "matched"
    async with monitoring_session_factory() as session:
        counts = (
            await session.execute(
                text(
                    """SELECT
                    (SELECT count(*) FROM offering_profiles WHERE is_active),
                    (SELECT count(*) FROM tariff_facts WHERE is_active),
                    (SELECT count(*) FROM retrieval_units WHERE is_active)"""
                )
            )
        ).one()
    assert counts[0] == 1
    assert counts[1] > 0 and counts[2] > 0
    async with monitoring_session_factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE tariff_facts SET value_json = CAST('\"tampered\"' AS jsonb) "
                "WHERE snapshot_id = :snapshot_id AND field_path = 'identity.product_name'"
            ),
            {"snapshot_id": old.id},
        )
    assert (await auditor.audit_snapshot(old.id)).status == "mismatch"

    await runs.finish(second_run.id, RunStatus.SUCCEEDED)
    _, third_run, third_execution = await _running_offering(monitoring_session_factory)
    legacy = _snapshot(third_run.id, third_execution.id).model_copy(
        update={
            "id": uuid4(),
            "created_at": newer.created_at + timedelta(seconds=1),
            "accepted_at": newer.accepted_at + timedelta(seconds=1),
            "semantic_extraction": {},
        }
    )
    await snapshots.save_attempt(legacy)
    audited = await backfill.run_scope(
        "ameria", "consumer_loan", "consumer_standard", batch_size=1
    )
    assert audited.projectable == 2
    assert [issue.snapshot_id for issue in audited.issues] == [legacy.id]
    assert (await auditor.audit_snapshot(legacy.id)).status == "unprojectable"
    failed_latest = await backfill.run_scope(
        "ameria", "consumer_loan", "consumer_standard", batch_size=1, apply=True
    )
    assert failed_latest.active_snapshot_id is None
    assert not await query.active_profiles(
        bank="ameria",
        product=ProductType.CONSUMER_LOAN,
        offering_ids=(OfferingId.CONSUMER_STANDARD,),
    )


@pytest.mark.asyncio
async def test_evidence_retention_audit_gates_legacy_embedding_deprecation(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    runs, run, execution = await _running_offering(monitoring_session_factory)
    snapshot = _snapshot(run.id, execution.id)
    # The cited source document must still be retained for the audit to pass.
    await PostgresOfferingPublicationRepository(monitoring_session_factory).publish(
        OfferingPublication(
            offering_execution_id=execution.id,
            documents=(_document(run.id, document_key="synthetic-page"),),
            snapshot=snapshot,
            manifests=(_manifest(run.id, execution.id),),
        )
    )
    await runs.finish(run.id, RunStatus.SUCCEEDED)
    await StructuredProjectionBackfill(monitoring_session_factory).run_scope(
        "ameria", "consumer_loan", "consumer_standard", apply=True
    )
    auditor = EvidenceRetentionAuditor(monitoring_session_factory)

    clean = await auditor.audit()

    assert clean.active_found_facts > 0
    assert clean.active_evidence_rows > 0
    assert clean.facts_without_evidence == 0
    assert clean.legacy_source_chunks > 0
    assert clean.legacy_embedded_chunks > 0
    assert clean.ready_to_deprecate_legacy_embeddings
    assert clean.gaps == ()

    async with monitoring_session_factory() as session, session.begin():
        await session.execute(
            text(
                "DELETE FROM fact_evidence WHERE fact_id IN ("
                "SELECT id FROM tariff_facts WHERE is_active AND status = 'found' "
                "ORDER BY id LIMIT 1)"
            )
        )

    gapped = await auditor.audit()

    assert gapped.facts_without_evidence == 1
    assert not gapped.ready_to_deprecate_legacy_embeddings
    assert gapped.gaps[0].kind == "fact_without_evidence"
    assert gapped.gaps[0].field_path


async def _accept_spec(session_factory: async_sessionmaker[AsyncSession], spec):
    """Accept one synthetic offering snapshot through the real run lifecycle."""
    runs = PostgresRunRepository(session_factory)
    submitted = await runs.submit(
        RunCommand(
            product=spec.product,
            offering_id=spec.offering_id,
            trigger=RunTrigger.API,
        )
    )
    claimed = await runs.claim_next("eval-worker")
    assert claimed is not None
    execution = await runs.create_offering_execution(
        submitted.run.id, spec.product, spec.offering_id
    )
    execution = await runs.start_offering_execution(execution.id)
    snapshot = build_snapshot(spec).model_copy(
        update={
            "run_id": submitted.run.id,
            "offering_execution_id": execution.id,
        }
    )
    await PostgresSnapshotRepository(session_factory).save_attempt(snapshot)
    await runs.finish(submitted.run.id, RunStatus.SUCCEEDED)
    return snapshot


async def _accept_corpus(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Publish every synthetic evaluation offering as an accepted projection.

    The prior mortgage version and its accepted change set are published too,
    so the history question has real old and new evidence to cite.
    """
    backfill = StructuredProjectionBackfill(session_factory)
    previous = await _accept_spec(session_factory, PREVIOUS_MORTGAGE_SPEC)
    for spec in CORPUS_SPECS:
        current = await _accept_spec(session_factory, spec)
        if spec.offering_id is OfferingId.MORTGAGE_PRIMARY:
            await PostgresSnapshotRepository(session_factory).save_changes(
                SnapshotChangeSet(
                    id=uuid4(),
                    run_id=current.run_id,
                    product=spec.product,
                    offering_id=spec.offering_id,
                    previous_snapshot_id=previous.id,
                    current_snapshot_id=current.id,
                    changes=(
                        SnapshotChange(
                            field="interest_rate",
                            previous="10",
                            current="11",
                            previous_display="10% minimum nominal rate",
                            current_display="11% minimum nominal rate",
                        ),
                    ),
                    created_at=datetime.now(UTC),
                )
            )
        result = await backfill.run_scope(
            "ameria", spec.product.value, spec.offering_id.value, apply=True
        )
        assert result.published >= 1, result


@pytest.mark.asyncio
async def test_structured_read_model_answers_all_25_questions_on_postgres(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _accept_corpus(monitoring_session_factory)
    resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings())
    service = StructuredTariffQueryService(
        PostgresStructuredTariffQueryRepository(monitoring_session_factory)
    )
    lexical_hits = 0
    single_offering_questions = 0
    failures: list[str] = []

    for question in TARGET_QUESTIONS:
        resolution = (await resolver.resolve_turn(question.question)).resolution
        plan = issue_resolution_plan(
            question.question,
            resolution,
            session_id=f"pg-eval-{question.case_id}",
            turn_id=question.case_id,
        )
        result = await service.answer(plan, question.question)
        if result.status is not question.expected_status:
            failures.append(
                f"{question.case_id}: {result.status.value} "
                f"!= {question.expected_status.value} ({result.reason})"
            )
            continue
        if (
            question.expected_winner is not None
            and result.metadata.get("winner") != question.expected_winner.value
        ):
            failures.append(
                f"{question.case_id}: winner {result.metadata.get('winner')}"
            )
        if plan.operation is QueryOperation.SINGLE and result.facts:
            single_offering_questions += 1
            lexical_hits += bool(result.retrieval_units)

    assert not failures, failures
    # Weighted `simple` full-text search must find supporting units for the
    # descriptive part of most single-offering questions.
    assert single_offering_questions >= 10
    assert lexical_hits / single_offering_questions >= 0.85, (
        lexical_hits,
        single_offering_questions,
    )


@pytest.mark.asyncio
async def test_accepted_facts_never_leak_across_offering_or_family_scope(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _accept_corpus(monitoring_session_factory)
    repository = PostgresStructuredTariffQueryRepository(monitoring_session_factory)
    service = StructuredTariffQueryService(repository)
    resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings())

    for question in TARGET_QUESTIONS:
        resolution = (await resolver.resolve_turn(question.question)).resolution
        plan = issue_resolution_plan(
            question.question,
            resolution,
            session_id=f"pg-scope-{question.case_id}",
            turn_id=question.case_id,
        )
        result = await service.answer(plan, question.question)
        assert all(fact.offering_id in plan.offering_ids for fact in result.facts)
        assert all(
            unit.offering_id in plan.offering_ids for unit in result.retrieval_units
        )

    with pytest.raises(ValueError):
        await repository.active_profiles(
            bank="ameria",
            product=ProductType.CONSUMER_LOAN,
            offering_ids=(OfferingId.MORTGAGE_PRIMARY,),
        )


@pytest.mark.asyncio
async def test_renderer_upgrade_rerenders_units_and_drops_stale_vectors(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    runs, run, execution = await _running_offering(monitoring_session_factory)
    snapshot = _snapshot(run.id, execution.id)
    await PostgresSnapshotRepository(monitoring_session_factory).save_attempt(snapshot)
    await runs.finish(run.id, RunStatus.SUCCEEDED)
    backfill = StructuredProjectionBackfill(monitoring_session_factory)
    await backfill.run_scope("ameria", "consumer_loan", "consumer_standard", apply=True)
    # Simulate a projection written by the previous renderer, with its vector.
    async with monitoring_session_factory() as session, session.begin():
        await session.execute(
            text(
                """UPDATE retrieval_units SET renderer_version = 1,
                detail_text = 'rate.nominal.minimum: 12',
                content = 'stale', content_sha256 = repeat('a', 64),
                embedding = :vector, embedding_model = 'gemini-embedding-001',
                embedding_dimensions = 768
                WHERE snapshot_id = :snapshot_id"""
            ),
            {
                "snapshot_id": snapshot.id,
                "vector": "[" + ",".join("0.01" for _ in range(768)) + "]",
            },
        )

    await backfill.run_scope("ameria", "consumer_loan", "consumer_standard", apply=True)

    async with monitoring_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """SELECT renderer_version, detail_text, content,
                    embedding IS NULL AS vector_cleared, embedding_model
                    FROM retrieval_units WHERE snapshot_id = :snapshot_id"""
                ),
                {"snapshot_id": snapshot.id},
            )
        ).all()
    assert rows
    assert all(row.renderer_version == RENDERER_VERSION for row in rows)
    assert all(row.content != "stale" for row in rows)
    assert all(row.vector_cleared and row.embedding_model is None for row in rows)
    assert any("minimum nominal interest rate" in row.detail_text for row in rows)
