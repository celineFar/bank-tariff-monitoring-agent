"""IXS08: migration 023 and one accepted publication, on a copy of the dev database.

    uv run python fix-process/indexing/scenarios/run_ixs08_replay.py

1. Rebuilds `ixs08_dev_copy` in the dev container from the Phase 0 dump
   (`fix-process/indexing/data/dev-db-before.dump`) and applies migration 023.
2. Replays the next accepted publication of `overdraft`, with no model call:
   - the documents are the offering's active *page and PDF* versions, read back
     from their rows (content, metadata and stored vectors), because a run on this
     branch produces no `api:*` documents (payload normalization was removed);
   - the snapshot is a copy of the latest accepted snapshot, with a new id, run
     and execution, and the offering summary is projected from it (text only);
   - it is published through `PostgresOfferingPublicationRepository`.
3. Records the counts before migration, after it, and after the publication, in
   `fix-process/indexing/data/ixs08-replay.json`.

The real dev database is never touched.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import load_seed_catalog  # noqa: E402
from app.domain.knowledge import (  # noqa: E402
    EmbeddedKnowledgeChunk,
    EmbeddedKnowledgeDocument,
)
from app.domain.models import (  # noqa: E402
    KnowledgeDocumentKind,
    OfferingId,
    ProductType,
)
from app.domain.monitoring import (  # noqa: E402
    OfferingPublication,
    RunCommand,
    RunStatus,
    RunTrigger,
)
from app.domain.semantic_extraction import SemanticExtractionResult  # noqa: E402
from app.repositories.monitoring import (  # noqa: E402
    PostgresOfferingPublicationRepository,
    PostgresRunRepository,
    PostgresSnapshotRepository,
)
from app.services.knowledge_projection import (  # noqa: E402
    KnowledgeProjectionService,
    OfferingSummaryProjector,
)
from app.services.snapshot_lifecycle import (  # noqa: E402
    canonical_sha256,
    canonical_tariff_payload,
)

CONTAINER = "bank-tariff-monitoring-agent-db-1"
DATABASE = "ixs08_dev_copy"
URL = f"postgresql+asyncpg://tariff:tariff@localhost:5434/{DATABASE}"
DUMP = ROOT / "fix-process/indexing/data/dev-db-before.dump"
# The dev database stopped at migration 015: 016-022 (review workflow columns
# dropped, acquisition baselines, source freshness, discovery offering scope, PDF
# link selections, extraction prompt cache and review memory, review evidence
# sets) are applied first, as a deployment would, then 023. All are idempotent.
PENDING = tuple(
    sorted(
        path
        for path in (ROOT / "migrations").glob("*.sql")
        if "016" <= path.name[:3] <= "022"
    )
)
MIGRATION = ROOT / "migrations/023_indexing_publication_sets.sql"
REPORT = ROOT / "fix-process/indexing/data/ixs08-replay.json"
OFFERING = OfferingId.OVERDRAFT

COUNTS = {
    "documents_by_state": """
        SELECT publication_state || '/' || is_active, count(*)
        FROM knowledge_documents GROUP BY 1 ORDER BY 1""",
    "chunks_by_active": """
        SELECT is_active::text, count(*) FROM knowledge_chunks GROUP BY 1 ORDER BY 1""",
    "active_api_documents": """
        SELECT 'n', count(*) FROM knowledge_documents
        WHERE is_active AND document_key LIKE 'api:%'""",
    "active_html_chunks": """
        SELECT 'n', count(*) FROM knowledge_chunks
        WHERE is_active AND content ~ '<(p|br|sup|span|div|strong|li)[ />]'""",
    "active_page_versions_per_url": """
        SELECT source_url, count(*) FROM knowledge_documents
        WHERE is_active AND document_kind = 'source' GROUP BY 1 ORDER BY 1""",
    "active_evidence_unlinked": """
        SELECT 'n', count(*) FROM fact_evidence e JOIN tariff_facts f ON f.id = e.fact_id
        WHERE f.is_active AND e.source_document_id IS NULL""",
    "active_evidence": """
        SELECT 'n', count(*) FROM fact_evidence e JOIN tariff_facts f ON f.id = e.fact_id
        WHERE f.is_active""",
    "active_chunks_without_vector": """
        SELECT 'n', count(*) FROM knowledge_chunks
        WHERE is_active AND embedding IS NULL""",
    "snapshot_sets": """
        SELECT s.status, count(*) FROM snapshot_documents sd
        JOIN tariff_snapshots s ON s.id = sd.snapshot_id GROUP BY 1 ORDER BY 1""",
}


def _psql(*args: str) -> None:
    subprocess.run(
        ["docker", "exec", CONTAINER, *args], check=True, capture_output=True
    )


def rebuild_copy() -> None:
    subprocess.run(
        ["docker", "cp", str(DUMP), f"{CONTAINER}:/tmp/ixs08.dump"], check=True
    )
    for path in (*PENDING, MIGRATION):
        subprocess.run(
            ["docker", "cp", str(path), f"{CONTAINER}:/tmp/ixs08-{path.name}"],
            check=True,
        )
    _psql("dropdb", "-U", "tariff", "--if-exists", DATABASE)
    _psql("createdb", "-U", "tariff", DATABASE)
    _psql("pg_restore", "-U", "tariff", "-d", DATABASE, "/tmp/ixs08.dump")


def migrate(*paths: Path) -> None:
    for path in paths:
        _psql(
            "psql", "-U", "tariff", "-d", DATABASE, "-v", "ON_ERROR_STOP=1", "-q",
            "-f", f"/tmp/ixs08-{path.name}",
        )  # fmt: skip


async def counts(sessions: async_sessionmaker) -> dict[str, Any]:
    result: dict[str, Any] = {}
    async with sessions() as session:
        for name, query in COUNTS.items():
            try:
                rows = (await session.execute(text(query))).all()
            except Exception as exc:  # snapshot_documents before 023
                await session.rollback()
                result[name] = f"n/a ({type(exc).__name__})"
                continue
            result[name] = {str(row[0]): row[1] for row in rows}
    return result


async def stored_documents(sessions: async_sessionmaker, run_id) -> tuple:
    """The offering's active page and PDF versions, read back from their rows."""
    async with sessions() as session:
        documents = (
            (
                await session.execute(
                    text(
                        """
                    SELECT * FROM knowledge_documents
                    WHERE is_active AND offering_id = :offering
                      AND document_kind = 'source'
                      AND document_key NOT LIKE 'api:%'
                    ORDER BY document_key
                    """
                    ),
                    {"offering": OFFERING.value},
                )
            )
            .mappings()
            .all()
        )
        rebuilt = []
        for row in documents:
            chunks = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT ordinal, content, page_start, page_end, section,
                               language, extraction_method, quality_score, metadata,
                               embedding::text AS embedding
                        FROM knowledge_chunks
                        WHERE document_id = :id AND is_active
                        ORDER BY ordinal
                        """
                        ),
                        {"id": row["id"]},
                    )
                )
                .mappings()
                .all()
            )
            rebuilt.append(
                EmbeddedKnowledgeDocument(
                    run_id=run_id,
                    bank=row["bank"],
                    product=ProductType(row["product"]),
                    offering_id=OFFERING,
                    document_kind=KnowledgeDocumentKind.SOURCE,
                    document_key=row["document_key"],
                    document_name=row["document_name"],
                    source_url=row["source_url"],
                    final_url=row["final_url"],
                    mime_type=row["mime_type"],
                    content_sha256=row["content_sha256"],
                    retrieved_at=row["retrieved_at"],
                    extraction_method=row["extraction_method"],
                    quality_score=row["quality_score"],
                    metadata=row["metadata"],
                    chunks=tuple(
                        EmbeddedKnowledgeChunk(
                            ordinal=chunk["ordinal"],
                            content=chunk["content"],
                            page_start=chunk["page_start"],
                            page_end=chunk["page_end"],
                            section=chunk["section"],
                            language=chunk["language"],
                            extraction_method=chunk["extraction_method"],
                            quality_score=chunk["quality_score"],
                            metadata=chunk["metadata"],
                            embedding=tuple(json.loads(chunk["embedding"]))
                            if chunk["embedding"]
                            else None,
                        )
                        for chunk in chunks
                    ),
                )
            )
    return tuple(rebuilt)


async def replay_publication(sessions: async_sessionmaker) -> dict[str, Any]:
    runs = PostgresRunRepository(sessions)
    submitted = await runs.submit(
        RunCommand(
            product=ProductType.CONSUMER_LOAN,
            offering_id=OFFERING,
            trigger=RunTrigger.API,
        )
    )
    claimed = await runs.claim(submitted.run.id, "ixs08-replay")
    assert claimed is not None, "the replay run could not be claimed"
    execution = await runs.create_offering_execution(
        submitted.run.id, ProductType.CONSUMER_LOAN, OFFERING
    )
    execution = await runs.start_offering_execution(execution.id)
    previous = await PostgresSnapshotRepository(sessions).get_latest_accepted(
        bank="ameria", product=ProductType.CONSUMER_LOAN, offering_id=OFFERING
    )
    assert previous is not None, "no accepted overdraft snapshot to replay"
    now = datetime.now(UTC)
    # The stored snapshot predates this branch's canonical form; today's
    # structured projector refuses it ("accepted snapshot and final semantic
    # extraction disagree"). The replay stores what this branch would write for
    # the same extraction: the payload re-canonicalized from it.
    extraction = SemanticExtractionResult.model_validate(previous.semantic_extraction)
    assert extraction.loan_product is not None
    payload = canonical_tariff_payload(extraction.loan_product)
    snapshot = previous.model_copy(
        update={
            "normalized_tariff": payload,
            "canonical_sha256": canonical_sha256(payload),
            "id": uuid4(),
            "run_id": submitted.run.id,
            "offering_execution_id": execution.id,
            "created_at": now,
            "accepted_at": now,
            "previous_accepted_snapshot_id": previous.id,
        }
    )
    documents = await stored_documents(sessions, submitted.run.id)
    # An accepted run also publishes the offering summary; built from the
    # snapshot as the pipeline does, text only (no model call): the embedding
    # sweep would fill its vector.
    summary = OfferingSummaryProjector(
        KnowledgeProjectionService(), load_seed_catalog()
    ).project(snapshot)
    documents = (*documents, EmbeddedKnowledgeDocument.text_only(summary))
    result = await PostgresOfferingPublicationRepository(sessions).publish(
        OfferingPublication(
            offering_execution_id=execution.id,
            documents=documents,
            snapshot=snapshot,
        )
    )
    await runs.finish(submitted.run.id, RunStatus.SUCCEEDED)
    async with sessions() as session:
        linked = (
            await session.execute(
                text(
                    """
                    SELECT count(e.source_document_id) AS linked,
                           count(*) - count(e.source_document_id) AS unlinked
                    FROM fact_evidence e JOIN tariff_facts f ON f.id = e.fact_id
                    WHERE f.snapshot_id = :id
                    """
                ),
                {"id": snapshot.id},
            )
        ).one()
        unlinked_keys = (
            await session.execute(
                text(
                    """
                    SELECT e.source_document_key, count(*)
                    FROM fact_evidence e JOIN tariff_facts f ON f.id = e.fact_id
                    WHERE f.snapshot_id = :id AND e.source_document_id IS NULL
                    GROUP BY 1 ORDER BY 1
                    """
                ),
                {"id": snapshot.id},
            )
        ).all()
    return {
        "previous_snapshot_id": str(previous.id),
        "replayed_snapshot_id": str(snapshot.id),
        "documents_published": [document.document_key for document in documents],
        "document_results": [
            item.model_dump(mode="json") for item in result.document_results
        ],
        "evidence_linked": linked.linked,
        "evidence_unlinked": linked.unlinked,
        "unlinked_by_document_key": {str(key): n for key, n in unlinked_keys},
    }


async def main() -> None:
    rebuild_copy()
    engine = create_async_engine(URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        report: dict[str, Any] = {"as_of": datetime.now(UTC).isoformat()}
        report["before_migration"] = await counts(sessions)
        await engine.dispose()
        migrate(*PENDING)
        migrate(MIGRATION)
        report["after_migration"] = await counts(sessions)
        report["publication"] = await replay_publication(sessions)
        report["after_publication"] = await counts(sessions)
    finally:
        await engine.dispose()
    REPORT.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
