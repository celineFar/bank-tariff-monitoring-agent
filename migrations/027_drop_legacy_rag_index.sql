-- The RAG answer path was removed: every question is answered from accepted,
-- typed facts (offering_profiles, tariff_facts, fact_evidence, retrieval_units).
--
-- knowledge_documents and knowledge_chunks stay, as text: a snapshot's document
-- set anchors each fact's evidence (version, checksum) and is what a reviewer
-- reads. Their vectors, full-text column and search indexes were read only by
-- the RAG retriever, and the offering-summary documents only by its answers.
DROP INDEX IF EXISTS knowledge_chunks_embedding_hnsw_idx;
DROP INDEX IF EXISTS knowledge_chunks_search_gin_idx;
DROP INDEX IF EXISTS knowledge_chunks_missing_embedding_idx;

ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS search_vector;

-- Chunks and snapshot links cascade; manifests and fact evidence keep their
-- rows with the document reference cleared.
DELETE FROM knowledge_documents WHERE document_kind = 'offering_summary';
