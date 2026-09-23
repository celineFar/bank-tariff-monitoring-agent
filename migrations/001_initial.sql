CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS monitoring_runs (
    id uuid PRIMARY KEY,
    trigger_type text NOT NULL CHECK (trigger_type IN ('user', 'schedule')),
    product text NOT NULL CHECK (product IN ('consumer_loan', 'mortgage')),
    query text,
    status text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    error_code text
);

CREATE TABLE IF NOT EXISTS tariff_snapshots (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL UNIQUE REFERENCES monitoring_runs(id),
    product text NOT NULL,
    normalized_tariff jsonb NOT NULL,
    evidence jsonb NOT NULL,
    accepted_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tariff_changes (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES monitoring_runs(id),
    previous_snapshot_id uuid REFERENCES tariff_snapshots(id),
    current_snapshot_id uuid NOT NULL REFERENCES tariff_snapshots(id),
    changes jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS human_reviews (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES monitoring_runs(id),
    reason_code text NOT NULL,
    evidence jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    reviewer text,
    comment text,
    decided_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_events (
    id bigserial PRIMARY KEY,
    run_id uuid REFERENCES monitoring_runs(id),
    event_type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
