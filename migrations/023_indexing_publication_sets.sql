-- Indexing fix (fix-process/indexing/): immutable document versions, snapshot-owned
-- document sets, text-only content under review, partial retrieval indexes.

-- IX5/IX7: chunks of a review-required run (and of a quota-deferred run) are stored
-- without vectors; `embed_missing` fills them once they are active.
ALTER TABLE knowledge_chunks ALTER COLUMN embedding DROP NOT NULL;

-- IX2: a version is one projection of one source. The same raw bytes projected
-- into other chunks (another discovery selection, labels or projection code) is
-- another version, so a candidate can never rewrite live chunks. Rows written
-- before this migration carry zeros: the first projection after deploy is a new
-- version, and set replacement (IX1) retires the old one.
ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS projection_sha256 char(64) NOT NULL
        DEFAULT repeat('0', 64)
        CHECK (projection_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE knowledge_documents
    DROP CONSTRAINT IF EXISTS knowledge_documents_version_uq;
ALTER TABLE knowledge_documents
    ADD CONSTRAINT knowledge_documents_version_uq UNIQUE (
        bank, product, offering_id, document_kind, document_key,
        content_sha256, projection_sha256
    );

-- IX1/IX3/IX12: the document versions each snapshot was built from. Activation
-- makes an offering's active set exactly one snapshot's set; evidence links go
-- through it instead of the run that first saw a version.
CREATE TABLE IF NOT EXISTS snapshot_documents (
    snapshot_id uuid NOT NULL REFERENCES tariff_snapshots(id) ON DELETE CASCADE,
    document_id uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    PRIMARY KEY (snapshot_id, document_id)
);
CREATE INDEX IF NOT EXISTS snapshot_documents_document_idx
    ON snapshot_documents (document_id);

-- Active documents belong to their offering's latest accepted snapshot.
INSERT INTO snapshot_documents (snapshot_id, document_id)
SELECT latest.id, d.id
FROM knowledge_documents AS d
JOIN LATERAL (
    SELECT s.id
    FROM tariff_snapshots AS s
    WHERE s.status = 'accepted'
      AND lower(s.bank) = d.bank
      AND s.product = d.product
      AND s.offering_id = d.offering_id
    ORDER BY s.accepted_at DESC NULLS LAST, s.created_at DESC
    LIMIT 1
) AS latest ON true
WHERE d.is_active
ON CONFLICT DO NOTHING;

-- Documents awaiting review belong to the review-required snapshot of the run
-- that first saw them or last re-published them.
INSERT INTO snapshot_documents (snapshot_id, document_id)
SELECT s.id, d.id
FROM knowledge_documents AS d
JOIN tariff_snapshots AS s
  ON s.run_id IN (d.run_id, d.last_seen_run_id)
 AND s.offering_id = d.offering_id
 AND s.product = d.product
 AND s.status = 'review_required'
WHERE d.publication_state = 'pending_review'
ON CONFLICT DO NOTHING;

-- IX9: a document that was never published is deleted, not kept as `rejected` or
-- `superseded` (nothing reads those states). A manifest row outlives the document
-- it recorded, so its link becomes NULL instead of blocking the delete.
ALTER TABLE source_manifests
    DROP CONSTRAINT IF EXISTS source_manifests_document_id_fkey;
ALTER TABLE source_manifests
    ADD CONSTRAINT source_manifests_document_id_fkey
        FOREIGN KEY (document_id) REFERENCES knowledge_documents(id)
        ON DELETE SET NULL;

DELETE FROM knowledge_documents
WHERE publication_state IN ('rejected', 'superseded');

ALTER TABLE knowledge_documents
    DROP CONSTRAINT IF EXISTS knowledge_documents_publication_state_check;
ALTER TABLE knowledge_documents
    ADD CONSTRAINT knowledge_documents_publication_state_check
        CHECK (publication_state IN ('pending_review', 'active', 'retired'));

-- IX8: retrieval reads only active chunks, so the indexes hold only those. Dead
-- rows then never crowd the HNSW candidate list before the offering filter.
-- Queries must repeat these predicates verbatim for the planner to use them.
DROP INDEX IF EXISTS knowledge_chunks_embedding_hnsw_idx;
CREATE INDEX knowledge_chunks_embedding_hnsw_idx
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
    WHERE is_active AND embedding IS NOT NULL;

DROP INDEX IF EXISTS knowledge_chunks_search_gin_idx;
CREATE INDEX knowledge_chunks_search_gin_idx
    ON knowledge_chunks USING gin (search_vector)
    WHERE is_active;

-- The embedding sweep looks for active chunks still without a vector.
CREATE INDEX IF NOT EXISTS knowledge_chunks_missing_embedding_idx
    ON knowledge_chunks (document_id)
    WHERE is_active AND embedding IS NULL;
