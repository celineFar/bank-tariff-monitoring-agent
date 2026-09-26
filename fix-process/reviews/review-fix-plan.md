# Review process: fix plan

Date: 2026-09-26 · Branch: `fix/reviews` (from `integration/process-fixes` after the
semantic-extraction merge) · Status: **implemented and validated** (Phases 0–5 done; deployment needs approval). Source report:
[../review-process-report.md](../review-process-report.md). Decisions the report left open
were taken without asking the user, as instructed; each is recorded in
[Decisions](#decisions) and in [../note.md](../note.md).

## Scope

The path from a snapshot's review signals to a human decision:

- signal detection ([snapshot_lifecycle.py](../../app/services/snapshot_lifecycle.py)
  `detect_review_signals`, `detect_large_rate_changes`);
- review creation ([monitoring_pipeline.py](../../app/services/monitoring_pipeline.py)
  `_review_tasks`) and storage ([repositories/reviews.py](../../app/repositories/reviews.py));
- the review view ([review_resolution.py](../../app/services/review_resolution.py)
  `build_review_view`, `review_policy`) and the CLI
  ([cli.py](../../app/cli.py) `_ordered_evidence`, `_relevant_evidence`, `_show_review`);
- decisions ([review_decisions.py](../../app/services/review_decisions.py));
- the model-facing read tool `get_current_tariffs` ([tools/reads.py](../../app/tools/reads.py));
- chat model-call attribution ([model_call_usage.py](../../app/services/model_call_usage.py)).

**Out of scope:** B3/D7 (override support check; the report decided to leave it as an
accepted risk), and embedding similarity for ranking (open question 4; declined here,
see Q4).

## How this was checked

- **Code.** Read on `integration/process-fixes` at `f47240d` (the semantic-extraction merge).
- **Scale re-measured** (the report's first "when resuming" step), on the 13 captured seeds
  with pages and all labelled PDFs, with the new evidence catalog and the planner's units:
  [unit-measurements.txt](unit-measurements.txt). Passages per offering: 52–443; units:
  17–53; the largest table has 70 rows and the largest section 88 passages (9.4k characters).
  The report's bounds (R4, R5, R7) are therefore still needed.
- **Stored reviews.** The dev database holds the report's 4 Overdraft reviews (old format,
  full evidence copies). They are the compatibility check for rows written before this fix.
- **Real extraction results** for the 13 seeds are regenerated offline, at no model cost,
  from the extraction cache the semantic-extraction validation left
  (`fix-process/semantic_extraction/.cache/extraction-cache.json`); they feed the review
  scenarios.

## What changed since the report

The report was paused before the pipeline change. The semantic-extraction fix
([../semantic_extraction/](../semantic_extraction/)) since merged:

- **Table rows are records** (SE1/SE4): each value names its column path, a
  continuation row carries its rate type, and cited notes come with the row. This is
  what D6 asked of a "display rendering", and it is also the stored form, so the
  evidence IDs are content- and structure-based (SE10) rather than positional.
  P5 is resolved by that change; no second rendering is needed (Q6 below).
- **Evidence IDs no longer change with unrelated page content** (SE10), so a review's
  stored references stay meaningful across runs.
- **Keyword ranking is gone from extraction** (SE6). `FIELD_KEYWORDS`/`_field_score`,
  which the report proposed reusing (P1, R3, R4), no longer exist. The whole-word
  field terms in `app/domain/extraction_terms.py` and the planner's label-based unit
  scoring (`build_units`, `_labels`) replace them.
- **Full evidence mode** (default) sends every selected passage to each extraction call,
  so "the passages Gemini was given for this field" (R3, P2) is the whole selected
  catalog in full mode, and the budgeted selection in budgeted mode.
- **Review decisions are remembered** (SE12) and validation errors are more specific
  (SE17/SE18), so `extraction_invalid` reviews (B1/D2) carry clearer causes.
- `main`'s five commits (D1) are merged (`91c5189`); **B2 is fixed**.

## Summary

| ID | Problem (report ref) | Severity | Status |
|---|---|---|---|
| RV1 | The review's relevant evidence is re-guessed at every step (P1, R1, Part 3.1) | **high** | **fixed** |
| RV2 | A `not_stated` field's review points at the first 20 catalog entries (P2, R3) | **high** | **fixed** |
| RV3 | Unvalidated Gemini evidence IDs reach references (P3) | medium | **fixed** |
| RV4 | Signal-level references are dropped when the review is created (P4, B6) | **high** | **fixed** |
| RV5 | Validation failures are reported as `missing_required_field` (B1, D2) | **high** | **fixed** |
| RV6 | Resolving one review removes another review's signal (B4) | medium | **fixed** |
| RV7 | Every review row stores a full copy of the snapshot's evidence (B5, D4) | medium | **fixed** |
| RV8 | `get_current_tariffs` hands the model the whole evidence catalog (P6, D5) | **high** (cost) | **fixed** |
| RV9 | Whole tables/sections as display units, bounded (R2, R4, R5, R7) | medium | **fixed** |
| RV10 | `?` has no path to the captured content (R5, P6) | medium | **fixed** |
| RV11 | The reviewer sees less of a passage than the check uses (B8) | low | **fixed** |
| RV12 | Chat model calls cannot be attributed to a run (B7) | low | **fixed** |
| RV13 | Ranking misses are invisible (R4 "log when the citation is outside the units") | low | **fixed** |
| — | Sibling reviews of one field superseded each other (found in Phase 1) | high | **fixed** (migration 022) |
| — | `get_tariff_history` sends whole snapshots to the model (same cause as RV8) | high (cost) | **fixed** (Phase 4) |
| — | Overrides fail with several reviews (B2) | — | **already fixed** (`4bf3d3f`, merged in `91c5189`) |
| — | Table rows hard to read (P5, D6) | — | **resolved by SE1/SE4** (records) |
| — | Override not checked against its passage (B3, D7) | — | **accepted risk** (report decision) |


---

## RV1. The review's relevant evidence is decided once, as references

**Where.** `detect_review_signals` ([snapshot_lifecycle.py:223](../../app/services/snapshot_lifecycle.py#L223)),
`build_review_view` ([review_resolution.py:465](../../app/services/review_resolution.py#L465)),
the CLI's `_ordered_evidence` / `_relevant_evidence` ([cli.py:583](../../app/cli.py#L583),
[:604](../../app/cli.py#L604)).

**What happens.** Three rankers guess, from the field name as a substring, which passages
matter, each time the review is shown (P1). The knowledge available when the signal was
raised (the field's citations, the failed check, the passages extraction read) is thrown
away (Part 3.1).

**Fix (R1).** A new module `app/services/review_evidence.py` builds a `ReviewEvidenceSet`
when the signal is raised, from what the pipeline already knows:

```
ReviewEvidenceSet
  units: [ReviewEvidenceUnit]      # display units, in the order shown
    kind: table | section | passage
    key: "<document_id>|<table id>" or "<document_id>|<section path>"
    evidence_ids: [...]            # the passages shown, in source order (bounded, RV9)
    seed_ids: [...]                # the passages that put this unit in the set
    why: cited | batch | candidate | ocr | rate_new
    omitted: n                     # passages of the unit left out by the bounds
  unknown_ids: [...]               # IDs Gemini cited that are not in the catalog (RV3)
```

Seeds per reason (R3, adapted to the new pipeline):

| Reason | Seeds | Units |
|---|---|---|
| `missing_required_field` (not stated / absent) | the passages the field's extraction call read (RV2), scored with the planner's label scoring for this field | best unit, a second within `HITL_DOCUMENT_RANK_GAP` (R4) |
| `extraction_invalid` (RV5) | Gemini's citations, filtered against the catalog | units holding them, ≤ 2, by cited count then precedence |
| `source_applicability` | the field's citations | the same |
| `official_source_conflict` | each candidate's passage | one unit per candidate |
| `ocr_evidence` | the OCR citations | the OCR page passage(s) |
| `large_rate_change` | the new value's citations (RV4/B6) | their units; before/after numbers stay in the guidance |

Near-duplicate units (a page table and its PDF copy) are merged before picking, keeping
the higher-precedence one (R4). The three rankers and both `term` special cases are
deleted; the view and the CLI read the set.

## RV2. A `not_stated` field's review points at the first 20 catalog entries

**Where.** [snapshot_lifecycle.py:309](../../app/services/snapshot_lifecycle.py#L309).

**Fix.** `SemanticExtractionResult.call_evidence`: per extraction call (batch id), the
evidence IDs it read, for fresh calls and cache hits alike. RV1 seeds a
`missing_required_field` review from the call that held the field. For old results
without it, the fallback is the whole catalog scored for the field (R3's fallback), never
"the first 20".

## RV3. Unvalidated Gemini evidence IDs reach references

**Where.** [semantic_extraction.py `_review_item`](../../app/services/semantic_extraction.py)
(`evidence_ids` copied from the raw citations), [snapshot_lifecycle.py:316-330](../../app/services/snapshot_lifecycle.py#L316-L330).

**Fix.** The builder keeps only IDs present in the catalog; the others go to
`unknown_ids` and are shown as "Gemini cited a passage that does not exist". References
passed to a `ReviewCandidate` are capped at its 20-reference limit.

## RV4. Signal-level references are dropped when the review is created

**Where.** [monitoring_pipeline.py:845 `_review_tasks`](../../app/services/monitoring_pipeline.py#L845)
reads references only from `candidates`; a `large_rate_change` signal has none (B6).

**Fix.** Every signal carries its `evidence_set` (RV1), and `_review_tasks` stores it on the
review. `large_rate_change` signals get the new value's citations from the validated field.
Old signals without a set fall back to their `evidence_references`, then the builder.

## RV5. Validation failures are reported as `missing_required_field`

**Where.** [snapshot_lifecycle.py:316-330](../../app/services/snapshot_lifecycle.py#L316-L330),
[cli.py `_show_review`](../../app/cli.py) ("No valid X was extracted").

**Fix (D2, decided).** `ReviewReason.EXTRACTION_INVALID`:
- raised for a review item whose model result exists (a value failed a check), for any
  field, required or not (Q2 below);
- its candidate is Gemini's proposed value, with the valid cited passages as references;
- its guidance names the value and the failed checks ("Gemini proposed X; check failed: Y");
- allowed decisions: `select_candidate` (accept Gemini's value after checking it), `override`,
  `reject_all` (Q1 below).

`missing_required_field` stays for a *required* field that is `not_stated`, or absent from
the answer. A non-required field absent from the answer is `extraction_invalid` without a
candidate (Q2).

## RV6. Resolving one review removes another review's signal

**Where.** [review_decisions.py:319 `_without_review_signal`](../../app/services/review_decisions.py#L319).

**Fix.** Remove only the signal with the review's own reason *and* scope. Approving the
OCR review of `interest_rate` leaves its `large_rate_change` signal in place, and
`validation.accepted` stays false while it is pending.

## RV7. Every review row stores a full copy of the snapshot's evidence

**Where.** [monitoring_pipeline.py:878](../../app/services/monitoring_pipeline.py#L878)
(`{"items": list(snapshot.evidence)}`), [review_decisions.py `_evidence_items`](../../app/services/review_decisions.py).

**Fix (D4, R1).** New review rows store `{"set": <ReviewEvidenceSet>, "rate_change": …}`.
Passage content is read from the snapshot's `evidence`, which never changes after the
snapshot is created. `build_review_view` and `ReviewDecisionService` take the snapshot's
evidence; rows written before keep working through their `items`.

## RV8. `get_current_tariffs` hands the model the whole evidence catalog

**Where.** [tools/reads.py:89](../../app/tools/reads.py#L89) returns
`result.model_dump()`, with `normalized_tariff` and `evidence` per offering (≈272 kB for
Overdraft; 56% of chat spend in the report's ledger).

**Fix (D5, option i).** The tool returns, per offering, `offering_id`, `freshness`,
`accepted_at`, `age_seconds`, `snapshot_id`, `pending_newer_review`, and the list of field
names with their status (not values), the "what to watch" item of D5. The REST route is
unchanged (it calls the service directly).

## RV9. Whole tables and sections, bounded (R2, R4, R5, R7)

**Fix.** Units come from the IDs the pipeline has: a table is every passage of one
`{table id}:row|note` family in one document; a section is a window around the seed block
in source order (R7): up to 2 blocks either side, stopping at a heading change or 3,000
characters. Bounds (R5), as code constants (Q3):

| Bound | Value |
|---|---|
| Units per review | 1, a second within the rank gap |
| Table shown whole up to | 30 rows |
| Larger table | seed rows ± 3 rows, "*n* more rows" |
| Section | seed ± 2 blocks, ≤ 3,000 characters |

The CLI prints each unit with its rows numbered and the seed rows marked; a reviewer cites
one row. **The model gets only the seed passages, trimmed** (R6): the review pause
payload carries the guidance, candidate, input format and up to 5 seed excerpts. The CLI
renders the units from the review row and the snapshot through its own repositories.

## RV10. `?` has no path to the captured content

**Fix (R5).** At snapshot creation, the rendered Markdown of the *selected* sources
(`render_normalized_markdown` of the selected bundle) is saved with the snapshot
(migration: `tariff_snapshots.selected_sources_markdown text`). The CLI's `?` opens it in
the pager (search with `/`). It is never sent to the model.

## RV11. The reviewer sees less of a passage than the check uses

**Where.** CLI 400 characters ([cli.py:673](../../app/cli.py#L673)), view 1,500.

**Fix.** The CLI shows a unit's passages whole (records are short since SE1; a single
passage is bounded at 4,000 characters, the same limit the stored citation uses). The
saved override citation quotes the passage up to that same limit.

## RV12. Chat model calls cannot be attributed to a run

**Where.** [model_call_usage.py:367](../../app/services/model_call_usage.py#L367) records
`run_id=None` for every ADK call.

**Fix.** The ADK usage callback reads the active run from the invocation's session state
(the monitoring node's run key) and records it; calls outside a run stay `NULL`.

## RV13. Ranking misses are invisible

**Fix (R4).** When a reviewer's decision cites a passage outside the units shown, the
decision service writes a `review_citation_outside_shown_units` audit event with the review,
the field and the cited ID: a direct measure of ranking misses.

---

## Decisions

The report left these open or awaiting approval. The user asked not to be consulted during
the work, so each takes the report's recommendation where it had one, and otherwise the
safer option. All are mirrored in [../note.md](../note.md).

| # | Question (report ref) | Decision | Affects |
|---|---|---|---|
| Q1 | Allowed decisions for the new reason (D2) | `select_candidate` (accept Gemini's value once a human has checked it), `override`, `reject_all`. Not `approve`: there is no accepted value to approve. | RV5 |
| Q2 | A validation failure on a *non-required* field (D2) | Still a review, as `extraction_invalid`. Publishing requires every extracted field to be valid; dropping the field silently would lose data without anyone seeing it. | RV5 |
| Q3 | Bounds as code constants or settings (R5, open question 1) | **Code constants** (report's recommendation), with the rank gap from `HITL_DOCUMENT_RANK_GAP`. | RV9 |
| Q4 | Keyword misses in `not_stated` ranking (open question 4) | **Accept, with `?` and logging** (report's recommendation). No embeddings in review routing: it is a new model use where AGENTS.md prefers determinism. | RV1, RV13 |
| Q5 | The generic "Information Guide" tagged `current_product` (open question 5) | **Track separately**: a source-discovery hand-off, in `../note.md`. | — |
| Q6 | Table display rendering (D6) | **No second rendering.** SE1/SE4 made the stored row *the* readable record (column paths, notes); its quotes stay exact substrings, so D6's quote-mapping question disappears. | P5 |
| Q7 | What `get_current_tariffs` returns (D5) | **Option (i): freshness only**, plus field names with their status (D5's "what to watch"). | RV8 |
| Q8 | Section units (R7, open question 2) | **A window around the seed block** (report's recommendation). | RV9 |
| Q9 | What `?` shows (R5, open question 3) | **The selected sources' Markdown, saved with the snapshot** (report's recommendation); never sent to the model. | RV10 |
| Q10 | Final name of the new reason (D2) | **`extraction_invalid`.** | RV5 |
| Q11 | What the model receives with a review (R6) | Guidance, candidate, input format, and **at most 5 seed passages, 600 characters each**. The CLI renders the units itself. | RV9 |

**One-time effects after deploy.**
- New reviews store references (`evidence.set`), not evidence copies. Existing review rows
  keep `evidence.items` and are shown as before.
- Migration adds `tariff_snapshots.selected_sources_markdown`; snapshots written before it
  have none, and `?` says so.
- `get_current_tariffs` stops returning `normalized_tariff` and `evidence` to the model; the
  REST route is unchanged.

---

## Implementation phases

Order:
1. failing tests;
2. what the signal knows (evidence set, reasons, references);
3. how reviews store and show it;
4. `?` and ranking-miss logging;
5. model payloads and attribution;
6. validation.

Each phase ends green on `uv run pytest tests/unit tests/integration`.

### Phase 0: Preparation

- [x] Create branch `fix/reviews` from `integration/process-fixes` (`f47240d`).
- [x] Re-measure the scale on the new pipeline: [unit-measurements.txt](unit-measurements.txt).
- [x] Run `uv run pytest tests/unit tests/integration` and record the baseline.
- [x] Add regression tests, `xfail(strict=True)`, one per item, asserting the target behaviour:
  - [x] RV1/RV2: a `not_stated` required field's signal carries an evidence set seeded from
        its extraction call, not the first 20 catalog entries;
  - [x] RV3: an unknown cited ID lands in `unknown_ids`, not in references;
  - [x] RV4: a signal's evidence set survives into the review; a `large_rate_change` review
        links the new value's citations;
  - [x] RV5: a value that failed a check raises `extraction_invalid` with Gemini's value as
        candidate and the failed check in the guidance;
  - [x] RV6: resolving the OCR review keeps the `large_rate_change` signal of the same field;
  - [x] RV7: a new review row stores references, not the evidence catalog;
  - [x] RV8: `get_current_tariffs` returns no `evidence` and no `normalized_tariff`;
  - [x] RV9: a unit shows a whole table up to 30 rows, a window around a seed block, at most
        2 units, and the model payload carries ≤ 5 seed passages;
  - [x] RV10: a snapshot carries the selected sources' Markdown;
  - [x] RV12: an ADK model call during a run records the run id;
  - [x] RV13: a decision citing a passage outside the shown units writes an audit event.
- [x] Check each `xfail` with `--runxfail` to fail today.
- [x] Write the scenario files `scenarios/R01…R06` (Phase 5).

**Phase 0 notes (done).**
- Baseline on `fix/reviews` before any change: **1041 passed, 5 skipped**; the only
  failures/errors are the 4 known tests that need a live Gemini key
  (`test_agent`, `test_agent_engine_app`, `test_server_e2e`).
- `tests/unit/test_review_fixes.py`: 10 `xfail(strict=True)` tests. RV3 is asserted
  inside the RV5 test (the unknown ID and the failed value come from the same answer);
  RV7 inside the first RV4 test (the stored set is the signal's set, with no `items`).
  RV11 is a CLI rendering change and is tested in Phase 2 with the CLI tests.
- With `--runxfail`, each fails for its own missing piece (`call_evidence`,
  `EXTRACTION_INVALID`, `evidence_set`, `_without_review_signal` arity,
  `current_tariffs_payload`, `set`, `selected_sources_markdown`, `ACTIVE_RUN_STATE_KEY`,
  the audit events on `ReviewSnapshotUpdate`).
- Scenario files: [scenarios/](scenarios/) R01–R06, results filled in Phase 5.
- The tests fix these target APIs: `SemanticExtractionResult.call_evidence`;
  signals with `evidence_set` (`units[kind,key,evidence_ids,seed_ids,why,omitted]`,
  `unknown_ids`); `_without_review_signal(validation, scope, reason)`;
  `current_tariffs_payload(result)` in `app/tools/reads.py`;
  `build_snapshot_attempt(..., selected_sources_markdown=)`;
  `ACTIVE_RUN_STATE_KEY` in `model_call_usage.py`; `ReviewSnapshotUpdate.audit_events`.

### Phase 1: What the signal knows (RV2, RV3, RV1, RV5, RV4, RV6)

- [x] RV2: `SemanticExtractionResult.call_evidence` (call id → evidence IDs), for fresh
      calls and cache hits; the field → call mapping from the batches.
- [x] RV1/RV3: `app/services/review_evidence.py`: units (table, section window, passage),
      near-duplicate merge, seeds per reason, label scoring with `extraction_terms`, bounds,
      `unknown_ids`.
- [x] RV5: `ReviewReason.EXTRACTION_INVALID`; `detect_review_signals` splits review items
      into `extraction_invalid` (with candidate) and `missing_required_field` (required and
      not stated or absent); policy and guidance.
- [x] RV4: every signal carries `evidence_set`; `large_rate_change` gets the new value's
      citations.
- [x] RV6: `_without_review_signal` matches reason and scope.
- [x] (Found during the work) Two reviews of one field in one snapshot superseded each
      other; migration `022` keys pending reviews on field *and* reason (see notes).

**Phase 1 notes (done).**
- **RV2.** `SemanticExtractionResult.call_evidence` maps every call (fresh or cached)
  to the evidence IDs it was given; `evidence_read_by(batch_id)` also resolves a repair
  call (`<batch>__repair_<field>`) to its batch, since a repair reads the same packet.
  Results stored before this change have no map: the builder then scores the whole
  catalog (R3's fallback), never "the first 20".
- **RV1/RV3.** [app/services/review_evidence.py](../../app/services/review_evidence.py):
  `cited_evidence_set` (citations, candidates, OCR pages, the new rate value) and
  `field_evidence_set` (a field with nothing extracted: the call's passages ranked with
  the planner's own label scoring, `field_unit_scores`/`labelled_for`, newly public in
  `extraction_planner.py`). Units: a table (`<table id>:row|note` family per document),
  a section (window: seeds ± 2 blocks, ≤ 3,000 characters, seeds always shown), or a
  single passage. A table over 30 passages shows seeds ± 3 rows (± 1, then seeds only,
  if that still exceeds 30). Near-duplicates: word-set Jaccard ≥ 0.8 against a unit
  ranked above it (a page table and its PDF copy). IDs not in the catalog go to
  `unknown_ids` and never into units or candidate references. Models
  `ReviewEvidenceSet`/`ReviewEvidenceUnit` live in `app/domain/review.py`.
- **RV5.** `ReviewReason.EXTRACTION_INVALID`. A review item with a proposed value is
  `extraction_invalid`, with the candidate `extracted:<review item id>` (Gemini's
  parsed value, its valid citations as references, the first quote) plus
  `proposed_value` and `failed_checks` on the signal. A required field not stated or
  missing from the answer stays `missing_required_field` (seeded from its call); any
  other failure (e.g. an optional field missing from the answer) is
  `extraction_invalid` without a candidate (Q2). If none of the cited IDs exists, the
  set falls back to the field's call passages and keeps the `unknown_ids`. Policy:
  `select_candidate`, `override`, `reject_all` (Q1).
- **RV4.** Every signal carries `evidence_set` (and `evidence_references` = its seeds,
  for readers of old signals). `large_rate_change` signals get the validated field's
  citations (`why=rate_new`). The rank gap is `HITL_DOCUMENT_RANK_GAP`, passed through
  `TariffMonitoringPipeline(review_rank_gap=)` → `build_snapshot_attempt`.
- **RV6.** `_without_review_signal(validation, scope, reason)`.
- **Found: sibling reviews superseded each other.** `human_reviews_active_scope_uq`
  and the repository's supersede-on-create keyed on (product, offering, field). An
  OCR review and a rate-change review of `interest_rate` in one snapshot therefore
  collided: the second superseded the first. Before RV6 the remaining decision
  removed both signals (the OCR reading was never checked); after RV6 the superseded
  review's signal could never be cleared. Migration
  [022](../../migrations/022_review_evidence_sets.sql) makes the pending index
  (field, reason); the supersede query skips a same-snapshot review with another
  reason. A newer snapshot still supersedes every pending review of the field.
  Postgres test: `test_two_reasons_on_one_field_of_one_snapshot_both_stay_pending`.
- Suite: 1049 passed, 5 skipped, 6 xfailed (Phase 2–4 items); the 4 known Gemini-key
  failures. Postgres tests need `TEST_DATABASE_URL` (the local test database on
  port 5434); without it 42 tests skip.
- A field with no labelled passage gets an **empty** set (e.g. `fees` when nothing is
  labelled "fee"): the reviewer reads `?` and may cite any passage (logged, RV13).
  This is Q4's accepted risk.

### Phase 2: How reviews store and show it (RV7, RV9, RV11)

- [x] RV7: `_review_tasks` stores `{"set": …, "rate_change": …}`; `build_review_view` and
      `ReviewDecisionService` read passage content from the snapshot's evidence; old rows
      with `items` still work.
- [x] RV9: the review pause payload carries ≤ 5 seed passages (600 characters); the CLI
      renders the units (rows numbered, seeds marked) from its own repositories.
- [x] RV11: the CLI shows whole passages (up to 4,000 characters); the saved override quote
      uses the same limit.
- [x] Delete the three rankers and both `term` special cases.

**Phase 2 notes (done).**
- **RV7.** `_review_tasks` stores `{"set", "rate_change", "failed_checks",
  "proposed_value"}`; no `items`. A signal stored before sets existed gets a set built
  from its `evidence_references` (`_signal_evidence_set`). Passage content comes from
  the snapshot: `review_passages(task, snapshot.evidence)` returns the row's own
  `items` for rows written before this change, else the snapshot's evidence.
  `ReviewResolutionService(snapshots=)` gained `passages(task)`; `prompt_view` and
  `validate` take the passages (the node loads them once per review).
  `ReviewDecisionService` loads the snapshot first and resolves citations against it;
  the candidate-exists and approve-allowed checks still run before any read.
- **Scope of a citation.** An override may cite **any passage of the snapshot**, not
  only the shown units (the old scope was the full copy in `items`, so this keeps the
  same reach); citing outside the units is logged in Phase 3 (RV13).
- **RV9.** The pause payload (`build_review_view`) carries guidance, candidates and
  ≤ 5 seed excerpts of ≤ 600 characters (`model_excerpts`). The CLI loads the review's
  units itself through `ReviewDisplayService` (container field `review_display`,
  passed to `ChatSession(displays=)`); without it (tests, or a load error) it shows the
  pause's excerpts. Units print as numbered rows, seeds marked `▶`, with
  "*n* more passages … not shown". `all` lists every passage of the snapshot for
  citing one outside the units; `?` shows the selected sources (Markdown from
  Phase 3, else the `all` list). With one shown passage that literally states the
  typed value, it is used as support without asking (before: only when exactly one
  passage was shown).
- **Rows written before this change** whose items are not valid catalog records (ids
  outside `ev_<24 hex>`, as in the demo script and fixtures) cannot be grouped into
  units: each cited item becomes its own `passage` unit. A `missing_required_field`
  row of that kind with no parsable items shows no passages (use `all`).
- **RV11.** The CLI prints whole passages up to 4,000 characters; the override check
  (`_evidence_excerpt`) uses the same 4,000; the saved citation quotes up to 4,000.
  **Correction to the plan:** the stored citation limit was 1,500, not 4,000;
  `EvidenceCitation.quote` is raised to 4,000 so all three agree. The model's
  excerpt stays at 600.
- **Deleted:** `_ordered_evidence`, `_relevant_evidence` (CLI), the `rank` in
  `build_review_view`, and both `term` regex special cases. `term_supported_by_passage`
  stays: it checks support, it does not rank.
- `extraction_invalid` guidance names the value and up to 3 failed checks
  ("Gemini proposed …; check failed: …"). Test: selecting Gemini's value resolves the
  field and clears its signal.
- Suite: 1054 passed, 5 skipped, 4 xfailed (Phases 3–4); the 4 known Gemini-key
  failures.

### Phase 3: `?` and ranking misses (RV10, RV13)

- [x] RV10: migration `022` adds `tariff_snapshots.selected_sources_markdown`; the pipeline
      renders the selected bundle; the repository reads and writes it; the CLI's `?` opens
      it in the pager.
- [x] RV13: the decision service writes `review_citation_outside_shown_units`.

**Phase 3 notes (done).**
- **RV10.** `SnapshotAttempt.selected_sources_markdown` (excluded from dumps) is set by
  the pipeline from `render_normalized_markdown(build_selected_source_bundle(...))`
  (the same selected bundle the RAG projection indexes, now built once) and written by
  `_insert_snapshot`. Migration 022 adds the column. The general snapshot reads do not
  map it (they already carry the large `evidence`); `PostgresSnapshotRepository.
  selected_sources_markdown(id)` fetches it, and `ReviewDisplayService` calls it. The
  CLI's `?` pages it through `rich`'s pager; a snapshot written before the migration
  has none and `?` lists every passage instead.
- **RV13.** `ReviewDecisionService` adds a `review_citation_outside_shown_units` event
  (review id, reason, field, cited evidence id, shown unit keys) to
  `ReviewSnapshotUpdate.audit_events` when an **override** cites a passage outside the
  review's stored units. The repository writes `update.audit_events` into
  `audit_events` in the decision's transaction. Rows without a stored set (written
  before this change) are never logged: they had no bounded "shown" set.
- Tests: pipeline saves the selection's Markdown (SD7 test); Postgres round trip of the
  column and the audit event; CLI `?` with and without Markdown; inside-units override
  writes no event.
- Suite: 1060 passed, 5 skipped, 2 xfailed (Phase 4); the 4 known Gemini-key failures.

### Phase 4: Model payloads and attribution (RV8, RV12)

- [x] RV8: `get_current_tariffs` returns freshness and field statuses only.
- [x] RV12: ADK usage callbacks record the active run id from session state.
- [x] (Added) `get_tariff_history` returns snapshots without `evidence`,
      `semantic_extraction` and `validation` (same cause as RV8).

**Phase 4 notes (done).**
- **RV8.** `app/tools/reads.py` `current_tariffs_payload(result)`: per offering
  `product`, `offering_id`, `freshness`, `snapshot_id`, `accepted_at`, `age_seconds`,
  `pending_newer_review` and `fields` (field name → status, e.g. `"term": "not_stated"`).
  No values, no evidence. `missing_means` is still added when an offering is missing.
  The REST route `GET /tariffs/current` is unchanged (it calls the service).
- **Knock-on (decided).** `answer_tariff_query` used to reply to a scope-only plan with
  "use get_current_tariffs or get_tariff_history for this scope", i.e. read values from
  the snapshot. That path no longer carries values, so the hint now says: ask which
  field the user wants and resolve again; `get_current_tariffs` reports freshness only.
  Values keep reaching the user only through `answer_tariff_query`, with citations.
- **Added: history payload.** `get_tariff_history` dumped up to 100 whole snapshots,
  each with its evidence catalog and the full extraction record (raw model outputs):
  the same "storage payload as model payload" cause as RV8, larger. It now uses
  `tariff_history_payload`, which keeps `normalized_tariff`, times, ids and the change
  sets and drops `evidence`, `semantic_extraction` and `validation`.
- **RV12.** `ACTIVE_RUN_STATE_KEY = "temp:monitoring_active_run"` in
  `model_call_usage.py`. The monitoring node writes `{run_id, invocation_id}` there as
  soon as it knows its run (new, found, or resumed; it re-runs from the top on resume,
  so a resumed invocation sets it again). `adk_usage_callbacks` records that run id when
  the invocation matches; other calls keep `run_id = NULL`. `temp:` state is never
  persisted. The model call that decides to start monitoring precedes the run and stays
  `NULL`; the calls after the node (the reply) are attributed.
- Suite: 1063 passed, 5 skipped, 0 xfailed; the 4 known Gemini-key failures.

### Phase 5: Validation

- [x] Run the offline scenarios:
  - R01: the test suite;
  - R02: the report's confirmed problems fixed;
  - R03: review sets on the 13 seeds' real extraction results (regenerated from the cache,
    $0), with sizes within the bounds;
  - R04: the 4 stored old-format reviews still build views;
  - R05: the tool payload size;
  - R06: the ranking-miss event.
- [x] Update [docs/native-hitl-review.md](../../docs/native-hitl-review.md),
      [docs/review-quarantine.md](../../docs/review-quarantine.md),
      [docs/architecture.md](../../docs/architecture.md) and the report's status line.
- [x] Update this plan's Summary statuses; write `scenario-results.md`.

**Phase 5 notes (done).** Results: [scenario-results.md](scenario-results.md).
- R01–R06 all pass. R03's input changed (the extraction cache holds one seed, not 13;
  budget spent): Part A runs that seed's real answers, Part B every seed's real catalog
  with an extractor that finds nothing.
- **R03 changed the code.** 6 of 48 missing-field reviews missed the labelled value on
  the first run; `field_evidence_set` now breaks score ties by precedence then tables,
  and gives the second slot to the best table after a non-table unit (46/48 after).
  Test: `test_missing_field_review_adds_the_table_after_a_headline_section`.
- Docs updated: `docs/native-hitl-review.md` (new "What a review shows"),
  `docs/review-quarantine.md`, `docs/architecture.md`, `docs/tariff-query-services.md`;
  the report's status line.

## Deployment (not done: needs human approval)

- Apply migration `022_review_evidence_sets.sql` (drops `human_reviews_active_scope_uq`,
  adds `human_reviews_active_scope_reason_uq` and `tariff_snapshots.selected_sources_markdown`).
- One-time effects: see [Decisions](#decisions). Reviews already pending keep their
  `evidence.items` and are shown from it; snapshots written before have no `?` text.
- After deploy, watch `review_citation_outside_shown_units` events: each is a review
  whose units missed the passage the reviewer used.

