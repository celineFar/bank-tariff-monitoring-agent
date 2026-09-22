-- Content-addressed embedding reuse across documents, runs and offering versions.
CREATE TABLE embedding_cache (
    model_id varchar(200) NOT NULL,
    dimensions integer NOT NULL CHECK (dimensions > 0),
    task_type varchar(40) NOT NULL,
    content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    embedding vector(768) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (model_id, dimensions, task_type, content_sha256)
);
