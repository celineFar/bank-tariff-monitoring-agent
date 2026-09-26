# Indexing: fix plan

Date: 2026-09-26 · Branch: `fix/indexing` (to create from `integration/process-fixes` at
`a812f69`) · Status: **in progress** (Phases 0–4 done).

The four design choices this plan depends on (D1–D4) were confirmed by the user on
2026-09-26. The other decisions (D5–D12) are Claude's; each is listed in
[Decisions](#decisions) so it can be overridden before implementation.

## Scope

The path from a selected, normalized source bundle to searchable RAG chunks:

- projection into documents and chunks
  ([knowledge_projection.py](../../app/services/knowledge_projection.py));
- embedding and the embedding cache
  ([knowledge_index.py](../../app/services/knowledge_index.py),
  [embedding_cache.py](../../app/repositories/embedding_cache.py));
- the pipeline's projection, embedding and publication steps
  ([monitoring_pipeline.py:388-470](../../app/services/monitoring_pipeline.py#L388-L470));
- publication and document versioning
  ([monitoring.py `publish`, `_upsert_document`](../../app/repositories/monitoring.py#L1213));
- activation and quarantine on review decisions
  ([reviews.py `_activate_snapshot`, `_mark_documents`](../../app/repositories/reviews.py#L518));
- linking fact evidence to document versions
  ([structured_projection.py:120](../../app/repositories/structured_projection.py#L120));
- hybrid retrieval over the chunks ([rag_retrieval.py](../../app/repositories/rag_retrieval.py)).

**Out of scope:**
- The structured read model's own embeddings (`retrieval_units`,
  [structured_unit_embeddings.py](../../app/services/structured_unit_embeddings.py)).
- The `'simple'` text-search configuration, which does no stemming.
- HTML inside captured API payloads. `api_payload_normalizer.py` was removed from this
  branch in `e52ad64`, so no new chunks can get raw HTML. The existing rows are cleaned
  up by IX1 (see [One-time effects](#one-time-effects-after-deploy)).

## How this was checked

- **Code.** Read on `integration/process-fixes` at `a812f69`.
- **Dev database** (`bank-tariff-monitoring-agent-db-1`, port 5434), 2026-09-26:
  - **Documents:** 17 `knowledge_documents` rows, all for `overdraft`: 10 active (9
    `source`, 1 `offering_summary`) and 7 `rejected`.
  - **Chunks:** 999. Source chunks average 1,410 characters and the largest is 1,500;
    all are English.
  - **Duplicate versions:** the overdraft page URL has 3 different `page:<hash>` keys.
    Several API URLs have two keys each (`api:9:…` and `api:12:…` hold the same content).
  - **HTML:** 135 chunks contain HTML tags, all under `api:*` documents. 5 of those
    documents are active.
  - **Evidence links:** 22 of the 246 active `fact_evidence` rows have no
    `source_document_id`. 6 of the 10 active documents have a `run_id` other than the
    accepted snapshot's run (see IX12).
- **Chunk coverage** (the "does a 6,000-character chunk fit the embedding input?"
  question):
  - Runtime uses `RAG_CHUNK_SIZE_CHARS = 1500`, not the constructor's 6,000.
  - `gemini-embedding-001` accepts up to 2,048 tokens. Even at one token per character,
    a 1,500-character chunk fits, so nothing is truncated today.
  - The config allows up to 20,000 characters, and anything over about 2,000 could be
    truncated silently (IX14).
- **Versions.** pgvector 0.8.6, which supports partial HNSW indexes and
  `hnsw.iterative_scan`, on PostgreSQL 17.
- **Cost.** A full re-embed of the corpus is about 1,000 chunks × about 350 tokens,
  roughly 0.35M tokens at $0.15 per 1M, so about **$0.05**.

## Summary

| ID | Problem | Severity | Fix |
|---|---|---|---|
| IX1 | Old versions of a page or PDF, and sources that disappear, are never retired | **critical** | Publishing replaces the offering's whole active set (D2) |
| IX2 | A review-required run overwrites live chunks in place (quarantine bypass) | **critical** | Version identity includes a projection hash; version rows are immutable |
| IX3 | Approval can leave approved documents inactive (`run_id` = first-seen run) | **high** | `snapshot_documents` mapping; activation by snapshot, not `run_id` |
| IX4 | Approving a stale review rolls back a newer accepted result | **high** | Supersede on accepted publish, plus a guard at approval (D3) |
| IX5 | Content under review is embedded before anyone approves it | **high** (cost) | Store text only; embed on approval (D1) |
| IX6 | Approval never builds the offering summary; the old summary stays live | **high** | Approval projects the summary from the final snapshot |
| IX7 | Quota deferral publishes no documents at all; nothing fills the gap later | medium | Publish the text-only set; a worker sweep embeds it (D1) |
| IX8 | Dead vectors dilute filtered HNSW search; nothing is ever cleaned up | medium | Partial indexes, iterative scan, delete discarded rows (D4) |
| IX9 | `rejected`/`superseded` document states are write-only and harmful | medium | States become `pending_review`, `active`, `retired`; discarded rows are deleted |
| IX10 | Split table pieces lose title and header; chunks lack heading context | medium | Repeat title and header per piece; heading breadcrumb per chunk |
| IX11 | The summary is re-versioned and re-embedded on every accepted run | low | Timestamps move out of the summary content |
| IX12 | Fact evidence is linked to documents by `run_id`, so unchanged documents are not linked | **high** | Link through `snapshot_documents` |
| IX13 | `_split_unit` drops the unit's discovery label | low | Carry the label |
| IX14 | `chunk_overlap_chars` is never used; chunk-size bounds disagree | low | Remove the overlap setting; align the bounds |
| IX15 | A second, unused writer always writes `is_active=True` | low | Delete it |

---

## Target design

The fixes share one model, so it is described once here. The items below refer to it.

**Version rows are immutable.** A `knowledge_documents` row is one *projected* version
of one source for one offering.

- **Identity:** `bank, product, offering_id, document_kind, document_key, content_sha256,
  projection_sha256`.
- **`projection_sha256`** is new. It is the SHA-256 of the canonical JSON of the chunks
  (everything except the embedding) plus `PROJECTION_SCHEMA_VERSION`. The same bytes
  with a different selection, labels or projection code give a **new** row.
- **What an upsert may change:** only bookkeeping (`last_seen_run_id`, `last_seen_at`)
  and a chunk embedding that is still `NULL`. Content, metadata and chunks never change.
- **`content_sha256` and `document_key` stay the raw source hash and the normalized
  document id.** Fact evidence stores and verifies both (`source_checksum`,
  `source_document_key`), so changing them would break
  [structured_tariff_query.py:318-330](../../app/repositories/structured_tariff_query.py#L318-L330).
- **Keys no longer drive retirement.** Set replacement does (see "An offering's active
  set" below), so content-addressed keys are harmless.

**Snapshots own their document set.** A new table records which document versions each
snapshot was built from:

```
snapshot_documents
  snapshot_id  uuid  → tariff_snapshots(id)     ON DELETE CASCADE
  document_id  uuid  → knowledge_documents(id)  ON DELETE CASCADE
  PRIMARY KEY (snapshot_id, document_id)
```

- **Who writes it:** publication, for accepted and review-required snapshots alike,
  and the approval, for the summary it adds.
- **`knowledge_documents.run_id`** keeps its present meaning, "first seen in". Nothing
  selects documents by it any more.

**An offering's active set is a snapshot's set.** One function,
`activate_snapshot_set(session, snapshot_id)`, used by accepted publication and by
approval, does the following:

1. Take the offering's publication advisory lock (already held by both callers).
2. Retire every active document of the offering that is **not** in the snapshot's set,
   and all of its chunks: `is_active=false`, `publication_state='retired'`,
   `retired_at=now`.
3. Activate every document in the set and its chunks: `is_active=true`,
   `publication_state='active'`, `retired_at=NULL`.

**Unreviewed content is text only** (`knowledge_chunks.embedding` becomes nullable).

| Moment | Documents | Embedding |
|---|---|---|
| Accepted run | new versions inserted and the set activated | embedded in the pipeline (cache first); on quota exhaustion, published text-only and flagged |
| Review-required run | new versions inserted as `pending_review`, inactive; existing rows untouched | **none** |
| Approval (all reviews of the snapshot approved) | summary added to the set, set activated | after commit: `embed_missing(offering)`, best effort |
| Rejection or supersession | `pending_review` versions referenced by no other live snapshot are **deleted** | none |
| Worker tick | none | `embed_missing()` sweep over active chunks with `NULL` vectors, bounded per tick |

A chunk without a vector is still found by lexical search. Vector search skips it
(`embedding IS NOT NULL`) until the sweep fills it in.

---

## IX1. Old versions and vanished sources are never retired

**Where.**
- `document_key` is the normalized document id, built from the content hash:
  - pages: `page:{page_content_hash[:16]}`
    ([normalization.py:139](../../app/services/normalization.py#L139));
  - PDFs: `document:{sha256[:12]}`
    ([normalization.py:236](../../app/services/normalization.py#L236)).
- Retirement matches older rows with the same `document_key` only, both in
  `_upsert_document` ([monitoring.py:1680](../../app/repositories/monitoring.py#L1680))
  and in `_activate_snapshot` (`identity_match`).

**What happens.**
- A changed page gets a new key, so the old version stays active next to the new one.
- A PDF that is removed from the page, or no longer selected, stays active forever.
- The previous summary survives an approval: the user's earlier finding, and the same
  cause.
- The 5 active `api:*` documents, which include the 135 HTML chunks, will never be
  retired, because this branch can no longer produce those keys.

**Fix (D2).**
- `activate_snapshot_set` (see Target design) replaces the offering's whole active set.
- `_upsert_document`'s per-key supersession and `_activate_snapshot`'s `identity_match`
  retirement are deleted.
- A source that failed to download this run drops out of the index until the next
  accepted run. This was accepted with D2.

## IX2. A review-required run overwrites live chunks in place

**Where.**
- The version id is `uuid5(key, content_sha256)` over the **raw** source hash
  ([knowledge.py:149](../../app/domain/knowledge.py#L149)).
- Chunk ids are built from that hash plus the ordinal
  ([knowledge.py:163](../../app/domain/knowledge.py#L163)).
- The chunk upsert always overwrites `content`, `embedding` and `metadata`; only
  `is_active` depends on `activate`
  ([monitoring.py:1742-1755](../../app/repositories/monitoring.py#L1742-L1755)).

**What happens.**
- A review-required run over unchanged bytes, whose discovery selected different blocks
  (Gemini variance), maps onto the live version.
- It rewrites the active chunks with unreviewed text.
- If it produces fewer chunks, the leftover old ordinals stay active, mixing two runs
  in one document.

**Fix.**
- Add `projection_sha256` to the version identity (see Target design).
- `chunk_id` becomes `sha256(version_id, ordinal)`.
- The chunk upsert becomes insert-if-absent, plus filling a `NULL` embedding.
- The document upsert updates bookkeeping columns only.

## IX3. Approval can leave approved documents inactive

**Where.**
- `_activate_snapshot` selects candidates with
  `run_id = :run_id AND publication_state = 'pending_review'`
  ([reviews.py:537](../../app/repositories/reviews.py#L537)).
- `run_id` is the run that first inserted the row. A conflicting insert updates only
  `last_seen_run_id`.

**What happens.**
1. Run A needs review, and its review is superseded or rejected, so `_mark_documents`
   marks A's rows.
2. Run B produces the same content (same version id) and also needs review.
3. B is approved. The shared rows still carry `run_id = A` and a non-pending state, so
   they are never activated.

**Fix.**
- Activation reads the snapshot's `snapshot_documents` rows (`activate_snapshot_set`),
  so a version shared with an earlier run is activated like any other.
- `_mark_documents` is deleted (IX9).

## IX4. Approving a stale review rolls back a newer accepted result

**Where.**
- A pending review is superseded only by a newer *review* of the same scope
  ([reviews.py:84-110](../../app/repositories/reviews.py#L84-L110)).
- `approve_with_snapshot` checks only that the snapshot is still `review_required` and
  its hash is unchanged.

**What happens.** Approving run A after run B was accepted:
- retires B's documents;
- replaces B's structured projection (`retrieval_units`, `tariff_facts`) with A's older
  values.

**Fix (D3).**
- **At accepted publication:** in the same transaction, supersede every `pending`
  review of the offering whose snapshot is older than the one being published:
  - write the `review.superseded` audit event (payload
    `replacement_snapshot_id`);
  - delete the superseded snapshot's discarded documents (IX9);
  - mark those snapshots and executions the way the existing supersede path does.
- **At approval:** before activation, if an accepted snapshot of the offering is newer
  than this one, raise `ReviewConflictError("a newer accepted snapshot exists")`. The
  resolution service then supersedes the review. This is a guard against races between
  a run finishing and a reviewer answering.
- The CLI shows a superseded review as no longer pending. That path already exists.

## IX5. Content under review is embedded before anyone approves it

**Where.** `_embed_all_or_defer` runs for every snapshot
([monitoring_pipeline.py:420](../../app/services/monitoring_pipeline.py#L420)),
including review-required ones, before publication.

**Fix (D1).**
- **Review-required runs:** the pipeline projects source documents and skips embedding.
  `publish` stores them text-only (`embedding NULL`) as `pending_review`.
- **Migration:** `knowledge_chunks.embedding` drops `NOT NULL`.
- **Domain models:** `EmbeddedKnowledgeChunk.embedding` becomes optional. The
  dimension and finite-value checks apply when a vector is present.
- **Approval:** `ReviewResolutionService`, after the approval commits and the set is
  activated, calls `KnowledgeIndexer.embed_missing(offering_id)`.
  - Its chunks are mostly embedding-cache hits, because an unchanged page was embedded
    by earlier accepted runs.
  - A failure is logged and left to the sweep (IX7). It never fails the approval.

## IX6. Approval never builds the offering summary

**Where.**
- `project_summary` runs only for accepted snapshots in the pipeline
  ([monitoring_pipeline.py:404](../../app/services/monitoring_pipeline.py#L404)).
- The approval path never projects one.

**Fix.**
- `ReviewDecisionService` builds the summary `KnowledgeDocument` (text only) from the
  **final** snapshot. The final snapshot includes the reviewer's overrides, so the
  summary cannot be built at run time.
- To build it, the service is given the `KnowledgeProjectionService` and the seed
  catalog (display name, seed URL).
- `ReviewSnapshotUpdate` carries the summary.
- `approve_with_snapshot` inserts it, adds it to `snapshot_documents`, then calls
  `activate_snapshot_set`. The old summary retires through IX1's rule.

## IX7. Quota deferral publishes no documents at all

**Where.** `_embed_all_or_defer` returns `()` on `EmbeddingQuotaExhausted`
([monitoring_pipeline.py:495](../../app/services/monitoring_pipeline.py#L495)). The
accepted snapshot is then published with no source chunks and no summary, and the old
corpus keeps answering.

**Fix (D1).**
- On quota exhaustion, keep the projected documents and publish them text-only. Chunks
  already embedded in this run keep their vectors (the cache has them anyway).
- The set is activated as usual, so lexical search serves the new tariff at once.
- `indexing.embedding_deferred` stays as a manifest warning.
- **New worker sweep:** `MonitoringWorker` calls `KnowledgeIndexer.embed_missing()` on
  each tick:
  - it takes up to `RAG_EMBED_SWEEP_BATCH` active chunks with `NULL` vectors (default
    200);
  - it groups them into full provider batches of 20;
  - it stops for the tick on quota exhaustion;
  - it writes model-call usage under stage `indexing.embedding_sweep`.
- The deferral docstring that says "the previous corpus stays searchable" is rewritten.

## IX8. Dead vectors dilute filtered HNSW search

**Where.**
- The indexes cover every chunk
  ([002_rag_knowledge_store.sql:62-67](../../migrations/002_rag_knowledge_store.sql#L62-L67)).
- The vector query filters on `is_active`, bank, product and offering after the
  approximate search (default `ef_search` 40).
- Retired and discarded rows are never deleted.

**Fix (D4).**
- **Partial indexes.** Replace both indexes:
  - `knowledge_chunks_embedding_hnsw_idx ... WHERE is_active AND embedding IS NOT NULL`;
  - `knowledge_chunks_search_gin_idx ... WHERE is_active`.

  The query predicates must be written **exactly** as the index predicates:
  `c.is_active AND c.embedding IS NOT NULL`, not `c.is_active IS TRUE`. Otherwise the
  planner cannot use the partial index. Verify with `EXPLAIN`.
- **Iterative scan.** `search_candidates` runs `SET LOCAL hnsw.iterative_scan =
  relaxed_order` in its transaction, so the offering filter cannot empty the result
  when many offerings share the index. The existing rank order already re-sorts
  candidates.
- **Deletion.** Discarded documents are deleted (IX9). Retired versions are kept,
  because accepted fact evidence links to them by `source_document_id`.

## IX9. `rejected` and `superseded` document states

**Where.** `_mark_documents` ([reviews.py:714](../../app/repositories/reviews.py#L714))
writes these states, but nothing reads them. It also selects by `run_id`, so it can mark
a row another run shares (IX3).

**Fix.**
- **States.** `publication_state` becomes `pending_review | active | retired`, enforced
  by a `CHECK` constraint.
- **On rejection or supersession:** delete the snapshot's `snapshot_documents` rows,
  then delete every `pending_review` document that no longer appears in any
  `snapshot_documents` row. Chunks go with it through `ON DELETE CASCADE`.
- **Audit record:** the reviewer's copy of what they saw is kept in
  `tariff_snapshots.selected_sources_markdown` (RV10).
- `_mark_documents` is removed.
- **Migration:** delete the existing `rejected`/`superseded` rows (7 in dev).

## IX10. Split table pieces and chunks lack context

**Where.**
- `_split_unit` ([knowledge_projection.py:477](../../app/services/knowledge_projection.py#L477))
  splits a table by lines. Only the first piece keeps the `### title` and the header
  rows.
- A block's heading path goes only into `section` metadata. It is neither embedded nor
  in the tsvector.

**Fix.**
- **Tables.** Every piece of a split table starts with the title and the header row
  plus separator. The limit applies to the piece including that prefix.
- **Headings.** A chunk that does not start with a heading block starts with its first
  unit's heading path as a breadcrumb line (`## A / B`).
- **Knock-on effects.** Chunk content is not evidence (evidence comes from normalized
  blocks), so no quote check changes. `PROJECTION_SCHEMA_VERSION` is bumped, so every
  version is re-projected once, at a one-time re-embed of about $0.05.

## IX11. The summary is re-versioned on every accepted run

**Where.** `render_offering_summary` writes `As of: <timestamp>` into the content
([knowledge_projection.py:354](../../app/services/knowledge_projection.py#L354),
[:360](../../app/services/knowledge_projection.py#L360)).

**Fix.**
- Drop the `As of` line from the content. The snapshot's time is already
  `retrieved_at` on the document, and it is also put in `metadata.as_of`.
- The summary's hash now changes only when the tariff or its evidence ids change.

## IX12. Fact evidence is linked to documents by `run_id`

**Where.** `publish_structured_projection` finds each cited document with
`WHERE run_id = :run_id AND offering_id = :offering_id AND document_key = ANY(...)`
([structured_projection.py:120](../../app/repositories/structured_projection.py#L120)).

**What happens.**
- A document unchanged since an earlier run keeps its first-seen `run_id`, so it is not
  found.
- The evidence row is stored with `source_document_id = NULL`, and the checksum
  verification in
  [structured_tariff_query.py:324](../../app/repositories/structured_tariff_query.py#L324)
  is skipped for it.
- In dev, 22 of 246 active evidence rows are unlinked.

**Fix.**
- The query joins `snapshot_documents` on `snapshot_id = :snapshot_id` instead of
  filtering on `run_id`.
- Publication writes `snapshot_documents` before `publish_structured_projection` runs,
  both at accepted publication and at approval.
- The first accepted run after deploy relinks each offering's evidence.

## IX13. `_split_unit` drops the unit's label

**Where.** [knowledge_projection.py:492-500](../../app/services/knowledge_projection.py#L492-L500)
builds the pieces without `label=unit.label`.

**Fix.**
- Pass the label through, so an oversized unit's pieces keep their
  `product_associations`, `precedence` and the rest of the label metadata.
- They also stop forcing chunk breaks, because `_association` returns `None` for an
  unlabelled piece.

## IX14. Chunk settings

**Where.** [models.py:291-308](../../app/config/models.py#L291-L308).

**Fix.**
- Remove `chunk_overlap_chars` (and `RAG_CHUNK_OVERLAP_CHARS`). It is validated and
  never used, and IX10's context lines serve the same purpose.
- Set `chunk_size_chars` bounds to `ge=500, le=2000`:
  - 500 is the projection's own minimum;
  - above 2,000 characters, `gemini-embedding-001` (2,048 tokens) could truncate
    silently.

## IX15. A second, unused writer

**Where.**
- `PostgresKnowledgeStore.upsert_document` and `list_document_versions`
  ([knowledge_store.py:178](../../app/repositories/knowledge_store.py#L178)),
  `KnowledgeIndexer.index`, and the `KnowledgeStoreRepository` contract.
- The writer always writes `is_active=True` and never sets `publication_state`, so it
  would bypass review if anyone called it.

**Fix.**
- Delete the writer, `index` and the contract, and the tests that cover only them
  (`tests/integration/test_knowledge_store_postgres.py`, and the fake in
  `test_knowledge_index.py`).
- Keep the ORM record classes and `_validate_embeddings`, which move to a small
  `knowledge_records.py`.
- `KnowledgeIndexer` keeps `embed` and gains `embed_missing`.

---

## Decisions

| # | Question | Decision | By | Affects |
|---|---|---|---|---|
| D1 | What a review-required run stores before the decision | Text only, no vectors. Embed on approval; a worker sweep also covers quota deferral. | **user** | IX5, IX7 |
| D2 | Which active documents a publication retires | All of the offering's active documents not in the published snapshot's set. A failed fetch drops out until the next accepted run. | **user** | IX1 |
| D3 | A pending review older than a newer accepted snapshot | Superseded at accepted publication, plus a guard at approval. | **user** | IX4 |
| D4 | Dead rows | Partial indexes on active chunks; delete never-published (discarded) documents; keep retired versions (evidence links to them). | **user** | IX8, IX9 |
| D5 | Rekey documents by source URL? | **No.** Evidence stores and verifies `document_key` and `content_sha256`; set replacement makes key-based retirement unnecessary. | Claude | IX1, IX2 |
| D6 | How to stop in-place overwrites | `projection_sha256` in the version identity; version rows immutable apart from bookkeeping and filling `NULL` vectors. | Claude | IX2 |
| D7 | How a snapshot names its documents | A `snapshot_documents` join table (many-to-many: a version can serve several snapshots). | Claude | IX1, IX3, IX12 |
| D8 | Where the approval summary is built | In `ReviewDecisionService`, from the final snapshot, carried in `ReviewSnapshotUpdate`. | Claude | IX6 |
| D9 | When approval embeds | After the approval commits, best effort; the sweep retries. Approval never fails on embedding. | Claude | IX5 |
| D10 | Chunk context | Repeat table title and header in each piece; heading breadcrumb on chunks that do not start with a heading. One-time re-embed about $0.05. | Claude | IX10 |
| D11 | Chunk overlap | Remove the unused setting instead of implementing it. | Claude | IX14 |
| D12 | The legacy writer | Delete it. | Claude | IX15 |

## One-time effects after deploy

- **Migration 023** (`023_indexing_publication_sets.sql`):
  - `knowledge_chunks.embedding` drops `NOT NULL`;
  - `knowledge_documents.projection_sha256` is added, with existing rows set to 64
    zeros, and the version unique constraint is rebuilt to include it;
  - `snapshot_documents` is created;
  - existing `rejected` and `superseded` documents are deleted;
  - the `publication_state` check constraint is added;
  - both chunk indexes are rebuilt as partial indexes.
- **Backfill `snapshot_documents`:**
  - each active document maps to its offering's latest accepted snapshot;
  - each `pending_review` document maps to the `review_required` snapshot of its
    `run_id`.
- **The first accepted run per offering:**
  - it re-projects every document (new `projection_sha256` and schema version), so each
    active row is replaced by a new version;
  - the embedding cache misses only where IX10 changed the text, about $0.05 overall;
  - set replacement retires everything else, including the `api:*` HTML documents and
    the duplicate page versions;
  - IX12 relinks the offering's evidence.
- **Reviews pending at deploy time** keep working. Their documents are mapped by the
  backfill, and approval activates them through the new path.

---

## Validation scenarios

Scenario files go in [scenarios/](scenarios/) (Phase 0), and results in
`scenario-results.md` (Phase 6). All are offline, at $0, unless marked.

| ID | Checks | Pass when |
|---|---|---|
| IXS01 | Test suite | `uv run pytest tests/unit tests/integration` green (only the known live-key failures) |
| IXS02 | Changed page, two accepted runs (IX1) | exactly one active version per source; the vanished PDF retired; the old summary retired |
| IXS03 | Review-required run over unchanged bytes with a different selection (IX2) | live chunks byte-identical before and after; the candidate is a separate version row |
| IXS04 | Reject, then approve over shared content (IX3) | the approved snapshot's full set is active; nothing from before stays active |
| IXS05 | Stale review (IX4) | accepted publish supersedes the older pending review; approval of a stale review raises the conflict |
| IXS06 | Embedding spend (IX5, IX7) | zero `indexing.embedding` calls for a review-required run; embedding on approval; quota → text-only active set, sweep fills it |
| IXS07 | Retrieval (IX8) | `EXPLAIN` uses both partial indexes; with 20× dead rows the top-k equals the clean-index top-k |
| IXS08 | Dev DB migration and relink (IX9, IX12) | migration applies on a copy of dev; after one replayed accepted publication: `api:*` retired, 0 unlinked evidence rows |
| IXS09 | Chunk shape (IX10, IX11, IX13) | every table piece has title and header; summary hash equal across two identical runs; split pieces carry labels |
| IXS10 | Live overdraft run (**optional, needs budget approval**) | IXS02/IXS08 checks hold on a real run; embedding cost reported from the usage ledger |

---

## Implementation phases

Order:
1. failing tests;
2. schema;
3. version identity and projection;
4. publication and activation;
5. reviews;
6. embedding lifecycle and retrieval;
7. validation.

Each phase ends green on `uv run pytest tests/unit tests/integration`. Postgres tests need
`TEST_DATABASE_URL` (the local test database on port 5434).

### Phase 0: Preparation

- [x] Create branch `fix/indexing` from `integration/process-fixes` (`a812f69`).
- [x] Run `uv run pytest tests/unit tests/integration` and record the baseline.
- [x] Save a dump of the dev knowledge tables (`knowledge_documents`,
      `knowledge_chunks`, `fact_evidence`) to `fix-process/indexing/data/` for IXS08.
- [x] Add regression tests, `xfail(strict=True)`, one per item, asserting the target
      behaviour:
  - [x] IX1: a second accepted publication with a changed page leaves one active
        version; a source missing from the second set is retired; the old summary is
        retired;
  - [x] IX2: a review-required publication over the live version's bytes with different
        chunks leaves the live chunks unchanged;
  - [x] IX3: reject run A, then approve run B with the same content, and B's documents
        are active;
  - [x] IX4: an accepted publication supersedes an older pending review; approving a
        review older than an accepted snapshot raises `ReviewConflictError`;
  - [x] IX5: a review-required run makes no `embed_documents` call and stores chunks
        with `NULL` embeddings;
  - [x] IX6: approval activates a summary built from the final snapshot, including an
        override value;
  - [x] IX7: on `EmbeddingQuotaExhausted` an accepted snapshot publishes its documents
        text-only and activates them; `embed_missing` fills them;
  - [x] IX8: the vector query predicate matches the partial index (`EXPLAIN` in a
        Postgres test);
  - [x] IX9: rejecting a review deletes its unshared `pending_review` documents and
        keeps a version shared with an accepted snapshot;
  - [x] IX10: every piece of a split table starts with its title and header;
  - [x] IX11: two summaries of the same snapshot values at different times hash equal;
  - [x] IX12: evidence citing a document unchanged since an earlier run gets its
        `source_document_id`;
  - [x] IX13: pieces of an oversized labelled unit keep the label metadata;
  - [x] IX14: `chunk_size_chars=300` and `=2500` are rejected by settings validation.
- [x] Check with `--runxfail` that each fails today, for its own reason.
- [x] Write the scenario files `scenarios/IXS01…IXS10`.

**Phase 0 notes (done).**
- Branch `fix/indexing` from `integration/process-fixes` at `a812f69`.
- Baseline before any change: **1064 passed, 5 skipped**, 1 failed + 3 errors (the 4 known
  Gemini-key tests: `test_agent_stream` and the 3 `test_server_e2e` tests). Postgres tests
  ran with `TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_acquisition_test`.
- Dev DB dump: `fix-process/indexing/data/dev-db-before.dump` (`pg_dump -Fc` of
  `tariff_monitor`, 7.5 MB, git-ignored; restore with `pg_restore` into a scratch DB for
  IXS08). The dev DB is migrated by hand (migrations run automatically only on a fresh
  volume), so 023 must apply to an existing schema.
- **19 `xfail(strict=True)` tests**, each failing today for its own missing piece
  (checked with `--runxfail`):
  - `tests/unit/test_indexing_fixes.py` (9): IX2 (`projection_sha256` missing), IX5 (the
    source is embedded), IX6 (`OfferingSummaryProjector` missing), IX7 (no documents
    published), IX10 (piece starts with a row), IX11 (hashes differ), IX13 (labels
    missing), IX14 ×2 (300 and 2,500 accepted).
  - `tests/integration/test_indexing_fixes_postgres.py` (10): IX1 (old page, PDF and
    summary stay active), IX2 (**live chunk rewritten to "unreviewed rate 99%"**), IX3
    (nothing active after approval), IX4 ×2 (older review stays pending; stale approval
    succeeds), IX6 (text-only summary cannot be built), IX7 (`knowledge_embeddings`
    missing), IX8 (index not partial), IX9 (`document:9999` kept as `rejected`), IX12
    (second run links 0 of 17 evidence rows).
- **Target APIs the tests fix:** `KnowledgeDocument.projection_sha256`;
  `EmbeddedKnowledgeChunk.embedding` optional; `OfferingSummaryProjector(projection,
  catalog)` in `knowledge_projection.py`; `ReviewDecisionService(..., summaries=)`;
  `ReviewSnapshotUpdate.summary`; `KnowledgeIndexer(provider, embeddings=)` with
  `embed_missing()`; `PostgresChunkEmbeddingRepository` in
  `app/repositories/knowledge_embeddings.py`; summary `metadata.as_of`; the conflict
  message "a newer accepted snapshot exists".
- The Postgres module imports its fixtures and helpers from
  `test_monitoring_repository_postgres.py` (there is no `conftest.py`).
- Scenario files: [scenarios/](scenarios/) IXS01–IXS10; results filled in Phase 6.

### Phase 1: Schema (migration 023)

- [x] Write `migrations/023_indexing_publication_sets.sql`:
  - [x] `knowledge_chunks.embedding` drop `NOT NULL`;
  - [x] `knowledge_documents.projection_sha256 char(64) NOT NULL DEFAULT repeat('0', 64)`;
        rebuild `knowledge_documents_version_uq` to include it;
  - [x] create `snapshot_documents` (see Target design) with an index on `document_id`;
  - [x] backfill `snapshot_documents` (active → latest accepted snapshot of the
        offering; `pending_review` → the `review_required` snapshot of its `run_id`);
  - [x] delete documents in `rejected`/`superseded`; add the `publication_state`
        `CHECK (pending_review, active, retired)`;
  - [x] replace the HNSW and GIN indexes with the partial ones (IX8).
- [x] Mirror the schema in the ORM records (nullable `embedding`, `projection_sha256`,
      partial indexes) and add a `SnapshotDocumentRecord`.
- [x] Update `tests/unit/test_knowledge_schema.py`; apply the migration to the test DB.
- [x] Apply to a copy of the dev DB and record row counts before and after (IXS08 input).

**Phase 1 notes (done).**
- [migrations/023_indexing_publication_sets.sql](../../migrations/023_indexing_publication_sets.sql):
  nullable `embedding`; `projection_sha256` (legacy rows: 64 zeros) in the version unique
  constraint; `snapshot_documents` (+ index on `document_id`) with the backfill; delete of
  `rejected`/`superseded` documents; state check `pending_review | active | retired`;
  partial HNSW (`WHERE is_active AND embedding IS NOT NULL`) and GIN (`WHERE is_active`);
  `knowledge_chunks_missing_embedding_idx` for the Phase 5 sweep.
- **Found: `source_manifests.document_id` had no `ON DELETE` rule**, so deleting a
  discarded document a manifest recorded would fail. 023 recreates the FK as
  `ON DELETE SET NULL` (the manifest row keeps key, URL and checksum).
- ORM mirror in `knowledge_store.py`: `projection_sha256`, nullable `embedding`, partial
  indexes, `SnapshotDocumentRecord` (plus a `tariff_snapshots` stub table for the FK).
  The move to `knowledge_records.py` is Phase 2 (IX15).
- **Interim IX9 (to be replaced in Phase 4).** The new state check forbids `rejected`, so
  `_mark_documents` became `_discard_documents`: it **deletes** the run's
  `pending_review`, inactive documents (still selected by `run_id`). This already makes
  `test_ix9_…` pass, so its `xfail` was removed; Phase 4 re-bases it on
  `snapshot_documents`.
- Tests adjusted to the schema: `test_knowledge_schema.py` (partial indexes, nullable
  vector, 023 text); `test_knowledge_store_postgres.py` (states `active`,
  `pending_review`, `retired`; the HNSW plan query repeats the partial predicate).
- **Dev copy (IXS08 input):** `ixs08_dev_copy` database in the dev container, restored
  from the Phase 0 dump; 023 applied with `ON_ERROR_STOP`. Counts in
  [data/ixs08-migration-counts.txt](data/ixs08-migration-counts.txt): documents 10 active +
  7 rejected → 10 active; chunks 993 → 493 (the 506 rejected chunks deleted); all 10
  active documents mapped to the accepted snapshot, 0 without a set; still 5 active
  `api:*` documents with 67 active HTML chunks, and 22/246 unlinked evidence rows (these
  are cleared by the first accepted publication, Phase 6). **The real dev DB is
  untouched** (deployment needs approval).
- Suite: 1065 passed, 5 skipped, 18 xfailed (the 4 known Gemini-key tests excluded).

### Phase 2: Version identity and projection (IX2, IX10, IX11, IX13, IX14, IX15)

- [x] Add `PROJECTION_SCHEMA_VERSION` and `projection_sha256` (computed from the chunks)
      to `KnowledgeDocument`.
- [x] `document_version_id` includes `projection_sha256`; `chunk_id` becomes
      `sha256(version_id, ordinal)`.
- [x] `EmbeddedKnowledgeChunk.embedding` becomes optional; dimension and finite checks
      run only when present.
- [x] IX13: `_split_unit` carries `label`.
- [x] IX10: table pieces repeat title and header; heading breadcrumb on chunks that do
      not start with a heading; limit counts the prefix.
- [x] IX11: drop `As of` from the summary content; add `metadata.as_of`.
- [x] IX14: remove `chunk_overlap_chars` (settings, loader, environment, `.env.example`,
      docs); bounds `ge=500, le=2000`.
- [x] IX15: delete `PostgresKnowledgeStore.upsert_document`, `list_document_versions`,
      `KnowledgeStoreRepository`, `KnowledgeIndexer.index` and their tests; move the
      records and `_validate_embeddings` to `app/repositories/knowledge_records.py`;
      update `runtime.py` wiring.
- [x] Record the Phase 2 notes here.

**Phase 2 notes (done).**
- **Identity (IX2).** `PROJECTION_SCHEMA_VERSION = "2"` and the
  `KnowledgeDocument.projection_sha256` property (canonical JSON of the chunks without
  vectors, plus the schema version) in [app/domain/knowledge.py](../../app/domain/knowledge.py).
  `document_version_id` includes it; `chunk_id` is `sha256("<version id>:<ordinal>")`,
  with `version_chunk_id(version_id, ordinal)` for callers that already hold the id
  (hashing a version is O(chunks), so per-chunk recomputation would be quadratic).
  `_upsert_document` now writes `projection_sha256`, which alone makes a candidate with
  other chunks a separate row: **the IX2 Postgres test passes** (its `xfail` removed).
  The rest of the upsert rewrite (insert-if-absent) is Phase 3.
- **Optional vectors.** `EmbeddedKnowledgeChunk.embedding: tuple[float, ...] | None`
  (empty tuple still rejected); `EmbeddedKnowledgeDocument.text_only(document)` and
  `.fully_embedded`. `validate_embeddings` checks only vectors that are present.
- **Projection** ([knowledge_projection.py](../../app/services/knowledge_projection.py)):
  - IX13: `_split_unit` builds pieces with `dataclasses.replace`, so label,
    locators and `repeat_prefix` carry over.
  - IX10 tables: `_ProjectionUnit.repeat_prefix` (title + header + separator); each piece
    repeats it, and the limit counts it. Falls back to no repeat when the prefix is over
    half the budget (a table with a huge header).
  - IX10 breadcrumbs: a chunk whose first unit is not a heading, table or summary opens
    with `## <heading path>` (≤ 200 characters). The grouping and the splitting both
    reserve its length, so chunks stay within the limit.
  - IX11: no `As of` line; `metadata.as_of` on the summary document;
    `summary_schema` is `loan_product_or_snapshot_v2`.
  - Default `max_chunk_chars` is now 1,500 (was 6,000), matching the runtime setting.
- **IX14.** `chunk_overlap_chars` removed from `RagSettings`, the env model, the loader,
  `.env.example` and `docs/configuration.md` (an old `.env` line is ignored: the env model
  has `extra="ignore"`). `chunk_size_chars` is `ge=500, le=2_000`.
  `test_config.py` updated.
- **IX15.** `app/repositories/knowledge_store.py` → `knowledge_records.py` (records,
  `validate_embeddings`); `PostgresKnowledgeStore`, `KnowledgeStoreRepository`,
  `DocumentVersionSummary` and `KnowledgeIndexer.index` deleted. `KnowledgeIndexer` is now
  `(embedding_provider, embeddings=None, embedding_cache=None, usage_repository=None)`;
  `embeddings` is the new `ChunkEmbeddingRepository` protocol (in `contracts.py`),
  implemented in Phase 5.
- **Tests.** `test_knowledge_store_postgres.py` → `test_knowledge_retrieval_postgres.py`:
  the three writer-semantics tests are deleted (publication tests cover them); the index,
  hybrid-retrieval, quarantine and SD7 tests insert rows with the new
  `tests/fixtures/knowledge.py::store_active_document`. `test_knowledge_index.py` tests
  `embed` directly. New `test_ix10_a_chunk_starting_mid_section_opens_with_its_heading_path`.
  The Postgres regression module binds the fixtures as module attributes (ruff F811).
- `docs/architecture.md` still names `PostgresKnowledgeStore`; docs are Phase 6.
- Suite: 1069 passed, 5 skipped, 11 xfailed (4 known Gemini-key tests excluded); ruff
  check and format clean.

### Phase 3: Publication and activation (IX1, IX2, IX12)

- [x] Rewrite `_upsert_document` as insert-if-absent: bookkeeping-only update on
      conflict; chunk insert-if-absent; fill `embedding` only where it is `NULL`; no
      supersession, no activation.
- [x] Add `activate_snapshot_set(session, snapshot_id)` (retire the offering's active
      documents outside the set, activate the set and its chunks).
- [x] `publish`: insert versions; write `snapshot_documents`; if accepted, call
      `activate_snapshot_set`, then `publish_structured_projection`; if review-required,
      new versions stay `pending_review`.
- [x] IX12: `publish_structured_projection` links evidence through `snapshot_documents`
      for the snapshot, not `run_id`.
- [x] Record the Phase 3 notes here.

**Phase 3 notes (done).**
- New module [app/repositories/knowledge_publication.py](../../app/repositories/knowledge_publication.py),
  used inside the caller's transaction:
  - `store_document_version(session, document, now)` replaces `_upsert_document` (deleted
    from `monitoring.py`). A new version is inserted **inactive** (`pending_review`)
    for accepted and review-required runs alike; only activation makes it searchable.
    On an existing row it updates bookkeeping only: `last_seen_run_id`, `last_seen_at`,
    `retrieved_at`, and the document `metadata` (not part of the version's content; it
    keeps the summary's `as_of` current). Chunks are insert-if-absent; a present vector
    fills a stored `NULL` one (`ON CONFLICT ... WHERE embedding IS NULL`).
    The advisory lock is now on the version id (the offering lock already serializes
    publications).
  - `link_snapshot_documents(session, snapshot_id, document_ids)`.
  - `activate_snapshot_set(session, snapshot_id, now)`: retires active documents (and
    chunks) of the snapshot's offering outside its set, activates the set. Returns
    `(retired, activated)`.
- `publish`: store versions → insert snapshot → link the set → if accepted, activate
  the set (**only when the publication has documents**, so an empty publication never
  empties an offering's index) → structured projection. `IndexWriteResult`'s
  `chunks_retired`/`versions_retired` are now always 0 (retirement is the activation's);
  nothing read them.
- **IX12.** `publish_structured_projection` links evidence through `snapshot_documents`.
  A snapshot with no recorded set (accepted before 023 and re-projected by
  `structured_backfill`) falls back to the old `run_id` lookup.
- `_activate_snapshot` (approval) is unchanged in this phase and still selects the
  candidate by `run_id`; Phase 4 moves it to `activate_snapshot_set`.
- IX1 and IX12 regression tests pass (markers removed). Suite: 1071 passed, 5 skipped,
  9 xfailed (Gemini-key tests excluded).

### Phase 4: Reviews (IX3, IX4, IX6, IX9)

- [x] IX3: `_activate_snapshot` calls `activate_snapshot_set`; delete the `run_id`
      candidate queries and `identity_match`.
- [x] IX6: `ReviewDecisionService` gets the projection service and the seed catalog;
      builds the summary from the final snapshot; `ReviewSnapshotUpdate.summary`;
      the repository inserts it and its `snapshot_documents` row before activation.
- [x] IX4: accepted `publish` supersedes older pending reviews of the offering (audit
      event with `replacement_snapshot_id`); `approve_with_snapshot` raises
      `ReviewConflictError` when a newer accepted snapshot exists; the resolution
      service supersedes on that conflict.
- [x] IX9: on rejection or supersession, delete the snapshot's `snapshot_documents`
      rows and orphaned `pending_review` documents; delete `_mark_documents`.
- [x] Record the Phase 4 notes here.

**Phase 4 notes (done).**
- **IX3.** `_activate_snapshot` stores the approval's summary (if any), links it to the
  snapshot, and calls `activate_snapshot_set`. The `run_id` candidate queries and
  `identity_match` are gone, so a version first stored by an earlier run is activated
  like any other.
- **IX6.** `OfferingSummaryProjector(projection, catalog).project(snapshot)` in
  `knowledge_projection.py` (display name, seed URL and language from
  `SeedCatalog.get`). `ReviewDecisionService(..., summaries=)` builds the summary from
  the final snapshot **only on the decision that activates it** (`ready_for_activation`);
  earlier decisions of a multi-review batch carry none. It travels as
  `ReviewSnapshotUpdate.summary` (text only). `runtime.py` shares one
  `KnowledgeProjectionService` between the pipeline and the projector.
- **IX4.** New module [app/repositories/review_supersession.py](../../app/repositories/review_supersession.py):
  - `supersede_reviews_older_than(session, snapshot_id, now)`: pending reviews of the
    offering's snapshots created before this one become `superseded`, with a
    `review.superseded` audit event (`reason: newer_accepted_snapshot`,
    `replacement_snapshot_id`), and their snapshots' documents are discarded. Called by
    accepted `publish` **and by approval** (an approval publishes too).
  - `newer_accepted_snapshot_exists`: `approve_with_snapshot` raises the new
    `StaleReviewError` (a `ReviewConflictError`; message "a newer accepted snapshot exists
    for this offering") before writing anything. `ReviewResolutionService.apply` catches
    it, records `review.superseded_stale`, and supersedes the review.
  - As before, superseding does not change the old snapshot's or execution's status
    (the existing supersede path never did); `complete_runs_without_pending_reviews`
    finishes the run.
- **IX9.** `discard_snapshot_documents(session, snapshot_id)` (in
  `knowledge_publication.py`) deletes the snapshot's `snapshot_documents` rows, then the
  `pending_review`, inactive versions that no other snapshot names. Used on rejection,
  on `supersede`/`fail` (`_terminal_update`) and when a newer review supersedes. The
  Phase 1 interim `_discard_documents` (by `run_id`) is deleted.
- **Found: lock order.** Publication now updates review rows (IX4) while holding the
  offering's publication lock, and review paths lock the review row first; the opposite
  order could deadlock. Every path that touches an offering's documents or pending
  reviews now takes `lock_offering_publication` **first**: `publish`, `create` (before
  its `review:` lock), `_decide`, `_terminal_update` and `approve_with_snapshot`
  (`lock_review_publication` reads the review's scope without locking it).
- Tests: IX3, IX4 ×2, IX6 ×2 markers removed; new
  `test_a_review_made_stale_by_a_newer_accepted_run_is_superseded`
  (`test_review_resolution.py`). Suite: 1077 passed, 5 skipped, 4 xfailed.

### Phase 5: Embedding lifecycle and retrieval (IX5, IX7, IX8)

- [ ] IX5: the pipeline embeds only accepted snapshots; review-required documents are
      published text-only.
- [ ] IX7: on quota exhaustion, publish the projected documents text-only (keep
      vectors already made) and keep the `indexing.embedding_deferred` warning; rewrite
      the deferral docstring.
- [ ] Add `KnowledgeIndexer.embed_missing(offering_id=None, limit=...)`: select active
      chunks with `NULL` vectors, embed through the cache in full batches of 20, fill
      them with `UPDATE ... WHERE embedding IS NULL`, stop on quota.
- [ ] Call `embed_missing(offering)` after a committed approval (best effort, logged).
- [ ] Add the worker sweep (`RAG_EMBED_SWEEP_BATCH`, default 200) to `MonitoringWorker`'s
      tick, with usage stage `indexing.embedding_sweep`.
- [ ] IX8: rewrite the retrieval predicates to match the partial indexes
      (`c.is_active AND c.embedding IS NOT NULL` for vectors, `c.is_active` for text);
      `SET LOCAL hnsw.iterative_scan = relaxed_order` in `search_candidates`.
- [ ] Record the Phase 5 notes here.

### Phase 6: Validation and docs

- [ ] Run IXS01–IXS09 and write `scenario-results.md`.
- [ ] Ask for budget approval before IXS10 (live overdraft run); run it if approved.
- [ ] Update [docs/indexing-projection.md](../../docs/indexing-projection.md),
      [docs/knowledge-store.md](../../docs/knowledge-store.md),
      [docs/rag-retrieval.md](../../docs/rag-retrieval.md),
      [docs/review-quarantine.md](../../docs/review-quarantine.md) and
      [docs/architecture.md](../../docs/architecture.md) (persistence responsibilities
      and the worker sweep change, as AGENTS.md requires).
- [ ] Update this plan's Summary with statuses, and add the decisions to
      [../note.md](../note.md).

## Deployment (needs human approval)

- [ ] Apply migration `023_indexing_publication_sets.sql`.
- [ ] Confirm the backfill: every active document and every pending review's documents
      have a `snapshot_documents` row.
- [ ] Run one accepted monitoring run per offering (or wait for the schedule) and check:
  - the old versions and `api:*` documents are retired;
  - there are 0 unlinked evidence rows;
  - `embed_missing` leaves no active `NULL` vectors.
- [ ] Watch `indexing.embedding_sweep` usage and the `indexing.embedding_deferred`
      warning after deploy.
