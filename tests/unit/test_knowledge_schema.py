from pathlib import Path

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed

from app.domain.knowledge import EMBEDDING_DIMENSIONS
from app.repositories.knowledge_store import KnowledgeChunkRecord


def test_knowledge_chunk_schema_declares_vector_and_lexical_indexes() -> None:
    table = KnowledgeChunkRecord.__table__
    embedding_type = table.c.embedding.type

    assert isinstance(embedding_type, Vector)
    assert embedding_type.dim == EMBEDDING_DIMENSIONS
    assert isinstance(table.c.search_vector.computed, Computed)
    assert {index.name for index in table.indexes} >= {
        "knowledge_chunks_search_gin_idx",
        "knowledge_chunks_embedding_hnsw_idx",
    }


def test_migration_matches_the_repository_index_contract() -> None:
    migration = Path("migrations/002_rag_knowledge_store.sql").read_text(
        encoding="utf-8"
    )

    assert f"embedding vector({EMBEDDING_DIMENSIONS}) NOT NULL" in migration
    assert "USING gin (search_vector)" in migration
    assert "USING hnsw (embedding vector_cosine_ops)" in migration
