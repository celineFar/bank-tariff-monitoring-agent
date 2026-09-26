-- Review fix (fix-process/reviews/review-fix-plan.md).
--
-- One snapshot can raise two reviews of the same field for different reasons
-- (an OCR reading of `interest_rate` that is also a large rate change). The
-- pending-scope index and the supersede-on-create rule keyed on the field
-- alone, so the second review superseded the first; once a decision removes
-- only its own signal (RV6), the superseded review's signal could never be
-- cleared and the snapshot never activated. Pending reviews are now unique per
-- field *and* reason; a newer snapshot still supersedes every pending review of
-- the field from older snapshots (the repository's create).
DROP INDEX IF EXISTS human_reviews_active_scope_uq;

CREATE UNIQUE INDEX IF NOT EXISTS human_reviews_active_scope_reason_uq
    ON human_reviews (product, offering_id, issue_scope, reason_code)
    WHERE status = 'pending';
