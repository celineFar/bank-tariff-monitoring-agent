"""Postgres storage for the semantic-extraction fix's Phase 7 (SE11, SE12)."""

import os
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.models import ProductType
from app.domain.semantic_extraction import (
    ExtractionBatchResponse,
    ExtractionField,
    ExtractionStatus,
    ModelFieldResult,
    RememberedReviewDecision,
    ValidatedFieldResult,
)
from app.repositories.review_memory import PostgresReviewDecisionMemory
from app.repositories.semantic_extraction import PostgresSemanticExtractionRepository

pytestmark = pytest.mark.postgres


async def _fresh_schema(url: str) -> None:
    connection = await asyncpg.connect(
        url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        await connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        for migration in sorted(Path("migrations").glob("*.sql")):
            await connection.execute(migration.read_text())
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_extraction_cache_is_keyed_by_prompt_and_keeps_answers_needing_review() -> (
    None
):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required")
    assert url.endswith("_test")
    await _fresh_schema(url)
    engine = create_async_engine(url)
    try:
        repository = PostgresSemanticExtractionRepository(async_sessionmaker(engine))
        response = ExtractionBatchResponse(
            results=(
                ModelFieldResult(
                    field=ExtractionField.TERM, status=ExtractionStatus.NOT_STATED
                ),
            )
        )
        key = {
            "product": ProductType.MORTGAGE,
            "schema_version": "6",
            "prompt_version": "6",
            "model_name": "model-a",
        }
        await repository.save(
            **key,
            values=[("a" * 64, response), ("b" * 64, response)],
            validation_statuses={"b" * 64: "review"},
        )
        found = await repository.get_exact(**key, fingerprints=["a" * 64, "b" * 64])
        assert set(found) == {"a" * 64, "b" * 64}
        assert (
            await repository.get_exact(
                **{**key, "model_name": "model-b"}, fingerprints=["a" * 64]
            )
            == {}
        )
        connection = await asyncpg.connect(
            url.replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            statuses = dict(
                await connection.fetch(
                    "SELECT prompt_fingerprint, validation_status "
                    "FROM semantic_extraction_batches"
                )
            )
        finally:
            await connection.close()
        assert statuses == {"a" * 64: "accepted", "b" * 64: "review"}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_review_decisions_are_found_by_prompt_or_by_result() -> None:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required")
    assert url.endswith("_test")
    await _fresh_schema(url)
    engine = create_async_engine(url)
    try:
        memory = PostgresReviewDecisionMemory(async_sessionmaker(engine))
        decision = RememberedReviewDecision(
            offering_id="overdraft",
            field=ExtractionField.GRACE_PERIOD_DAYS,
            prompt_fingerprint="c" * 64,
            result_fingerprint="d" * 64,
            decision=ValidatedFieldResult(
                field=ExtractionField.GRACE_PERIOD_DAYS,
                status=ExtractionStatus.FOUND,
                value=51,
                batch_id="memory:r1",
            ),
            reviewer="analyst",
            review_id="0b8f0000-0000-4000-8000-000000000001",
        )
        await memory.remember(decision)
        await memory.remember(decision)  # idempotent on the result key
        by_prompt = await memory.find(
            offering_id="overdraft",
            field=ExtractionField.GRACE_PERIOD_DAYS,
            prompt_fingerprints=["c" * 64],
            result_fingerprints=[],
        )
        by_result = await memory.find(
            offering_id="overdraft",
            field=ExtractionField.GRACE_PERIOD_DAYS,
            prompt_fingerprints=[],
            result_fingerprints=["d" * 64],
        )
        assert by_prompt is not None and by_prompt.decision.value == 51
        assert by_result is not None and by_result.reviewer == "analyst"
        assert (
            await memory.find(
                offering_id="credit_line",
                field=ExtractionField.GRACE_PERIOD_DAYS,
                prompt_fingerprints=["c" * 64],
                result_fingerprints=["d" * 64],
            )
            is None
        )
    finally:
        await engine.dispose()
