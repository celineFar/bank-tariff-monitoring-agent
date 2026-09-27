-- A lease for executing runs, and a durable request to stop one.
--
-- The process executing a run (worker or chat) refreshes `heartbeat_at` every
-- RUN_HEARTBEAT_SECONDS. A `running` run whose heartbeat (or, before the first
-- beat, its claim) is older than RUN_LEASE_SECONDS belongs to a process that is
-- gone, and any worker or chat may close it as `run.abandoned`. Before this, the
-- only recovery was a worker start 30 minutes later, so a killed process left
-- its offering blocked.
--
-- `cancel_requested_at` lets a process that does not own a run ask the owner
-- to stop it (Ctrl-C in a chat that is following a worker's run). The owner
-- reads it with each heartbeat and cancels its pipeline, which closes the run
-- as `run.cancelled`.

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz,
    ADD COLUMN IF NOT EXISTS cancel_requested_at timestamptz,
    ADD COLUMN IF NOT EXISTS cancel_requested_by varchar(200);

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS heartbeat_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (heartbeat_at AT TIME ZONE 'Asia/Yerevan') STORED;

ALTER TABLE monitoring_runs
    ADD COLUMN IF NOT EXISTS cancel_requested_at_yerevan timestamp without time zone
    GENERATED ALWAYS AS (cancel_requested_at AT TIME ZONE 'Asia/Yerevan') STORED;

COMMENT ON COLUMN monitoring_runs.heartbeat_at IS
    'Last lease renewal by the process executing the run; stale means the owner is gone.';

COMMENT ON COLUMN monitoring_runs.cancel_requested_at IS
    'Set when another process asked the owner to stop this run.';

COMMENT ON COLUMN monitoring_runs.cancel_requested_by IS
    'The claimed_by-style identity of the process that asked for the stop.';
