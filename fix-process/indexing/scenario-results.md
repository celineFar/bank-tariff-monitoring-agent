# Indexing fix: scenario results

Date: 2026-09-26 · Branch: `fix/indexing` · Plan: [indexing-fix-plan.md](indexing-fix-plan.md).
Scenario definitions: [scenarios/](scenarios/). All offline, at $0 in model spend;
IXS10 was not run (it needs budget approval).

| ID | Scenario | Result |
|---|---|---|
| IXS01 | Test suite | **PASS**: 1087 passed, 5 skipped; only the 4 known Gemini-key tests fail (baseline 1064 passed) |
| IXS02 | Changed page over two accepted runs (IX1) | **PASS** |
| IXS03 | Review-required run over unchanged bytes (IX2) | **PASS** |
| IXS04 | Approving content first seen by an earlier run (IX3) | **PASS** |
| IXS05 | Stale reviews (IX4) | **PASS** |
| IXS06 | Embedding spend and the text-only lifecycle (IX5–IX7) | **PASS** |
| IXS07 | Retrieval over partial indexes (IX8) | **PASS**, with one finding (see below) |
| IXS08 | Migration 023 on a dev copy, then one accepted publication | **PASS**, with one deployment finding (dev DB at 015) |
| IXS09 | Chunk shape on the 13 seeds (IX10, IX11, IX13, IX14) | **PASS** |
| IXS10 | Live overdraft run | **Not run** (needs budget approval) |

## IXS01: the test suite

```bash
TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_acquisition_test \
  uv run pytest tests/unit tests/integration -q
```

**1087 passed, 5 skipped, 1 failed + 3 errors.** The four are the known tests that need
a live Gemini key (`test_agent_stream`, and `test_server_e2e` ×3), the same as the
Phase 0 baseline (1064 passed). No `xfail` is left in `tests/unit/test_indexing_fixes.py`
or `tests/integration/test_indexing_fixes_postgres.py`. `ruff check` and
`ruff format --check` are clean.

## IXS02–IXS06: behaviour, one test each

| Scenario | Tests (all passing) |
|---|---|
| IXS02 | `test_ix1_accepted_publication_replaces_the_whole_active_set`: after the second accepted run, exactly the new page and new summary are active; the old page version, the vanished PDF and the old summary are retired |
| IXS03 | `test_ix2_review_required_run_never_rewrites_live_chunks` (the live chunks keep "live rate 13.5%" and their count; the candidate is a second row); `test_ix2_same_source_bytes_with_other_chunks_is_another_version` |
| IXS04 | `test_ix3_approval_activates_a_version_first_seen_by_an_earlier_run`: run A's review is superseded by run B's, with a shared version; approving B activates it |
| IXS05 | `test_ix4_accepted_publication_supersedes_older_pending_reviews`; `test_ix4_approval_is_refused_when_a_newer_snapshot_was_accepted` (the newer documents stay active); `test_a_review_made_stale_by_a_newer_accepted_run_is_superseded` (resolution service) |
| IXS06 | `test_ix5_review_required_run_embeds_nothing_and_publishes_text` (no `embed` call); `test_ix5_approval_embeds_the_activated_documents_after_the_last_decision` ×2 (a failure never fails the decision); `test_ix6_final_decision_carries_a_summary_of_the_final_snapshot` and `test_ix6_approval_activates_the_summary_it_carries`; `test_ix7_quota_refusal_publishes_the_corpus_as_text`; `test_ix7_text_only_active_chunks_are_filled_by_embed_missing` (3 chunks, one provider batch); worker sweep ×3; `test_ix9_rejection_deletes_only_unshared_candidate_documents` |

## IXS07: retrieval over partial indexes

- `test_ix8_vector_search_uses_a_partial_index_over_active_vectors`: both chunk indexes
  are partial, and with `enable_seqscan` and `enable_sort` off the hybrid query plans
  through `knowledge_chunks_embedding_hnsw_idx`. That can only happen if the query
  repeats the index predicate.
- `test_ix8_retired_chunks_never_crowd_the_vector_search`: 200 retired chunks nearer the
  query than 5 active ones, with the HNSW path forced, after a VACUUM. All 5 active chunks
  are returned. **Against a full (non-partial) index it fails** (4 of 5 returned);
  checked by temporarily removing the predicate from migration 023.

**Finding: the hybrid query never used the HNSW index.** The query vector came from the
`search_input` CTE, which is a column. pgvector orders by an index only when the query
vector is a constant or parameter, so retrieval has always been an exact scan: correct,
but O(n). The vector side now orders by the bound parameter. At today's size (~500
active chunks) the planner still prefers a btree path plus a sort, and the index
becomes worth using as the corpus grows.

**Not asserted:** cross-offering ANN recall on tiny graphs. With 200 closer chunks of
another offering, 4 of 5 were returned with or without `hnsw.iterative_scan`. That is
approximate search on a 205-node graph, not filtering. A retired row's entry also stays
in the partial index until (auto)vacuum. Iterative scan (kept, per pgvector's guidance
for filtered queries) covers both.

## IXS08: migration 023 on a copy of the dev database

Run: `uv run python fix-process/indexing/scenarios/run_ixs08_replay.py`. It restores the
Phase 0 dump into `ixs08_dev_copy`, applies the pending migrations 016–022 and 023, then
replays one accepted `overdraft` publication from the stored rows with no model call.
Report: [data/ixs08-replay.json](data/ixs08-replay.json).

| | Before | After 023 | After one accepted publication |
|---|---|---|---|
| Documents | 10 active, 7 rejected | 10 active | 5 active (page, 3 PDFs, summary), 10 retired |
| Chunks | 493 active, 506 inactive | 493 active | 44 active, 493 retired |
| Active `api:*` documents | 5 | 5 | **0** |
| Active chunks matching HTML tags | 67 | 67 | 6 (see below) |
| Active page versions per URL | 1 | 1 | 1 |
| Active evidence rows unlinked | 22 of 246 | 22 of 246 | **0 of 246** |
| Snapshot sets | n/a | 10 rows (latest accepted) | 15 rows |
| Active chunks without a vector | 0 | 0 | 9 (the text-only summary, left for the sweep) |

- The 6 remaining matches are the projection's own `<br>` line breaks inside table cells
  and one `<sup>` footnote marker from the page's Markdown rendering. None is leaked API
  HTML.
- **How the replay was built.** The replay publishes the offering's active page and PDF
  versions as read back from their rows. A run on this branch produces no `api:*`
  documents, since payload normalization was removed. The stored snapshot predates this
  branch's canonical form, and today's structured projector refuses it ("accepted
  snapshot and final semantic extraction disagree"). The replay therefore stores the
  payload re-canonicalized from the same extraction, as a run on this branch would.
  The summary is projected from the snapshot, text only.
- **Deployment finding: the dev database stops at migration 015.** 016–022 have never
  been applied there: the review workflow columns 016 drops are still present, and the
  objects from 017 (acquisition baselines), 018 (source freshness), 019 (discovery
  offering scope), 020 (PDF link selections), 021 (prompt cache, review memory) and
  022 (review evidence sets) are missing. 023 depends on none of them. A deployment
  must apply 016–023 in order. The replay does this; all are idempotent.

## IXS09: chunk shape on the 13 seeds

Run: `uv run python fix-process/indexing/scenarios/run_ixs09_projection.py`. It replays
each seed's page, PDFs and stored discovery (no model call), then projects the selected
bundle with this branch's projection and with the projection at `a812f69`, both at
1,500 characters. Report: [data/ixs09-projection.json](data/ixs09-projection.json).

| Totals (13 seeds, 53 documents) | Before | After |
|---|---|---|
| Chunks | 559 | 565 |
| Largest chunk / over the limit | 1,499 / 0 | 1,500 / 0 |
| Table-only chunks opening on a bare row (no title or header) | **40** | **1** |
| Chunks opening mid-section with a heading breadcrumb | 0 of 182 | **136 of 178** |
| Characters | 611,298 | 649,840 (+6%) |
| Full re-embed (characters/4 tokens at $0.15/1M) | $0.023 | $0.024 |

- **Deterministic:** projecting twice gives the same `projection_sha256` for every
  version.
- Some seeds have *fewer* chunks (e.g. `consumer_standard` 40 → 37). Split pieces now
  keep their label (IX13), so they no longer force a chunk break on every piece.
- The 1 remaining bare table chunk is the notes-only piece of a table with neither a
  title nor a header, so there is nothing to repeat.
- The 42 mid-section chunks without a breadcrumb open with a unit that has no heading
  path (PDF paragraphs outside any heading); a later unit in the same chunk has one,
  which is why the metric counts them.

## IXS10: live overdraft run

Not run. It needs the user's approval of the model spend (acquisition, discovery,
extraction and embedding calls). IXS08 exercises the same database path on real rows.
