DROP INDEX IF EXISTS monitoring_runs_active_product_uq;

CREATE UNIQUE INDEX monitoring_runs_active_product_uq
    ON monitoring_runs (product)
    WHERE status IN ('queued', 'running', 'awaiting_review')
      AND trigger_type IN ('api', 'schedule', 'adk');
