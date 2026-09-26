"""The source-discovery cache is scoped to the offering (migration 019)."""

import os
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.normalization import SourceReference
from app.domain.source_discovery import (
    Authority,
    DecisionSource,
    DiscoveryScope,
    InformationRole,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    TemporalStatus,
)
from app.repositories.source_discovery import PostgresSourceDiscoveryRepository

pytestmark = pytest.mark.postgres

URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"


def _assessment(association: ProductAssociation) -> SourceAssessment:
    return SourceAssessment(
        source_id="page::table::t2",
        document_id="page",
        scope=DiscoveryScope.TABLE,
        product_association=association,
        role=InformationRole.PRICING,
        relevance=Relevance.RELEVANT,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        reason="Express mortgage table",
        decision_source=DecisionSource.LLM,
        input_fingerprint="a" * 64,
        structural_fingerprint="b" * 64,
        source_refs=(
            SourceReference(
                source_item_id="t2",
                locator=SourceLocator(source_url=URL, source_type=SourceType.PAGE),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_the_same_content_is_cached_per_offering() -> None:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required")
    assert url.endswith("_test")
    connection = await asyncpg.connect(
        url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        await connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        for migration in sorted(Path("migrations").glob("*.sql")):
            await connection.execute(migration.read_text())
        # Migration 019 is safe to apply again.
        await connection.execute(
            Path("migrations/019_source_discovery_offering_scope.sql").read_text()
        )
    finally:
        await connection.close()
    engine = create_async_engine(url)
    try:
        repository = PostgresSourceDiscoveryRepository(async_sessionmaker(engine))
        versions = {
            "product": ProductType.MORTGAGE,
            "policy_version": "2",
            "prompt_version": "2",
            "model_name": "gemini-3.1-flash-lite",
        }
        await repository.save(
            **versions,
            offering_id="mortgage_express",
            assessments=(_assessment(ProductAssociation.CURRENT_PRODUCT),),
        )
        await repository.save(
            **versions,
            offering_id="mortgage_primary",
            assessments=(_assessment(ProductAssociation.RELATED_PRODUCT),),
        )

        express = await repository.get_exact(
            **versions, offering_id="mortgage_express", content_fingerprints=("a" * 64,)
        )
        primary = await repository.get_exact(
            **versions, offering_id="mortgage_primary", content_fingerprints=("a" * 64,)
        )
        other = await repository.get_structural_priors(
            **versions,
            offering_id="mortgage_renovation",
            structural_fingerprints=("b" * 64,),
        )

        assert (
            express["a" * 64].product_association is ProductAssociation.CURRENT_PRODUCT
        )
        assert (
            primary["a" * 64].product_association is ProductAssociation.RELATED_PRODUCT
        )
        assert other == {}
    finally:
        await engine.dispose()
