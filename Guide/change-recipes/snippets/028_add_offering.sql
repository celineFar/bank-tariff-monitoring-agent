-- Dry-run 2026-09-28: applied after migrations 001-027 on a scratch pgvector:pg17 DB;
-- 'student_loan' inserts, an unknown id is still rejected.
-- Copy to migrations/028_<name>.sql, replace student_loan (consumer list) or add to the mortgage list.
-- Allow the new offering id `student_loan` (consumer_loan family).
-- The four offering/product CHECK constraints from 006 list every id.

ALTER TABLE monitoring_runs
    DROP CONSTRAINT IF EXISTS monitoring_runs_offering_product_check,
    ADD CONSTRAINT monitoring_runs_offering_product_check
    CHECK (
        offering_id IS NULL
        OR (
            product = 'consumer_loan'
            AND offering_id IN (
                'consumer_standard',
                'overdraft',
                'credit_line',
                'online_consumer_finance',
                'student_loan'
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

ALTER TABLE offering_executions
    DROP CONSTRAINT IF EXISTS offering_executions_offering_product_check,
    ADD CONSTRAINT offering_executions_offering_product_check
    CHECK (
        (
            product = 'consumer_loan'
            AND offering_id IN (
                'consumer_standard',
                'overdraft',
                'credit_line',
                'online_consumer_finance',
                'student_loan'
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

ALTER TABLE source_manifests
    DROP CONSTRAINT IF EXISTS source_manifests_offering_product_check,
    ADD CONSTRAINT source_manifests_offering_product_check
    CHECK (
        (
            product = 'consumer_loan'
            AND offering_id IN (
                'consumer_standard',
                'overdraft',
                'credit_line',
                'online_consumer_finance',
                'student_loan'
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

ALTER TABLE tariff_snapshots
    DROP CONSTRAINT IF EXISTS tariff_snapshots_offering_product_check,
    ADD CONSTRAINT tariff_snapshots_offering_product_check
    CHECK (
        offering_id IS NULL
        OR (
            product = 'consumer_loan'
            AND offering_id IN (
                'consumer_standard',
                'overdraft',
                'credit_line',
                'online_consumer_finance',
                'student_loan'
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
