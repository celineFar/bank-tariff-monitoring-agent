# IXS06: embedding spend and the text-only lifecycle (IX5, IX6, IX7)

**Checks.**
1. A review-required run makes no embedding call and publishes its chunks without
   vectors.
2. The final approval carries a summary built from the final snapshot, and activates it.
3. A quota refusal publishes the accepted corpus as text, active at once.
4. `embed_missing` fills active chunks without vectors, in one provider batch.

**Run.** Unit: `test_ix5_…`, `test_ix6_final_decision_…`, `test_ix7_quota_refusal_…`.
Postgres: `test_ix6_approval_activates_the_summary_it_carries`,
`test_ix7_text_only_active_chunks_are_filled_by_embed_missing`.

**Pass when.** All pass; the usage ledger records no `indexing.embedding` call for a
review-required run.

**Result.** _Filled in Phase 6._
