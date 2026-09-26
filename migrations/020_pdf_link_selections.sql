-- Source discovery's decisions on linked PDFs, made from link metadata before
-- transcription: whether each admitted PDF is the offering's own document,
-- terms shared with other loans, another product's document, bank-wide
-- material, or unclear. Keyed by offering and a fingerprint of the link
-- metadata the decision was made from, so an unchanged link is never asked
-- about twice.

CREATE TABLE IF NOT EXISTS pdf_link_selections (
    id bigserial PRIMARY KEY,
    offering_id varchar(100) NOT NULL,
    policy_version varchar(50) NOT NULL,
    prompt_version varchar(50) NOT NULL,
    model_name varchar(200) NOT NULL,
    link_fingerprint char(64) NOT NULL CHECK (
        link_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    choice jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pdf_link_selections_uq UNIQUE (
        offering_id,
        policy_version,
        prompt_version,
        model_name,
        link_fingerprint
    )
);
