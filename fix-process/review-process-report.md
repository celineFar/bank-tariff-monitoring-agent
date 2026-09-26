# Review process: problem report

Date: 2026-09-25 · Status: **paused** (see below). Findings and first decisions are recorded;
see [Decisions and open questions](#decisions-and-open-questions) at the end.

> **Paused on 2026-09-25, during the ranking brainstorm (Part 4).** The monitoring pipeline is
> about to change. After that change, each seed may produce much less data, so the scale
> assumptions behind Part 4 (262 passages, 52 units, tables of up to 25 rows, 77-passage
> sections) may no longer hold.
>
> **When resuming:**
> 1. Re-measure a snapshot from the new pipeline: passage count, unit count, table sizes,
>    section sizes. If an offering yields only a few passages, R4/R5/R7 (picking 1–2 units,
>    bounds, section windows) may be unnecessary, and "show everything" may be enough.
> 2. Check which Part 1/Part 2 findings still apply after the pipeline change. P1, P2 and R3
>    depend on how the extraction batches and the evidence catalog are built.
> 3. Still valid whatever the pipeline does: P3 (unvalidated IDs), P4 (signal refs dropped),
>    B1 + D2 (reason split, decided), B4 (signal removal by scope), D5 (`get_current_tariffs`
>    payload), D6 (table display rendering, decided), R1 (decide once, store references).
>
> `main`'s five fixes (D1) have since been merged into `adk-native-runtime`.

## How this was checked

- **Code.** Fixes land on `adk-native-runtime`, the new ADK run design. Line references point
  there unless marked `main`. Every problem in Part 1 also exists on `main`/`demo/safe-failure`.
  Part 2 marks the ones that differ by branch.
- **Data.** Read-only queries against the running demo database: `human_reviews` (4 rows),
  their two Overdraft snapshots, `model_call_usage`, and the ADK `events` table. The
  running stack is on the `demo/safe-failure` schema (it still has the `workflow_*` columns).
- **Replay.** The real `build_review_view` was run over the four stored reviews to see which
  passages a reviewer is actually shown.

## Where review evidence flows

```
semantic extraction ──> snapshot                        (snapshot_lifecycle.py)
                          evidence   = whole catalog (262 passages for Overdraft)
                          validation.review_signals[]   <- detect_review_signals
                            each signal: reason, issue_scope, evidence_references?, candidates?
                    ──> ReviewTask per signal           (monitoring_pipeline.py:720 _review_tasks)
                          evidence   = copy of whole catalog
                          candidates = from signal.candidates only
                    ──> ReviewPromptView                (review_resolution.py:451 build_review_view)
                          rank, then cut to 20 passages
                    ──> model (tool result)  /  CLI (re-ranks and filters again, cli.py:583-624)
                    ──> decision                        (review_decisions.py)
```

No step computes "the passages relevant to this review" once and passes that set on. Each
later step guesses again from strings. That underlies most of what follows.

---

## Part 1: Reported problems (all confirmed)

### P1. Evidence ranking is field-specific rather than general

[review_resolution.py:466-480](../app/services/review_resolution.py#L466-L480) ranks every passage
into four tiers:

| Tier | Rule |
|---|---|
| 0 | cited by a *candidate* |
| 1 | `field == "term"` and matches `term (months)` / `indefinite term`: the one-off rule |
| 2 | `issue_scope.replace("_", " ") in content` (plain substring) |
| 3 | everything else |

Then it keeps the first 20 ([line 500](../app/services/review_resolution.py#L500)). Ties keep
catalog order, which is precedence, then document, then source item. That order has nothing
to do with the field.

Why tier 2 fails in general:

- **The literal field name is often absent from the page.** Replaying the four stored reviews:

  | Review | Passages | Passages containing the field name | Passages Gemini cited | Cited passages the reviewer sees |
  |---|---|---|---|---|
  | `repayment` (×2) | 262 | 20 | 4 | 4 |
  | `product_name` | 262 | **0** | 2 | **0** |
  | `eligibility` | 262 | **0** | 2 | **0** |

  For `product_name` and `eligibility`, the reviewer was never shown the passages Gemini used.
  The CLI printed "No captured passage directly mentions this field", and `?` showed 20
  arbitrary passages.
- **When the field name does appear, the substring is too loose.** `"term"` matches
  "Other **term**s can be applied…", "de**term**ined" and "Loan **term**s". In the Overdraft
  snapshot, 58 of 262 passages contain `term`, so the real rows compete with noise and catalog
  order decides.
- **There are three rankers, and they disagree.** The service ranker above, plus the CLI's
  [`_ordered_evidence`](../app/cli.py#L583) (its own `row: {field}` tier) and
  [`_relevant_evidence`](../app/cli.py#L604) (a second copy of the `term` regex).

**The pipeline already knows what "relevant to a field" means.** The extraction planner has a
per-field vocabulary,
[`FIELD_KEYWORDS`](../app/services/extraction_planner.py#L103), which already includes
`"term (months)"`, and a relevance score,
[`_field_score`](../app/services/extraction_planner.py#L396) (keywords, role, product
association, canonical page). It uses these to choose which passages Gemini sees for each field.
The review ranker ignores both. The one-off `term` rule rediscovers a keyword the planner
already had.

### P2. `missing_required_field` falls back to generic evidence

[snapshot_lifecycle.py:291-304](../app/services/snapshot_lifecycle.py#L291-L304): when Gemini
returns `not_stated` for a required field, the signal's references are
`result.evidence_catalog[:20]`. That is the first 20 catalog entries in precedence and
document order. Nothing ties them to the field.

Two related gaps:

- The second `missing_required_field` path
  ([lines 308-320](../app/services/snapshot_lifecycle.py#L308-L320)) uses the review item's
  `evidence_ids`. When the field was *absent* from Gemini's response (the cardinality check in
  [`_validate_individual_fields`](../app/services/semantic_extraction.py#L1513)), `raw_result` is
  `None` and the references are empty.
- Neither list reaches the reviewer anyway (see P4).

For a `not_stated` field, the most relevant set is **the passages Gemini was given for that
field's batch**, since those are what it judged insufficient. Today that set is not saved in the
result: `SemanticExtractionResult` keeps `batch_id` on each field but not which passages the
batch contained.

### P3. Unvalidated evidence IDs reach `evidence_references`

[semantic_extraction.py:1760](../app/services/semantic_extraction.py#L1760): a review item's
`evidence_ids` are copied from Gemini's raw citations. They then become the signal's
`evidence_references` ([snapshot_lifecycle.py:318](../app/services/snapshot_lifecycle.py#L318))
without being checked against the catalog.

The review item is created *because* validation failed, and two of those failures are about
the IDs themselves:
[`"field cites evidence that was not supplied in its batch"`](../app/services/semantic_extraction.py#L1504)
and [`"unknown evidence ID"`](../app/services/semantic_extraction.py#L1625). So this path
carries IDs in exactly the cases where they are most likely to be wrong.

The stored data happens to be clean (0 unknown references across the 4 stored signals), but
the path is live. One more constraint for the fix: the raw list is not length-limited, while
`ReviewCandidate.evidence_references` allows at most 20
([review.py:48](../app/domain/review.py#L48)). Copying the raw list straight into a
review would fail validation.

### P4. Signal-level evidence references are dropped when the review is created

[monitoring_pipeline.py:737](../app/services/monitoring_pipeline.py#L737) reads references only
from `raw_signal["candidates"][*]`. `raw_signal["evidence_references"]` is never read. What
each reason carries, and what survives:

| Reason | Signal refs | Candidates | Cited evidence that reaches the review |
|---|---|---|---|
| `ocr_evidence` | yes | yes | yes, through the candidates |
| `official_source_conflict` | no | yes | yes, through the candidates |
| `source_applicability` | yes | no | **none** |
| `missing_required_field` | yes | no | **none** |
| `large_rate_change` | no | no | none; `main` adds only the before/after numbers |

In the database, all 4 reviews were created with 0 candidates. Each dropped the 2–4 references
its signal carried. Tier 0 of the ranker ("candidate references first") was therefore empty
for every real review, which is why P1 decided everything.

### P5. Table rows are shown in a format that is hard to interpret

> **Decided:** add a separate display rendering. The stored content and evidence IDs stay as
> they are. See [decision D6](#d6-tables-a-separate-display-rendering).

[extraction_evidence.py:51-54](../app/services/extraction_evidence.py#L51-L54) turns each table
row into one passage: `Headers: a | b | c` followed by `Row: x | y | z`. As a citation this works
well: one row, an exact locator, an easy-to-check quote. As something to read a value from, it
does not. A real Overdraft row:

```
Headers: Card type ¹ |  | Arca Classic, Master Card Standard/VISA Classic, … |  | Mastercard Gold/VISA Gold, … ,
Row: Loan terms ³ | Term (months) | Indefinite term (until requested back): until loan cancellation … |  |  |  |
```

- The reader has to match cells to headers by position. Empty cells, merged headers and
  row-group labels (`Loan terms ³`) make that unreliable. Gemini, the reviewer and the parser
  of the reviewer's answer all do that matching.
- Footnote markers (`³`) point at table notes, which are separate passages
  ([line 65](../app/services/extraction_evidence.py#L65)) and may not be shown at all.
- Wide rows get cut. The review view keeps 1,500 characters
  ([review_resolution.py:566](../app/services/review_resolution.py#L566)); the CLI shows 400.
- **Constraint for any fix:** `evidence_id` is a hash of the passage content
  ([line 99](../app/services/extraction_evidence.py#L99)). Changing how rows are rendered changes
  every table evidence ID. That invalidates extraction caches and makes the next snapshot look
  like an evidence change.

### P6. Review cost: confirmed, but the cause is different from the note

The note says the review view hands the model all 262 passages. The committed code does not
do that. `build_review_view` cuts to 20
([review_resolution.py:500](../app/services/review_resolution.py#L500)), and so do `main`'s
`monitoring_workflow.py:481` and the code in the running container. One review view measures
8–12 kB, about 2–3k tokens. That matches the ~3.4k-token step per review visible in the
ledger.

**The 262 passages come from `get_current_tariffs`.**
[tools/reads.py:114](../app/tools/reads.py#L114) returns `result.model_dump()`, and each item
carries `evidence=snapshot.evidence`
([tariff_queries.py:109](../app/services/tariff_queries.py#L109)): the whole catalog. The
largest surviving session event is one `get_current_tariffs` response of 272 kB, of which
`items[0].evidence` is 262 kB with 262 entries. The agent calls this tool at the start of the
typical flow ("what is the current tariff?", then monitor, then review). The ~100k tokens then
stay in the durable session and are re-sent on every later turn, including review turns.

Ledger (`stage = adk.cli`, 219 calls, $2.90 total):

| Input size | Calls | Cost | Share |
|---|---|---|---|
| < 20k tokens | 189 | $1.03 | 35% |
| 20k–90k | 11 | $0.25 | 9% |
| ≥ 90k | 19 | **$1.63** | **56%** |

The jump happens in one step (3,277 → 106,158 input tokens) and never goes back down. That is
a single large tool result entering the history, not reviews adding up.

The parts of the note that hold:

- Review views do accumulate in the history, about 3.4k tokens per fetched review.
- The model needs far less than it gets.

One claim does not hold. The CLI's `?` "All captured passages" view
([cli.py:663](../app/cli.py#L663)) re-sorts the ≤20 passages already in the view; it is not the
full catalog. **No path to the full list exists today.** "Keep the full list for `?`" would be
new work, not something a trim could accidentally break.

---

## Part 2: Other bugs and design flaws found

### B1. High: validation failures are reported as `missing_required_field`

[snapshot_lifecycle.py:308-320](../app/services/snapshot_lifecycle.py#L308-L320) turns every
extraction review item into `missing_required_field`, whatever the cause. All 4 stored reviews
are in fact validation failures of values Gemini *did* find:

| Field | Actual cause (`validation_issues`) |
|---|---|
| `repayment` | "citation quote is not present in the supplied evidence excerpt" |
| `eligibility` | "citation quote is not present in the supplied evidence excerpt" |
| `product_name` | "product_name must be anchored to the canonical product page…" |
| `repayment` | "condition-specific alternatives were returned without conditions" |

Consequences:

- The reviewer is told "No valid *X* was extracted" ([cli.py:638](../app/cli.py#L638)). They are
  never shown Gemini's proposed value, the failed check, or the quote it cited. All of that is
  saved in `semantic_extraction.review_items`, but none of it reaches the review.
- The field does not have to be required. A validation failure on any field (`variants`,
  `special_conditions`, …) opens a "missing *required* field" review and blocks the snapshot.

### B2. High, this branch only: overrides fail when a snapshot has more than one review

[review_decisions.py:199-202](../app/services/review_decisions.py#L199-L202) raises unless the
*whole* extraction is acceptable once *one* field is fixed. With two open field reviews, that
never happens, so every override fails and only `reject_all` works. Both stored multi-review
snapshots ended as rejected plus superseded.

This was **already found and fixed on `main`** in `4bf3d3f` ("Let a run with several field
reviews be approved"), but that commit is not on `adk-native-runtime`. It carries over
without conflict. See [D1](#d1-fixes-land-on-adk-native-runtime-mains-five-commits-come-over)
for all five `main`-only commits.

### B3. High: an override does not have to be supported by the passage it cites

> **Decided:** accepted risk; left as is. See [D7](#d7-must-an-overrides-value-appear-in-the-cited-passage).

The override path checks the value against the cited passage only for "indefinite term"
([review_input.py:122-123](../app/services/review_input.py#L122-L123)). For every other field, and
for any JSON override, the reviewer can cite any passage in the review. Nothing checks that the
passage states the value. The CLI asks for a "supporting passage" number
([cli.py:803](../app/cli.py#L803)) and accepts any of them.

The saved citation's quote is then the whole passage (`content[:1500]`,
[review_decisions.py:334](../app/services/review_decisions.py#L334)), not the words that state the
value. This weakens the AGENTS.md rule that "every accepted non-missing tariff value must
retain verifiable source evidence". After a review, "verifiable" only means "points at some
passage".

### B4. Medium: resolving one review removes another review's signal

[`_without_review_signal`](../app/services/review_decisions.py#L268-L277) filters on
`issue_scope` alone. `ocr_evidence` and `source_applicability` can both fire for the same found
field ([snapshot_lifecycle.py:221-269](../app/services/snapshot_lifecycle.py#L221-L269)), which
creates two reviews. Approving the OCR one also deletes the `source_applicability` signal, and
`validation.accepted` can be written `true` while that review is still pending.

Publishing is still safe: the repository holds the snapshot until no review is unresolved
([reviews.py:332-345](../app/repositories/reviews.py#L332-L345)). But the snapshot's stored
`validation` misstates its own state, and anything that reads it is misled.

Merging `main`'s `221f73f` makes this more likely. That commit runs the rate guard on every
candidate, not only clean ones, so `large_rate_change` on `interest_rate` can now sit next to
`ocr_evidence` on `interest_rate`. Approving the OCR review would then erase the rate signal.

### B5. Medium: every review row stores a full copy of the snapshot's evidence

`evidence={"items": list(snapshot.evidence)}`
([monitoring_pipeline.py:766](../app/services/monitoring_pipeline.py#L766)) makes each
`human_reviews` row about 261 kB, duplicating `tariff_snapshots.evidence`. Four reviews hold four
copies of the same 262 passages. It is also the reason every consumer has to rank and trim for
itself. Whatever the P1/P6 fix decides a review should hold (references only, a ranked subset,
or a full copy) should be decided here.

### B6. Low: `large_rate_change` reviews carry no evidence link

The signal has no references and no candidates
([snapshot_lifecycle.py:350-360](../app/services/snapshot_lifecycle.py#L350-L360)), so the reviewer
gets whatever mentions "interest rate". The passages that support the *new* value are already
in the snapshot, in the validated field's `evidence`, but are not linked to the review. This
is the same gap as P4.

### B7. Low: chat model calls cannot be attributed to a run

All 219 `adk.cli` rows in `model_call_usage` have `run_id = NULL`. The cost of reviewing a run
cannot be queried; it had to be pieced together by hand from timestamps.

### B8. Low: the reviewer sees less of a passage than the check uses

The reviewer sees 400 characters in the CLI and 1,500 in the view. The override support check
(where one exists) and the saved citation use the full content. On a long table row, the
reviewer can cite a passage whose relevant part they never saw.

---

## Part 3: Common causes (starting points for the discussion)

1. **The relevant evidence is never decided at the point where it is known.** When a signal
   is raised, the code knows the field's validated citations, Gemini's raw citations, the
   batch's passages and the failed check. It throws most of that away, and later steps guess
   from strings (P1, P2, P4, B1, B6).
2. **There is no shared definition of field relevance.** Three rankers use literal field
   names, while the planner's `FIELD_KEYWORDS` and `_field_score` go unused (P1).
3. **Model-facing payloads are the storage payloads.** `get_current_tariffs` and the review
   view serialize domain objects as they are, so the model receives citation archives it
   doesn't need (P6, B5).
4. **Review reasons are too coarse.** "Gemini said not stated" and "Gemini's answer failed a
   check" are different problems for a reviewer (B1).
5. **The branches have drifted apart.** A known fix and the rate-review work exist only on
   `main` (B2).

## Part 4: Ranking brainstorm

Agreed so far: (1) a review's relevant passages are **decided once**, when the signal is raised,
not re-ranked each time the review is shown; (2) for `missing_required_field` the reviewer should
see **whole tables or sections** of the source, not isolated rows. The recommendations below build
on both. Each one is marked **Recommend**; the questions at the end are still open.

### R1. Decide once, store references, read content from the snapshot

**Recommend:** when a signal is raised, compute a *review evidence set* and store it on the
signal and the review as references only:

```
evidence_set:
  units:                          # display units, in order
    - kind: table | section | passage
      key: "<document_id>/<table_id>"  or  "<document_id>/<heading path>"
      evidence_ids: [...]         # every passage of the unit, in source order
      seed_ids: [...]             # the passages that put this unit in the set
      why: cited | batch | candidate | ocr | rate_new | rate_previous
  unknown_ids: [...]              # IDs Gemini cited that are not in the catalog (P3)
```

- The passage text is read from the snapshot's `evidence` when the review is shown. A snapshot's
  evidence never changes after it is created (`approve_with_snapshot` updates the tariff,
  extraction and validation, not `evidence`), so references stay valid.
- This replaces the 261 kB copy in every review row (B5) and answers **D4**.
- `ReviewTask.evidence` still exists, so old rows keep working. New rows use `evidence_set`.
- One builder, called from `detect_review_signals` (or right after it). The three rankers in
  `build_review_view` and the CLI, and both `term` special cases, are deleted (P1).

### R2. Passages stay the citation unit; tables and sections become the display unit

**Recommend:** build units from IDs the pipeline already has. No schema change is needed.

- **Table:** all passages whose `source_item_id` starts with the same `{table_id}:`, meaning
  rows `{table_id}:row:{n}` and notes `{table_id}:note:{i}`. They are shown together with the
  headers once, using the D6 display rendering. Footnotes finally sit next to the rows that
  reference them.
- **Section:** text blocks of one document that share the same heading path (`section`).
- **Passage:** fallback for a passage that belongs to neither (for example an OCR page).

A reviewer still cites *one row* for an override, so rows are numbered inside each unit, and
the citation stays as precise as it is today.

### R3. What seeds the set, per reason

The rule for every reason: **seeds come from what the pipeline already knew when it raised the
signal.** String matching on the field name is never the primary source.

| Reason | Seeds | Units shown |
|---|---|---|
| `missing_required_field` (not stated / absent) | The passages Gemini was **given** for this field's batch, ordered by the planner's `_field_score` for *this* field (a batch serves several fields) | The parent tables/sections of the top seeds, **whole** (your point 2) |
| `extraction_invalid` (new, D2) | The passages Gemini **cited**, filtered against the catalog; unknown IDs go to `unknown_ids` and are shown as "Gemini cited a passage that does not exist" | Parent units of the cited passages, with the cited rows marked, plus Gemini's value as the candidate |
| `source_applicability` | The field's citations | Parent units of the citations |
| `official_source_conflict` | Each candidate's passage | One unit per candidate, so the sources sit side by side |
| `ocr_evidence` | The OCR citations | The OCR page passage(s) |
| `large_rate_change` | The new value's citations in this snapshot | Their parent units, plus the before/after numbers in the guidance (from `471ed9e`). **Decided:** the previous snapshot's passages are not shown. |

**Answers D3.** For a `not_stated` field, "where Gemini looked" is the honest set: the
reviewer is confirming Gemini's search or finding what it missed. That requires one extraction
change: save each batch's evidence IDs in `SemanticExtractionResult` (P2). The plan already
knows them, including for cache hits (`cached_batches`).

**Fallback** when batch IDs are missing (old snapshots): rank the whole catalog with the
planner's `_field_score` for the field. It is the same scoring the planner used, so it is
nearly the same set.

### R4. Pick one unit, and a second only when it is nearly as strong

**Agreed:** a review shows 1–2 tables or sections, never 10.

**Tested on real data.** The Overdraft snapshot (262 passages) was grouped into units (52: 15
tables, 37 sections). Each unit was scored with the planner's `_field_score`, taking the best
passage in the unit (`max`, not `sum`, so a big table doesn't win by size alone):

| Field | Top unit | Right? |
|---|---|---|
| `term` | Page table "Card type … Overdraft conditions" (25 rows), containing `Loan terms ³ \| Term (months) \| Indefinite term …` | **Yes.** Units 2–3 are PDF copies of the same row. |
| `eligibility` | The same page table; unit 2 is the PDF "Information summary" row `Eligible age … 18-65` | Unit 2 is the better one |
| `repayment` | Generic "Information Guide" sections (differentiated/annuity formulas for a *property-secured* loan) | **No.** The real rule, "pay the interest accrued … and 3% of the used amount", is passage `b54` in a 77-passage section and uses none of the repayment keywords. |

Three things this shows:

1. For **cited** reasons (`extraction_invalid`, `source_applicability`, conflict, OCR, rate),
   choosing units is easy: the units that hold the cited passages, which is almost always 1–2.
   Rank them by how many cited passages each holds, then by precedence.
2. **Duplicates are common.** The same terms appear as a page table and as a PDF table. Units
   whose rows are largely the same text must be merged, keeping the higher-precedence source.
   Otherwise the second slot is wasted on a copy.
3. **Keyword scoring misses reworded content** (`repayment`). Adding keywords is the `term`
   one-off again. The generic guide can't be pushed down by product association, because
   source discovery tagged it `current_product` / `official_terms` (a discovery issue in its
   own right).

**Recommend:**
- Cited reasons: units that hold cited passages; at most 2; ranked by cited count, then
  precedence.
- `missing_required_field`: units of the passages **Gemini was given** for the field (R3),
  scored `max(_field_score)`. Show the top unit. Add the second only if its score is within a
  margin of the first (same idea as the existing `hitl_document_rank_gap`); otherwise show one.
- Merge near-duplicate units before picking.
- Accept that `not_stated` will sometimes show the wrong unit. The safety net is `?` (R5),
  which shows everything. Log when the reviewer's chosen citation is outside the units shown:
  that is a direct measure of ranking misses, and it points at the planner, which chose the
  batch with the same scoring.
- Inside a unit, source order is kept; relevant rows are marked, not moved.

### R5. Bounds, and what `?` shows

**Recommend** these bounds, as code constants first (see open question 1):

| Bound | Value | Why |
|---|---|---|
| Units per review | 1, a 2nd within the margin | Agreed above |
| Table shown whole up to | 30 rows | The largest Overdraft table is 25 rows |
| Larger table | Headers + seed rows ± 3 rows + "*n* more rows" | Keeps the neighbourhood of the relevant row |
| Section | Seed block ± 2 blocks, at most 3,000 characters | See R7: heading-level sections are too big |

**`?` shows the acquired offering content as Markdown** (your proposal). The pipeline already
renders it (`render_normalized_markdown`, used by the audit archive for `3_selected_sources.md`),
but only to local audit files, which are best-effort and not shared between the API and worker
containers.

**Recommend:**
- Save the rendered Markdown of the **selected sources** with the snapshot at extraction time
  (a text column; 40 kB for Overdraft). It holds everything the evidence came from, in source
  order, with tables intact.
- Not the full acquisition: the unselected material is far larger (this run's source-selection
  report alone is 19 MB) and holds nothing that can be cited.
- Show it in the CLI's pager, with search. Never send it to the model.
- A later step, if wanted: tag each citable passage in that Markdown with its number, so the
  reviewer can cite something found through `?` directly.

### R6. What each consumer receives

| Consumer | Receives |
|---|---|
| Review row | `evidence_set` (IDs and structure only) |
| Snapshot | Also the selected-sources Markdown, for `?` |
| CLI | The 1–2 units rendered within R5's bounds, rows numbered, seed rows marked; `?` opens the Markdown |
| Model (via the `RequestInput` payload / session history) | Field, reason, guidance, candidate, input format, and **only the seed passages**, trimmed. The model relays the question; the CLI shows the evidence. |

To verify during implementation: how much of the `RequestInput` payload reaches later model
turns in the new node design. On `main`, every fetched review stayed in the history
(~3.4k tokens each).

### R7. Section boundaries: a window, not the whole heading

"Same heading path" is too coarse. On the Overdraft page, `Overdraft > Terms and conditions`
covers 77 passages, and the repayment rule is one of them.

**Recommend:** a section unit is the seed block plus its neighbouring blocks in source order,
stopping at a heading change, at 2 blocks either side, or at 3,000 characters, whichever comes
first. Tables stay whole units, because a table has natural edges.

### Decisions and remaining questions for ranking

Decided:
- Relevant passages are decided once, when the signal is raised (R1).
- Whole tables/sections are shown instead of isolated rows (R2), with at most 2 per review (R4).
- `?` shows the acquired content as Markdown (R5).
- `large_rate_change` shows only the new value's passages plus the before/after numbers (R3).

Recommended, awaiting your OK:
1. **Bounds as code constants first**, moved into the `hitl_*` settings only if they need
   tuning per environment. Values in R5.
2. **Section = window around the seed block** (R7).
3. **The `?` Markdown covers the selected sources**, saved with the snapshot (R5).

New questions:
4. **Keyword misses (`repayment`).** Accept them with `?` as the safety net plus logging
   (recommended for now), or add embedding similarity to unit scoring? The latter finds reworded
   text, but it is a new model use in review routing, where AGENTS.md prefers determinism, and
   it fails when embeddings are deferred for quota.
5. **The generic "Information Guide" tagged as `current_product`** is a source-discovery
   finding. Track it separately?

## Decisions and open questions

| # | Question | State |
|---|---|---|
| D1 | Which branch do fixes land on? | **Done:** `adk-native-runtime`. `main`'s five commits merged in `91c5189`. |
| D2 | Should the review reason be split? | **Decided:** yes. (b) gets its own reason. |
| D3 | Relevant passages for a `not_stated` field | Proposed in [Part 4](#part-4-ranking-brainstorm) (R3). |
| D4 | What a review row stores | Proposed in [Part 4](#part-4-ranking-brainstorm) (R1). |
| D5 | What the model needs from `get_current_tariffs` | Proposal below (freshness only); awaiting your OK. |
| D6 | Tables: change stored content or add a display rendering? | **Decided:** separate display rendering. |
| D7 | Must an override's value appear in its cited passage? | **Decided:** leave as is. B3 is an accepted risk. |

### D1. Fixes land on `adk-native-runtime`; `main`'s five commits come over

The question was whether `main`'s fixes still apply to the new ADK design, and whether they
conflict with it. To find out, `main` was trial-merged into `adk-native-runtime` in a
throwaway worktree, which has since been removed. Nothing was committed and the checkout was
not touched.

- **Git conflicts:** one. `monitoring_workflow.py` was deleted on this branch and edited on
  `main`. Every other file merged automatically.
- **Unit tests on the merged tree:** 642 passed, 5 skipped, **1 failed**. The failure is
  `test_a_rate_review_tells_the_reviewer_the_size_of_the_jump`, which imports
  `monitoring_workflow.build_review_request`, and that module no longer exists.

| Commit | What it fixes | Applies to the new design? | Merge work |
|---|---|---|---|
| `4bf3d3f` Let a run with several field reviews be approved | B2: an override fails while a sibling review is open | Yes. `review_decisions.py` is unchanged on this branch, so the bug is here too. | None; merges and its tests pass. |
| `221f73f` Guard every rate jump, and pair rates by what they describe | Rate guard skipped runs that also had field reviews; false alarms from pairing rates by position | Yes. `snapshot_lifecycle.py` is unchanged on this branch. | None. Makes B4 more likely (see B4). |
| `471ed9e` Tell a rate reviewer what the rate changed from and to | Rate review never said the old and new values | Yes. The problem is P4/B6 in another form. | **Port needed.** The pipeline half merges. The guidance half (`_with_rate_change`) lived in `monitoring_workflow._review_prompt` and must move into `review_resolution.build_review_view`, and the failing test's import must change. Not yet verified after the port. |
| `ac19d24` Survive a provider quota instead of discarding the run | 429 at embedding threw away a reviewed run | Yes. Not review-related. | None. It touches `monitoring_pipeline.py`, which this branch rewrote, but it merges and its quota-deferral tests pass. |
| `c79faf3` Log every model call, not only what it cost | Quota refusals invisible in the spend ledger | Yes. Not review-related. | None. |

**Done (2026-09-25):** merged into `adk-native-runtime` as `91c5189`, with the
`_with_rate_change` port into `review_resolution.build_review_view`. Results: 643 unit tests
passed, 5 skipped; lint clean. Integration tests against a separate `_test` database: 64
passed. 4 failed, the same way on the pre-merge commit: they need a Gemini API key and a
server start.

**Conclusion:** all five are real fixes, and none conflicts with the new design. Four merge as
they are. One needs a small port into `review_resolution.py`. Because they touch the same
files (`review_decisions.py`, `snapshot_lifecycle.py`, `_review_tasks`), merging them
*before* the review fixes in this report avoids fixing the same code twice.

### D2. Should the review reason be split?

Today a review's `reason` is one of five labels, and `missing_required_field` covers three
situations that ask different things of a reviewer:

| Situation | What Gemini returned | Example from the database | What the reviewer could be shown | What the reviewer is really asked |
|---|---|---|---|---|
| **a. Not stated** | "This page does not state the field" (`not_stated`) | none stored yet | Where Gemini looked (the field's batch passages) | "Find the value, or confirm it really is absent." |
| **b. Answer failed a check** | A value **and** a quote, but a deterministic check rejected it | all 4 stored reviews: "citation quote is not present in the supplied evidence excerpt", "product_name must be anchored to the canonical product page", … | Gemini's proposed value, the quote it gave, the passage it cited, and the check that failed | "Gemini says X. Our check failed because Y. Is X right?" |
| **c. Field missing from the answer** | Nothing for this field | none stored | Where Gemini looked | Same as (a). |

(b) is a different task from (a). There *is* a candidate value, so the reviewer could accept or
correct it instead of typing from nothing. Right now (b) is shown as "No valid repayment was
extracted", with no candidate and none of Gemini's passages (P4, B1). (b) also fires for
fields that are *not* required (B1), so "missing **required** field" is wrong twice over.

"Splitting the reason" means giving (b) its own label, say `extraction_invalid`, so it gets its
own guidance, its own candidate (Gemini's value), and possibly its own allowed decisions. For
example, "approve Gemini's value" becomes possible once a human has checked it. (a) and (c)
could stay together as `missing_required_field`.

Cost of the change: no database migration, because `reason_code` has no check constraint. The
enum, the review policy, the CLI wording and the docs change. Old rows keep their old label.

**Decided: split.** (b) gets its own reason (working name `extraction_invalid`), with its own
guidance and Gemini's proposed value as a candidate. (a) and (c) stay `missing_required_field`,
and only for required fields. Still open, to settle during implementation: the final name, the
allowed decisions for the new reason (in particular whether "approve Gemini's value" is
allowed), and what a validation failure on a *non-required* field should do.

This feeds the ranking brainstorm: in (b) the relevant passages start from the ones Gemini
cited (after P3's check against the catalog); in (a) and (c) they start from the ones Gemini
was given.

### D3. Relevant passages for a `not_stated` field

To explore together, as part of ranking. Starting points gathered so far: the field's batch
passages (not saved today, P2), the planner's `FIELD_KEYWORDS`/`_field_score` (P1), and
knowledge-store retrieval.

### D4. What a review row stores

To explore together, as part of ranking. Starting point: B5. Today each row stores a 261 kB
full copy of the evidence, and no path shows the full list (P6).

### D5. What the model needs from `get_current_tariffs`

Not decided. What the code says about how the tool is used on this branch:

- **The prompt uses it for freshness only.** [agent.py:37-39](../app/agent.py#L37-L39): answer
  from `answer_tariff_query`; "if it abstains … check freshness once with
  `get_current_tariffs`, and offer monitoring if the value is missing or stale." Values and
  citations are supposed to come from `answer_tariff_query`, which carries its own evidence.
- **It returns much more than that.** For each offering: `freshness`, `accepted_at`,
  `age_seconds`, `pending_newer_review`, `snapshot_id`, the whole `normalized_tariff` (9 kB),
  and the whole `evidence` catalog (262 kB).
- **Every other caller already takes only freshness.** `get_monitoring_status`
  ([monitoring.py:205-212](../app/tools/monitoring.py#L205-L212)) keeps only `accepted_at`. The
  REST route `GET /tariffs/current` ([routes.py:224-234](../app/api/routes.py#L224-L234)) returns
  the full result to API clients. It calls the service directly, so trimming the tool leaves
  it unaffected.
- **Risk on the other side.** When `answer_tariff_query` abstains and the model holds
  `normalized_tariff`, it can answer from the raw snapshot, which is the path that just
  declined. Removing `normalized_tariff` removes that option; keeping it without evidence
  removes the model's ability to cite what it says.

Options considered: (i) freshness fields only; (ii) freshness plus `normalized_tariff`, no
evidence; (iii) keep everything but cap the evidence.

**Proposal: (i), freshness only.** For each offering the tool returns `offering_id`,
`freshness`, `accepted_at`, `age_seconds`, `snapshot_id` and `pending_newer_review`, about
150 bytes instead of about 272 kB. Reasons:

- It is what the prompt uses the tool for: deciding whether to offer monitoring.
- Values reach the user only through `answer_tariff_query`, which carries its own citations.
  Without `normalized_tariff`, the model cannot answer from the snapshot after the query path
  has declined, and every value it states stays citable.
- (ii) keeps that bypass open, and its values could not be cited. (iii) still sends tens of kB
  per call, and any cap is arbitrary.
- It removes the largest cost in the ledger, the ≥90k-token turns (56% of chat spend).

What to watch: if the model later needs to say *why* the query abstained ("the accepted
snapshot has no term"), add a list of field names with their status, not the values. The trim
belongs in the tool ([reads.py:114](../app/tools/reads.py#L114)), not in
`CurrentTariffService`, so the API is unaffected.

### D6. Tables: a separate display rendering

**Decided.** The stored passage content, and therefore every `evidence_id` hash, cache key and
citation check, stays as it is. A display form (for example, each cell paired with its
header, with the row group and footnotes attached) is produced where the text is *shown*.

Point to settle when designing it: **who sees the display form.** The reviewer, the CLI and the
chat model clearly do. Gemini's extraction prompt is different: Gemini must return quotes that
are exact substrings of the *stored* content
([semantic_extraction.py:1498](../app/services/semantic_extraction.py#L1498)). If Gemini reads
a paired rendering, its quotes may stop matching. Either Gemini keeps the stored form, or the
quote check has to map a quote from the display form back to the stored form.

### D7. Must an override's value appear in the cited passage?

**What happens today.** When a reviewer overrides, they give a value and pick a passage as
support. Only an "indefinite term" is checked against that passage. For everything else, a
reviewer can enter repayment = "annuity" and cite a passage about required documents, and it
is accepted. The stored citation's quote is the whole passage (B3). A value Gemini produces
must quote a substring of its passage. A value a human produces does not.

**Why it matters.** AGENTS.md: "every accepted non-missing tariff value must retain verifiable
source evidence." After an override, nothing checks that the citation supports the value; it
only has to exist.

**Options:**

| Option | How it works | Pros | Cons |
|---|---|---|---|
| A. Check the value against the passage | Per field type: numbers (rate, amount, term months) must appear in the passage; enum values (annuity, differentiated) must appear via a word list; free-text lists (eligibility, documents) have no reliable check | Nothing extra for the reviewer | Needs code per field type; free-text fields stay unchecked; Armenian/English wording differs |
| B. Reviewer supplies the supporting quote | Same rule Gemini follows: the reviewer marks or pastes the words that state the value, and they must be an exact substring of the passage. That quote is stored, not the whole passage. | One rule for all fields; the stored citation becomes precise | One extra step for the reviewer; in chat, the model would relay the quote |
| C. Keep today's behaviour, but label it | The citation is marked "reviewer-attested" so it can be told apart from machine-checked ones | Least work | Doesn't close the gap, only makes it visible |

**Decided: leave as is.** No support check is added for overrides. B3 stays recorded as an
accepted risk: override citations point at a passage but are not checked to support the
value.
