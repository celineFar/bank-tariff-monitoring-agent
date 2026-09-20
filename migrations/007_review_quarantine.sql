ALTER TABLE monitoring_runs
    DROP CONSTRAINT IF EXISTS monitoring_runs_status_check;

ALTER TABLE monitoring_runs
    ADD CONSTRAINT monitoring_runs_status_check
        CHECK (
            status IN (
                'queued',
                'running',
                'awaiting_review',
                'succeeded',
                'partial_success',
                'failed'
            )
        ) NOT VALID;

ALTER TABLE human_reviews
    ADD COLUMN offering_execution_id uuid
        REFERENCES offering_executions(id) ON DELETE CASCADE,
    ADD COLUMN snapshot_id uuid
        REFERENCES tariff_snapshots(id) ON DELETE CASCADE,
    ADD COLUMN product varchar(50),
    ADD COLUMN offering_id varchar(100),
    ADD COLUMN issue_scope varchar(500),
    ADD COLUMN candidates jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN decision jsonb,
    ADD COLUMN idempotency_key varchar(500),
    ADD COLUMN workflow_app_name varchar(200),
    ADD COLUMN workflow_user_id varchar(200),
    ADD COLUMN workflow_session_id varchar(500),
    ADD COLUMN workflow_invocation_id varchar(500),
    ADD COLUMN workflow_interrupt_id varchar(500),
    ADD COLUMN failure_detail varchar(2000),
    ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE human_reviews
    ADD CONSTRAINT human_reviews_status_check
        CHECK (
            status IN ('pending', 'approved', 'rejected', 'superseded', 'failed')
        ) NOT VALID;

CREATE UNIQUE INDEX human_reviews_idempotency_uq
    ON human_reviews (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX human_reviews_active_scope_uq
    ON human_reviews (product, offering_id, issue_scope)
    WHERE status = 'pending';

CREATE INDEX human_reviews_pending_created_idx
    ON human_reviews (status, created_at, id);

ALTER TABLE knowledge_documents
    ADD COLUMN publication_state varchar(50) NOT NULL DEFAULT 'active',
    ADD CONSTRAINT knowledge_documents_publication_state_check
        CHECK (
            publication_state IN (
                'active',
                'pending_review',
                'rejected',
                'superseded',
                'retired'
            )
        ) NOT VALID;

CREATE INDEX knowledge_documents_publication_state_idx
    ON knowledge_documents (publication_state, product, offering_id);
