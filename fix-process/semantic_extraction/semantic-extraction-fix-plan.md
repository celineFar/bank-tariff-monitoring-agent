# Semantic extraction: problem report and fix plan

Date: 2026-09-26 · Branch: `fix/semantic-extraction` (to be created from
`integration/process-fixes` at `89f888e`) · Status: **proposed**. Decisions Q1–Q7 are
settled with the user; Q8 (extraction fallback model) is open.
Gemini budget for validation: **$2** (Q5).

## Scope

Semantic extraction turns the sources that discovery selected into a validated
`LoanProduct` with cited evidence. It runs after source discovery:

- the evidence catalog ([extraction_evidence.py](../../app/services/extraction_evidence.py));
- batch planning and evidence selection ([extraction_planner.py](../../app/services/extraction_planner.py));
- the prompt, the Gemini extractor, output normalization, validation, repair, the cache
  lookup and assembly ([semantic_extraction.py](../../app/services/semantic_extraction.py));
- the batch cache ([repositories/semantic_extraction.py](../../app/repositories/semantic_extraction.py));
- settings ([config/models.py](../../app/config/models.py) `SemanticExtractionSettings`,
  [config/environment.py](../../app/config/environment.py));
- how results become reviews ([snapshot_lifecycle.py](../../app/services/snapshot_lifecycle.py),
  [review_resolution.py](../../app/services/review_resolution.py)).

**Upstream, in scope by decision Q3**, where extraction cannot repair the damage itself:
table normalization ([table_normalizer.py](../../app/services/table_normalizer.py)), headline
blocks in the HTML parser ([html_parser.py](../../app/services/html_parser.py)), and the PDF
transcription schema ([gemini_pdf_extractor.py](../../app/services/gemini_pdf_extractor.py),
[pdf_extraction.py](../../app/services/pdf_extraction.py)).

**Out of scope.** Discovery's classification. One label found here is handed off
(see [Hand-offs](#hand-offs)). Out of scope as well: the RAG index, and the change-detection
rules beyond what SE22 changes in their input.

## How this was checked

- **Code.** Read on `integration/process-fixes` at `89f888e`, after the normalization and
  source-discovery fixes.
- **Probe.** [survey/probe_evidence_recall.py](survey/probe_evidence_recall.py) needs no
  Gemini call:
  - it normalizes the 13 captured seed pages (`fix-process/normalization/.cache-live-2`,
    without PDFs);
  - it replays the discovery assessments stored in
    [discovery-check-final.json](../source_discovery/data/discovery-check-final.json);
  - it runs today's evidence catalog and batch planner;
  - it locates every ground-truth fact of
    [seed-ground-truth.json](../normalization/data/seed-ground-truth.json) that maps to an
    extraction field.

  Output: [data/probe-output-before.txt](data/probe-output-before.txt), per fact in
  [data/evidence-recall-before.json](data/evidence-recall-before.json). Run it with
  `uv run python fix-process/semantic_extraction/survey/probe_evidence_recall.py`.
- **One real extraction.** The accepted Overdraft snapshot in the dev database (2026-09-23,
  pages and PDFs) was replayed through the planner: 262 evidence items, **83 reach any batch**.
  Model usage for `semantic.extraction` in `model_call_usage`: 72 calls, 898,764 input and
  67,699 output tokens, about **$0.93** with `gemini-3.7-flash`.
- **Reproductions.** The normalizer cases, the malformed-term crash and the stale raw
  response were run directly against today's functions (scratch scripts). Phase 0 turns each
  into an `xfail` test.

"Confirmed" means the probe or a reproduction shows it. "Code" means reasoned from the code
and not reproduced.

---

## Your original list: where each item stands

Several items were fixed by the normalization, acquisition and source-discovery plans that
merged since they were written.

| # | Item | Now |
|---|---|---|
| 1 | PDFs bypass product-relevance classification | **fixed** by SD2 (Gemini selects PDFs from link metadata). S04 still shows 4 wrong keeps. |
| 2 | Discovery does not know the target product | **fixed** by SD1 (`OfferingContext`: offering, names, seed URL, page title) |
| 3 | Only one table header row | **open** → SE1 |
| 4 | Mid-table header rows lost | **open** → SE1, SE5 |
| 5 | PDF grouping relies on transcription repeating labels | **open** → SE3 |
| 6 | Columns associated by position | **open** → SE1 |
| 7 | Footnotes detached from rows | **open** → SE4 |
| 8 | Qualifier rows omitted by ranking | **open** → SE5, SE6 |
| 9 | Document ID from raw HTML | **partly fixed**: acquisition A1 hashes the parsed visible page without chrome. Still one hash for the whole page → SE10 |
| 10 | Positional evidence IDs | **open** → SE10 |
| 11 | Batch fingerprint includes filler | **open** → SE11 |
| 12 | Cache key built from unstable inputs | **open** → SE10, SE11 |
| 13 | Discovery input cut at 3,000 characters | **fixed** by SD3, SD12 and SD17 (split, not cut; tables send their row labels) |
| 14 | PDF transcription sampling not pinned | **open** → SE3 |
| 15 | Discovery classifier varies on recompute | **fixed** by SD14 / Q9 (temperature 0 for every model) |
| 16 | Hashing model output | agreed. Nothing in extraction keys on model output except PDF evidence text, which is stable while the PDF transcription cache hits (see [Checked](#checked-no-change-needed)). |

Your questions:

- **Is the cache design stable?** No, in both directions: see SE10–SE12.
- **Is `_field_score` good enough?** No: see SE6. It is measured on all 13 seeds.
- **The limits:** see SE6, SE7 and SE9. The 20-item cap is the only limit that binds. The
  20,000-character budget is never reached, and the real prompt is 24–53k characters.
- **One schema for all seeds:** see SE20 and SE21. The previous-run "ground truth" in the
  database is a single Overdraft snapshot. The survey ground truth covers normalization, not
  extracted field values, so Phase 0 adds field-level labels.
- **The empty fallback list:** see SE25 and Q8.

---

## Summary

| ID | Problem | Severity | Evidence | Status |
|---|---|---|---|---|
| SE1 | Table header hierarchy and merged columns are flattened; cells are tied to headers by position | **critical** | confirmed | proposed |
| SE2 | Headline values are separate blocks from their labels | **high** | confirmed | proposed |
| SE3 | PDF structure survives only as text the transcription model repeats; transcription runs unpinned | **high** | code | proposed |
| SE4 | Footnotes are separate evidence items; 46% miss the batch of the row that cites them | **high** | confirmed | proposed |
| SE5 | Qualifier rows are not sent with the rows they qualify | **high** | confirmed | proposed |
| SE6 | Row-level keyword ranking drops 22% of current-product facts | **critical** | confirmed | proposed (Q1, Q2) |
| SE7 | Long items are cut silently | medium | code | proposed |
| SE8 | Evidence is sent in score order, not document order | medium | confirmed | proposed |
| SE9 | Most of the prompt is envelope, not evidence | medium | confirmed | proposed |
| SE10 | Evidence IDs change with unrelated page content and with position | **high** | code | proposed |
| SE11 | The cache key hashes filler, and misses the prompt and what the model sees | **high** | confirmed | proposed |
| SE12 | Batches needing review are never cached; review decisions are forgotten | **high** | code | proposed (Q6) |
| SE13 | A failed batch is reported with another offering's model output | **high** | confirmed | proposed |
| SE14 | Substring keywords make `not_stated` fail validation | **high** | confirmed | proposed |
| SE15 | Output normalizers change what values mean | **high** | confirmed | proposed |
| SE16 | A malformed value crashes the whole offering | medium | confirmed | proposed |
| SE17 | Rate, amount and fee alternatives may be unconditional | **high** | confirmed | proposed |
| SE18 | Citations need not contain the value | **high** | code | proposed (Q7) |
| SE19 | Runtime validators encode single-seed wording | medium | code | proposed |
| SE20 | Seed-specific rules are hard-coded in shared code | **high** | code | proposed (Q4) |
| SE21 | Every product family's fields are extracted, then discarded | medium | confirmed | proposed (Q4) |
| SE22 | Condition names are free text | medium | code (noted in `snapshot_lifecycle.py`) | proposed |
| SE23 | Extraction runs without temperature 0 or an output cap | medium | code | proposed |
| SE24 | Retries stack; parse failures are not retried | low | code | proposed |
| SE25 | One failed batch fails the offering; the fallback rarely triggers and is empty | medium | code | proposed (Q8 open) |
| SE26 | Batches run one after another; repairs are spent in batch order | low | code | proposed |

---

## SE1. Table header hierarchy and merged columns are flattened

**Where.** [domain/normalization.py:147](../../app/domain/normalization.py#L147)
(`NormalizedTable.headers` is one flat tuple),
[table_normalizer.py](../../app/services/table_normalizer.py),
[extraction_evidence.py:54](../../app/services/extraction_evidence.py#L54)
(`Headers: a | b | c` then `Row: x | y | z`).

**What happens.**
- A table has one header row. A second header level, a qualifier row inside the body, and
  merged (colspan) columns are either copied into every spanned column or left as data rows.
- Evidence renders a row as two pipe-joined lines. To tie `21%` to its card tier or
  currency, the model has to count pipes. Empty cells left by merged columns shift the count.

**Confirmed on the seeds.**
- **Overdraft `t1`.** The card-tier row became the header, duplicated per spanned column:
  `Card type¹ | Card type¹ | Arca Classic… | Arca Classic… | Mastercard Gold… | Mastercard Gold… | Mastercard Gold…`.
  The rate row is `Loan terms³ | Interest rate | AMD: 21% |  | AMD: 20% |  | `.
- **Mortgage Primary `t1`.** The headers are invented (`Section | Item | Terms 1 | Terms 2 | Terms 3`).
  What the columns mean (AMD / USD / EUR) is a body row, `3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR`.
  The rate `13.5% | 11.0% | 8.5%` (row 11) is a separate row from its rate type
  `3.4.1. Fixed | Fixed | Fixed` (row 10).

**Fix (normalization, then evidence).**
- `NormalizedTable` gains `header_rows: tuple[tuple[HeaderCell, ...], ...]`, each cell with
  its text and span, and `column_paths: tuple[tuple[str, ...], ...]`: for each column, the
  header texts above it, top to bottom, merged duplicates collapsed. `headers` stays as the
  last level, for older readers.
- A **qualifier row** is a body row whose first cells are labels and whose other cells name
  columns, not values: `Currency | AMD | USD | EUR`, a card-type row. It becomes a header
  level for the rows below it, until the next qualifier row or a section row. It is detected
  structurally: every non-label cell is short and has no number with a unit, and the row sits
  above value rows of the same width. Detected rows are recorded, not dropped.
- A **continuation row** (same label cells as the row above, the row above holding only rate
  types) is linked to it: `row.continues: row_id`.
- Every cell gets `column_path`, and every row gets `label_path` (its label cells, section
  first).
- Evidence renders a row as a record in which every value names its column:

  ```
  3. Loan terms > 3.4. Nominal annual interest rate²
    Currency: AMD → 13.5% (Fixed)
    Currency: USD → 11.0% (Fixed)
    Currency: EUR → 8.5% (Fixed)
  ```

- The normalization ground truth gains facts for column paths (Overdraft card tiers, Primary
  currencies), checked by `check_ground_truth.py`.

## SE2. Headline values are separate blocks from their labels

**Where.** [html_parser.py](../../app/services/html_parser.py) (block segmentation),
[extraction_planner.py:391](../../app/services/extraction_planner.py#L391)
(`field_has_evidence_marker` looks at one item).

**What happens.** Every seed's header shows its key figures as cards. The value block comes
*before* its label block: `AMD 3-150 million` then `Loan amount`; `12.9%` then
`Nominal interest rate`; `13.84% - 16.03%` then `Actual interest rate`. Each is its own
evidence item. The value has no label, and the label has no value.

**Confirmed.** 16 of the 26 `no_marker` facts in the probe are these value blocks (and one
more is the "How to apply" heading). The other 9 are table rows whose labels are not in the
keyword lists (SE6).
**Loan amount reaches its batch for 3 of 15 facts.** These are the page's headline numbers.

**Fix.** In the parser, a card container holding exactly one short value block and one short
label block becomes one key/value block (`Loan amount: AMD 3-150 million`), as `dt`/`dd`
pairs already do (N14). The pairing is by DOM container, not by block order. Unpaired blocks
are unchanged.

## SE3. PDF structure survives only as text the transcription model repeats

**Where.** [gemini_pdf_extractor.py:37-50](../../app/services/gemini_pdf_extractor.py#L37-L50)
(instruction), [gemini_pdf_extractor.py:78](../../app/services/gemini_pdf_extractor.py#L78)
(config), [pdf_extraction.py](../../app/services/pdf_extraction.py).

**What happens.**
- The transcription schema is a flat item list. Group structure is kept only because the
  prompt says: "repeat visually merged group labels in every applicable row". If the model
  drops or rewords a label, the row loses its group, and nothing downstream can tell.
- Multi-level PDF headers have no field either, so SE1 applies to PDFs too.
- The config pins `thinking_budget=0` but not `temperature` (your item 14).

**Fix.**
- Schema: items carry `section_path` (list of headings), and tables carry `header_rows` with
  spans plus `row_group` per row. The normalizer builds `column_paths` and `label_path` from
  these fields, as in SE1.
- The prompt asks for structure in fields, not repetition in text. Repeated text is still
  accepted, but it no longer carries the structure.
- `temperature=0` through the model registry flag (SD14).
- Bump the PDF extraction schema and prompt versions: every selected PDF is transcribed
  once more.

## SE4. Footnotes are separate evidence items

**Where.** [extraction_evidence.py:69-78](../../app/services/extraction_evidence.py#L69-L78).

**What happens.** Table notes become their own evidence items (`t1:note:2`). A row cites
them by marker (`Loan terms³`, `interest rate²`), but selection treats the row and the note
independently.

**Confirmed.** Across the 13 seeds' batches, rows reference a note of their own table 155
times. **In 71 (46%), the note is not in the same batch.** Examples: Overdraft note ³ ("Other
terms can be applied for applications…"), and Primary note ⁴ (the adjustable-rate threshold).

**Fix.** A row's record lists the text of every note its cells, labels or column headers
reference, and the table's unmarked `*` notes, under `Notes:`. Notes stay addressable
evidence of their own, for citation, so a quote from the note still validates against the
note's ID.

## SE5. Qualifier rows are not sent with the rows they qualify

**Where.** [extraction_planner.py:297-388](../../app/services/extraction_planner.py#L297-L388).

**What happens.** Selection is per row, by field keywords. Rows that qualify others
(`Currency`, card type, `Variant`) match no rate keyword and are left out.

**Confirmed.** On Mortgage Primary and Secondary Market, the `core_financial` batch holds
rows 7, 9–16, 18–19, 21–22… of `t1`, but **not row 6 (`Currency | AMD | USD | EUR`)**. The
model reads `13.5% | 11.0% | 8.5%` under `Terms 1/2/3`. It can get the currency only by
lining up columns with the loan-limit row.

**Fix.** Covered by SE1 (a qualifier row becomes a header level, so every value names it) and
by SE6 (the selection unit is a whole table, never a row).

## SE6. Row-level keyword ranking drops 22% of current-product facts

**Where.** [extraction_planner.py:104](../../app/services/extraction_planner.py#L104)
(`FIELD_KEYWORDS`), [:297](../../app/services/extraction_planner.py#L297)
(`select_evidence_for_fields`), [:391](../../app/services/extraction_planner.py#L391)
(marker), [:396](../../app/services/extraction_planner.py#L396) (`_field_score`).

**What happens.**
- An item is eligible for a field only if a keyword occurs in it as a **substring**.
- Eligible items are ranked by `_field_score`:
  - a constant of about 32 points for every current-product item on the canonical page
    (+14 association, +8 canonical page, +6 role, +4 precedence);
  - plus a few points per keyword present.
- Each field gets a quota of `ceil(20 / fields in group)` items, and a batch holds 20 items.
- Ties are broken by `(precedence, document_id, source_item_id)` as strings, so
  `t1:row:10` sorts before `t1:row:2`.

**Confirmed (probe, 13 seeds, page evidence).** 197 ground-truth facts map to a field.
45 belong to sibling offerings and are rightly excluded (the Express Home table shown on four
mortgage pages). Of the other **152**:

| Outcome | Facts |
|---|---|
| reaches its batch | **119 (78%)** |
| never passes the keyword marker (`no_marker`) | 26 |
| passes, ranked below the quota | 7 |

- **Keyword substrings.** `age` matches *advantages, percentage, management, mortgage,
  languages*: 45 of 47 Overdraft hits. `fee` matches *feedback*, `charge` matches
  *discharged*. The lists are English-only.
- **Labels outside the lists:** `Financing Limit`, `Late payment fines and penalties`,
  `Cashing of the loan amount`, `Minimum payment required`, `Prepayment`,
  `Increase of credit limit of card`.
- **Ties.** In **126 of 152** fields with more candidates than their quota, the cut falls
  inside a group of equal scores. For example, Primary's "online refinancing" rate row scores
  39, equal to the top item, and ranks 7th against a quota of 5.
- **Boilerplate first.** A credit-history disclosure ("…annual interest rate, outstanding
  liabilities…", `b110`) is the **#1 interest-rate item** on Mortgage Primary. The same text is
  #1 on Consumer Standard (`b98`).
- **Coverage.** Only 29–98 of each seed's catalog reach any batch. On the real Overdraft run,
  83 of 262 did.

**Fix (Q1, Q2): two selection modes, chosen by one setting, `semantic_extraction.evidence_mode`.**

- **`full` (default).** Every call receives the offering's whole selected evidence.
  - The offering's own items (current product, unknown, generic bank information) come first,
    then related-product items in a separate block titled "Other products on this page: for
    telling variants apart, not for values".
  - The evidence is in document order and uses SE1 records.
  - There is no ranking and no keyword list, so nothing is lost by selection.
  - Size, page only: the offering's own evidence is 3,164–44,683 characters; all selected
    evidence is at most 63,698. On the one real run with PDFs (Overdraft), it was 45,960.
  - A hard ceiling (`max_packet_chars`, default 200,000) fails the offering loudly with
    `semantic_extraction.packet_too_large`. It never cuts.
  - With the whole packet in every call, input cost is proportional to the number of calls.
    So full mode uses **3 calls** in place of today's 6 groups:
    - identity + core financial;
    - fees, repayment, eligibility and application;
    - required documents + category details.

    The field groups stay as they are for budgeted mode. (Proposal, measured in S10.)
- **`budgeted` (the cheaper mode).** A per-call character budget
  (`budget_chars`, default 16,000). Nothing like today's row ranking:
  - The **unit** is a whole table (all rows as records, with notes) or a whole section
    (heading plus its blocks, including SE2 key/value pairs). It is never a single row. A
    table over the unit limit is split by row group, repeating its header levels.
  - **Scoring** matches field terms with word boundaries against a unit's *labels* only:
    heading path, table title, row labels, column paths and keys. Terms are weighted by
    inverse frequency across the offering's units, so `loan` counts for almost nothing.
  - Current-product units rank first, the canonical page next. Related-product units are
    used only if budget remains. Ties go by document order.
  - Every field in the call is first guaranteed its best unit, then units are added by score
    within the budget.
  - The run records which mode it used, the units sent and the units left out.
- The keyword lists move out of the planner into a small per-field **term table**
  (`app/domain/extraction_terms.py`). Only budgeted mode reads it. SE14 removes its use in
  validation.

## SE7. Long items are cut silently

**Where.** [extraction_planner.py:313-325](../../app/services/extraction_planner.py#L313-L325)
(`content[:limit]`, and the first pass's `content_limit=reserved`).

**What happens.** An item longer than 5,000 characters, or longer than the first pass's
reserved share, is cut at a character offset, with no marker. `18.5%` can become `18.`.
The citation check still passes, because the quote only has to be a substring of the cut
text. It was not hit on the page seeds (longest item 1,028 characters). PDF blocks can be
longer.

**Fix.** No character cuts. Full mode has no per-item limit below the ceiling. Budgeted mode
splits a unit at row or paragraph boundaries and marks each part
(`[part 2 of 3; continues]`).

## SE8. Evidence is sent in score order

**Where.** [extraction_planner.py:297-388](../../app/services/extraction_planner.py#L297-L388).

**Confirmed.** In all 6 batches of the Overdraft run, and on every seed in the probe, the
packet order is selection order: rows of one table are scattered among blocks and notes.

**Fix.** Both modes render in document order, grouped as document → section → table.

## SE9. Most of the prompt is envelope, not evidence

**Where.** [semantic_extraction.py:739](../../app/services/semantic_extraction.py#L739)
(`build_extraction_prompt`: `batch.model_dump_json(indent=2)` and pretty-printed JSON
Schemas).

**Confirmed.** Prompts are 24,089–53,296 characters for 768–13,758 characters of evidence.
Each item carries its CSS selector, XPath, precedence, fingerprint and the batch's own
fingerprint. The core-financial field schemas alone are 16,595 characters.

**Fix.**
- A compact packet: per item, only `id`, source (page or PDF name), section path, association
  and the record text. Locators stay server-side for citation hydration.
- Field contracts are minified, and each call sends only its own fields' contracts.
- The packet comes first and is byte-identical across an offering's calls, so Gemini's
  implicit prefix caching can apply. S10 measures `cached_content_token_count`.

## SE10. Evidence IDs change with unrelated page content and with position

**Where.** [extraction_evidence.py:106-116](../../app/services/extraction_evidence.py#L106-L116)
(`identity = document_id ‖ source_item_id ‖ content`),
[normalization.py:139](../../app/services/normalization.py#L139)
(`page:{page_content_hash[:16]}`).

**What happens.**
- `document_id` is a hash of the whole visible page. Any change anywhere on the page, such as
  a promo card or an "Update on 06.08.2026 11:12" line, renames every evidence item on it.
- `source_item_id` is positional (`b17`, `t1:row:9`). Insert one block and the rest shift.
- So identical evidence gets a new ID and every cache entry misses. This is your items 9,
  10 and 12.

**Fix.**
- `evidence_id = "ev_" + sha256(source key ‖ structural path ‖ normalized text ‖ occurrence)[:24]`:
  - **source key** is the canonical page URL, or the PDF's SHA-256;
  - **structural path** is heading path ‖ table title ‖ row `label_path` ‖ column path;
  - **occurrence** is the index among items with the same key, so exact duplicates stay
    distinct.
- `source_item_id` stays for locating an item, but is no longer part of the identity.
- A changed value gets a new ID; that is intended.
- Consumers of evidence IDs are listed in Phase 3 and checked: `fact_evidence`,
  structured projection, review candidates, snapshot evidence.

## SE11. The cache key hashes filler, and misses the prompt and what the model sees

**Where.** [extraction_planner.py:260-283](../../app/services/extraction_planner.py#L260-L283),
[repositories/semantic_extraction.py](../../app/repositories/semantic_extraction.py),
[config/models.py:386-387](../../app/config/models.py#L386-L387),
[config/environment.py:117-118](../../app/config/environment.py#L117-L118).

**What happens.**
- **Too much.** The fingerprint covers every selected item, so a change in a low-ranked
  filler item misses the cache (your item 11).
- **Too little.** It leaves out things the model is shown: section path, role, authority and
  precedence. It also leaves out the instruction text and the field contracts. For example,
  a heading renamed from "Unsecured" to "Secured" above an unchanged row reuses the old
  answer.
- **Manual versions.** The prompt and schema versions are bumped by hand.
  - Commit `83391e3` changed the instruction and `TermRange` (indefinite terms) without a
    bump. The version has been `5` since `23b20de`.
  - The two defaults disagree: `"4"` in `models.py` and `"5"` in `environment.py`.

**Fix.**
- `prompt_fingerprint = sha256(model ‖ generation config ‖ system instruction ‖ user prompt)`:
  exactly what is sent.
- Rendering is deterministic: ordering, number formatting and JSON separators are fixed, so
  identical evidence gives an identical prompt. With SE10 this makes the key stable to
  anything that does not change what the model sees.
- Budgeted mode keys on its units, so an unrelated unit changing does not miss.
- `schema_version` and `prompt_version` stay as labels on the row, and as a manual
  invalidation switch, but lookup no longer needs them to be right. One default, in
  `config/models.py`.
- Migration: `prompt_fingerprint` column, lookup by it. Old rows are left to expire.

## SE12. Batches needing review are never cached; review decisions are forgotten

**Where.** [semantic_extraction.py:1596](../../app/services/semantic_extraction.py#L1596)
(cache only when a batch has no review), [snapshot_lifecycle.py:223](../../app/services/snapshot_lifecycle.py#L223),
[review_resolution.py](../../app/services/review_resolution.py).

**What happens.** A field that fails validation the same way on every run triggers, on every
run: a fresh extraction call, a repair call, and a new review for the same question. SE14 is
one such case. The reviewer's answer is applied to that run's snapshot only.

**Fix (Q6).**
- Cache every response, with its validation outcome, under its prompt fingerprint.
- **Review decision memory**, a new table: `offering_id`, `field`, the prompt fingerprint of
  the reviewed call, the reviewed field result's fingerprint (its `value_json` and cited
  evidence IDs), the decision, the reviewer, and the time.
- A later run reuses the decision, with no model call and no review, when either:
  - the call's prompt fingerprint is unchanged (the cached response is used); or
  - the new result for that field is identical to the reviewed one. Evidence IDs are
    content-based (SE10), so the same IDs mean the same evidence.
- Anything else opens a new review. Every reuse writes an audit event
  (`review_decision_reused`).
- The review ID stops depending on the positional batch ID (SE13).

## SE13. A failed batch is reported with another offering's model output

**Where.** [semantic_extraction.py:279](../../app/services/semantic_extraction.py#L279),
[:331](../../app/services/semantic_extraction.py#L331), [:484](../../app/services/semantic_extraction.py#L484),
[:1776](../../app/services/semantic_extraction.py#L1776),
[snapshot_lifecycle.py:209](../../app/services/snapshot_lifecycle.py#L209).

**What happens.**
- One `AdkSemanticExtractor` serves the whole process. It keeps `raw_responses` by batch ID,
  and batch IDs are positional (`extract_000`–`extract_005`), the same for every offering.
- A response is stored only after the model returns. If a call fails first (API error, or
  "no final response"), `_raw_response()` returns the previous offering's output for that
  batch ID.
- `non_reviewable_extraction_failure` then sees a raw response. So an execution failure
  becomes a HITL review that shows another product's output.
- The runner also creates a session per call and never deletes it, and `raw_responses`
  never shrinks: both grow for the life of the worker.

**Confirmed** by simulation: after "offering A" stored `extract_002`, a failing call for
"offering B" returned A's response.

**Fix.**
- `extract()` returns the raw text with the parsed response, or raises an error that carries
  the raw text (or none). No shared dictionary.
- Batch ID is `{offering_id}:{call}`.
- Delete the session after each call.

## SE14. Substring keywords make `not_stated` fail validation

**Where.** [semantic_extraction.py:1349-1365](../../app/services/semantic_extraction.py#L1349-L1365).

**What happens.** `not_stated` is rejected for a completeness field whenever any target
item passes the field's keyword marker (SE6). Examples:
- Every mortgage page contains "mortgage", which contains "age". So a mortgage offering that
  states no age limit cannot pass: each run spends a repair call, then opens a review.
- `apr` matches *appraisal* and *April*.

**Confirmed** on the keyword counts (see SE6). It did not fire on Overdraft, where age is stated.

**Fix.** Remove the keyword-based completeness check. Recall is guaranteed by construction in
full mode (SE6) and measured by the label check (Phase 9), not guessed at runtime.
In budgeted mode, a `not_stated` answer for a field whose best unit was left out for budget is
marked `not_stated_budget_limited` in the result's explanation, for the reviewer.

## SE15. Output normalizers change what values mean

**Where.** [semantic_extraction.py:798-1199](../../app/services/semantic_extraction.py#L798-L1199).

**Confirmed** (run against today's functions):

| Input | Becomes | Should be |
|---|---|---|
| age `"from 21 years"`, `"21+"`, `"not younger than 18"` | `max_age` | `min_age` |
| rates `{min:18, currency:AMD}`, `{min:14, currency:USD}` | two unconditional rates, currency dropped | two rates conditioned on currency |
| document `"Passport for identification"` | `requirement: conditional` | `required` |
| collateral `"not required"` | `applicable: true` | `applicable: false` |
| condition `"real estate pledge"` | `dimension: program` ("state" in "estate") | `collateral` or other |

**Fix.** Normalizers only *reshape*: rename a known alias key, wrap a bare value in
`{value, conditions}`, and canonicalize percentage points. They never infer meaning.
- An unknown key that names a condition (`currency`, `borrower_type`, `variant_id`) moves
  into `conditions`. Any other unknown key fails validation and goes to repair.
- String heuristics (`" for "`, `"at least"`, `"state"`) are deleted. A string where an
  object is required fails validation and goes to repair.
- The same rules serve human review input, which already shares the function.

## SE16. A malformed value crashes the whole offering

**Where.** [semantic_extraction.py:507](../../app/services/semantic_extraction.py#L507)
(`_normalize_response_contract` outside the `try`), [:960-982](../../app/services/semantic_extraction.py#L960-L982).

**Confirmed.** A term of `{"min_value": "6 months"}` raises `ValueError`, and
`{"min_value": "five", "min_unit": "years"}` raises `decimal.InvalidOperation`. Either one
fails the offering as an internal error, and the batches that succeeded are not cached,
because the save comes later.

**Fix.** Normalize inside the per-batch `try`. A normalizer error becomes that field's
validation issue, which goes to repair and then review. Save successful batches before
anything can raise (SE25).

## SE17. Rate, amount and fee alternatives may be unconditional

**Where.** [semantic_extraction.py:1222-1233](../../app/services/semantic_extraction.py#L1222-L1233)
(`_CONDITION_SENSITIVE_FIELDS`), [:1402-1421](../../app/services/semantic_extraction.py#L1402-L1421).

**What happens.**
- The unconditional-alternatives check covers term, down payment, LTV, repayment, age,
  channel, documents and collateral. It does not cover interest rate, effective rate, loan
  amount, credit limit or fees: the fields that matter most.
- Where it does apply, it fires only if the cited text contains a cue word (`solar`,
  `yerevan`, `goods`…).

**Confirmed.** With SE15's dropped currency, `[18%, 14%]` with no conditions passes.

**Fix.** For every list-valued field, reject alternatives that differ in value but have
identical conditions, including two empty condition lists. This is structural and has no
cue words. Such a result goes to repair, then review.

## SE18. Citations need not contain the value

**Where.** [semantic_extraction.py:1498-1511](../../app/services/semantic_extraction.py#L1498-L1511),
[:1614-1636](../../app/services/semantic_extraction.py#L1614-L1636),
[domain/semantic_extraction.py:408](../../app/domain/semantic_extraction.py#L408)
(`quote` min length 1).

**What happens.** A citation passes if its quote is a case-insensitive substring of the
evidence. The quote does not have to contain the value: a found `21%` citing
`"Interest rate"` is accepted. The quote must also match whitespace exactly, so a
non-breaking space in the source fails a correct quote.

**Fix (Q7).**
- Every number in an accepted value (rates, amounts, terms, percentages, ages, fees) must
  equal a number found in the text its citations point at.
- Comparison runs after the scalar normalizer on both sides, so `AMD 3,000,000` = 3 million,
  `12,5%` = 12.5, and `1.5 mln` = 1,500,000.
- For a record evidence item (SE1), the quote may be the whole record line.
- Quotes and evidence are compared after collapsing whitespace, including NBSP.
- A failure goes to the bounded repair, then review.

## SE19. Runtime validators encode single-seed wording

**Where.** [semantic_extraction.py:1234-1252](../../app/services/semantic_extraction.py#L1234-L1252)
(`_CONDITION_CUES`: `solar`, `goods`, `services`, `yerevan`, `state-supported`…),
[:1423-1453](../../app/services/semantic_extraction.py#L1423-L1453) (term threshold regex:
`exceeding|above|over|more than N months`), [:1455-1476](../../app/services/semantic_extraction.py#L1455-L1476)
(English income markers).

**What happens.** These checks were added for specific seed errors. Elsewhere they fire on
unrelated text: "more than 6 months of employment" in a cited term row forces a split at
6 months. And they stay silent on the same error worded differently.

**Fix.** Phase 0's field labels decide each check:
- a check that catches a labelled error on some seed stays, rewritten structurally where
  possible (thresholds from scalar candidates, not regex);
- a check that catches none is deleted, with a test case moved into the eval set.

SE17 replaces the cue list.

## SE20. Seed-specific rules are hard-coded in shared code

**Where.**
- [extraction_planner.py:233](../../app/services/extraction_planner.py#L233)
  (`_PRIMARY_VARIANT_PATTERN`), [:437-462](../../app/services/extraction_planner.py#L437-L462)
  (`_target_scope`, `_outside_canonical_scope`: active only if the URL contains
  `/mortgage/primary`);
- [semantic_extraction.py:1253](../../app/services/semantic_extraction.py#L1253)
  (`_PRIMARY_OUT_OF_SCOPE`), [:1479](../../app/services/semantic_extraction.py#L1479);
- the instruction [semantic_extraction.py:87-182](../../app/services/semantic_extraction.py#L87-L182):
  Express, secondary-market, construction, renovation, Solar, "6-60 month term … 48 months".

**What happens.**
- One seed gets scope rules and twelve get none.
- The planner's and the validator's exclusion lists disagree: only one has `developer` and
  `flexible opportunit`, only the other has `flexible_mortgage`. Neither matches the
  hyphenated slug `flexible-mortgage`.
- The prompt teaches every offering one seed's exceptions.

**Fix (Q4).**
- Delete both lists and the URL gate.
- Scope comes from discovery's offering-aware association (SD1), and from the offering
  context in the prompt: offering name, catalog aliases, seed URL, page title, category.
- The instruction keeps its generic rules (canonical product, variants, conditional values)
  with neutral examples.
- Any offering-specific scope note, if the labels show one is still needed, lives in the
  seed catalog entry, not in code.

## SE21. Every product family's fields are extracted, then discarded

**Where.** [extraction_planner.py:50-69](../../app/services/extraction_planner.py#L50-L69)
(`_PRODUCT_FIELDS` by `ProductType`), [semantic_extraction.py:1872-1924](../../app/services/semantic_extraction.py#L1872-L1924).

**What happens.**
- Consumer-loan offerings (consumer loans, overdraft and credit line alike) extract collateral
  and income and creditworthiness requirements *and* credit limit, grace period, revolving
  and linked card.
- The model's category then picks the details model, and the rest is dropped. A dropped
  field can still open a review and block the product.

**Confirmed.** The accepted Overdraft snapshot paid for, validated and then dropped
`collateral` (3 citations) and `creditworthiness_assessment_required`.

**Fix (Q4).**
- Seed catalog offerings gain `category` (`consumer_loan`, `overdraft`, `credit_line`,
  `mortgage`), validated against the family.
- The field set comes from the category. A model category that disagrees with the catalog is
  a review signal, replacing today's product-type check.
- **One schema for all seeds**: the `LoanProduct` model with category details stays. The
  prompt's field set and contracts become per category.

## SE22. Condition names are free text

**Where.** [domain/semantic_extraction.py:69](../../app/domain/semantic_extraction.py#L69)
(`Condition.dimension: str`), [semantic_extraction.py:910](../../app/services/semantic_extraction.py#L910)
(`_condition_dimension` guesses), [snapshot_lifecycle.py:402-408](../../app/services/snapshot_lifecycle.py#L402-L408).

**What happens.** The same condition is named differently from run to run. The comment in
`snapshot_lifecycle.py` records `card_type` in one run and `card_tier` in the next on
identical pages, and change detection had to add fuzzy pairing to cope.

**Fix.**
- `dimension` becomes an enum: `currency`, `borrower_type`, `residency`, `variant_id`,
  `card_tier`, `term_range`, `amount_range`, `channel`, `program`, `collateral`, `rate_type`,
  `location`, `other`.
- The prompt asks for condition *values* copied from the column path or row label of the
  cited record (SE1), so they are stable text.
- `_condition_dimension` is deleted.
- The fuzzy pairing in the rate guard stays until one run of history exists in the new
  form.

## SE23. Extraction runs without temperature 0 or an output cap

**Where.** [semantic_extraction.py:266-271](../../app/services/semantic_extraction.py#L266-L271).

**What happens.** Every other model stage pins `temperature=0` (discovery, intent). Extraction
uses the model default. After any cache miss, the same evidence can give different values,
which turn into false tariff changes. There is no `max_output_tokens`, so a runaway list is
bounded only by the model limit.

**Fix.** `temperature=0` through the model registry flag (SD14). Add a `max_output_tokens`
setting (default 16,384), and treat a truncated response as a retryable parse failure
(SE24).

## SE24. Retries stack; parse failures are not retried

**Where.** [semantic_extraction.py:262](../../app/services/semantic_extraction.py#L262)
(SDK `attempts=3`), [:281-301](../../app/services/semantic_extraction.py#L281-L301).

**What happens.**
- The SDK retries 3 times inside each of 3 application attempts: up to 9 calls per batch
  (SD13 in discovery).
- A response that is not valid JSON for the schema is not retried. The whole batch goes to
  review.

**Fix.** SDK `attempts=1`, as in SD13. One retry on a parse or schema failure, before repair.

## SE25. One failed batch fails the offering; the fallback rarely triggers and is empty

**Where.** [semantic_extraction.py:525](../../app/services/semantic_extraction.py#L525),
[:2015-2059](../../app/services/semantic_extraction.py#L2015-L2059),
[snapshot_lifecycle.py:209](../../app/services/snapshot_lifecycle.py#L209),
[config/models.py:385](../../app/config/models.py#L385).

**What happens.**
- The fallback chain runs only when *every* batch fails. A single failed batch, after
  retries, makes `non_reviewable_extraction_failure` fail the whole offering. The other
  batches' results are lost, because the cache save comes after that point.
- The fallback service also cannot reuse the primary model's cache: `model_name` is in the
  key.
- `fallback_model_names` is empty by default.

**Fix.**
- Per call: after the primary model's retries, try the next model for *that call only*.
- Save every successful call as it completes.
- If a call still fails on every model, the offering fails with
  `semantic_extraction.execution_failed` and the saved calls are reused next run.
- The fallback model is Q8.

## SE26. Batches run one after another; repairs are spent in batch order

**Where.** [semantic_extraction.py:470](../../app/services/semantic_extraction.py#L470),
[:611-645](../../app/services/semantic_extraction.py#L611-L645).

**Fix.**
- Run an offering's calls concurrently, bounded by a `max_concurrent_calls` setting
  (default 3).
- Spend the repair budget on required tariff fields first (interest rate, effective rate,
  loan amount, term, fees), then the rest.

---

## Hand-offs

- **Discovery (label).** On `consumer_standard`, the bank-wide "Loan service fees" table is
  labelled `related_product`, so its 5 fee rows never reach extraction. The prompt expects
  such fees as `general_loan_service`, so the table should be `generic_bank_information`
  or `current_product`. For the source-discovery hand labels and prompt.
- **Discovery (S04).** 4 PDFs are still kept wrongly. That is tracked in the source-discovery
  plan.

## Checked, no change needed

- **The hash functions.** SHA-256 is deterministic. The instability is in the inputs, as your
  item 12 says; SE10 and SE11 fix the inputs.
- **Model output in keys.** The only model output that becomes evidence is PDF
  transcription. It is cached by PDF SHA-256 (N17 is deferred: link metadata is still in that
  key), so a PDF's evidence text is stable while its bytes are unchanged. Your items 14 and 16
  matter only after a transcription cache miss, and SE3 pins that call.
- **Repair bounded to the original packet.** Keep it. It stops a repair from citing evidence
  the original call never saw.
- **Official PDFs at precedence 1.** Right once SD2 selects only the offering's PDFs. Full
  mode sends everything anyway.
- **Related-product evidence in the packet.** Keep it, marked, for telling variants apart.
  Validation already rejects a value supported only by related evidence
  ([semantic_extraction.py:1367-1379](../../app/services/semantic_extraction.py#L1367-L1379)).

---

## Decisions

| # | Question | Answer | Status | Affects |
|---|---|---|---|---|
| Q1 | How should extraction choose its evidence? | **A main mode that sends all selected evidence, and a cheaper mode that is not as naive as today's.** Main: `full`. Cheaper: `budgeted`, whole tables and sections scored on labels (SE6). | decided (user, 2026-09-26) | SE6, SE7, SE14 |
| Q2 | When is the cheaper mode used? | **Config switch only**: `semantic_extraction.evidence_mode`, no automatic switch. Full mode has a hard ceiling that fails loudly. | decided (user) | SE6 |
| Q3 | Fix root causes upstream? | **Yes**: table normalization, headline pairs in the parser, PDF transcription schema. | decided (user) | SE1–SE3 |
| Q4 | Seed-specific behaviour | **Catalog-driven**: delete URL-gated rules and seed prompt text; the catalog declares each offering's category; the field set follows it. | decided (user) | SE20, SE21 |
| Q5 | Gemini budget for validation | **Up to $2.** No live baseline: "before" is the offline replay (the probe). One live pass after the fix, a cache re-run, and a small budgeted-mode pass. | decided (user) | Phases 0, 9 |
| Q6 | Remember review decisions? | **Yes, per evidence**: reused while the call or the field's result is unchanged; any change re-opens. Every reuse audited. | decided (user) | SE12 |
| Q7 | Citation grounding | **Enforce numbers**: every number in an accepted value must appear in its cited text, after scalar normalization. | decided (user) | SE18 |
| Q8 | Which fallback model for extraction? | Proposal: a non-lite model this key can call. `gemini-2.5-flash-lite` answers 404 to this key (source-discovery Q2), and a lite model is a weak fallback for extraction. Phase 8 probes candidates with one small call each and asks the user. | **open** | SE25 |
| Q9 | Field-level ground truth | Claude drafts `data/seed-extraction-labels.json` from the pages and PDFs; the user confirms it before it is used as a pass criterion (as for source discovery). | proposed | Phases 0, 9 |
| Q10 | Call layout in full mode | Proposal: 3 calls per offering (SE6); S10 compares it with the 6 groups on cost and label accuracy. | proposed | SE6, SE9 |

**One-time effects on the first production run after deploy.**
- Evidence IDs change (SE10) and the cache key changes (SE11), so every offering is
  extracted once more: about $1.3–2 for the 13 offerings.
- PDF transcription versions bump (SE3), so every selected PDF is transcribed once more.
  That is small: 46 transcriptions cost cents with `gemini-3.1-flash-lite`.
- References to evidence IDs (fact evidence, projections, open reviews) point at the old IDs.
  Open reviews are resolved or superseded before deploy (see [Deployment](#deployment)).
- Condition names move to the enum (SE22), and category fields are no longer extracted
  (SE21). Change detection will report condition and field changes once, and may open
  reviews, although the bank changed nothing.
- Review decision memory starts empty.

---

## Implementation phases

Order:
1. labels, probe and failing tests;
2. contained bug fixes;
3. the upstream structure the evidence depends on;
4. evidence identity and rendering;
5. selection;
6. scope and schema;
7. validation rules;
8. cache and review memory;
9. execution;
10. validation.

Each phase ends green on `uv run pytest tests/unit tests/integration`.

### Phase 0: Preparation

- [x] Create branch `fix/semantic-extraction` from `integration/process-fixes` (`89f888e`).
- [x] Run `uv run pytest tests/unit tests/integration` and record the baseline (count, known
      failures, skips needing `TEST_DATABASE_URL` or a Gemini key).
- [x] Write [survey/probe_evidence_recall.py](survey/probe_evidence_recall.py) and save
      [data/probe-output-before.txt](data/probe-output-before.txt) and
      [data/evidence-recall-before.json](data/evidence-recall-before.json) (no Gemini).
- [x] Extend the probe:
  - [x] a `--pdfs` option that adds PDF evidence, replaying stored transcriptions from
        `pdf_extraction_cache` (as normalization S06) and refusing any model call;
  - [x] the new selection modes as they land (`--mode full|budgeted`).
- [x] **Field-level labels (Q9).** For each of the 13 seeds, record in
      `data/seed-extraction-labels.json` the expected value, with its source, for:
  - [x] `product_name`, `category`, `loan_amount`, `interest_rate`, `effective_rate`,
        `term`;
  - [ ] the main `fees`, `repayment`, `age_requirements`, `residency_requirements`,
        `application_channel`;
  - [x] per category: `down_payment_pct`, `ltv_pct`, `collateral`, `credit_limit`,
        `grace_period_days`;
  - [ ] fields that are genuinely not stated, recorded as `not_stated`.
- [ ] **Confirm the labels with the user.** They are the pass criteria of Phase 9.
- [x] Write `survey/check_extraction_labels.py`:
  - [x] it runs extraction on the replayed evidence with a chosen extractor (`fake`, or
        `gemini` behind a spend guard that estimates every call and refuses above the
        budget);
  - [x] it scores each field against the labels: `match`, `wrong value`, `wrong conditions`,
        `missing`, `spurious`;
  - [x] it reports tokens and dollars.
- [x] Write the scenario files `scenarios/S01…S10` (see Phase 9) with pass criteria.
- [x] Add regression tests, `xfail(strict=True)`, one per confirmed or code-level bug,
      each asserting the correct behaviour:
  - [x] SE13: a failing call after another offering's call carries no raw response;
  - [x] SE16: a malformed term becomes a field review item, not an exception;
  - [x] SE15: `"from 21 years"` is not guessed into `max_age`; a rate's `currency` becomes a
        condition; a bare `"not required"` collateral string is not guessed `applicable: true`
        (reshape only: an unparseable string fails validation and goes to repair);
  - [x] SE14: a mortgage packet with no age statement accepts `not_stated` without repair;
  - [x] SE17: `[18%, 14%]` interest rates with no conditions are rejected;
  - [x] SE18: a found `21%` whose quote has no 21 is rejected; a quote differing only by
        NBSP is accepted;
  - [x] SE10: inserting a block above a table leaves that table's evidence IDs unchanged;
  - [x] SE11: changing the instruction text changes the cache key; a heading rename above a
        row changes it; an unrelated block's change does not (budgeted mode);
  - [x] SE1: in the Overdraft card-tier fixture, the cell `AMD: 20%` has a column path naming
        the Gold tier; in the Primary fixture, `13.5%` has column path `Currency: AMD`;
  - [x] SE2: the Primary headline yields `Loan amount: AMD 3-150 million` as one block;
  - [x] SE4: a row citing ³ carries note ³'s text in its record;
  - [x] SE21: an overdraft offering requests no `collateral` field;
  - [x] SE20: the construction offering gets the same scope handling as the primary
        offering (no URL gate);
  - [x] SE25: with one call failing, the others are saved, and the failing call is tried on
        the next model.
- [x] Check each `xfail` with `--runxfail` to fail today.

#### Phase 0 notes (2026-09-26)

**State: done, except two label sub-items and the user's confirmation of the labels.** None of
them blocks Phases 1–8. The labels are Phase 9's pass criteria. Commit: *Semantic extraction
Phase 0: preparation*.

**Test baseline** (`uv run pytest tests/unit tests/integration`, with
`TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_acquisition_test`,
before any fix): **995 passed, 5 skipped, 1 failed, 3 errors**. The failure
(`test_agent.py::test_agent_stream`) and the errors (three `test_server_e2e.py` tests) need a
Gemini key, as on the parent branch. The 5 skips are optional-OCR tests.

**Survey tools** (all in [survey/](survey/)):
- [replay.py](survey/replay.py) is shared by the probe and the checker. It replays one seed's
  sources with no model call:
  - the page is the normalization survey's last live capture (`.cache-live-2`), re-parsed;
  - discovery is the stored `discovery-check-final.json`;
  - with `pdfs`, the seed's `current_product` and `shared_terms` PDFs (source-discovery hand
    labels) are added from the stored Gemini transcriptions in `pdf_extraction_cache`
    (`tariff_rt`, `tariff_monitor`, read-only). Their assessments are built from the same
    hand labels: current product, or generic bank information for shared terms.
  - Only **10 PDFs have a stored transcription**. 16 labelled PDFs are missing, including
    most offerings' own terms PDFs (for example `mortgage_commercial_purchase_eng.pdf`,
    `Consumer_loan_unsecured_eng.pdf`). They are reported per seed, never transcribed here.
    Phase 9 transcribes them within the budget.
- [probe_evidence_recall.py](survey/probe_evidence_recall.py) now uses `replay.py` and has
  `--pdfs`. With the 10 replayed PDFs
  ([data/probe-output-before-pdfs.txt](data/probe-output-before-pdfs.txt)), current-product
  recall **drops from 78% to 73% (115/157)**: PDF rows compete for the same slots, fees
  most (11 ranked out). `--mode` comes with Phase 4.
- [check_extraction_labels.py](survey/check_extraction_labels.py) runs the real
  `SemanticExtractionService` on replayed evidence:
  - with a `fake` extractor (plumbing, $0), or `gemini` behind a per-call spend guard;
  - it scores every labelled field: `match`, `wrong_value`, `missing`, `spurious`, `review`,
    `ambiguous`, plus informational `extra_numbers`;
  - "wrong conditions" from the plan is folded into `wrong_value`. The labels check numbers,
    not condition wording, which SE22 changes anyway.
  - It adapts to the extraction signature (it passes an `OfferingContext` once `extract`
    takes one).
  - Fake run today: 13 `match` (the category), 92 `review`, 15 `missing`, 117 fake calls. The
    reviews are SE14: `not_stated` is rejected wherever a keyword substring matches.

**Field labels** ([data/seed-extraction-labels.json](data/seed-extraction-labels.json)):
- 120 labelled fields over 13 seeds, drafted by Claude from the captured pages. They are
  **not confirmed by the user**; the file says so.
- Each found field lists the numbers it must contain and the numbers it may contain. So the
  label tolerates the page's own inconsistencies without dictating one value. For example,
  Mortgage Primary's headline says "12.9% nominal" and its table says 13.5 / 11.0 / 8.5 by
  currency: the table's rates are required, and 12.9 is allowed.
- The categories: `credit_line` and `overdraft` for those two offerings, `consumer_loan` for
  the other two consumer offerings, `mortgage` for the nine others. Phase 5 puts these into
  the seed catalog.
- **Not done:** `application_channel` is not labelled on any seed; `residency_requirements`
  only on `consumer_standard`. No field is labelled `not_stated`: none was certain from the
  pages alone. These two sub-items stay open.

**Scenarios.** [scenarios/S01…S10](scenarios/) written with pass criteria, all *not run*.
S06's pass bar is a proposal, to be agreed with the user when the labels are confirmed.

**Regression tests.** [tests/unit/test_semantic_extraction_fixes.py](../../tests/unit/test_semantic_extraction_fixes.py):
20 tests, `xfail(strict=True)`, one or more per item (SE1 ×2, SE2, SE4, SE10, SE11 ×3, SE13,
SE14, SE15 ×3, SE16, SE17, SE18 ×2, SE20, SE21, SE25).
- Each was checked with `--runxfail` to fail for the intended reason: the missing API, a
  wrong value, or an exception from today's code. None fails on a fixture error.
- They fix the target APIs:
  - `SemanticExtractionCallError.raw_response`;
  - `NormalizedTableCell.column_path` and `NormalizedTableRow.continues`;
  - `SemanticExtractionSettings.evidence_mode`;
  - `build_extraction_batches(..., category=)`.
- The fixtures follow the real HTML: Overdraft's `td` header row with colspans; Primary's
  title row, `3.1. Currency` row and `Fixed` / value row pair; the `features3-grid__col`
  headline cards (`h6` value, then `p` label).

**Design points found while preparing** (they refine the plan):
- **Headline cards** are `<h6>` value + `<p>` label in a `features3-grid__col`. The parser
  makes the `h6` a *heading*, so the label block's heading path contains the value, and the
  value then stays in the heading path of later blocks (Primary's "Actual interest rate:
  13.67-13.68%" sits "under" `from 10%`). SE2 fixes both.
- **Qualifier rows stay in force across in-table section rows.** On Primary, the
  `3.1 Currency | AMD | USD | EUR` row precedes the section row "Term and interest rate", and
  the rates under that section are still per currency. The plan's SE1 said "until the next
  qualifier row or a section row"; Phase 2 uses **until the next qualifier row**.
- **Outline numbers** (`3.1.1. AMD`) must be stripped before a row is judged a qualifier.

**Spend so far: $0.**


### Phase 1: Contained bug fixes (SE13, SE16, SE15, SE23, SE24, SE14)

- [x] SE13: remove `raw_responses` from `AdkSemanticExtractor`. `extract()` returns the raw
      text with the response; the error carries the raw text or none.
- [x] SE13: batch IDs `{offering_id}:{call}`; the review ID is built from offering, field and
      issue, not position.
- [x] SE13: delete the ADK session after each call.
- [x] SE16: move `_normalize_response_contract` into the per-batch `try`; a normalizer
      exception becomes a validation issue.
- [x] SE15: rewrite normalizers to reshape only. Unknown condition-like keys move into
      `conditions`; delete the string heuristics and `_condition_dimension`'s substring rules.
- [x] SE15: check that review input still normalizes through the same function
      (`review_input.py`).
- [x] SE23: `temperature=0` from the model registry flag; add `max_output_tokens` to
      `SemanticExtractionSettings`; record both in usage.
- [x] SE24: SDK `HttpRetryOptions(attempts=1)`; one retry on parse or schema failure or
      truncation, before repair.
- [x] SE14: delete the keyword-based `not_stated` completeness check.
- [x] Remove the matching `xfail` markers; the full suite is green.

#### Phase 1 notes (2026-09-26)

**State: done.** Commit: *Semantic extraction Phase 1: contained bug fixes*. Full suite:
**1,009 passed**, 5 skipped, 14 xfailed (later phases). The same 4 Gemini-key tests fail as
at baseline.

**SE13 (raw responses, batch IDs, sessions).**
- `AdkSemanticExtractor` no longer keeps `raw_responses`.
  - `extract()` returns `ExtractorOutput(response, raw_response)`.
  - A call that yields nothing usable raises `SemanticExtractionCallError`, carrying *its
    own* raw text, or `None`.
  - The service unpacks either form (`_unpack`), so test fakes that return a plain
    `ExtractionBatchResponse` still work.
  - API errors pass through unchanged, so `is_model_fallback_error` still sees them.
- Batch IDs are `{offering_id}:{group}` (`build_extraction_batches(..., offering_id=)`, fed
  from `discovery.offering_id`; the product value when there is none). The review ID
  already hashed the batch ID, so it is now positional-free with no further change.
- The ADK session is deleted after every call.
- The two demonstration scripts read the raw text from the error now.

**SE16.** Normalization runs inside the per-batch `try`. `_normalize_field_contract` also
catches a normalizer error per field and leaves that field as the model gave it, so the
field's own validation reports it (repair, then review). One malformed field no longer
costs the batch, let alone the offering.

**SE15 (reshape only).**
- Value models used in field contracts now derive from `ValueModel` with
  `extra="forbid"`. Before, pydantic silently *ignored* unknown keys, so a rate's
  `currency` vanished even without the normalizer. That was a second cause of SE15's
  dropped currency, found while implementing.
- The normalizer moves condition-naming keys (`currency`, `borrower_type`, `variant_id`,
  `card_tier`, …) into `conditions`. It keeps every other unknown key, for validation to
  reject.
- Deleted guesses:
  - age prose parsing (`"from 21"` → `max_age`);
  - `" for "` / `"when "` → conditional documents: a bare document string is now
    `requirement: unknown`;
  - bare collateral strings → `applicable: true`: now left for repair, except the literal
    `n/a` / `not applicable`;
  - `"state"` / `"collateral"` / `"program"` substrings as condition dimensions: only a
    bare currency code gets a dimension;
  - the `mortgage` → `product` fee-scope alias;
  - `int("6 months")`-style conversions that raised.
- `_normalize_rate` and `_normalize_term` keep unknown keys instead of dropping them.
- **Review input**: human reviewers type plain text, which the old guesses served. Their
  documented formats now have explicit parsers in `review_input.py`: ages (`18-65`,
  `at least 18`, `21+`, `up to 65`), documents (`… upon request`), collateral (`none`).
  The shared normalizer only reshapes the result. Parsing a documented input syntax is
  not guessing at model prose.

**SE23.**
- Temperature 0 for every model, as in discovery (Q9 there). The model registry only
  decides the thinking form (`thinking_level=MINIMAL` for
  `gemini-3.5-flash-lite` when the budget is 0).
- `max_output_tokens` (default 16,384) is a new setting:
  `SEMANTIC_EXTRACTION_MAX_OUTPUT_TOKENS`, in `.env.example` and `docs/configuration.md`.
- Both values are logged when the extractor is built, and kept on it as attributes.
  They are not written to `model_call_usage`: that table has no column for them.

**SE24.**
- SDK `HttpRetryOptions(attempts=1)`; the application loop keeps backoff.
- An answer that is empty, cut at `MAX_TOKENS`, or does not parse against the schema is
  asked once more (`parse_retries=1`), then fails with its raw text.

**SE14.** The keyword `not_stated` completeness check and `_COMPLETENESS_FIELDS` are
deleted. `field_has_evidence_marker` is still used by the product-name anchor; SE19 reviews
that check in Phase 6.

**Tests changed.**
- Four older tests encoded the deleted guesses and now assert the new behaviour: the
  document requirement is `unknown`; a channel is wrapped without a guessed `available`;
  the age case uses an object.
- The bounded-repair test is now triggered by a malformed term shape: a `not_stated`
  answer is no longer "suspicious".
- New tests: temperature, output cap and one SDK attempt (SE23); one retry, then the raw
  text on failure (SE24); the reviewer age grammar and `none` collateral.

**Measured.** The fake-extractor check
([data/extraction-check-phase1-fake.json](data/extraction-check-phase1-fake.json)) went
from 92 `review` and 117 calls to **0 `review` and 78 calls**: no repair is spent on a
`not_stated` answer any more.

**Remaining.** The prompt, schema and cache versions are not bumped. Cached responses are
re-validated on every read, and one that now fails validation is ignored. Phase 7 replaces
the cache key anyway.


### Phase 2: Upstream structure (SE1, SE2, SE3)

- [x] SE1: add `header_rows` (with spans) and `column_paths` to `NormalizedTable`, and
      `label_path`, `continues` and cell `column_path` to rows and cells. Keep `headers`, and
      make sure stored artifacts still load.
- [x] SE1: build multi-level header rows from `thead` rows and `rowspan`/`colspan`; collapse
      merged duplicates.
- [x] SE1: detect qualifier rows (label cells, then column-naming cells, no unit numbers, over
      same-width value rows); apply them as a header level until the next qualifier or
      section row.
- [x] SE1: link continuation rows (rate type row → value row).
- [x] SE1: extend `seed-ground-truth.json` with column-path facts (Overdraft card tiers,
      Primary and Secondary currencies, one more multi-column seed), and run
      `fix-process/normalization/survey/check_ground_truth.py`: no regression, new facts
      pass.
- [x] SE2: pair value and label blocks inside one card container into a key/value block;
      add the headline facts to the ground truth; re-run the check.
- [x] SE2: confirm the acquisition page identity is unchanged on the 13 captures (the
      pairing changes blocks, not the visible text).
- [x] SE3: extend the PDF transcription schema (`section_path`; `header_rows` with spans;
      `row_group`) and the instruction; build `column_paths` and `label_path` from them.
- [x] SE3: `temperature=0` for transcription; bump the PDF extraction schema and prompt
      versions.
- [x] SE3: replay the stored transcriptions for the old schema (still load, flat), and
      transcribe the selected PDFs of 2 seeds with the new schema. *Spends Gemini budget:
      ≤ $0.05.*
- [x] Update [docs/normalization.md](../../docs/normalization.md).

#### Phase 2 notes (2026-09-26)

**State: done**, with two deliberate departures from the plan (SE2 identity, SE3
prompt), both recorded in [../note.md](../note.md). Commit: *Semantic extraction Phase
2: upstream structure*. Full suite **1,013 passed** (same 4 Gemini-key failures).
Normalization ground truth: **0 of 372 checks failed**. The 20 new SE1/SE2 facts all
fail on the Phase 1 code, and nothing regressed.

**SE1 (tables, `table_normalizer.py`, `domain/normalization.py`).**
- New fields:
  - `NormalizedTable.stub_columns` and `column_paths`;
  - `NormalizedTableRow.label_path`, `continues` and `qualifies`;
  - `NormalizedTableCell.column_path`.

  All default empty, so stored artifacts load. The plan's `header_rows` with spans was
  not added to `NormalizedTable`: `column_paths` already carries the collapsed
  hierarchy, and nothing downstream needs the raw spans.
- **Stub columns**: a header cell spanning from column 0 sets them (Overdraft's "Card
  type" spans 2); with invented `Section | Item` headers they are 2; otherwise 1.
- **Column paths**: the header texts per column, merged duplicates collapsed. A cell
  spanning columns with different paths gets their common prefix (Overdraft's
  "Payments" spans both card tiers, so it has none).
- **Qualifier rows**: stay in force until the next qualifier row, *not* until a
  section row (the plan's wording). On Primary, the rates under the section row "Term
  and interest rate" are still per currency.
- **Real tables** (`.cache-live-2`):
  - currency qualifiers on all 8 mortgage tables that have one;
  - card tiers on Overdraft and Credit line;
  - `Term | Refinancing | New loans` on the no-income-verification campaign table,
    which ties APR 12.05–12.45% to refinancing and 13.67–13.68% to new loans.
- **Continuations**: first found list items under one label (repayment methods,
  insurance clauses). Tightened: the row above must hold only short digit-free type
  words, and every value of the continuing row a number. Now only Primary's `Fixed` →
  rate and `Fixed` → APR pairs link.

**SE2 (headline cards, `html_parser.py`).**
- A container whose only texted children are a short heading (≤ 60 characters, one
  line) followed by a short label (first line ≤ 60 characters, no digits) becomes one
  `key_value` block: `Loan amount: AMD 3-150 million`. For Online consumer finance,
  `Nominal interest rate: 17% *` keeps its second line (the APR) in the block.
- The value is not pushed as a heading. The label's block id is reserved, so ids
  after the card do not shift (stored assessments and survey data still line up).
- A lone `h5`/`h6` in a small card that does *not* pair (Overdraft's "Indefinite
  term" with a long description) is scoped to its card, so it no longer heads later
  blocks either.
- **Departure:** the page identity is a hash of parsed blocks, so it changes once on
  all 13 pages (old against new parser, same captures). The plan expected no change.
  The acquisition drop guard is unaffected: it measures characters, tables and PDF
  links, and pairing only adds `": "`.

**SE3 (PDF transcription).**
- Schema: `PdfModelItem` and `PdfExtractedTable` gain optional `header_rows` and
  `row_groups`. Stored transcriptions load unchanged.
- Temperature 0; thinking form from the model registry
  (`thinking_level=MINIMAL` for `gemini-3.5-flash-lite`).
- `PDF_EXTRACTION_SCHEMA_VERSION` and `PDF_EXTRACTION_PROMPT_VERSION` go to 3, so every
  selected PDF is transcribed once more after deploy.
- PDF tables get stub, column paths, qualifiers and continuations from
  `structure_text_table`, the text-row twin of the HTML rules. A header row counts
  only if it reads as a header (cells ≤ 60 characters, no amounts). The model's own
  `headers` row serves when it gives no `header_rows`. Placeholder names it invents
  (`Details`, `Item`, `Description`, …) name nothing. On the replayed PDFs this gives
  `AMD/USD/EUR` on Primary's refinancing table and `New loans/Refinancing` on the
  campaign terms.
- **Departure: the transcription instruction is unchanged.** Live trial, 13
  transcriptions, `gemini-3.1-flash-lite`:
  - asking for the fields in detail made the Overdraft PDF come back with 4 empty
    pages;
  - a lighter wording kept all pages but lost rows on the Primary terms PDF (35
    against 40);
  - neither wording got the model to fill `row_groups` or a real header row on any of
    3 PDFs.

  So the fields stay optional and the production instruction stays. Page coverage
  also varied between runs at temperature 0: handed off to normalization in
  [../note.md](../note.md).
- **Spend**: 13 transcriptions, not metered (no usage repository in the trial).
  Estimated ≤ $0.10 from the stored `pdf.transcription` usage per call.

**Docs.** [docs/normalization.md](../../docs/normalization.md): headline cards, the
table structure, PDF temperature and optional structure fields.

**Probe.** Current-product facts reaching their batch: **80% (122/153)**, up from 78%.
The paired headline blocks now carry label and value together. The selection itself is
still Phase 4's.


### Phase 3: Evidence identity and rendering (SE10, SE4, SE8, SE9)

- [x] SE10: new `evidence_id` from source key, structural path, normalized text and
      occurrence; `source_item_id` kept as locator only.
- [x] SE10: list every consumer of evidence IDs (`grep -rn evidence_id app/`): fact
      evidence, structured projection, review candidates, snapshot evidence, RAG. Check each
      works with the new IDs, and record the list in the phase notes.
- [x] SE1/SE4: render table rows as records (label path; column path → value; `Notes:` with
      the referenced notes). Notes stay citable items.
- [x] SE8: render the packet in document order (document → section → table).
- [x] SE9: compact packet (id, source, section path, association, text); locators stay
      server-side; minified per-call contracts; the packet first and identical across an
      offering's calls.
- [x] Re-run the probe: evidence IDs unchanged when a block is inserted on a capture copy;
      prompt characters per call recorded.

#### Phase 3 notes (2026-09-26)

**State: done.** Commit: *Semantic extraction Phase 3: evidence identity and rendering*.
Unit suite **948 passed**; SE4, SE10 and the SE11 heading-rename test pass without their
`xfail`.

**SE10 (identity, `extraction_evidence.py`).**
- `evidence_id = "ev_" + sha256(source key ‖ structural path ‖ whitespace-collapsed text
  ‖ occurrence)[:24]`, where:
  - the source key is `page:<page URL>` or `pdf:<PDF sha256>`;
  - the structural path is heading path, table title, row section and row label path
    for a row; heading path for a block; heading path, title and `note` for a note;
  - the occurrence is the count among items with the same key, so duplicates stay
    distinct.
- The page hash and `source_item_id` are no longer part of the identity.
  `source_item_id` stays for locating an item.
- **Check on a real capture:** a paragraph inserted at the start of Mortgage Primary's
  `<body>` shifts every block id (`b70` → `b71`) and a new page hash is set. **All 54
  evidence IDs of the tariff table are unchanged.**
- A change that *does* move structure changes IDs by design. Inserting inside the
  banner made the parser stop scoping the page's `h1` to it, so the tables gained the
  `h1` in their heading path. Heading paths are part of the identity, because the
  model sees them (SE11).
- **Consumers** of evidence IDs (`grep -rln evidence_id app/`):
  - `domain/monitoring.py`, `domain/review.py`, `domain/structured_tariffs.py`;
  - `repositories/structured_projection.py`, `repositories/structured_tariff_query.py`;
  - `services/answer_read_model.py`, `evidence_retention_audit.py`,
    `knowledge_projection.py`, `pipeline_audit.py`, `review_decisions.py`,
    `review_resolution.py`, `snapshot_lifecycle.py`, `structured_projection.py`,
    `structured_tariff_query.py`, and `app/cli.py`.

  All treat IDs as opaque links inside one run's snapshot (facts to evidence, review
  candidates to evidence). None parses them or compares them across runs. The format
  (`ev_` + 24 hex) is unchanged. Effect: on the first run after deploy every ID
  changes once (already in the one-time effects).

**SE1/SE4 (records, `render_row`).**
- A table row is now a record: `Section: …`, then `label path:`, then one line per
  value, `column path → value`. A row without column paths is `label: v1 | v2`.
- A continuation row carries the row above's word: `Currency: AMD → 13.5% (Fixed)`.
- The notes the row cites by marker (superscripts or `*`, in cells, labels, column
  paths or the section) follow under `Notes:`. Notes also stay citable items of their
  own.
- One older test (`test_normalization_fixes.py`) looked up the note by its text and
  now found the row first; it selects the note by id and also asserts the row
  carries it.

**SE8 (order).** `EvidenceItem.order` records reading order:
- documents in bundle order;
- a table's rows at the position of the table's block;
- PDF tables after the PDF's blocks.

The catalog is sorted by it, no longer by precedence.

**SE9 (prompt, `build_extraction_prompt`).**
- The evidence packet comes first, then target, requested fields, minified contracts
  for the call's fields only, and any repair context.
- Per item: `[id] source | association | section`, qualifiers only when present
  (conditions, effective periods, a non-current temporal status), then the text.
  Related-product items come last, in a marked block.
- Locators, fingerprints, precedence and role are no longer sent.
- The instruction's "repair_context_json" wording became "a REPAIR CONTEXT section".
- **Prompt size: 4,345–20,545 characters per call, down from 24,089–53,296**, on the
  same batches ([data/probe-output-phase3.txt](data/probe-output-phase3.txt)).

**Probe caveats.**
- Recall moved 80% → 77%: today's keyword ranker scores the new record text
  differently. Phase 4 replaces that ranker, so it was not tuned.
- The probe's footnote line counts separate note items missing from a batch. With
  notes inside row records it no longer measures SE4. SE4 is covered by
  `test_se4_row_record_carries_its_referenced_note`.


### Phase 4: Selection modes (SE6, SE7, SE5)

- [x] Add `evidence_mode` (`full` | `budgeted`), `max_packet_chars` (200,000) and
      `budget_chars` (16,000) to `SemanticExtractionSettings`; remove `max_items_per_batch`,
      `max_evidence_chars_per_item` and `max_chars_per_batch`. Document them in
      [docs/configuration.md](../../docs/configuration.md).
- [x] `full`: the whole selected evidence per call, own items first, related items in a
      marked block; fail with `semantic_extraction.packet_too_large` above the ceiling.
- [x] `full`: 3-call layout (Q10) behind a constant, so S10 can compare with 6.
- [x] `budgeted`: units (whole table or section; tables over the unit limit split by row
      group with header levels repeated); label-only word-boundary scoring with
      inverse-frequency weights; per-field guarantee, then by score; ties by document order.
- [x] Move keyword lists into `app/domain/extraction_terms.py`; delete `_field_score`,
      `field_has_evidence_marker` and the per-row quota.
- [x] SE7: no character cuts; budgeted splits mark `[part i of n; continues]`.
- [x] Record in the result: mode, units sent, units left out for budget.
- [x] Probe pass criteria: `full` sends 100% of current-product ground-truth facts to every
      call that extracts the field; `budgeted` ≥ 95%, with no sibling facts in the offering's
      own block.

#### Phase 4 notes (2026-09-26)

**State: done.** Commit: *Semantic extraction Phase 4: selection modes*. Unit suite
**952 passed**; the SE20 and SE11-budgeted tests pass without `xfail`.

**Settings.** `SEMANTIC_EXTRACTION_EVIDENCE_MODE` (`full`), `…_MAX_PACKET_CHARS`
(200,000) and `…_BUDGET_CHARS` (16,000) replace the three per-batch limits, in
`.env.example`, `environment.py`, `loader.py`, `models.py` and `docs/configuration.md`.

**Full mode.**
- Every call gets all selected evidence except navigation and historical or future
  versions. Related-product items are rendered last, in the marked block.
- Three calls (`FULL_MODE_CALLS`): identity + core financial; fees, repayment and
  eligibility; documents + category details.
- Above the ceiling it raises `EvidencePacketTooLargeError`
  (`semantic_extraction.packet_too_large: N > ceiling`), mapped to
  `source.size_rejected`.

**Budgeted mode**, in the same three calls. Two departures from the plan, both
measured:
- **Selection works on items within units, not only whole units.** Whole-unit
  selection reached only 73% (six calls) or 69% (three calls): one long tariff table,
  labelled for many fields, took the whole budget. The final rule:
  - each field gets an equal share of the budget, spent on items *labelled* for it
    (row label, column path, key, section), breadth-first over its top 3 units;
  - then whole units by score, taking a unit's labelled items when it does not fit;
  - related units only with room left.

  Table rows are self-contained records since Phase 3 (column paths, notes, rate
  types), so taking some rows of a table loses no context. That was the reason the
  plan asked for whole units (SE5).
- **No `[part i of n]` marker in the content.** Items are never cut, so a partial
  unit is recorded instead: `units_left_out` lists `key [partial]` on the batch and in
  `SemanticExtractionResult.units_left_out`.
- Scores use whole-word term matches with inverse unit frequency, on labels only.
  Ties go by reading order.
- `not_stated` for a field whose labelled items were left out gets
  `not_stated_budget_limited` in its explanation.

**Code removed.** `FIELD_KEYWORDS`, `_ROLE_GROUPS`, `_field_score`,
`field_has_evidence_marker`, `select_evidence_for_fields`, the per-row quota, and
`_outside_canonical_scope` (with `_PRIMARY_VARIANT_PATTERN`, ahead of Phase 5, since
nothing called it any more). Terms live in `app/domain/extraction_terms.py`, extended
with the labels Phase 0 found missing: `financing limit`, `fine`, `penalty`,
`cashing`, `minimum payment`, `prepayment`, `actual interest rate`, … The product-name
anchor uses the word-boundary `mentions_field`.

**Prompt size.**
- Contracts lose their generated `title` keys.
- Consecutive items that share source, association and section print one `==`
  header.
- **Full mode's total prompt over the 13 seeds fell from 2.23M to 1.68M characters**
  on the same evidence.

**Measured (S03, [data/probe-output-phase4-full.txt](data/probe-output-phase4-full.txt),
[…-budgeted.txt](data/probe-output-phase4-budgeted.txt), `-pdfs` variants):**

| Mode | Evidence | Current-product facts sent | Prompt characters, 13 seeds |
|---|---|---|---|
| before (Phase 0) | page | 119/152 (78%) | — |
| full | page | **153/153 (100%)** | 1,676,558 |
| budgeted | page | **147/153 (96%)** | 862,345 (**51%** of full) |
| full | page + 10 replayed PDFs | **158/158 (100%)** | 2,346,581 |
| budgeted | page + 10 replayed PDFs | 146/158 (92%) | 914,217 (39%) |

- Sibling facts: all 45 go to the marked related block (full) or are excluded
  (budgeted). None is in the offering's own block.
- S10 asks budgeted ≤ 50% of full's input. Page-only it is 51%; a 15,000 budget gives
  50.1% at the same recall. The ratio is set by the small offerings, where both modes
  send everything. So the default stays at the plan's 16,000.


### Phase 5: Scope and schema (SE20, SE21, SE22)

- [x] SE21: add `category` to seed catalog offerings, validated against the family; update
      [docs/seed-catalog.md](../../docs/seed-catalog.md) and the catalog tests.
- [x] SE21: the field set per category; a category disagreeing with the catalog is a review
      signal.
- [x] SE20: delete `_PRIMARY_VARIANT_PATTERN`, `_PRIMARY_OUT_OF_SCOPE`, `_target_scope`'s URL
      branch, `_outside_canonical_scope`'s URL branch and `_outside_target_scope`.
- [x] SE20: pass the offering context (name, aliases, seed URL, page title, category) into
      the prompt as the target scope.
- [x] SE20: rewrite the instruction with generic rules and neutral examples; no seed product
      names.
- [x] SE22: `Condition.dimension` enum; the prompt asks for values copied from column paths
      and row labels; normalizer maps only exact synonyms (`card_type` → `card_tier`).
- [x] Run `check_extraction_labels.py --extractor fake` for plumbing.

#### Phase 5 notes (2026-09-26)

**State: done.** Commit: *Semantic extraction Phase 5: scope and schema*. Unit suite
**956 passed**; the SE21 test passes without `xfail`.

**SE21 (category).**
- `SeedCatalogEntry.category` (`OfferingCategory`): `consumer_loan`, `overdraft`,
  `credit_line` or `mortgage`. It is validated against the family and defaults to the
  family's own category, so catalogs without it still load. `overdraft` and
  `credit_line` declare theirs in `seed_catalog.yaml`.
- `OfferingContext.category` carries it. It is excluded from serialization, so the
  discovery prompt and cache are unchanged.
- `build_extraction_batches(..., category=, offering=)` uses `CATEGORY_FIELDS`:
  - an overdraft asks credit limit, grace period, revolving and linked card, and no
    collateral;
  - a consumer loan asks collateral, income and creditworthiness, and no credit limit;
  - a mortgage asks what it asked before;
  - without a category (callers outside the catalog), the family's union as before.
- A model category that differs from the catalog raises in
  `_validate_semantic_completeness`, so it is a review. The batch carries `category`.
- `SemanticExtractionService.plan/extract`, `FallbackSemanticExtractionService`, the
  pipeline's `SemanticExtractionPort` and `_audit_plan` take `offering`. The pipeline
  passes the context it already builds for discovery.

**SE20 (no URL rules).**
- Removed: `_PRIMARY_OUT_OF_SCOPE`, `_outside_target_scope` and their two uses in
  validation; `_target_scope`'s `/mortgage/primary` branch. `_PRIMARY_VARIANT_PATTERN`
  and `_outside_canonical_scope` went in Phase 4.
- The target scope now lists family, category, offering name and id, the catalog's
  other names, page title, heading and summary, and the canonical URL.
- The instruction is rewritten without any seed product (no Express, Solar,
  secondary-market, 6–60 months). It gains:
  - how to read row records (column path → conditions; a parenthesised type; row
    notes qualify values);
  - quotes must contain the value's numbers;
  - two alternatives never share conditions;
  - condition values are copied verbatim from the column path, label or note.
- The prompt and schema versions go to **6**. `models.py` and `environment.py` now
  agree; they were "4" and "5".

**SE22 (condition dimensions).**
- `Condition.dimension` is `ConditionDimension`, 17 names including `other`. The JSON
  Schema sent to the model lists them.
- The canonical mapping is a `model_validator(mode="before")` on `Condition` itself,
  not in the normalizer: synonyms map (`card_type` → `card_tier`, `customer_type` →
  `borrower_type`, …), and an unknown dimension becomes `other` with its name kept in
  the value (`season: summer`). This way snapshots, cached responses and review
  decisions stored with free-text dimensions still load.
- The normalizer's fallback dimension is `other`, not `condition`.
- The rate guard's fuzzy pairing in `snapshot_lifecycle.py` stays, as the plan says,
  until history exists in the new form.

**Plumbing.** `check_extraction_labels.py --extractor fake`: 13 category matches, 39
calls (3 per offering), no errors
([data/extraction-check-phase5-fake.json](data/extraction-check-phase5-fake.json)).

**Docs.** [docs/seed-catalog.md](../../docs/seed-catalog.md) documents `category`.


### Phase 6: Validation rules (SE17, SE18, SE19)

- [ ] SE17: reject alternatives with different values and identical conditions, for every
      list-valued field; delete `_CONDITION_CUES`.
- [ ] SE18: number grounding through the scalar normalizer (value numbers ⊆ numbers in the
      cited text); whitespace-collapsed quote matching.
- [ ] SE19: run each remaining heuristic validator (term threshold, income markers,
      product-name anchor) against the Phase 0 labels; keep and rewrite structurally the ones
      that catch a labelled error; delete the rest, moving their cases into the eval set.
- [ ] Record the kept and deleted checks in the phase notes.

### Phase 7: Cache and review memory (SE11, SE12)

- [ ] SE11: `prompt_fingerprint` over model, generation config, instruction and user prompt;
      deterministic rendering (ordering, number formats, JSON separators).
- [ ] SE11: migration adding `prompt_fingerprint` (and a `validation_status` column) to
      `semantic_extraction_batches`; look up by fingerprint; one default for the versions in
      `config/models.py`.
- [ ] SE12: cache every response with its validation outcome.
- [ ] SE12: migration for `review_decision_memory` (offering, field, prompt fingerprint,
      result fingerprint, decision, reviewer, time); write on resolution in
      `review_resolution.py`.
- [ ] SE12: reuse rule (same prompt fingerprint, or same field result) in extraction before
      review items are created; audit event `review_decision_reused`.
- [ ] Update [docs/architecture.md](../../docs/architecture.md) (persistence responsibilities)
      and [docs/native-hitl-review.md](../../docs/native-hitl-review.md).

### Phase 8: Execution and reliability (SE25, SE26, Q8)

- [ ] SE25: per-call model fallback; save each successful call as it completes; an offering
      fails only when a call fails on every model.
- [ ] SE26: concurrent calls with `max_concurrent_calls` (3); repair budget spent on required
      tariff fields first.
- [ ] **Q8.** Probe candidate fallback models with one small call each (a few cents) and
      **ask the user** which to configure; set it in `.env.example` and
      [docs/configuration.md](../../docs/configuration.md).

### Phase 9: Validation

Budget (Q5): **$2**, enforced by the spend guard.
- Live full-mode pass on 13 seeds: estimated $1.3–1.5.
- Budgeted-mode pass on 4 seeds: about $0.2.
- Leftover PDF transcriptions and discovery: about $0.15.
- The cache re-run costs $0.

Scenarios:

| # | Scenario | Pass criteria | Gemini |
|---|---|---|---|
| S01 | Offline test suite | all green; every Phase 0 `xfail` removed | — |
| S02 | Confirmed bugs fixed | each reproduction from "How this was checked" now behaves correctly | — |
| S03 | Evidence recall, replay | `full`: 100% of current-product facts reach every call extracting the field; `budgeted`: ≥ 95%; 0 sibling facts in the own block | — |
| S04 | Table structure | column-path facts pass in `check_ground_truth.py`; no regression on existing facts | — |
| S05 | Identity and cache stability | inserting a block keeps other evidence IDs; a second run makes 0 extraction calls | $0 |
| S06 | Live extraction vs labels | full mode on 13 seeds scored by `check_extraction_labels.py`; the pass bar is agreed with the user after the labels are confirmed | ≤ $1.5 |
| S07 | Review memory | a known-failing field is reviewed once; the next run reuses the decision; changing its evidence re-opens it | $0 (fake extractor) |
| S08 | Failure handling | one failing call: others saved, fallback tried for that call only; no raw response from another offering | $0 (fake) |
| S09 | Grounding | a value whose number is not in its citation goes to repair, then review | $0 (fake) |
| S10 | Cost and layout | prompt tokens per offering, 3-call vs 6-call layout, `cached_content_token_count` recorded; budgeted mode ≤ 50% of full-mode input tokens | in S06 |

- [ ] Run S01–S05 and S07–S09 offline; record results under `scenarios/results/`.
- [ ] Run S06 (live, full mode) with the spend guard; save
      `data/extraction-check-after.json`.
- [ ] Run S05's cache re-run live: 0 extraction calls.
- [ ] Run the budgeted-mode pass on 4 seeds (two mortgage, two consumer); save
      `data/extraction-check-budgeted.json`.
- [ ] S10 from the recorded usage; choose the full-mode layout (Q10) and record it.
- [ ] Write `scenario-results.md` with the results, the spend, and anything that failed.
- [ ] Update [docs/semantic-extraction.md](../../docs/semantic-extraction.md) and
      [docs/semantic-extraction-maintenance-guide.md](../../docs/semantic-extraction-maintenance-guide.md).
- [ ] Update this plan's Summary statuses and Decisions.

## Deployment

- [ ] Resolve or supersede open reviews before deploy: their evidence IDs change (SE10).
- [ ] Apply the migrations (cache fingerprint and validation status; review decision memory).
- [ ] Set `SEMANTIC_EXTRACTION_EVIDENCE_MODE=full` (or `budgeted`) and the fallback model (Q8)
      in the environment.
- [ ] Expect the one-time effects listed under [Decisions](#decisions): every offering
      re-extracted (about $1.3–2), PDFs re-transcribed, a round of structural changes and
      possible reviews without a bank change.
- [ ] After the first scheduled run, check `model_call_usage` for `semantic.extraction`, and
      confirm that the second run reuses the cache.
