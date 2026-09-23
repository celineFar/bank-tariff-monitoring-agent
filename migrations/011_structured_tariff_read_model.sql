-- Rebuildable, accepted-snapshot read projections. Existing tariff_snapshots remain
-- authoritative; publication code will maintain active flags transactionally.
CREATE TABLE offering_profiles (
    snapshot_id uuid PRIMARY KEY REFERENCES tariff_snapshots(id) ON DELETE CASCADE,
    bank varchar(100) NOT NULL,
    product varchar(50) NOT NULL,
    offering_id varchar(100) NOT NULL,
    display_name text NOT NULL,
    extracted_name text,
    formal_names jsonb NOT NULL DEFAULT '[]'::jsonb,
    aliases jsonb NOT NULL DEFAULT '[]'::jsonb,
    category varchar(50),
    purposes jsonb NOT NULL DEFAULT '[]'::jsonb,
    variants jsonb NOT NULL DEFAULT '[]'::jsonb,
    property_market varchar(50),
    attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
    accepted_at timestamptz NOT NULL,
    schema_version integer NOT NULL CHECK (schema_version > 0),
    is_active boolean NOT NULL DEFAULT false
);
CREATE INDEX offering_profiles_scope_idx
    ON offering_profiles (bank, product, offering_id, is_active, accepted_at DESC);

CREATE TABLE tariff_facts (
    id char(64) PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
    snapshot_id uuid NOT NULL REFERENCES offering_profiles(snapshot_id) ON DELETE CASCADE,
    offering_id varchar(100) NOT NULL,
    field_path varchar(150) NOT NULL,
    variant_key varchar(100) NOT NULL,
    status varchar(30) NOT NULL CHECK (status IN ('found', 'not_stated', 'ambiguous', 'conflicting')),
    value_json jsonb,
    number_value numeric,
    unit varchar(50),
    currency varchar(10),
    rate_basis varchar(20),
    fee_scope varchar(50),
    conditions jsonb NOT NULL DEFAULT '[]'::jsonb,
    taxonomy_version integer NOT NULL CHECK (taxonomy_version > 0),
    is_active boolean NOT NULL DEFAULT false,
    UNIQUE (snapshot_id, field_path, variant_key),
    CHECK (status <> 'found' OR value_json IS NOT NULL),
    CHECK (status <> 'not_stated' OR value_json IS NULL)
);
CREATE INDEX tariff_facts_scope_field_idx
    ON tariff_facts (offering_id, field_path, is_active, snapshot_id);
CREATE INDEX tariff_facts_rank_idx
    ON tariff_facts (field_path, currency, rate_basis, unit, number_value)
    WHERE is_active AND status = 'found' AND number_value IS NOT NULL;
CREATE INDEX tariff_facts_conditions_gin_idx
    ON tariff_facts USING gin (conditions);

CREATE TABLE fact_evidence (
    fact_id char(64) NOT NULL REFERENCES tariff_facts(id) ON DELETE CASCADE,
    evidence_id varchar(50) NOT NULL,
    quote text NOT NULL CHECK (length(quote) > 0),
    source_url text NOT NULL,
    source_item_id varchar(200) NOT NULL,
    source_document_key varchar(200),
    source_document_id uuid REFERENCES knowledge_documents(id) ON DELETE SET NULL,
    source_checksum char(64),
    locator jsonb NOT NULL CHECK (jsonb_typeof(locator) = 'object' AND locator <> '{}'::jsonb),
    authority varchar(100) NOT NULL,
    PRIMARY KEY (fact_id, evidence_id)
);
CREATE INDEX fact_evidence_id_idx ON fact_evidence (evidence_id);
CREATE INDEX fact_evidence_source_idx ON fact_evidence (source_document_id, source_item_id);

CREATE TABLE retrieval_units (
    id char(64) PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
    snapshot_id uuid NOT NULL REFERENCES offering_profiles(snapshot_id) ON DELETE CASCADE,
    offering_id varchar(100) NOT NULL,
    kind varchar(30) NOT NULL CHECK (kind IN ('profile', 'field_detail')),
    field_paths text[] NOT NULL DEFAULT '{}',
    fact_ids text[] NOT NULL DEFAULT '{}',
    evidence_ids text[] NOT NULL DEFAULT '{}',
    language varchar(35) NOT NULL,
    identity_text text NOT NULL DEFAULT '',
    alias_purpose_text text NOT NULL DEFAULT '',
    detail_text text NOT NULL DEFAULT '',
    content text NOT NULL CHECK (length(content) > 0),
    renderer_version integer NOT NULL CHECK (renderer_version > 0),
    content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', identity_text), 'A') ||
        setweight(to_tsvector('simple', alias_purpose_text), 'B') ||
        setweight(to_tsvector('simple', detail_text), 'C')
    ) STORED,
    embedding vector(768),
    is_active boolean NOT NULL DEFAULT false
);
CREATE INDEX retrieval_units_scope_idx
    ON retrieval_units (offering_id, kind, is_active, snapshot_id);
CREATE INDEX retrieval_units_fields_gin_idx ON retrieval_units USING gin (field_paths);
CREATE INDEX retrieval_units_search_gin_idx ON retrieval_units USING gin (search_vector);
CREATE INDEX retrieval_units_embedding_hnsw_idx
    ON retrieval_units USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

CREATE TABLE model_call_usage (
    id uuid PRIMARY KEY,
    call_id varchar(100) NOT NULL,
    attempt integer NOT NULL CHECK (attempt > 0),
    called_at timestamptz NOT NULL,
    stage varchar(100) NOT NULL,
    operation varchar(100) NOT NULL,
    model_id varchar(200) NOT NULL,
    billing_platform varchar(50) NOT NULL,
    run_id uuid REFERENCES monitoring_runs(id) ON DELETE SET NULL,
    offering_id varchar(100),
    request_id varchar(100),
    input_tokens bigint CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens bigint CHECK (output_tokens IS NULL OR output_tokens >= 0),
    input_count bigint CHECK (input_count IS NULL OR input_count >= 0),
    latency_ms bigint NOT NULL CHECK (latency_ms >= 0),
    outcome varchar(30) NOT NULL CHECK (outcome IN ('succeeded', 'failed', 'cache_hit')),
    error_class varchar(100),
    price_version varchar(100),
    input_rate_usd_per_million numeric,
    output_rate_usd_per_million numeric,
    estimated_cost_usd numeric,
    unknown_cost_reason varchar(100),
    UNIQUE (call_id, attempt),
    CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0),
    CHECK (estimated_cost_usd IS NOT NULL OR unknown_cost_reason IS NOT NULL)
);
CREATE INDEX model_call_usage_day_stage_idx
    ON model_call_usage (called_at, stage, model_id);
CREATE INDEX model_call_usage_run_idx ON model_call_usage (run_id, offering_id, called_at);
