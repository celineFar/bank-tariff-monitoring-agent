-- Semantic-extraction fix, Phase 7 (SE11, SE12).
--
-- The batch cache is keyed by the fingerprint of exactly what a call sends:
-- model, generation settings, instruction and user prompt. Rows written before
-- this migration have no prompt fingerprint and are never matched again; they
-- expire in place. Every response is cached now, with whether it passed
-- validation, so a field that fails the same way on every run is not asked again.
ALTER TABLE semantic_extraction_batches
    ADD COLUMN IF NOT EXISTS prompt_fingerprint char(64) CHECK (
        prompt_fingerprint IS NULL OR prompt_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    ADD COLUMN IF NOT EXISTS validation_status varchar(20) NOT NULL DEFAULT 'accepted'
        CHECK (validation_status IN ('accepted', 'review'));

CREATE INDEX IF NOT EXISTS semantic_extraction_batches_prompt_idx
    ON semantic_extraction_batches (model_name, prompt_fingerprint)
    WHERE prompt_fingerprint IS NOT NULL;

-- A reviewer's decision on one field of one offering, remembered against what it
-- was a decision about: the call that produced the field (prompt fingerprint)
-- and the field's result itself (value and cited evidence). While either is
-- unchanged, a later run reuses the decision instead of asking again; evidence
-- IDs are content-based, so changed evidence re-opens the question.
CREATE TABLE IF NOT EXISTS review_decision_memory (
    id bigserial PRIMARY KEY,
    offering_id varchar(100) NOT NULL,
    field varchar(100) NOT NULL,
    prompt_fingerprint char(64) CHECK (
        prompt_fingerprint IS NULL OR prompt_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    result_fingerprint char(64) NOT NULL CHECK (
        result_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    decision jsonb NOT NULL,
    reviewer varchar(200),
    review_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT review_decision_memory_result_uq UNIQUE (
        offering_id,
        field,
        result_fingerprint
    )
);

CREATE INDEX IF NOT EXISTS review_decision_memory_prompt_idx
    ON review_decision_memory (offering_id, field, prompt_fingerprint)
    WHERE prompt_fingerprint IS NOT NULL;
