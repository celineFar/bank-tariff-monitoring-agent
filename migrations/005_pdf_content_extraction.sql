ALTER TABLE content_extractions
    ADD COLUMN status varchar(30) NOT NULL DEFAULT 'success'
        CHECK (status IN ('success', 'needs_ocr')),
    ADD COLUMN page_count integer NOT NULL DEFAULT 0 CHECK (page_count >= 0),
    ADD COLUMN text_character_count bigint NOT NULL DEFAULT 0
        CHECK (text_character_count >= 0),
    ADD COLUMN block_count integer NOT NULL DEFAULT 0 CHECK (block_count >= 0),
    ADD COLUMN table_count integer NOT NULL DEFAULT 0 CHECK (table_count >= 0),
    ADD COLUMN needs_ocr boolean NOT NULL DEFAULT false,
    ADD COLUMN pages_requiring_ocr jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(pages_requiring_ocr) = 'array'),
    ADD COLUMN ocr_assessment jsonb NOT NULL
        DEFAULT '{"status":"success","pages_requiring_ocr":[],"reason":null,"page_reasons":{}}'::jsonb
        CHECK (jsonb_typeof(ocr_assessment) = 'object'),
    ADD CONSTRAINT content_extractions_ocr_status_consistent
        CHECK ((status = 'needs_ocr') = needs_ocr),
    ADD CONSTRAINT content_extractions_ocr_pages_consistent
        CHECK (
            (needs_ocr AND jsonb_array_length(pages_requiring_ocr) > 0)
            OR (NOT needs_ocr AND jsonb_array_length(pages_requiring_ocr) = 0)
        );

CREATE INDEX content_extractions_status_idx
    ON content_extractions (status, extracted_at DESC);

CREATE INDEX content_extractions_needs_ocr_idx
    ON content_extractions (needs_ocr, extracted_at DESC)
    WHERE needs_ocr;
