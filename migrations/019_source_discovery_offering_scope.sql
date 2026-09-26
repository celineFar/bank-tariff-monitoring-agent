-- Scope source-discovery assessments to the offering they were made for.
--
-- "Current product" and "related product" are relative to one offering: the
-- Express mortgage table is the current product on the Express page and a
-- sibling on the primary-market page. The cache was keyed by product type only,
-- so an answer given for one mortgage offering was reused for every other
-- mortgage offering that showed the same content.
--
-- Rows written before this migration get offering_id '' and never match a real
-- offering; policy and prompt version 2 invalidate them as well.

ALTER TABLE source_discovery_assessments
    ADD COLUMN IF NOT EXISTS offering_id varchar(100) NOT NULL DEFAULT '';

ALTER TABLE source_discovery_assessments
    DROP CONSTRAINT IF EXISTS source_discovery_assessments_exact_uq;

ALTER TABLE source_discovery_assessments
    ADD CONSTRAINT source_discovery_assessments_exact_uq UNIQUE (
        product,
        offering_id,
        policy_version,
        prompt_version,
        model_name,
        content_fingerprint
    );

DROP INDEX IF EXISTS source_discovery_assessments_structural_idx;

CREATE INDEX IF NOT EXISTS source_discovery_assessments_structural_idx
    ON source_discovery_assessments (
        product,
        offering_id,
        policy_version,
        prompt_version,
        model_name,
        structural_fingerprint,
        updated_at DESC
    );

COMMENT ON COLUMN source_discovery_assessments.offering_id IS
    'The offering the assessment was made for; part of the cache key.';
