# IXS09: chunk shape (IX10, IX11, IX13, IX14)

**Checks.**
1. Every piece of a split table starts with its title and header row, within the size
   limit.
2. A chunk that starts mid-section starts with its heading breadcrumb.
3. Two summaries of the same values at different times hash equal.
4. Pieces of an oversized labelled unit keep the label metadata.
5. Chunk sizes outside 500–2,000 characters are rejected; there is no overlap setting.

**Run.** `tests/unit/test_indexing_fixes.py` (`test_ix10_…`, `test_ix11_…`, `test_ix13_…`,
`test_ix14_…`), plus the breadcrumb test added in Phase 2. Also re-project the 13 seed
captures offline and report chunk counts and the largest chunk.

**Pass when.** All pass; no chunk of the seed projection exceeds the configured size.

**Result.** _Filled in Phase 6._
