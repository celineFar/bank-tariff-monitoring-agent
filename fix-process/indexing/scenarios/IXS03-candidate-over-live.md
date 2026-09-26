# IXS03: a review-required run over unchanged bytes (IX2)

**Checks.** An accepted run publishes a page; a review-required run then publishes the
same raw bytes (same `content_sha256`) projected into different chunks (a different
discovery selection).

**Run.** `test_ix2_review_required_run_never_rewrites_live_chunks` (Postgres) and
`test_ix2_same_source_bytes_with_other_chunks_is_another_version` (unit).

**Pass when.** The live chunks are unchanged, content and count, and the candidate is a
separate `knowledge_documents` row (a new version) that stays inactive.

**Result.** _Filled in Phase 6._
