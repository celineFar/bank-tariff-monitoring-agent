from pathlib import Path

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed

from app.domain.knowledge import EMBEDDING_DIMENSIONS
from app.repositories.knowledge_records import KnowledgeChunkRecord


def test_knowledge_chunk_schema_declares_vector_and_lexical_indexes() -> None:
    table = KnowledgeChunkRecord.__table__
    embedding_type = table.c.embedding.type

    assert isinstance(embedding_type, Vector)
    assert embedding_type.dim == EMBEDDING_DIMENSIONS
    assert isinstance(table.c.search_vector.computed, Computed)
    indexes = {index.name: index for index in table.indexes}
    assert set(indexes) >= {
        "knowledge_chunks_search_gin_idx",
        "knowledge_chunks_embedding_hnsw_idx",
    }
    # Partial, over active chunks only (migration 023, IX8).
    assert str(
        indexes["knowledge_chunks_embedding_hnsw_idx"].dialect_options["postgresql"][
            "where"
        ]
    ) == ("is_active AND embedding IS NOT NULL")
    assert (
        str(
            indexes["knowledge_chunks_search_gin_idx"].dialect_options["postgresql"][
                "where"
            ]
        )
        == "is_active"
    )
    assert table.c.embedding.nullable is True


def test_migration_matches_the_repository_index_contract() -> None:
    created = Path("migrations/002_rag_knowledge_store.sql").read_text(encoding="utf-8")
    current = Path("migrations/023_indexing_publication_sets.sql").read_text(
        encoding="utf-8"
    )

    assert f"embedding vector({EMBEDDING_DIMENSIONS})" in created
    assert "ALTER COLUMN embedding DROP NOT NULL" in current
    assert "USING gin (search_vector)\n    WHERE is_active;" in current
    assert (
        "USING hnsw (embedding vector_cosine_ops)\n"
        "    WHERE is_active AND embedding IS NOT NULL;" in current
    )
