-- Keep the most recent acquisition of each seed URL so a run asked again
-- minutes later does not fetch the bank again.
--
-- Two monitoring runs for the same offering, minutes apart, were re-fetching
-- the page, re-rendering it in a browser and re-downloading every linked PDF
-- to arrive at content the previous run had already acquired. Within
-- ACQUISITION_FRESHNESS_HOURS the pipeline now serves the stored page artifact
-- instead. Only acquisition is skipped: normalization onward still execute and
-- resolve from their own content-addressed caches.
--
-- One row per source URL, replaced on every fresh acquisition -- this is a
-- reuse window, not a history. The audited record of what each run saw stays in
-- source_manifests and knowledge_documents.
--
-- The primary key is a SHA-256 of the URL rather than the URL itself: seed URLs
-- carry query strings and can exceed what a btree key accepts. source_url is
-- kept beside it so the table reads plainly.

CREATE TABLE IF NOT EXISTS acquisition_snapshots (
    url_key      varchar(64) PRIMARY KEY,
    source_url   text NOT NULL,
    content_hash varchar(64) NOT NULL,
    retrieved_at timestamptz NOT NULL,
    artifact     jsonb NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT acquisition_snapshots_url_key_check
        CHECK (url_key ~ '^[0-9a-f]{64}$'),
    CONSTRAINT acquisition_snapshots_content_hash_check
        CHECK (content_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS acquisition_snapshots_retrieved_idx
    ON acquisition_snapshots (retrieved_at DESC);

COMMENT ON TABLE acquisition_snapshots IS
    'Most recent acquisition per seed URL, reused within the freshness window.';

COMMENT ON COLUMN acquisition_snapshots.content_hash IS
    'PageArtifact.content_hash: the page plus everything reached from it.';
