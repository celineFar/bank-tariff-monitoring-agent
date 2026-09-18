CREATE TABLE IF NOT EXISTS pdf_extraction_cache (
    id bigserial PRIMARY KEY,
    document_sha256 char(64) NOT NULL CHECK (
        document_sha256 ~ '^[0-9a-f]{64}$'
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
    CONSTRAINT pdf_extraction_cache_exact_uq UNIQUE (
        document_sha256,
        schema_version,
        prompt_version,
        model_name,
        content_fingerprint
    )
);
