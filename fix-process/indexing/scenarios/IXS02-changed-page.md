# IXS02: a changed page, over two accepted runs (IX1)

**Checks.** Two accepted publications of one offering, where the page changed (new
content-addressed key), a PDF disappeared, and the summary changed.

**Run.** `test_ix1_accepted_publication_replaces_the_whole_active_set`
(`tests/integration/test_indexing_fixes_postgres.py`).

**Pass when.** Exactly the second publication's documents are active: the new page
version and the new summary. The old page version, the vanished PDF and the old summary
are `retired`.

**Result.** _Filled in Phase 6._
