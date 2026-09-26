-- The last good acquisition inventory of each seed URL, for the completeness
-- gate's regression check.
--
-- A render that loses most of a page -- three tariff tables down to none, ten
-- PDF links down to zero -- used to pass as long as some text remained, and the
-- run then extracted from what was left. The gate now compares each fresh
-- acquisition's counts with the last one that passed, and fails the offering on
-- a sharp drop.
--
-- Only an acquisition that passes the gate writes an inventory here, so a
-- degraded run can never become the next run's baseline. This is deliberately
-- separate from acquisition_snapshots, which every fresh acquisition replaces.
--
-- A drop keeps failing until an operator decides the page really changed and
-- runs `python -m scripts.reset_acquisition_baseline <offering_id>`. That
-- clears the inventory (NULL: no baseline) and stamps reset_by / reset_at; the
-- next passing run records a new inventory and the stamp stays as history.

CREATE TABLE IF NOT EXISTS acquisition_baselines (
    url_key      varchar(64) PRIMARY KEY,
    source_url   text NOT NULL,
    inventory    jsonb,
    recorded_at  timestamptz,
    reset_by     varchar(200),
    reset_at     timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    recorded_at_yerevan timestamp without time zone
        GENERATED ALWAYS AS (recorded_at AT TIME ZONE 'Asia/Yerevan') STORED,
    reset_at_yerevan timestamp without time zone
        GENERATED ALWAYS AS (reset_at AT TIME ZONE 'Asia/Yerevan') STORED,
    CONSTRAINT acquisition_baselines_url_key_check
        CHECK (url_key ~ '^[0-9a-f]{64}$'),
    CONSTRAINT acquisition_baselines_recorded_check
        CHECK ((inventory IS NULL) = (recorded_at IS NULL)),
    CONSTRAINT acquisition_baselines_reset_check
        CHECK ((reset_by IS NULL) = (reset_at IS NULL))
);

COMMENT ON TABLE acquisition_baselines IS
    'Last acquisition inventory per seed URL that passed the completeness gate.';

COMMENT ON COLUMN acquisition_baselines.inventory IS
    'AcquisitionInventory (main_chars, tables, pdf_links, payloads); NULL after a reset until the next passing run.';
