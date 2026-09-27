-- A run waiting for a person no longer blocks new runs of its scope.
--
-- 008 and 010 counted `awaiting_review` as active, so one unanswered review
-- stopped every later run of the offering -- and of its whole family for a
-- family-wide (scheduled) run -- until someone reviewed it. Monitoring now keeps
-- running: a newer candidate supersedes the waiting one's reviews, and a paused
-- run closes once none of its reviews is pending. Only queued and running runs
-- are exclusive.
DROP INDEX IF EXISTS monitoring_runs_active_offering_uq;
DROP INDEX IF EXISTS monitoring_runs_active_family_uq;

CREATE UNIQUE INDEX monitoring_runs_active_offering_uq
    ON monitoring_runs (product, offering_id)
    WHERE offering_id IS NOT NULL
      AND status IN ('queued', 'running')
      AND trigger_type IN ('api', 'schedule', 'adk');

CREATE UNIQUE INDEX monitoring_runs_active_family_uq
    ON monitoring_runs (product)
    WHERE offering_id IS NULL
      AND status IN ('queued', 'running')
      AND trigger_type IN ('api', 'schedule', 'adk');
