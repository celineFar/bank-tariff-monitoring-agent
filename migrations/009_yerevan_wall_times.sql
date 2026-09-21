-- Keep the authoritative timestamptz instants and materialize their Yerevan wall times.
-- Generated columns backfill existing rows and follow future writes automatically.
-- ADK-owned session and event tables are outside this migration.

ALTER TABLE audit_events
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE human_reviews
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE human_reviews
    ADD COLUMN IF NOT EXISTS decided_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (decided_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE human_reviews
    ADD COLUMN IF NOT EXISTS updated_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (updated_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE knowledge_chunks
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE knowledge_chunks
    ADD COLUMN IF NOT EXISTS retired_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (retired_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE knowledge_chunks
    ADD COLUMN IF NOT EXISTS updated_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (updated_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS first_seen_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (first_seen_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS last_seen_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (last_seen_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS retired_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (retired_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS retrieved_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (retrieved_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS claimed_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (claimed_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS completed_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (completed_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS queued_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (queued_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS started_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (started_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS updated_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (updated_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE offering_executions
    ADD COLUMN IF NOT EXISTS completed_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (completed_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE offering_executions
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE offering_executions
    ADD COLUMN IF NOT EXISTS started_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (started_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE offering_executions
    ADD COLUMN IF NOT EXISTS updated_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (updated_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE pdf_extraction_cache
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE pdf_extraction_cache
    ADD COLUMN IF NOT EXISTS updated_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (updated_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE semantic_extraction_batches
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE semantic_extraction_batches
    ADD COLUMN IF NOT EXISTS updated_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (updated_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE source_discovery_assessments
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE source_discovery_assessments
    ADD COLUMN IF NOT EXISTS updated_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (updated_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE source_documents
    ADD COLUMN IF NOT EXISTS retrieved_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (retrieved_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE source_manifests
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE tariff_changes
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE tariff_snapshots
    ADD COLUMN IF NOT EXISTS accepted_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (accepted_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE tariff_snapshots
    ADD COLUMN IF NOT EXISTS created_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (created_at AT TIME ZONE 'Asia/Yerevan') STORED;
