-- Drill C4: allow the new offering id in the four CHECK constraints from 006.
-- Apply to the running DB: docker compose exec -T db psql -U tariff -d tariff_monitor < migrations/028_car_loan_offering.sql

ALTER TABLE monitoring_runs
    DROP CONSTRAINT IF EXISTS monitoring_runs_offering_product_check,
    ADD CONSTRAINT monitoring_runs_offering_product_check
    CHECK (
        offering_id IS NULL
        OR (product = 'consumer_loan' AND offering_id IN (
                'consumer_standard', 'overdraft', 'credit_line', 'online_consumer_finance', 'car_loan'))
        OR (product = 'mortgage' AND offering_id IN (
                'mortgage_online', 'mortgage_primary', 'mortgage_diaspora', 'mortgage_secondary_market',
                'mortgage_commercial', 'mortgage_express', 'mortgage_no_income_verification',
                'mortgage_renovation', 'mortgage_construction'))
    ) NOT VALID;

ALTER TABLE offering_executions
    DROP CONSTRAINT IF EXISTS offering_executions_offering_product_check,
    ADD CONSTRAINT offering_executions_offering_product_check
    CHECK (
        (product = 'consumer_loan' AND offering_id IN (
                'consumer_standard', 'overdraft', 'credit_line', 'online_consumer_finance', 'car_loan'))
        OR (product = 'mortgage' AND offering_id IN (
                'mortgage_online', 'mortgage_primary', 'mortgage_diaspora', 'mortgage_secondary_market',
                'mortgage_commercial', 'mortgage_express', 'mortgage_no_income_verification',
                'mortgage_renovation', 'mortgage_construction'))
    ) NOT VALID;

ALTER TABLE source_manifests
    DROP CONSTRAINT IF EXISTS source_manifests_offering_product_check,
    ADD CONSTRAINT source_manifests_offering_product_check
    CHECK (
        (product = 'consumer_loan' AND offering_id IN (
                'consumer_standard', 'overdraft', 'credit_line', 'online_consumer_finance', 'car_loan'))
        OR (product = 'mortgage' AND offering_id IN (
                'mortgage_online', 'mortgage_primary', 'mortgage_diaspora', 'mortgage_secondary_market',
                'mortgage_commercial', 'mortgage_express', 'mortgage_no_income_verification',
                'mortgage_renovation', 'mortgage_construction'))
    ) NOT VALID;

ALTER TABLE tariff_snapshots
    DROP CONSTRAINT IF EXISTS tariff_snapshots_offering_product_check,
    ADD CONSTRAINT tariff_snapshots_offering_product_check
    CHECK (
        offering_id IS NULL
        OR (product = 'consumer_loan' AND offering_id IN (
                'consumer_standard', 'overdraft', 'credit_line', 'online_consumer_finance', 'car_loan'))
        OR (product = 'mortgage' AND offering_id IN (
                'mortgage_online', 'mortgage_primary', 'mortgage_diaspora', 'mortgage_secondary_market',
                'mortgage_commercial', 'mortgage_express', 'mortgage_no_income_verification',
                'mortgage_renovation', 'mortgage_construction'))
    ) NOT VALID;
