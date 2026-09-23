CREATE TABLE IF NOT EXISTS semantic_extraction_batches (
    id bigserial PRIMARY KEY,
    product varchar(50) NOT NULL CHECK (
        product IN ('consumer_loan', 'mortgage')
    ),
    schema_version varchar(50) NOT NULL,
    prompt_version varchar(50) NOT NULL,
    model_name varchar(200) NOT NULL,
    content_fingerprint char(64) NOT NULL CHECK (
        content_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    response jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT semantic_extraction_batches_exact_uq UNIQUE (
        product,
        schema_version,
        prompt_version,
        model_name,
        content_fingerprint
    )
);
