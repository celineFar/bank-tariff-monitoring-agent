-- Keep vector model identity explicit so cosine search never mixes model spaces.
ALTER TABLE retrieval_units
    ADD COLUMN embedding_model varchar(200),
    ADD COLUMN embedding_dimensions integer CHECK (embedding_dimensions IS NULL OR embedding_dimensions = 768);
CREATE INDEX retrieval_units_vector_scope_idx
    ON retrieval_units (offering_id, embedding_model, is_active)
    WHERE embedding IS NOT NULL;
