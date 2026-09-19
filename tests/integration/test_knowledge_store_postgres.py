import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

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

from app.config.models import RagSettings
from app.domain.knowledge import (
    EMBEDDING_DIMENSIONS,
    EmbeddedKnowledgeChunk,
    EmbeddedKnowledgeDocument,
)
from app.domain.models import ProductType
from app.domain.retrieval import (
    RetrievalRequest,
    RetrievalStatus,
    TariffField,
)
from app.repositories.knowledge_store import PostgresKnowledgeStore
from app.repositories.rag_retrieval import PostgresRagRetrievalRepository
from app.services.rag_retrieval import RagRetriever

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

    engine = create_async_engine(database_url, poolclass=NullPool)
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
                "TRUNCATE knowledge_chunks, knowledge_documents, "
                "monitoring_runs CASCADE"
            )
        )
    yield async_sessionmaker(database_engine, expire_on_commit=False)


async def _create_run(
    session_factory: async_sessionmaker[AsyncSession],
    product: ProductType = ProductType.CONSUMER_LOAN,
) -> UUID:
    run_id = uuid4()
    async with session_factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO monitoring_runs "
                "(id, trigger_type, product, status) "
                "VALUES (:id, 'user', :product, 'running')"
            ),
            {"id": run_id, "product": product.value},
        )
    return run_id


def _document(
    run_id: UUID,
    *,
    checksum: str = "a" * 64,
    content: str = "Nominal interest rate: 13.5%",
    include_fee_chunk: bool = False,
) -> EmbeddedKnowledgeDocument:
    chunks = [
        EmbeddedKnowledgeChunk(
            ordinal=0,
            content=content,
            page_start=3,
            page_end=3,
            section="Interest rate",
            language="en",
            extraction_method="digital_pdf",
            quality_score=0.98,
            embedding=tuple(0.01 for _ in range(EMBEDDING_DIMENSIONS)),
        )
    ]
    if include_fee_chunk:
        chunks.append(
            EmbeddedKnowledgeChunk(
                ordinal=1,
                content="Application fee: 5,000 AMD",
                page_start=4,
                page_end=4,
                section="Fees",
                language="en",
                extraction_method="digital_pdf",
                quality_score=0.97,
                embedding=tuple(0.02 for _ in range(EMBEDDING_DIMENSIONS)),
            )
        )
    return EmbeddedKnowledgeDocument(
        run_id=run_id,
        product=ProductType.CONSUMER_LOAN,
        document_key="consumer-loan-information-summary",
        document_name="Consumer Loan Information Summary",
        source_url="https://ameriabank.am/loans/consumer.pdf",
        final_url="https://www.ameriabank.am/loans/consumer.pdf",
        mime_type="application/pdf",
        content_sha256=checksum,
        retrieved_at=datetime(2026, 9, 16, 6, tzinfo=UTC),
        extraction_method="digital_pdf",
        quality_score=0.95,
        chunks=tuple(chunks),
    )


@pytest.mark.asyncio
async def test_unchanged_reingestion_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _create_run(session_factory)
    repository = PostgresKnowledgeStore(session_factory)
    document = _document(run_id)

    first = await repository.upsert_document(document)
    repeated = await repository.upsert_document(document)

    assert first.document_created is True
    assert first.chunks_created == 1
    assert repeated.document_id == first.document_id
    assert repeated.document_created is False
    assert repeated.chunks_created == 0
    assert repeated.chunks_updated == 1
    assert repeated.versions_retired == 0

    async with session_factory() as session:
        document_count = await session.scalar(
            text("SELECT count(*) FROM knowledge_documents")
        )
        chunk_count = await session.scalar(
            text("SELECT count(*) FROM knowledge_chunks")
        )
    assert document_count == 1
    assert chunk_count == 1


@pytest.mark.asyncio
async def test_changed_version_retires_old_chunks_but_preserves_history(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_run = await _create_run(session_factory)
    second_run = await _create_run(session_factory)
    repository = PostgresKnowledgeStore(session_factory)

    first = await repository.upsert_document(_document(first_run))
    changed = await repository.upsert_document(
        _document(
            second_run,
            checksum="b" * 64,
            content="Nominal interest rate: 14.0%",
        )
    )
    versions = await repository.list_document_versions(
        "ameria",
        ProductType.CONSUMER_LOAN,
        "consumer-loan-information-summary",
    )

    assert changed.document_id != first.document_id
    assert changed.versions_retired == 1
    assert changed.chunks_retired == 1
    assert len(versions) == 2
    assert [version.is_active for version in versions] == [False, True]

    async with session_factory() as session:
        states = (
            await session.execute(
                text(
                    "SELECT d.content_sha256, c.is_active "
                    "FROM knowledge_chunks c "
                    "JOIN knowledge_documents d ON d.id = c.document_id "
                    "ORDER BY d.content_sha256"
                )
            )
        ).all()
    assert states == [("a" * 64, False), ("b" * 64, True)]


@pytest.mark.asyncio
async def test_reingesting_same_version_retires_removed_chunks(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _create_run(session_factory)
    repository = PostgresKnowledgeStore(session_factory)

    await repository.upsert_document(_document(run_id, include_fee_chunk=True))
    result = await repository.upsert_document(_document(run_id))

    assert result.document_created is False
    assert result.chunks_retired == 1
    async with session_factory() as session:
        active_states = (
            await session.scalars(
                text("SELECT is_active FROM knowledge_chunks ORDER BY ordinal")
            )
        ).all()
    assert active_states == [True, False]


@pytest.mark.asyncio
async def test_vector_and_lexical_indexes_exist_and_vector_plan_uses_hnsw(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _create_run(session_factory)
    await PostgresKnowledgeStore(session_factory).upsert_document(_document(run_id))

    async with session_factory() as session, session.begin():
        indexes = set(
            (
                await session.scalars(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE tablename = 'knowledge_chunks'"
                    )
                )
            ).all()
        )
        await session.execute(text("SET LOCAL enable_seqscan = off"))
        query_vector = "[" + ",".join("0.01" for _ in range(EMBEDDING_DIMENSIONS)) + "]"
        plan_rows = (
            await session.execute(
                text(
                    "EXPLAIN SELECT id FROM knowledge_chunks "
                    "ORDER BY embedding <=> CAST(:embedding AS vector) LIMIT 1"
                ),
                {"embedding": query_vector},
            )
        ).all()
    plan = "\n".join(row[0] for row in plan_rows)

    assert "knowledge_chunks_search_gin_idx" in indexes
    assert "knowledge_chunks_embedding_hnsw_idx" in indexes
    assert "knowledge_chunks_embedding_hnsw_idx" in plan


class _QueryEmbeddingProvider:
    dimensions = EMBEDDING_DIMENSIONS

    async def embed_query(self, content: str) -> tuple[float, ...]:
        del content
        return (1.0, *(0.0 for _ in range(EMBEDDING_DIMENSIONS - 1)))


def _retrieval_document(
    run_id: UUID,
    *,
    product: ProductType,
    checksum: str,
    document_key: str,
    content: str,
    language: str,
    bank: str = "ameria",
) -> EmbeddedKnowledgeDocument:
    return EmbeddedKnowledgeDocument(
        run_id=run_id,
        bank=bank,
        product=product,
        document_key=document_key,
        document_name=f"{product.value} official tariff",
        source_url=f"https://ameriabank.am/{product.value}/tariff.pdf",
        final_url=f"https://www.ameriabank.am/{product.value}/tariff.pdf",
        mime_type="application/pdf",
        content_sha256=checksum,
        retrieved_at=datetime(2026, 9, 16, 6, tzinfo=UTC),
        extraction_method="digital_pdf",
        quality_score=0.97,
        chunks=(
            EmbeddedKnowledgeChunk(
                ordinal=0,
                content=content,
                page_start=2,
                page_end=2,
                section="Tariff",
                language=language,
                extraction_method="digital_pdf",
                quality_score=0.98,
                embedding=(1.0, *(0.0 for _ in range(EMBEDDING_DIMENSIONS - 1))),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_hybrid_retrieval_isolates_products_and_preserves_provenance(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    consumer_run = await _create_run(session_factory, ProductType.CONSUMER_LOAN)
    mortgage_run = await _create_run(session_factory, ProductType.MORTGAGE)
    other_bank_run = await _create_run(session_factory, ProductType.CONSUMER_LOAN)
    store = PostgresKnowledgeStore(session_factory)
    await store.upsert_document(
        _retrieval_document(
            consumer_run,
            product=ProductType.CONSUMER_LOAN,
            checksum="c" * 64,
            document_key="consumer-tariff",
            content="Consumer loan amount is up to 20,000,000 AMD.",
            language="en",
        )
    )
    await store.upsert_document(
        _retrieval_document(
            other_bank_run,
            product=ProductType.CONSUMER_LOAN,
            checksum="e" * 64,
            document_key="other-bank-consumer-tariff",
            content="Consumer loan amount is up to 99,000,000 AMD.",
            language="en",
            bank="other-bank",
        )
    )
    await store.upsert_document(
        _retrieval_document(
            mortgage_run,
            product=ProductType.MORTGAGE,
            checksum="d" * 64,
            document_key="mortgage-tariff",
            content="Հիփոթեքային վարկի ժամկետը մինչև 240 ամիս է",
            language="hy",
        )
    )
    retriever = RagRetriever(
        _QueryEmbeddingProvider(),
        PostgresRagRetrievalRepository(session_factory),
        RagSettings(retrieval_top_k=3, retrieval_min_score=0.25),
    )

    consumer = await retriever.retrieve(
        RetrievalRequest(
            query="consumer loan amount",
            bank="ameria",
            product=ProductType.CONSUMER_LOAN,
            fields=(TariffField.AMOUNT,),
        )
    )
    mortgage = await retriever.retrieve(
        RetrievalRequest(
            query="հիփոթեքային վարկի ժամկետը",
            bank="ameria",
            product=ProductType.MORTGAGE,
            fields=(TariffField.TERM,),
        )
    )

    assert consumer.status is RetrievalStatus.FOUND
    assert len(consumer.hits) == 1
    assert consumer.hits[0].document_checksum == "c" * 64
    assert consumer.hits[0].page_start == 2
    assert consumer.hits[0].section == "Tariff"
    assert mortgage.status is RetrievalStatus.FOUND
    assert len(mortgage.hits) == 1
    assert mortgage.hits[0].document_checksum == "d" * 64
    assert mortgage.hits[0].language == "hy"
