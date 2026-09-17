CREATE TABLE content_extractions (
    id uuid PRIMARY KEY,
    source_artifact_id uuid NOT NULL REFERENCES source_artifacts(id),
    product_id varchar(100) NOT NULL,
    source_url text NOT NULL,
    final_url text NOT NULL,
    language varchar(35),
    source_mime_type varchar(255) NOT NULL,
    extractor varchar(100) NOT NULL,
    extractor_version varchar(50) NOT NULL,
    representation_storage_key text NOT NULL,
    representation_sha256 char(64) NOT NULL
        CHECK (representation_sha256 ~ '^[0-9a-f]{64}$'),
    representation_size_bytes bigint NOT NULL CHECK (representation_size_bytes > 0),
    statistics jsonb NOT NULL CHECK (jsonb_typeof(statistics) = 'object'),
    warnings jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(warnings) = 'array'),
    extracted_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX content_extractions_source_artifact_idx
    ON content_extractions (source_artifact_id);
CREATE INDEX content_extractions_product_idx
    ON content_extractions (product_id, extracted_at DESC);
CREATE INDEX content_extractions_representation_idx
    ON content_extractions (representation_sha256);
