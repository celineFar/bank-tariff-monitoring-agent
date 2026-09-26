# IXS07: retrieval over partial indexes (IX8)

**Checks.**
1. The HNSW and GIN indexes on `knowledge_chunks` are partial (`is_active`, and for
   vectors `embedding IS NOT NULL`), and the hybrid search plan uses the HNSW index.
2. Dead rows do not change results: with 20× as many retired chunks as active ones
   (same offering, near-identical vectors), the top-k equals the top-k of a clean index.

**Run.** `test_ix8_vector_search_uses_a_partial_index_over_active_vectors`, plus the
recall check added in Phase 5.

**Pass when.** Both hold.

**Result.** _Filled in Phase 6._
