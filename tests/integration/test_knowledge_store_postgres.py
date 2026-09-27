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

from app.domain.knowledge import (
    EMBEDDING_DIMENSIONS,
    EmbeddedKnowledgeChunk,
    EmbeddedKnowledgeDocument,
)
from app.domain.models import ProductType
from tests.fixtures.knowledge import store_active_document

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
    product: ProductType | None = None,
) -> UUID:
    product = product or ProductType.CONSUMER_LOAN
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


@pytest.mark.asyncio
async def test_only_selected_offering_content_reaches_knowledge_chunks(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """SD7: the menu and a sibling product's table never reach the offering's index."""
    from app.domain.acquisition import SourceLocator, SourceType
    from app.domain.models import OfferingId
    from app.domain.normalization import (
        NormalizedBlock,
        NormalizedBlockType,
        NormalizedDocument,
        NormalizedSourceBundle,
        NormalizedTable,
        NormalizedTableCell,
        NormalizedTableRow,
        SourceReference,
    )
    from app.domain.source_discovery import (
        Authority,
        DecisionSource,
        DiscoveryScope,
        InformationRole,
        ProductAssociation,
        Relevance,
        SourceAssessment,
        SourceDiscoveryResult,
        TemporalStatus,
    )
    from app.services.knowledge_projection import KnowledgeProjectionService
    from app.services.source_selection import (
        build_selected_source_bundle,
        select_sources,
    )

    url = "https://ameriabank.am/en/personal/loans/mortgage/primary"

    def ref(item: str) -> SourceReference:
        return SourceReference(
            source_item_id=item,
            locator=SourceLocator(source_url=url, source_type=SourceType.PAGE),
        )

    def block(item: str, text_value: str) -> NormalizedBlock:
        return NormalizedBlock(
            id=item,
            type=NormalizedBlockType.PARAGRAPH,
            raw_text=text_value,
            text=text_value,
            heading_path=("Primary",),
            source_refs=(ref(item),),
        )

    cell = NormalizedTableCell(raw_text="12.5%", text="12.5%", source_refs=(ref("t1"),))
    page = NormalizedDocument(
        id="page:1",
        name="Primary Market Mortgage",
        source_url=url,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256="e" * 64,
        extraction_method="browser",
        blocks=(
            block("rate", "Nominal interest rate 12.9%"),
            block("menu", "Cards Deposits Transfers"),
        ),
        tables=(
            NormalizedTable(
                id="t1",
                title="Express Home Mortgage Loan",
                headers=("Rate",),
                rows=(NormalizedTableRow(id="r1", cells=(cell,)),),
                source_refs=(ref("t1"),),
            ),
        ),
    )

    def assessment(item, association, relevance, scope=DiscoveryScope.BLOCK):
        return SourceAssessment(
            source_id=f"page:1::x::{item}",
            document_id="page:1",
            scope=scope,
            product_association=association,
            role=InformationRole.PRICING,
            relevance=relevance,
            authority=Authority.OFFICIAL_PRODUCT_CONTENT,
            temporal_status=TemporalStatus.CURRENT,
            reason="fixture",
            decision_source=DecisionSource.LLM,
            input_fingerprint="a" * 64,
            structural_fingerprint="b" * 64,
            source_refs=(ref(item),),
        )

    bundle = NormalizedSourceBundle(
        canonical_url=url, acquisition_content_hash="d" * 64, documents=(page,)
    )
    discovery = SourceDiscoveryResult(
        product=ProductType.MORTGAGE,
        input_content_hash="d" * 64,
        policy_version="2",
        prompt_version="2",
        model_name="m",
        assessments=(
            assessment("rate", ProductAssociation.CURRENT_PRODUCT, Relevance.RELEVANT),
            assessment(
                "menu", ProductAssociation.GLOBAL_NAVIGATION, Relevance.IRRELEVANT
            ),
            assessment(
                "t1",
                ProductAssociation.RELATED_PRODUCT,
                Relevance.POSSIBLY_RELEVANT,
                DiscoveryScope.TABLE,
            ),
        ),
        llm_batch_count=1,
        reused_assessment_count=0,
    )
    run_id = await _create_run(session_factory, ProductType.MORTGAGE)
    (document,) = KnowledgeProjectionService().project_sources(
        run_id=run_id,
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        bundle=build_selected_source_bundle(bundle, discovery),
        retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        language="en",
        labels=select_sources(discovery).items,
    )
    await store_active_document(
        session_factory,
        EmbeddedKnowledgeDocument(
            **document.model_dump(exclude={"chunks"}),
            chunks=tuple(
                EmbeddedKnowledgeChunk(
                    **chunk.model_dump(),
                    embedding=tuple(0.01 for _ in range(EMBEDDING_DIMENSIONS)),
                )
                for chunk in document.chunks
            ),
        ),
    )

    async with session_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT c.content, c.metadata FROM knowledge_chunks c "
                    "JOIN knowledge_documents d ON d.id = c.document_id "
                    "WHERE d.offering_id = 'mortgage_primary' AND c.is_active"
                )
            )
        ).all()
    stored = "\n".join(row.content for row in rows)
    assert "Nominal interest rate 12.9%" in stored
    assert "Cards Deposits Transfers" not in stored
    assert "Express Home Mortgage Loan" not in stored
    assert all(
        row.metadata["product_associations"] == ["current_product"] for row in rows
    )
