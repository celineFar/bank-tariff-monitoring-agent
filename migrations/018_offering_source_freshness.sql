-- Say, on each offering execution, when the bank's page it used was fetched and
-- whether that fetch was reused from an earlier run.
--
-- Within ACQUISITION_FRESHNESS_HOURS a run serves the stored acquisition
-- instead of fetching the page again. That was recorded only as a trace
-- attribute, so a "no changes" answer from an hour-old fetch looked the same as
-- a fresh check. The chat now reads these columns and says which it was.

ALTER TABLE offering_executions
    ADD COLUMN IF NOT EXISTS source_retrieved_at timestamptz,
    ADD COLUMN IF NOT EXISTS acquisition_reused boolean;

ALTER TABLE offering_executions
    ADD COLUMN IF NOT EXISTS source_retrieved_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (source_retrieved_at AT TIME ZONE 'Asia/Yerevan') STORED;

COMMENT ON COLUMN offering_executions.source_retrieved_at IS
    'When the bank page this execution read was fetched (earlier than started_at when reused).';

COMMENT ON COLUMN offering_executions.acquisition_reused IS
    'True when the acquisition came from the freshness window instead of a new fetch.';
