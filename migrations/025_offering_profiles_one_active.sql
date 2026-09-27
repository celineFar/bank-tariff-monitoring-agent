-- One active structured projection per offering (resolution-and-RAG fix RR29).
-- Publication already retires the previous profile under the offering lock;
-- this makes the invariant a database guarantee. It fails loudly if any
-- offering has more than one active profile today, rather than picking one.
DO $$
DECLARE
    duplicates text;
BEGIN
    SELECT string_agg(bank || '/' || product || '/' || offering_id, ', ')
    INTO duplicates
    FROM (
        SELECT bank, product, offering_id
        FROM offering_profiles
        WHERE is_active
        GROUP BY bank, product, offering_id
        HAVING count(*) > 1
    ) AS offending;
    IF duplicates IS NOT NULL THEN
        RAISE EXCEPTION 'offerings with more than one active profile: %', duplicates;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS offering_profiles_one_active_uq
    ON offering_profiles (bank, product, offering_id)
    WHERE is_active;
