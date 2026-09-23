-- Targeted offerings can run independently; a family-wide run conflicts with each.
-- PostgreSQL advisory locking in PostgresRunRepository.submit serializes the
-- cross-scope check before either form is inserted.
DROP INDEX IF EXISTS monitoring_runs_active_product_uq;

CREATE UNIQUE INDEX IF NOT EXISTS monitoring_runs_active_offering_uq
    ON monitoring_runs (product, offering_id)
    WHERE offering_id IS NOT NULL
      AND status IN ('queued', 'running', 'awaiting_review')
      AND trigger_type IN ('api', 'schedule', 'adk');

CREATE UNIQUE INDEX IF NOT EXISTS monitoring_runs_active_family_uq
    ON monitoring_runs (product)
    WHERE offering_id IS NULL
      AND status IN ('queued', 'running', 'awaiting_review')
      AND trigger_type IN ('api', 'schedule', 'adk');
