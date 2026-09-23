ALTER TABLE monitoring_runs
    DROP CONSTRAINT IF EXISTS monitoring_runs_trigger_type_check;

ALTER TABLE monitoring_runs
    RENAME COLUMN finished_at TO completed_at;

ALTER TABLE monitoring_runs
    ALTER COLUMN started_at DROP NOT NULL,
    ALTER COLUMN started_at DROP DEFAULT;

ALTER TABLE monitoring_runs
    ADD COLUMN offering_id varchar(100),
    ADD COLUMN idempotency_key varchar(200),
    ADD COLUMN queued_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN failure_detail varchar(2000),
    ADD COLUMN summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN claimed_by varchar(200),
    ADD COLUMN claimed_at timestamptz,
    ADD COLUMN created_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE monitoring_runs
    ADD CONSTRAINT monitoring_runs_trigger_type_check
        CHECK (trigger_type IN ('user', 'api', 'schedule', 'adk')) NOT VALID,
    ADD CONSTRAINT monitoring_runs_status_check
        CHECK (
            status IN (
                'queued',
                'running',
                'succeeded',
                'partial_success',
                'failed'
            )
        ) NOT VALID,
    ADD CONSTRAINT monitoring_runs_offering_product_check
        CHECK (
            offering_id IS NULL
            OR (
                product = 'consumer_loan'
                AND offering_id IN (
                    'consumer_standard',
                    'overdraft',
                    'credit_line',
                    'online_consumer_finance'
                )
            )
            OR (
                product = 'mortgage'
                AND offering_id IN (
                    'mortgage_online',
                    'mortgage_primary',
                    'mortgage_diaspora',
                    'mortgage_secondary_market',
                    'mortgage_commercial',
                    'mortgage_express',
                    'mortgage_no_income_verification',
                    'mortgage_renovation',
                    'mortgage_construction'
                )
            )
        ) NOT VALID;

CREATE UNIQUE INDEX monitoring_runs_idempotency_uq
    ON monitoring_runs (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX monitoring_runs_active_product_uq
    ON monitoring_runs (product)
    WHERE status IN ('queued', 'running')
      AND trigger_type IN ('api', 'schedule', 'adk');

CREATE INDEX monitoring_runs_queue_idx
    ON monitoring_runs (status, queued_at, id);

CREATE TABLE offering_executions (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES monitoring_runs(id) ON DELETE CASCADE,
    product varchar(50) NOT NULL
        CHECK (product IN ('consumer_loan', 'mortgage')),
    offering_id varchar(100) NOT NULL,
    status varchar(50) NOT NULL
        CHECK (
            status IN (
                'pending',
                'running',
                'succeeded',
                'candidate_review',
                'failed'
            )
        ),
    current_stage varchar(100),
    started_at timestamptz,
    completed_at timestamptz,
    source_count integer NOT NULL DEFAULT 0 CHECK (source_count >= 0),
    document_count integer NOT NULL DEFAULT 0 CHECK (document_count >= 0),
    chunk_count integer NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
    warning_count integer NOT NULL DEFAULT 0 CHECK (warning_count >= 0),
    failure_count integer NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    review_count integer NOT NULL DEFAULT 0 CHECK (review_count >= 0),
    failure_code varchar(100),
    failure_detail varchar(2000),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT offering_executions_run_offering_uq
        UNIQUE (run_id, offering_id),
    CONSTRAINT offering_executions_offering_product_check
        CHECK (
            (
                product = 'consumer_loan'
                AND offering_id IN (
                    'consumer_standard',
                    'overdraft',
                    'credit_line',
                    'online_consumer_finance'
                )
            )
            OR (
                product = 'mortgage'
                AND offering_id IN (
                    'mortgage_online',
                    'mortgage_primary',
                    'mortgage_diaspora',
                    'mortgage_secondary_market',
                    'mortgage_commercial',
                    'mortgage_express',
                    'mortgage_no_income_verification',
                    'mortgage_renovation',
                    'mortgage_construction'
                )
            )
        )
);

CREATE INDEX offering_executions_run_status_idx
    ON offering_executions (run_id, status);

CREATE TABLE source_manifests (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES monitoring_runs(id) ON DELETE CASCADE,
    offering_execution_id uuid NOT NULL
        REFERENCES offering_executions(id) ON DELETE CASCADE,
    product varchar(50) NOT NULL
        CHECK (product IN ('consumer_loan', 'mortgage')),
    offering_id varchar(100) NOT NULL,
    source_url text NOT NULL,
    final_url text,
    document_key varchar(500),
    document_id uuid
        REFERENCES knowledge_documents(id),
    content_sha256 char(64)
        CHECK (
            content_sha256 IS NULL
            OR content_sha256 ~ '^[0-9a-f]{64}$'
        ),
    status varchar(50) NOT NULL
        CHECK (status IN ('indexed', 'unchanged', 'excluded', 'failed')),
    selected boolean NOT NULL DEFAULT false,
    reason_code varchar(100),
    warning_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_manifests_run_source_uq
        UNIQUE (run_id, offering_id, source_url, content_sha256),
    CONSTRAINT source_manifests_offering_product_check
        CHECK (
            (
                product = 'consumer_loan'
                AND offering_id IN (
                    'consumer_standard',
                    'overdraft',
                    'credit_line',
                    'online_consumer_finance'
                )
            )
            OR (
                product = 'mortgage'
                AND offering_id IN (
                    'mortgage_online',
                    'mortgage_primary',
                    'mortgage_diaspora',
                    'mortgage_secondary_market',
                    'mortgage_commercial',
                    'mortgage_express',
                    'mortgage_no_income_verification',
                    'mortgage_renovation',
                    'mortgage_construction'
                )
            )
        )
);

CREATE INDEX source_manifests_run_offering_idx
    ON source_manifests (run_id, offering_id, status);

ALTER TABLE tariff_snapshots
    DROP CONSTRAINT IF EXISTS tariff_snapshots_run_id_key;

ALTER TABLE tariff_snapshots
    ALTER COLUMN accepted_at DROP NOT NULL,
    ALTER COLUMN accepted_at DROP DEFAULT;

ALTER TABLE tariff_snapshots
    ADD COLUMN offering_execution_id uuid
        REFERENCES offering_executions(id) ON DELETE CASCADE,
    ADD COLUMN bank varchar(100) NOT NULL DEFAULT 'ameria',
    ADD COLUMN offering_id varchar(100),
    ADD COLUMN status varchar(50) NOT NULL DEFAULT 'accepted',
    ADD COLUMN semantic_extraction jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN validation jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN canonical_sha256 char(64),
    ADD COLUMN previous_accepted_snapshot_id uuid
        REFERENCES tariff_snapshots(id),
    ADD COLUMN created_at timestamptz NOT NULL DEFAULT now(),
    ADD CONSTRAINT tariff_snapshots_status_check
        CHECK (
            status IN (
                'candidate',
                'accepted',
                'review_required',
                'rejected'
            )
        ) NOT VALID,
    ADD CONSTRAINT tariff_snapshots_acceptance_time_check
        CHECK (
            (status = 'accepted' AND accepted_at IS NOT NULL)
            OR (status <> 'accepted' AND accepted_at IS NULL)
        ) NOT VALID,
    ADD CONSTRAINT tariff_snapshots_offering_product_check
        CHECK (
            offering_id IS NULL
            OR (
                product = 'consumer_loan'
                AND offering_id IN (
                    'consumer_standard',
                    'overdraft',
                    'credit_line',
                    'online_consumer_finance'
                )
            )
            OR (
                product = 'mortgage'
                AND offering_id IN (
                    'mortgage_online',
                    'mortgage_primary',
                    'mortgage_diaspora',
                    'mortgage_secondary_market',
                    'mortgage_commercial',
                    'mortgage_express',
                    'mortgage_no_income_verification',
                    'mortgage_renovation',
                    'mortgage_construction'
                )
            )
        ) NOT VALID,
    ADD CONSTRAINT tariff_snapshots_run_offering_uq
        UNIQUE (run_id, offering_id);

CREATE INDEX tariff_snapshots_latest_accepted_idx
    ON tariff_snapshots (
        bank,
        product,
        offering_id,
        accepted_at DESC,
        id DESC
    )
    WHERE status = 'accepted';

ALTER TABLE tariff_changes
    ADD COLUMN product varchar(50),
    ADD COLUMN offering_id varchar(100),
    ADD COLUMN change_count integer NOT NULL DEFAULT 0
        CHECK (change_count >= 0),
    ADD CONSTRAINT tariff_changes_current_snapshot_uq
        UNIQUE (current_snapshot_id);

CREATE INDEX tariff_changes_run_offering_idx
    ON tariff_changes (run_id, offering_id, created_at);

ALTER TABLE audit_events
    ADD COLUMN offering_execution_id uuid
        REFERENCES offering_executions(id) ON DELETE SET NULL,
    ADD COLUMN reason_code varchar(100);

CREATE INDEX audit_events_run_offering_idx
    ON audit_events (run_id, offering_execution_id, created_at);

ALTER TABLE knowledge_documents
    DROP CONSTRAINT IF EXISTS knowledge_documents_version_uq;

ALTER TABLE knowledge_documents
    ADD COLUMN offering_id varchar(100),
    ADD COLUMN document_kind varchar(50) NOT NULL DEFAULT 'source',
    ADD CONSTRAINT knowledge_documents_kind_check
        CHECK (document_kind IN ('source', 'offering_summary')),
    ADD CONSTRAINT knowledge_documents_version_uq
        UNIQUE (
            bank,
            product,
            offering_id,
            document_kind,
            document_key,
            content_sha256
        );

CREATE INDEX knowledge_documents_offering_active_idx
    ON knowledge_documents (
        bank,
        product,
        offering_id,
        document_kind,
        is_active
    );

CREATE INDEX knowledge_chunks_active_document_idx
    ON knowledge_chunks (document_id, is_active);
