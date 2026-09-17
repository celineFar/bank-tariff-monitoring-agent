CREATE TABLE source_ingestion_runs (
    id uuid PRIMARY KEY,
    monitoring_run_id uuid REFERENCES monitoring_runs(id),
    status varchar(20) NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
    manifest_key text NOT NULL UNIQUE,
    started_at timestamptz NOT NULL,
    completed_at timestamptz NOT NULL CHECK (completed_at >= started_at),
    product_count integer NOT NULL CHECK (product_count >= 0),
    candidate_count integer NOT NULL CHECK (candidate_count >= 0),
    source_count integer NOT NULL CHECK (source_count >= 0),
    warning_count integer NOT NULL CHECK (warning_count >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX source_ingestion_runs_monitoring_run_idx
    ON source_ingestion_runs (monitoring_run_id);
CREATE INDEX source_ingestion_runs_completed_idx
    ON source_ingestion_runs (completed_at DESC);

CREATE TABLE source_artifacts (
    id uuid PRIMARY KEY,
    content_sha256 char(64) NOT NULL UNIQUE
        CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    storage_key text NOT NULL UNIQUE,
    mime_type varchar(255) NOT NULL,
    size_bytes bigint NOT NULL CHECK (size_bytes > 0),
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL CHECK (last_seen_at >= first_seen_at),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX source_artifacts_mime_type_idx ON source_artifacts (mime_type);

CREATE TABLE source_ingestion_products (
    ingestion_run_id uuid NOT NULL
        REFERENCES source_ingestion_runs(id) ON DELETE CASCADE,
    product_id varchar(100) NOT NULL,
    product_name varchar(250) NOT NULL,
    category varchar(20) NOT NULL CHECK (category IN ('consumer', 'mortgage')),
    crawl_status varchar(20) NOT NULL
        CHECK (crawl_status IN ('success', 'partial', 'failed')),
    candidate_count integer NOT NULL CHECK (candidate_count >= 0),
    stored_source_count integer NOT NULL CHECK (stored_source_count >= 0),
    warnings jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(warnings) = 'array'),
    errors jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(errors) = 'array'),
    PRIMARY KEY (ingestion_run_id, product_id)
);

CREATE INDEX source_ingestion_products_product_idx
    ON source_ingestion_products (product_id, ingestion_run_id);

CREATE TABLE source_ingestion_candidates (
    id uuid PRIMARY KEY,
    ingestion_run_id uuid NOT NULL
        REFERENCES source_ingestion_runs(id) ON DELETE CASCADE,
    product_id varchar(100) NOT NULL,
    candidate_type varchar(30) NOT NULL
        CHECK (candidate_type IN ('product_page', 'supporting_page', 'document', 'page')),
    origin varchar(20) NOT NULL
        CHECK (origin IN ('registry', 'page_link', 'sitemap')),
    original_url text NOT NULL,
    normalized_url text NOT NULL,
    discovery_path jsonb NOT NULL CHECK (jsonb_typeof(discovery_path) = 'array'),
    anchor_text text,
    title text,
    context text,
    match_signals jsonb NOT NULL CHECK (jsonb_typeof(match_signals) = 'array'),
    retrieval_status varchar(20) NOT NULL
        CHECK (retrieval_status IN ('retrieved', 'not_retrieved', 'failed')),
    status_code integer CHECK (status_code IS NULL OR status_code BETWEEN 100 AND 599),
    content_sha256 char(64)
        CHECK (content_sha256 IS NULL OR content_sha256 ~ '^[0-9a-f]{64}$'),
    mime_type varchar(255),
    artifact_id uuid REFERENCES source_artifacts(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_ingestion_candidates_identity_uq
        UNIQUE (ingestion_run_id, product_id, normalized_url, candidate_type),
    CONSTRAINT source_ingestion_candidates_artifact_match_ck CHECK (
        (
            retrieval_status = 'retrieved'
            AND artifact_id IS NOT NULL
            AND content_sha256 IS NOT NULL
            AND mime_type IS NOT NULL
        )
        OR (
            retrieval_status <> 'retrieved'
            AND artifact_id IS NULL
            AND content_sha256 IS NULL
            AND mime_type IS NULL
        )
    )
);

CREATE INDEX source_ingestion_candidates_product_status_idx
    ON source_ingestion_candidates (product_id, retrieval_status);
CREATE INDEX source_ingestion_candidates_url_idx
    ON source_ingestion_candidates (normalized_url);

CREATE TABLE source_artifact_origins (
    id uuid PRIMARY KEY,
    ingestion_run_id uuid NOT NULL
        REFERENCES source_ingestion_runs(id) ON DELETE CASCADE,
    artifact_id uuid NOT NULL REFERENCES source_artifacts(id),
    product_id varchar(100) NOT NULL,
    candidate_type varchar(30) NOT NULL
        CHECK (candidate_type IN ('product_page', 'supporting_page', 'document', 'page')),
    source_url text NOT NULL,
    final_url text NOT NULL,
    language varchar(35),
    referrer_urls jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(referrer_urls) = 'array'),
    retrieved_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_artifact_origins_identity_uq
        UNIQUE (
            ingestion_run_id,
            product_id,
            artifact_id,
            source_url,
            final_url
        )
);

CREATE INDEX source_artifact_origins_product_idx
    ON source_artifact_origins (product_id, retrieved_at DESC);
CREATE INDEX source_artifact_origins_artifact_idx
    ON source_artifact_origins (artifact_id);
CREATE INDEX source_artifact_origins_final_url_idx
    ON source_artifact_origins (final_url);
