# Fix-process notes: decisions, assumptions, open points

Decisions taken without asking, as instructed on 2026-09-26 ("don't pause to ask; use
your best judgment; record decisions here"). Newest last. Each entry says what was
decided, why, and where it matters.

## Branches

- **Integration branch.** The instruction names `integration/fix-process`; no such
  branch exists. Every earlier fix (`fix/normalization`, `fix/source-discovery`) was
  merged into `integration/process-fixes`, so the semantic-extraction work is merged
  there too.
- **`fix/reviews`** did not exist; it is created from `integration/process-fixes` after
  the semantic-extraction merge, so the review work builds on it.

## Semantic extraction (fix-process/semantic_extraction/)

- **Field labels are unconfirmed.** `data/seed-extraction-labels.json` was drafted by
  Claude from the captured pages and is used as-is for S06. The user was not asked to
  confirm them, per the instruction not to pause. Read S06 results with that in mind.
- **S06 pass bar.** Adopted as proposed in the scenario: at least 85% `match` over
  labelled fields, and no rate or amount `wrong_value` caused by a wrong column or
  currency.
- **SE2 changes every page's identity once.** The plan expected the acquisition page
  identity to stay unchanged. It is a hash of the parsed blocks, and pairing headline
  cards changes blocks, so all 13 pages get a new id on the first run after deploy.
  Block ids after a card do not shift, because the consumed label keeps its id
  reserved. Added to the one-time effects.
- **SE3 prompt kept as in production.** A trial (13 PDF transcriptions,
  `gemini-3.1-flash-lite`) showed:
  - the model never filled `row_groups` or real header rows, even when asked;
  - asking cost rows (35 against 40 on the Primary terms PDF);
  - page coverage varied with incidental prompt wording, even at temperature 0.

  So the production instruction stays; `header_rows` and `row_groups` are optional
  schema fields used when present. PDF table structure comes from deterministic
  analysis of the rows, the same rules as HTML tables. Temperature 0 and the version
  bump (`PDF_EXTRACTION_*_VERSION=3`) stay.
- **Hand-off (normalization): PDF page coverage is fragile.** The same PDF came back
  with pages 4, 7, 8, 9 or 7, 8, 9 empty in some runs and complete in others, even at
  temperature 0. `PDF_PAGE_EMPTY` reports it, but nothing re-asks for those pages.
  A per-page re-transcription of empty text pages belongs in the normalization plan.
- **Extraction fallback model (plan Q8): `gemini-3.8-flash`.** The plan meant to ask the
  user. Following the instruction not to ask, one small call each on 2026-09-26 chose:
  - `gemini-3.8-flash`, `gemini-3.6-flash` and `gemini-3.5-flash-lite` answer this key;
  - `gemini-2.5-flash` returns 404 (retired for new users).

  `gemini-3.8-flash` is non-lite (a lite model is a weak fallback for extraction), in
  the primary's price tier, and newer than it. It is the default in `environment.py`
  and `.env.example`. `SemanticExtractionSettings` in `models.py` keeps an empty
  default, so code that builds settings directly (tests) has no chain unless it asks
  for one. On your earlier question "should the fallback list be empty by default?":
  no. Each call now falls back on its own, so one configured successor costs nothing
  until the primary fails.
- **S06 pass bar.** Adopted as proposed in the scenario, not agreed with the user: ≥ 85%
  `match` over labelled fields, and no rate or amount `wrong_value` from a wrong column or
  currency. Result: 104/120 (87%), no wrong values, after re-scoring.
- **Live run settings.** Repairs capped at 1 per offering (production default 3) and a
  $1.55 guard, to fit the $2 budget. The budgeted-mode live pass was dropped when the
  budget ran out; budgeted mode is measured offline only.

## Reviews (fix-process/reviews/)

Decisions the review-process report left open, taken without asking (plan table Q1–Q11):
- **`extraction_invalid`** is the new reason for a value that failed a check. Allowed:
  `select_candidate` (accept Gemini's value after checking), `override`, `reject_all`.
- **A validation failure on a non-required field is still a review** (as
  `extraction_invalid`). Dropping it silently would lose data.
- **Bounds are code constants** (1 unit, a second within `HITL_DOCUMENT_RANK_GAP`; tables
  whole up to 30 rows; section windows ±2 blocks, ≤ 3,000 characters).
- **No embeddings** in review ranking; ranking misses are logged instead.
- **The generic "Information Guide" tagged `current_product` on Overdraft** is a
  source-discovery issue: hand-off, not fixed here.
- **No separate table display rendering**: the semantic-extraction row records already are
  the readable form.
- **`get_current_tariffs` returns freshness and field statuses only** (D5 option i).
- **`?` shows the selected sources' Markdown saved with the snapshot**, never sent to the
  model.
- **The model gets at most 5 seed passages (600 characters each)** per review; the CLI
  renders the units itself.

### Reviews Phase 1 decisions (2026-09-26)

- **Sibling reviews (found, fixed).** Two reviews of one field in one snapshot (OCR +
  large rate change) superseded each other through `human_reviews_active_scope_uq` and
  the repository's supersede-on-create. Fixed in migration `022` (pending reviews unique
  per field *and* reason) and the supersede query; not in the report.
- **Unknown IDs with no valid citation.** An `extraction_invalid` answer citing only
  IDs that do not exist has no candidate (a candidate needs a real reference); its set
  falls back to the field's call passages, and the unknown IDs are listed.
- **Empty sets are allowed.** A not-stated field with no labelled passage gets no unit;
  the CLI says so and offers `?`. No keyword or embedding fallback (Q4).
- **Test database.** Postgres tests need
  `TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_acquisition_test`
  (local test container); without it they skip.

### Reviews Phase 2 decisions (2026-09-26)

- **Override scope = the whole snapshot.** A reviewer may cite any passage of the
  snapshot (as before, when the review copied all of it); a citation outside the shown
  units is allowed and logged (RV13). Restricting to the units would block the
  reviewer exactly when ranking missed.
- **Citation quote limit 4,000.** The plan assumed the stored citation already allowed
  4,000 characters; it allowed 1,500. `EvidenceCitation.quote` now allows 4,000 so
  the displayed passage, the override check and the saved quote are the same text.
- **Old rows with non-catalog items** show each cited item as its own passage; no
  keyword fallback for uncited ones.

### Reviews Phase 4 decisions (2026-09-26)

- **Scope-only questions.** With `get_current_tariffs` reduced to freshness (D5, decided
  in the report), the `answer_tariff_query` hint for scope-only plans now asks the model
  to ask which field is wanted, instead of pointing it at `get_current_tariffs` for
  values. Risk: "show me the overdraft terms" now needs one clarification turn; every
  value shown stays citable.
- **History payload trimmed too** (not in the plan; same cause). `get_tariff_history`
  keeps values and change sets, drops each snapshot's evidence and extraction record.
- **Run attribution uses `temp:` state**, so nothing about the run is persisted in the
  chat session; it is matched on the invocation id as well.

### Reviews Phase 5 (validation) decisions (2026-09-26)

- **R03 input changed.** The plan assumed the semantic-extraction cache held real answers
  for all 13 seeds; it holds one seed's 3 calls, the S06 reports keep no citations, and
  the $2 budget is spent. R03 ran on that seed's real answers plus all 13 real catalogs
  with an extractor that finds nothing. No paid call was made.
- **Ranking change from R03.** Ties broken by precedence then tables, and the best table
  takes the second slot after a non-table unit. Chosen because the misses were
  structural (page order, headline sections), not vocabulary; it adds no keyword.
- **No live chat review** was run (needs Gemini spend). Covered by unit and Postgres tests.
- **Merge.** `fix/reviews` is merged into `integration/process-fixes`, like the earlier
  fixes (see Branches).


## Indexing (fix-process/indexing/)

The user chose D1–D4 on 2026-09-26: text-only content before review, replacing the
whole set on publication, supersede-plus-guard for stale reviews, and partial indexes
with discarded rows deleted. Claude decided D5–D12 and recorded them in the plan.
Implemented on `fix/indexing`, merged into `integration/process-fixes` (`8a91579`).

- **`document_key` is not rekeyed by URL (D5).** Fact evidence stores and verifies
  `source_document_key` and `source_checksum`, so both stay the normalized id and raw
  hash. A new `projection_sha256` separates projections of the same bytes.
- **Found: `source_manifests.document_id` had no `ON DELETE` rule**; migration 023 makes
  it `SET NULL`, so discarded versions can be deleted.
- **Found: lock order.** Publication now supersedes reviews, so every path that touches
  an offering's documents or pending reviews takes the offering publication lock first.
- **Found: the hybrid query never used the HNSW index** (its query vector was a CTE
  column). It now orders by the bound vector. At today's size the planner still
  prefers a btree path and a sort.
- **Sweep settings are named `EMBEDDING_SWEEP_BATCH` / `EMBEDDING_SWEEP_INTERVAL_SECONDS`**,
  following the existing un-prefixed names (the plan said `RAG_EMBED_SWEEP_BATCH`).
  The sweep runs in its own worker loop, so a quota wait never blocks runs.
- **IXS07 recall check replaced** by a deterministic dead-row crowding check. ANN recall
  on a 205-node graph is approximate and was not asserted.
- **Found: the dev database is at migration 015.** 016–022 were never applied; a
  deployment must apply 016–023 (IXS08 did this on a copy).
- **IXS10 (live run) not run**: it needs the user's approval of the model spend.

## Stopping runs (fix-process/adk-behavior/)

Findings F1–F7 in `adk-behavior/stop-verification-report.md`, fixed on
`integration/process-fixes` at the user's request on 2026-09-27. Decisions taken
without asking:

- **Ctrl-C while following stops the followed run**, even one the scheduler or the API
  started. The chat said "Monitoring cancelled." and the user expects spending to stop;
  the alternative (only stop watching) left a run the user had just cancelled calling
  the model. The owner hears the request at its next heartbeat.
- **Lease defaults: heartbeat 5 s, lease 120 s, worker recovery every 60 s**
  (`RUN_HEARTBEAT_SECONDS`, `RUN_LEASE_SECONDS`, `RUN_RECOVERY_INTERVAL_SECONDS`, in
  `SchedulerSettings`). The old 30-minute lease is gone: a live run renews its lease,
  so a long run is never mistaken for an abandoned one. The lease must cover at least
  four heartbeats (validated).
- **F2 is fixed through F1**: SIGTERM now cancels the run within about a second, and
  the worker gets a 30 s `stop_grace_period`. `uv run` forwards SIGTERM to Python
  (checked with uv 0.12.15).
- **No cancel route in the API.** Only the chat asks for a stop; `cancel_run` is a
  repository method an API route could call later.
- **The chat also recovers stale runs** (before submitting and while following), so a
  dead owner cannot block monitoring when no worker is running.
- **Migration 024 must be applied** before deploying (the dev database is still at
  015, see the indexing notes).

## Resolution and RAG (fix-process/resolution_and_rag/)

- **Merged** into `integration/process-fixes` on 2026-09-27 as `f2f7e7b` (merge commit,
  like the earlier fixes). The suite on the merged branch: 1272 passed, with the 4
  known Gemini-key tests failing as before.
- **Branch.** `fix/resolution_and_rag` did not exist; it is created from
  `integration/process-fixes` at `180ea9f`.
- **Design choices agreed with the user** (2026-09-27): D1–D5 in the
  [plan](resolution_and_rag/resolution-and-rag-fix-plan.md#decisions). D6–D20 were taken
  without asking and are listed there as open to change.
- **Hand-off (monitoring/HITL): a run waiting for review blocks new runs.** `_find_active`
  ([repositories/monitoring.py](../app/repositories/monitoring.py)) counts
  `awaiting_review` as active:
  - a chat refresh is pulled into an older run's reviews, possibly a scheduler run;
  - a family refresh is refused as "already in progress" while an offering run waits,
    possibly for days.

  The rule is still open ("never block" or "block only this session's run"). Either
  rule needs four safeguards:
  1. Catch `ReviewConflictError` in the monitoring node's review loop and tell the
     reviewer the review was superseded and nothing was applied. A resumed pause whose
     review is no longer pending must say so, not drop the answer silently.
  2. Close a run as soon as its last pending review is superseded. Today that happens
     only at worker startup (`complete_runs_without_pending_reviews`).
  3. Review the newest waiting run of an offering first (`_oldest_awaiting_review` is
     oldest first). Approving a newer run should supersede the older one's reviews, so
     an older approval never leaves a stale comparison baseline.
  4. Expect daily scheduler runs to proceed while a review waits. The new review of the
     same field supersedes the old one, so the queue does not grow.

  "Block only this session's run" also needs a column recording the chat session that
  started a run; runs do not record it today.
- **Decisions taken without asking** (D6–D20 in the plan, all implemented):
  - **D6.** No keyword fallback when the interpreter fails: the turn is "unavailable".
  - **D7.** `resolve_request` and `answer_tariff_query` take no text argument.
  - **D8.** `overview` is a new operation.
  - **D9.** `/questions` asks the interpreter for the shape only.
  - **D10.** Unit embeddings moved to the worker sweep.
  - **D11.** Prefix `to_tsquery`, with stemmed terms.
  - **D12.** The intent enum values are unchanged, plus `route`.
  - **D13.** The standalone question is the question of record.
  - **D14 and D15.** History items without evidence are left out and listed; history
    citations are compact.
  - **D16.** Migration 025, a partial unique index.
  - **D17.** One family per turn.
  - **D18.** The `clarification_response` contract is kept.
  - **D19.** The V5 cross-check can only force a question, never add a scope.
  - **D20.** The model is unchanged (`generation_model`).
- **Decisions found while implementing:**
  - **Gemini rejects `additionalProperties`** in a response schema. The interpreter's
    output models use `extra="ignore"`, and pydantic still validates every value.
  - **The model is not deterministic at temperature 0,** so interpretations are
    recorded per case.
  - **V3 is enforced in code for replies:** `PendingClarification.expects_single_value`.
  - **One prompt rule was added,** after the live run: a singular value asked of a
    family is `single`.
  - **Lexical query terms are stemmed before the prefix,** because a prefix only
    matches forward.
  - **History citations come from the accepted snapshots,** not from the structured
    projection. This covers family-less history and pre-read-model snapshots.
- **Live runs.** The interpreter runs used `GEMINI_API_KEY` from
  `../bank-tariff-monitoring-agent/.env` at run time, without printing or copying it.
  They made intent-interpretation calls only, ~150 per full run, with ~3.8k input and
  ~200 output tokens per call. The final run scored 133/133 with 0 safety mismatches.
- **Not done (needs the user):**
  - RRS07, the whole-agent `agents-cli eval`, which spends whole-agent tokens.
  - Applying migration 025 to the dev database.
  - Deployment.
- **AGENTS.md updated** (2026-09-27, on the user's instruction). The Gemini boundary
  now reads "request interpretation (intent, catalog scope and the question's query
  shape, one tool-free call per chat turn, validated by code)" instead of "intent
  resolution".

## Review and publication fixes (fix/review-and-publication)

From the end-to-end review of 2026-09-27; merged into `integration/process-fixes`.

- **Rule for waiting reviews: never block** (the hand-off above asked for a choice;
  taken without asking, as "block only this session's run" needs a session column and
  still stalls the scheduler on its own paused runs). Migration `026` limits active-run
  uniqueness to `queued`/`running`. The four safeguards listed in the hand-off are in:
  1. an answer to a review superseded or aborted while the chat waited is reported
     (`answers_not_applied`), and a `ReviewConflictError` is no longer a tool error;
  2. paused runs with nothing pending are closed every recovery interval and by
     "review them", not only at worker start;
  3. "review them" walks the newest paused run first, and publishing any newer
     snapshot of an offering supersedes the older candidate's reviews;
  4. scheduled runs proceed while a review waits.
- **Superseding a snapshot's last review closes it** (snapshot `rejected`, execution
  `failed` at `review_superseded`), so "a newer candidate awaits review" stops being
  true for good. Snapshot age ties (two runs reusing one fetch) break on run queue time.
- **`reject_all` supersedes only its own snapshot's reviews** (family runs hold one
  snapshot per offering).
- **Reviews of runs that ended are superseded** (`close_orphaned_reviews`) and never
  announced.
- **OCR approvals are remembered** for the exact result approved; a remembered
  confirmation raises no OCR signal again. Reused review citations take the passage's
  current discovery labels. A candidate needing review with no signal fails the offering
  (`offering.validation_failed`) instead of pausing with nothing to ask.
- **Citation quotes are stored as the source's own text** (`source_span`), which the
  projector's exact-substring check requires.
- **Nested `details` fields** are compared and cited one by one (`tariff_fields`).
- **A linked document that failed this run** (not a 404) fails the offering with
  `source.linked_document_unavailable` when a field the last accepted snapshot found is
  no longer found.
- **Legacy RAG removed** at the user's request: the answer path, its settings
  (`TARIFF_ANSWER_READ_MODEL`, `RETRIEVAL_TOP_K`, `RETRIEVAL_MIN_SCORE`), chunk
  embeddings, offering summaries, the shadow read and the evidence-retention audit.
  Migration `027` drops the chunk vectors, full-text column and search indexes and the
  summary documents; chunk text stays (it anchors fact evidence).
- **Existing databases** need `026` and `027` (after `016`–`025`); a fresh volume gets
  all of them from `docker-entrypoint-initdb.d`.
- **Phase research scripts** under `fix-process/*/scenarios|probes|survey` reflect the
  code of their phase; several no longer run against this branch and are kept as
  records.
