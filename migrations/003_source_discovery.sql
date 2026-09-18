CREATE TABLE IF NOT EXISTS source_discovery_assessments (
    id bigserial PRIMARY KEY,
    product varchar(50) NOT NULL CHECK (
        product IN ('consumer_loan', 'mortgage')
    ),
    policy_version varchar(50) NOT NULL,
    prompt_version varchar(50) NOT NULL,
    model_name varchar(200) NOT NULL,
    source_id varchar(500) NOT NULL,
    content_fingerprint char(64) NOT NULL CHECK (
        content_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    structural_fingerprint char(64) NOT NULL CHECK (
        structural_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    assessment jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_discovery_assessments_exact_uq UNIQUE (
        product,
        policy_version,
        prompt_version,
        model_name,
        content_fingerprint
    )
);

CREATE INDEX IF NOT EXISTS source_discovery_assessments_structural_idx
    ON source_discovery_assessments (
        product,
        policy_version,
        prompt_version,
        model_name,
        structural_fingerprint,
        updated_at DESC
    );
