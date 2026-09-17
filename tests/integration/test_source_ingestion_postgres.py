import hashlib
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.domain.crawl import ProductCategory
from app.domain.discovery import (
    CandidateRetrievalStatus,
    DiscoveryOrigin,
    IngestedProduct,
    IngestedSource,
    SourceCandidate,
    SourceCandidateType,
    SourceIngestionResult,
    StoredArtifact,
)
from app.repositories.content_extraction import (
    ContentExtractionRecord,
    PostgresContentExtractionRepository,
)
from app.repositories.source_ingestion import (
    PostgresSourceIngestionRepository,
    SourceArtifactOriginRecord,
    SourceArtifactRecord,
    SourceIngestionCandidateRecord,
    SourceIngestionRunRecord,
)
from app.services.content_extractor import DocumentContentExtractor
from app.services.local_artifact_store import LocalArtifactStore

pytestmark = pytest.mark.postgres

NOW = datetime(2026, 9, 17, 6, tzinfo=UTC)
RUN_ID = UUID("58b1906d-04f5-4514-9643-47a1cd0d21f0")
SECOND_RUN_ID = UUID("6a71ba5d-e76e-47a7-b287-8cb5609567c2")
CHECKSUM = "a" * 64
PRODUCT_ID = "consumer.test"
PAGE_URL = "https://ameriabank.am/en/product"


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    database_name = make_url(database_url).database or ""
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must target a database ending in '_test'")
    return database_url


@pytest_asyncio.fixture(scope="session")
async def database_engine() -> AsyncIterator[AsyncEngine]:
    database_url = _test_database_url()
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        await connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        for migration in sorted(Path("migrations").glob("*.sql")):
            await connection.execute(migration.read_text(encoding="utf-8"))
    finally:
        await connection.close()

    engine = create_async_engine(database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(
    database_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    async with database_engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE source_artifact_origins, source_ingestion_candidates, "
                "source_ingestion_products, source_ingestion_runs, source_artifacts "
                "CASCADE"
            )
        )
    yield async_sessionmaker(database_engine, expire_on_commit=False)


def _ingestion(
    run_id: UUID = RUN_ID,
    *,
    completed_at: datetime = NOW,
    storage_key: str = f"raw/aa/{CHECKSUM}.html",
) -> SourceIngestionResult:
    artifact = StoredArtifact(
        storage_key=storage_key,
        sha256=CHECKSUM,
        mime_type="text/html",
        size_bytes=42,
        created=True,
    )
    retrieved = SourceCandidate(
        product_id=PRODUCT_ID,
        candidate_type=SourceCandidateType.PRODUCT_PAGE,
        origin=DiscoveryOrigin.REGISTRY,
        original_url=PAGE_URL,
        normalized_url=PAGE_URL,
        discovery_path=(PAGE_URL,),
        match_signals=("configured_product_seed",),
        retrieval_status=CandidateRetrievalStatus.RETRIEVED,
        status_code=200,
        content_sha256=CHECKSUM,
        mime_type="text/html",
    )
    proposed_url = f"{PAGE_URL}/proposal"
    proposed = SourceCandidate(
        product_id=PRODUCT_ID,
        candidate_type=SourceCandidateType.PAGE,
        origin=DiscoveryOrigin.SITEMAP,
        original_url=proposed_url,
        normalized_url=proposed_url,
        discovery_path=("https://ameriabank.am/sitemap.xml", proposed_url),
        match_signals=("alias:consumer",),
        retrieval_status=CandidateRetrievalStatus.NOT_RETRIEVED,
    )
    return SourceIngestionResult(
        run_id=run_id,
        started_at=completed_at - timedelta(minutes=1),
        completed_at=completed_at,
        manifest_key=f"manifests/{run_id}.json",
        products=(
            IngestedProduct(
                product_id=PRODUCT_ID,
                product_name="Consumer test",
                category=ProductCategory.CONSUMER,
                crawl_status="success",
                candidate_count=2,
                stored_source_count=1,
            ),
        ),
        sources=(
            IngestedSource(
                product_id=PRODUCT_ID,
                candidate_type=SourceCandidateType.PRODUCT_PAGE,
                source_url=PAGE_URL,
                final_url=PAGE_URL,
                language="en",
                retrieved_at=completed_at,
                artifact=artifact,
            ),
        ),
        candidates=(retrieved, proposed),
    )


@pytest.mark.asyncio
async def test_save_ingestion_is_idempotent_and_queryable(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = PostgresSourceIngestionRepository(session_factory)
    ingestion = _ingestion()

    first = await repository.save_ingestion(ingestion)
    repeated = await repository.save_ingestion(ingestion)

    assert first.artifacts_created == 1
    assert first.artifacts_reused == 0
    assert repeated.artifacts_created == 0
    assert repeated.artifacts_reused == 1
    assert await repository.get_run(RUN_ID) is not None
    artifact = await repository.get_artifact(CHECKSUM)
    assert artifact is not None
    assert artifact.storage_key == f"raw/aa/{CHECKSUM}.html"
    origins = await repository.list_product_sources(PRODUCT_ID, ingestion_run_id=RUN_ID)
    assert len(origins) == 1
    assert origins[0].artifact.sha256 == CHECKSUM

    async with session_factory() as session:
        counts = (
            await session.scalar(
                select(func.count()).select_from(SourceIngestionRunRecord)
            ),
            await session.scalar(
                select(func.count()).select_from(SourceArtifactRecord)
            ),
            await session.scalar(
                select(func.count()).select_from(SourceIngestionCandidateRecord)
            ),
            await session.scalar(
                select(func.count()).select_from(SourceArtifactOriginRecord)
            ),
        )
        proposed_artifact = await session.scalar(
            select(SourceIngestionCandidateRecord.artifact_id).where(
                SourceIngestionCandidateRecord.retrieval_status == "not_retrieved"
            )
        )
    assert counts == (1, 1, 2, 1)
    assert proposed_artifact is None


@pytest.mark.asyncio
async def test_artifact_is_reused_across_runs_and_conflicts_roll_back(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = PostgresSourceIngestionRepository(session_factory)
    await repository.save_ingestion(_ingestion())

    later = _ingestion(SECOND_RUN_ID, completed_at=NOW + timedelta(days=1))
    reused = await repository.save_ingestion(later)
    assert reused.artifacts_created == 0
    assert reused.artifacts_reused == 1
    artifact = await repository.get_artifact(CHECKSUM)
    assert artifact is not None
    assert artifact.first_seen_at == NOW
    assert artifact.last_seen_at == NOW + timedelta(days=1)

    conflicting_run = UUID("af884a90-ac70-4b2d-a28f-4c626047f67e")
    with pytest.raises(ValueError, match="conflicts"):
        await repository.save_ingestion(
            _ingestion(conflicting_run, storage_key="raw/conflicting.html")
        )
    assert await repository.get_run(conflicting_run) is None


@pytest.mark.asyncio
async def test_extracts_ingested_html_and_records_representation_metadata(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    html = (
        b'<html lang="en"><main id="wsc_main_content">'
        b"<h1>Consumer finance</h1><dl><dt>Loan amount</dt>"
        b"<dd>50,000 - 6,000,000 AMD</dd></dl></main></html>"
    )
    checksum = hashlib.sha256(html).hexdigest()
    store = LocalArtifactStore(tmp_path / "artifacts")
    artifact = await store.put(
        content=html,
        sha256=checksum,
        mime_type="text/html",
    )
    base = _ingestion()
    source = base.sources[0].model_copy(update={"artifact": artifact})
    candidate = base.candidates[0].model_copy(
        update={"content_sha256": checksum}
    )
    ingestion = base.model_copy(
        update={"sources": (source,), "candidates": (candidate, base.candidates[1])}
    )
    await PostgresSourceIngestionRepository(session_factory).save_ingestion(ingestion)
    extraction_repository = PostgresContentExtractionRepository(session_factory)
    extractor = DocumentContentExtractor(
        store,
        extraction_repository,
        clock=lambda: NOW,
    )

    first = await extractor.extract(source)
    repeated = await extractor.extract(source)
    persisted = await extraction_repository.get_extraction(first.extraction_id)

    assert persisted is not None
    assert persisted.representation_artifact.sha256 == (
        first.representation_artifact.sha256
    )
    assert repeated.representation_artifact.created is False
    assert first.blocks[1].label == "Loan amount"
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(ContentExtractionRecord)
        )
    assert count == 1
