from pathlib import Path

from app.repositories.knowledge_records import KnowledgeChunkRecord


def test_knowledge_chunks_are_stored_as_text_only() -> None:
    """Chunks anchor evidence and are read by reviewers; nothing searches them."""
    table = KnowledgeChunkRecord.__table__

    assert "embedding" not in table.c
    assert "search_vector" not in table.c
    assert {index.name for index in table.indexes} == {
        "knowledge_chunks_document_location_idx"
    }


def test_migration_drops_the_legacy_rag_index() -> None:
    migration = Path("migrations/027_drop_legacy_rag_index.sql").read_text(
        encoding="utf-8"
    )

    for statement in (
        "DROP INDEX IF EXISTS knowledge_chunks_embedding_hnsw_idx;",
        "DROP INDEX IF EXISTS knowledge_chunks_search_gin_idx;",
        "DROP INDEX IF EXISTS knowledge_chunks_missing_embedding_idx;",
        "ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS embedding;",
        "ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS search_vector;",
        "DELETE FROM knowledge_documents WHERE document_kind = 'offering_summary';",
    ):
        assert statement in migration
