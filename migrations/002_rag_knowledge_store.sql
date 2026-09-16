CREATE TABLE knowledge_documents (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES monitoring_runs(id),
    last_seen_run_id uuid NOT NULL REFERENCES monitoring_runs(id),
    bank varchar(100) NOT NULL,
    product varchar(50) NOT NULL CHECK (product IN ('consumer_loan', 'mortgage')),
    document_key varchar(500) NOT NULL,
    document_name varchar(1000) NOT NULL,
    source_url text NOT NULL,
    final_url text NOT NULL,
    mime_type varchar(255) NOT NULL,
    content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    retrieved_at timestamptz NOT NULL,
    extraction_method varchar(100) NOT NULL,
    quality_score double precision CHECK (
        quality_score IS NULL OR quality_score BETWEEN 0 AND 1
    ),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_active boolean NOT NULL DEFAULT true,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    retired_at timestamptz,
    CONSTRAINT knowledge_documents_version_uq
        UNIQUE (bank, product, document_key, content_sha256)
);

CREATE INDEX knowledge_documents_identity_idx
    ON knowledge_documents (bank, product, document_key, is_active);
CREATE INDEX knowledge_documents_checksum_idx
    ON knowledge_documents (content_sha256);
CREATE INDEX knowledge_documents_final_url_idx
    ON knowledge_documents (final_url);

CREATE TABLE knowledge_chunks (
    id char(64) PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
    document_id uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    page_start integer CHECK (page_start IS NULL OR page_start >= 1),
    page_end integer CHECK (
        page_end IS NULL OR (page_start IS NOT NULL AND page_end >= page_start)
    ),
    section varchar(500),
    language varchar(35) NOT NULL,
    content text NOT NULL CHECK (length(content) > 0),
    content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    extraction_method varchar(100) NOT NULL,
    quality_score double precision CHECK (
        quality_score IS NULL OR quality_score BETWEEN 0 AND 1
    ),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', content)
    ) STORED,
    embedding vector(768) NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    retired_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT knowledge_chunks_document_ordinal_uq UNIQUE (document_id, ordinal)
);

CREATE INDEX knowledge_chunks_document_location_idx
    ON knowledge_chunks (document_id, page_start, section, language, is_active);
CREATE INDEX knowledge_chunks_search_gin_idx
    ON knowledge_chunks USING gin (search_vector);
CREATE INDEX knowledge_chunks_embedding_hnsw_idx
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
