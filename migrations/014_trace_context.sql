-- Carry W3C trace context across the process boundaries a run already crosses.
--
-- A run is submitted by the API, the scheduler, or the CLI and executed by the
-- worker that claims it; a run paused for human review resumes inside whichever
-- process served the decision. Ambient OpenTelemetry context does not survive
-- either handoff, so the traceparent travels with the row, exactly as the run
-- state does. Restoring it makes every segment share one trace id.
--
-- A W3C traceparent is a fixed 55-character string:
--   version(2) "-" trace-id(32) "-" parent-id(16) "-" flags(2)
-- The column is nullable: rows written while tracing is disabled carry no
-- context, and the reader treats that as "start a new trace".

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS trace_parent varchar(55);

ALTER TABLE human_reviews
    ADD COLUMN IF NOT EXISTS trace_parent varchar(55);

COMMENT ON COLUMN monitoring_runs.trace_parent IS
    'W3C traceparent captured at submit, restored by the worker on claim.';

COMMENT ON COLUMN human_reviews.trace_parent IS
    'W3C traceparent captured when the workflow paused, restored on resume.';
