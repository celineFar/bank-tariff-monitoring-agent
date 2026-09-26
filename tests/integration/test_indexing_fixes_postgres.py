"""Regression tests for the indexing fix plan (fix-process/indexing/), on PostgreSQL.

Each test names its plan item (IX*). They need TEST_DATABASE_URL, like the other
PostgreSQL integration tests, and skip without it.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.knowledge import (
    EMBEDDING_DIMENSIONS,
    EmbeddedKnowledgeChunk,
    EmbeddedKnowledgeDocument,
)
from app.domain.models import KnowledgeDocumentKind, OfferingId, ProductType
from app.domain.monitoring import (
    OfferingPublication,
    RunStatus,
    SnapshotAttempt,
    SnapshotStatus,
)
from app.domain.review import (
    ReviewDecision,
    ReviewDecisionType,
    ReviewSnapshotUpdate,
    ReviewStatus,
)
from app.repositories.monitoring import PostgresOfferingPublicationRepository
from app.repositories.rag_retrieval import HYBRID_SEARCH_SQL
from app.repositories.reviews import PostgresReviewRepository, ReviewConflictError
from tests.integration import test_monitoring_repository_postgres as repository_tests
from tests.integration.test_monitoring_repository_postgres import (
    _review_task,
    _running_offering,
    _snapshot,
)

# The PostgreSQL fixtures live in the repository test module (no conftest.py).
monitoring_database_engine = repository_tests.monitoring_database_engine
monitoring_session_factory = repository_tests.monitoring_session_factory

URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
# The fixture snapshot's evidence cites this document key and URL.
EVIDENCE_KEY = "synthetic-page"
SUMMARY_KEY = "offering-summary:consumer_standard"


def _doc(
    run_id: UUID,
    *,
    key: str = EVIDENCE_KEY,
    checksum: str = "a" * 64,
    contents: Sequence[str] = ("Nominal interest rate: 13.5%",),
    kind: KnowledgeDocumentKind = KnowledgeDocumentKind.SOURCE,
    embedded: bool = True,
) -> EmbeddedKnowledgeDocument:
    return EmbeddedKnowledgeDocument(
        run_id=run_id,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        document_kind=kind,
        document_key=key,
        document_name="Consumer Loans",
        source_url=URL,
        final_url=URL,
        mime_type="text/html",
        content_sha256=checksum,
        retrieved_at=datetime.now(UTC),
        extraction_method="browser",
        quality_score=0.99,
        chunks=tuple(
            EmbeddedKnowledgeChunk(
                ordinal=index,
                content=content,
                section="Rates",
                language="en",
                extraction_method="browser",
                quality_score=0.99,
                embedding=(
                    tuple(0.01 for _ in range(EMBEDDING_DIMENSIONS))
                    if embedded
                    else None
                ),
            )
            for index, content in enumerate(contents)
        ),
    )


def _summary(run_id: UUID, content: str, *, embedded: bool = True):
    return _doc(
        run_id,
        key=SUMMARY_KEY,
        checksum=("5" + content.encode().hex() + "0" * 64)[:64],
        contents=(content,),
        kind=KnowledgeDocumentKind.OFFERING_SUMMARY,
        embedded=embedded,
    )


async def _publish(
    session_factory: async_sessionmaker[AsyncSession],
    documents,
    *,
    accepted: bool = True,
) -> SnapshotAttempt:
    """Publish one offering run; `documents` builds the documents from its run id."""
    runs, run, execution = await _running_offering(session_factory)
    snapshot = _snapshot(run.id, execution.id)
    if not accepted:
        snapshot = snapshot.model_copy(
            update={"status": SnapshotStatus.REVIEW_REQUIRED, "accepted_at": None}
        )
    await PostgresOfferingPublicationRepository(session_factory).publish(
        OfferingPublication(
            offering_execution_id=execution.id,
            documents=tuple(documents(run.id)),
            snapshot=snapshot,
        )
    )
    # A run awaiting review blocks the offering's next run; the tests drive
    # reviews directly, so every run is closed after publishing.
    await runs.finish(run.id, RunStatus.SUCCEEDED if accepted else RunStatus.FAILED)
    return snapshot


async def _review(session_factory, snapshot: SnapshotAttempt, key: str):
    return await PostgresReviewRepository(session_factory).create(
        _review_task(
            snapshot.run_id,
            snapshot.offering_execution_id,
            snapshot.id,
            idempotency_key=key,
            created_at=snapshot.created_at,
        )
    )


def _approval(snapshot: SnapshotAttempt, **extra) -> ReviewSnapshotUpdate:
    return ReviewSnapshotUpdate(
        snapshot_id=snapshot.id,
        expected_canonical_sha256=snapshot.canonical_sha256,
        normalized_tariff=snapshot.normalized_tariff,
        semantic_extraction=snapshot.semantic_extraction,
        validation={"accepted": True, "review_signals": []},
        canonical_sha256=snapshot.canonical_sha256,
        ready_for_activation=True,
        **extra,
    )


async def _approve(session_factory, review, snapshot, **extra):
    return await PostgresReviewRepository(session_factory).approve_with_snapshot(
        review.id,
        ReviewDecision(decision_type=ReviewDecisionType.APPROVE),
        _approval(snapshot, **extra),
        reviewer="reviewer@example.test",
    )


async def _active(session_factory) -> list[tuple[str, str, tuple[str, ...]]]:
    """(kind, key, active chunk contents) per active document, sorted."""
    async with session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT d.document_kind, d.document_key,
                           array_agg(c.content ORDER BY c.ordinal)
                               FILTER (WHERE c.is_active) AS contents
                    FROM knowledge_documents AS d
                    LEFT JOIN knowledge_chunks AS c ON c.document_id = d.id
                    WHERE d.is_active
                    GROUP BY d.id, d.document_kind, d.document_key
                    ORDER BY d.document_kind, d.document_key
                    """
                )
            )
        ).all()
    return [(row[0], row[1], tuple(row[2] or ())) for row in rows]


@pytest.mark.asyncio
async def test_ix1_accepted_publication_replaces_the_whole_active_set(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _publish(
        monitoring_session_factory,
        lambda run_id: (
            _doc(run_id, key="page:1111", checksum="1" * 64, contents=("old page",)),
            _doc(run_id, key="document:2222", checksum="2" * 64, contents=("pdf",)),
            _summary(run_id, "summary one"),
        ),
    )
    await _publish(
        monitoring_session_factory,
        lambda run_id: (
            _doc(run_id, key="page:3333", checksum="3" * 64, contents=("new page",)),
            _summary(run_id, "summary two"),
        ),
    )

    assert await _active(monitoring_session_factory) == [
        ("offering_summary", SUMMARY_KEY, ("summary two",)),
        ("source", "page:3333", ("new page",)),
    ]


@pytest.mark.asyncio
async def test_ix2_review_required_run_never_rewrites_live_chunks(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _publish(
        monitoring_session_factory,
        lambda run_id: (_doc(run_id, contents=("live rate 13.5%", "live term")),),
    )
    await _publish(
        monitoring_session_factory,
        lambda run_id: (_doc(run_id, contents=("unreviewed rate 99%",)),),
        accepted=False,
    )

    assert await _active(monitoring_session_factory) == [
        ("source", EVIDENCE_KEY, ("live rate 13.5%", "live term")),
    ]
    async with monitoring_session_factory() as session:
        versions = await session.scalar(
            text("SELECT count(*) FROM knowledge_documents WHERE document_key = :key"),
            {"key": EVIDENCE_KEY},
        )
    assert versions == 2


@pytest.mark.asyncio
async def test_ix3_approval_activates_a_version_first_seen_by_an_earlier_run(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    def candidate(run_id):
        return (_doc(run_id, contents=("reviewed rate 14%",)),)

    first = await _publish(monitoring_session_factory, candidate, accepted=False)
    await _review(monitoring_session_factory, first, "ix3:first")
    second = await _publish(monitoring_session_factory, candidate, accepted=False)
    # Supersedes the first review (same field), and with it the shared version.
    review = await _review(monitoring_session_factory, second, "ix3:second")

    await _approve(monitoring_session_factory, review, second)

    assert await _active(monitoring_session_factory) == [
        ("source", EVIDENCE_KEY, ("reviewed rate 14%",)),
    ]


@pytest.mark.asyncio
async def test_ix4_accepted_publication_supersedes_older_pending_reviews(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    older = await _publish(
        monitoring_session_factory,
        lambda run_id: (_doc(run_id, contents=("older candidate",)),),
        accepted=False,
    )
    review = await _review(monitoring_session_factory, older, "ix4:older")

    await _publish(
        monitoring_session_factory,
        lambda run_id: (_doc(run_id, contents=("newer accepted",)),),
    )

    stored = await PostgresReviewRepository(monitoring_session_factory).get(review.id)
    assert stored is not None
    assert stored.status is ReviewStatus.SUPERSEDED


@pytest.mark.asyncio
async def test_ix4_approval_is_refused_when_a_newer_snapshot_was_accepted(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    older = await _publish(
        monitoring_session_factory,
        lambda run_id: (_doc(run_id, contents=("older candidate",)),),
        accepted=False,
    )
    await _publish(
        monitoring_session_factory,
        lambda run_id: (_doc(run_id, contents=("newer accepted",)),),
    )
    # A review raised for the older snapshot after the newer one was accepted:
    # the race the approval guard exists for.
    review = await _review(monitoring_session_factory, older, "ix4:race")

    with pytest.raises(ReviewConflictError, match="newer accepted snapshot"):
        await _approve(monitoring_session_factory, review, older)

    assert await _active(monitoring_session_factory) == [
        ("source", EVIDENCE_KEY, ("newer accepted",)),
    ]


@pytest.mark.asyncio
async def test_ix6_approval_activates_the_summary_it_carries(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _publish(
        monitoring_session_factory,
        lambda run_id: (
            _doc(run_id, contents=("accepted rate",)),
            _summary(run_id, "summary of the accepted values"),
        ),
    )
    pending = await _publish(
        monitoring_session_factory,
        lambda run_id: (_doc(run_id, checksum="b" * 64, contents=("reviewed rate",)),),
        accepted=False,
    )
    review = await _review(monitoring_session_factory, pending, "ix6")

    await _approve(
        monitoring_session_factory,
        review,
        pending,
        summary=_summary(
            pending.run_id, "summary of the reviewed values", embedded=False
        ),
    )

    assert await _active(monitoring_session_factory) == [
        ("offering_summary", SUMMARY_KEY, ("summary of the reviewed values",)),
        ("source", EVIDENCE_KEY, ("reviewed rate",)),
    ]


class _Provider:
    dimensions = EMBEDDING_DIMENSIONS
    model_name = "test-embedding"

    def __init__(self) -> None:
        self.calls: list[int] = []

    async def embed_documents(self, contents):
        self.calls.append(len(contents))
        return [tuple(0.02 for _ in range(EMBEDDING_DIMENSIONS)) for _ in contents]


@pytest.mark.xfail(
    strict=True, reason="IX7: chunks cannot be published without vectors"
)
@pytest.mark.asyncio
async def test_ix7_text_only_active_chunks_are_filled_by_embed_missing(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from app.repositories.knowledge_embeddings import (
        PostgresChunkEmbeddingRepository,
    )
    from app.services.knowledge_index import KnowledgeIndexer

    await _publish(
        monitoring_session_factory,
        lambda run_id: (
            _doc(run_id, contents=("rate", "term", "fees"), embedded=False),
        ),
    )
    assert await _active(monitoring_session_factory) == [
        ("source", EVIDENCE_KEY, ("rate", "term", "fees")),
    ]
    provider = _Provider()
    indexer = KnowledgeIndexer(
        provider,
        embeddings=PostgresChunkEmbeddingRepository(monitoring_session_factory),
    )

    filled = await indexer.embed_missing()

    assert filled == 3
    assert provider.calls == [3]
    async with monitoring_session_factory() as session:
        missing = await session.scalar(
            text(
                "SELECT count(*) FROM knowledge_chunks "
                "WHERE is_active AND embedding IS NULL"
            )
        )
    assert missing == 0


@pytest.mark.xfail(strict=True, reason="IX8: chunk indexes cover dead rows")
@pytest.mark.asyncio
async def test_ix8_vector_search_uses_a_partial_index_over_active_vectors(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _publish(monitoring_session_factory, lambda run_id: (_doc(run_id),))
    async with monitoring_session_factory() as session:
        definitions = dict(
            (
                await session.execute(
                    text(
                        "SELECT indexname, indexdef FROM pg_indexes "
                        "WHERE tablename = 'knowledge_chunks'"
                    )
                )
            ).all()
        )
    async with monitoring_session_factory() as session, session.begin():
        await session.execute(text("SET LOCAL enable_seqscan = off"))
        explained = await session.execute(
            text("EXPLAIN " + HYBRID_SEARCH_SQL),
            {
                "bank": "ameria",
                "product": ProductType.CONSUMER_LOAN.value,
                "lexical_query": "rate",
                "query_embedding": "["
                + ",".join("0.01" for _ in range(EMBEDDING_DIMENSIONS))
                + "]",
                "candidate_limit": 5,
                "offering_id": OfferingId.CONSUMER_STANDARD.value,
                "document_kinds": [],
                "filter_document_kinds": False,
            },
        )
        plan = "\n".join(explained.scalars())

    hnsw = definitions["knowledge_chunks_embedding_hnsw_idx"]
    assert "WHERE (is_active AND (embedding IS NOT NULL))" in hnsw
    assert "WHERE is_active" in definitions["knowledge_chunks_search_gin_idx"]
    assert "knowledge_chunks_embedding_hnsw_idx" in plan


@pytest.mark.asyncio
async def test_ix9_rejection_deletes_only_unshared_candidate_documents(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _publish(
        monitoring_session_factory,
        lambda run_id: (_doc(run_id, contents=("shared live content",)),),
    )
    pending = await _publish(
        monitoring_session_factory,
        lambda run_id: (
            _doc(run_id, contents=("shared live content",)),
            _doc(run_id, key="document:9999", checksum="9" * 64, contents=("new",)),
        ),
        accepted=False,
    )
    review = await _review(monitoring_session_factory, pending, "ix9")

    await PostgresReviewRepository(monitoring_session_factory).reject(
        review.id, reviewer="reviewer@example.test"
    )

    async with monitoring_session_factory() as session:
        states = (
            await session.execute(
                text(
                    "SELECT document_key, publication_state FROM knowledge_documents "
                    "ORDER BY document_key"
                )
            )
        ).all()
    assert [tuple(row) for row in states] == [(EVIDENCE_KEY, "active")]


@pytest.mark.asyncio
async def test_ix12_evidence_links_a_document_unchanged_since_an_earlier_run(
    monitoring_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = await _publish(monitoring_session_factory, lambda run_id: (_doc(run_id),))
    second = await _publish(monitoring_session_factory, lambda run_id: (_doc(run_id),))

    async def linked(snapshot_id) -> int:
        async with monitoring_session_factory() as session:
            return await session.scalar(
                text(
                    """
                    SELECT count(e.source_document_id)
                    FROM fact_evidence AS e
                    JOIN tariff_facts AS f ON f.id = e.fact_id
                    WHERE f.snapshot_id = :snapshot_id
                    """
                ),
                {"snapshot_id": snapshot_id},
            )

    # The second run re-cites the same, unchanged document version, so its
    # evidence links exactly as the first run's did.
    assert await linked(first.id) > 0
    assert await linked(second.id) == await linked(first.id)
