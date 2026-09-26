# Normalization: problem report and fix plan

Date: 2026-09-26 · Branch: `fix/normalization` (from `integration/process-fixes`) ·
Status: **done** (Phases 0–6), with N17 (PDF cache key) deferred by the user. All decisions
Q1–Q6 are made. Validation was done without Gemini, per the user. See the phase notes.

## Scope

Normalization turns a `PageArtifact` into a `NormalizedSourceBundle`
([normalization.py](../../app/services/normalization.py)). This plan covers the code that
shapes that bundle:

- the HTML parser's blocks and tables ([html_parser.py](../../app/services/html_parser.py));
- table, block and scalar normalization ([table_normalizer.py](../../app/services/table_normalizer.py),
  [block_normalizer.py](../../app/services/block_normalizer.py),
  [scalar_normalizer.py](../../app/services/scalar_normalizer.py));
- PDF admission and transcription ([pdf_admission.py](../../app/services/pdf_admission.py),
  [pdf_extraction.py](../../app/services/pdf_extraction.py),
  [gemini_pdf_extractor.py](../../app/services/gemini_pdf_extractor.py));
- how the bundle becomes evidence ([extraction_evidence.py](../../app/services/extraction_evidence.py)).

The HTML parser belongs to acquisition, but everything it gets wrong reaches the bundle
unchanged, so the parser fixes are in this plan.

## How this was checked

- **Code.** Read on `integration/process-fixes` at `189e60e`. The normalization files there
  are identical to `adk-native-runtime`; `html_parser.py`, `acquisition.py` and
  `browser_renderer.py` changed in the acquisition fix, and every finding below was re-checked
  after that change.
- **Probe.** [data/probe_normalization.py](data/probe_normalization.py) runs the real parser,
  block normalizer and table normalizer on small HTML fixtures. Its output before any fix is
  in [data/probe-output-before.txt](data/probe-output-before.txt).
  Run it with `uv run python fix-process/normalization/data/probe_normalization.py`.
- **Scalars.** The scalar results below come from calling `extract_scalar_candidates` directly.
- **Not done yet.** Nothing was checked against the live bank pages or the `tariff_rt`
  database. Phase 0 records the live baseline.

"Confirmed" means the probe (or a direct call) produced the wrong output shown. "Code" means
the finding was reasoned from the code but not reproduced.

---

## Summary

| ID | Problem | Severity | Evidence | Status |
|---|---|---|---|---|
| N1 | Row-header and bold-first-row tables lose data rows | **critical** | confirmed | proposed |
| N2 | Section rows inside a table become notes; dedup then drops real rows | **critical** | confirmed | proposed (Q2) |
| N3 | Notes that start with a number lose it; footnote markers left out of evidence | **high** | confirmed | proposed |
| N4 | Text directly inside a `div` produces no block (accordion panels) | **high** | confirmed | proposed |
| N5 | A current PDF can be skipped as historical because of another link's text | **high** | code | proposed (Q4) |
| N6 | Text runs together (headings in cards, table cells), creating false numbers | **high** | confirmed | proposed |
| N7 | Heading path carries over into later accordions and sections | high | confirmed | proposed |
| N8 | Nested tables and nested lists are duplicated or misplaced | medium | confirmed | proposed |
| N9 | Single-column tables have no data rows | medium | confirmed | proposed |
| N10 | Table title is also added as a note | medium | confirmed | proposed |
| N11 | Dates are parsed as number ranges and the real dates are lost | medium | confirmed | proposed |
| N12 | `0,125%` read as 125%; a line break inside a number drops the whole match | medium | confirmed | proposed |
| N13 | List-item pattern misreads decimals and dates; list merge rules are narrow | medium | confirmed | proposed |
| N14 | `dt`/`dd` pairs are never joined into key/value fields | medium | confirmed | proposed |
| N15 | Missing Gemini key reported as `PDF_MODEL_FAILED`; OCR fallback skipped | medium | code | proposed |
| N16 | Catch-all `except Exception` turns code bugs into model warnings | medium | code | proposed |
| N17 | PDF transcription cache key includes link metadata, so identical PDFs are paid for again | medium | code | **deferred** (user, 2026-09-26) |
| N18 | PDF page-coverage check can never fail; empty text pages raise no warning | medium | code | proposed |
| N19 | PDF evidence only points at the page, never the row or cell | medium | code | proposed |
| N20 | HTML page `quality_score` is always 1.0 | low | code | proposed (Q3) |
| N21 | `normalize()` has branches production never reaches | low | code | proposed |
| N22 | Network payload normalization is not needed | low | user decision | proposed (Q1) |
| N23 | Table blocks are matched to tables by position | low | code | proposed |
| N24 | `AMBIGUOUS_TABLE` is defined but never raised | low | code | proposed |
| N25 | PDF table cells: numbers extracted from uncleaned text; headers not normalized | low | code | proposed |
| N26 | PDF admission keywords use substring matching | low | code | proposed |
| N27 | Small points | low | mixed | proposed |
| N28 | OCR fill-in after Gemini has never run on real bank PDFs | low | data | **decided** (Q6: keep and widen) |
| — | Page id changes with the raw HTML bytes | — | — | **already fixed** (acquisition A1, `7e8292d`) |

---

## N1. Row-header and bold-first-row tables lose data rows

**Where.** [html_parser.py:335-348](../../app/services/html_parser.py#L335-L348),
[html_parser.py:704](../../app/services/html_parser.py#L704),
[table_normalizer.py:68](../../app/services/table_normalizer.py#L68),
[table_normalizer.py:220-227](../../app/services/table_normalizer.py#L220-L227).

**What happens.**
- `_looks_like_header_row` says a row is a header row if *any* cell is a `<th>` or has a
  `scope` attribute, including `scope="row"`. It also says so if every cell is wholly bold.
- The parser then marks *every* cell in that row `is_header=True`.
- The normalizer takes any all-header row as the header until a data row has been accepted.
  It does not check whether headers are already set, so each new header-like row replaces the
  last.

**Confirmed.**
- `<tr><th scope="row">Interest rate</th><td>12%</td></tr><tr><th scope="row">Term</th><td>60 months</td></tr>`
  → `headers=('Term', '60 months')`, **no rows**. Both values are gone.
- A first data row with every cell in `<strong>` → `headers=('Rate', '12%')`.
- Two header rows (`Term | Rate` over `AMD | USD`) → `headers=('Term', 'AMD', 'USD')`, and
  `Rate` is lost.

**Fix.**
- Mark a cell as a header only when it is a `<th>` or sits in a `<thead>`. Record
  `scope="row"` as a row header, not a column header (a new `TableCellArtifact.scope` field,
  or `is_row_header`).
- A row is a column-header row only when all its direct cells are column headers. A row whose
  first cell is a row header and whose other cells are `<td>` is data.
- Drop the "all bold" rule, or apply it only to the first row, when no `<th>` exists anywhere in the
  table, and the row has no numbers.
- Stacked header rows: combine them per column (`Rate / AMD`, `Rate / USD`) instead of
  replacing the earlier row. Stop header detection at the first data row.

## N2. Section rows inside a table become notes; dedup then drops real rows

**Where.** [table_normalizer.py:59-74](../../app/services/table_normalizer.py#L59-L74).

**What happens.**
- A row with one full-width cell is a title if it comes before any data, and a note otherwise.
- In tariff tables, a full-width row after the header is almost always a section label
  (`AMD loans`, `USD loans`), not a footnote.
- Deduplication compares whole rows across the entire table. Once the section labels are
  gone, identical rows from different sections look like duplicates.

**Confirmed.** `Item | Value`, `AMD loans`, `Fee | 0%`, `USD loans`, `Fee | 0%`, `Rate | 9%` →
rows `Fee | 0%` and `Rate | 9%`; notes `AMD loans` and `USD loans`. The USD fee row is gone,
and nothing says which section `Rate | 9%` belongs to.

**Fix.**
- Treat a full-width row between data rows as a section label unless it looks like a note:
  it starts with a footnote marker (`*`, `¹`, `1)`), or it is long running text. Let the
  label apply to every row after it until the next one.
- Store the label on each row (see Q2) and include it in the row's evidence text.
- Deduplicate only *adjacent* identical rows within the same section, and log each drop.

## N3. Notes that start with a number lose it; markers left out of evidence

**Where.** [table_normalizer.py:19-22](../../app/services/table_normalizer.py#L19-L22)
(`_NOTE_MARKER_RE`), [extraction_evidence.py:65-75](../../app/services/extraction_evidence.py#L65-L75).

**What happens.** The marker pattern accepts any run of leading digits followed by optional
`.` or `)` and optional space. Every note that starts with a number is split.

**Confirmed.** `5 000 000 AMD is the maximum amount for unsecured loans` → marker `5`, text
`000 000 AMD is the maximum amount…`. Evidence is built from `note.text`, so the model sees
the wrong amount.

**Second problem.** Real markers (`¹ Fixed for the first year`) are stored in `note.marker`,
but evidence content is only `note.text`. The row still says `12%¹`, so the model can't link
the footnote to the value.

**Fix.**
- Accept a digit marker only when it is short (1–2 digits) and followed by `)` or `.` and a
  space, or when it is a superscript digit or `*`, `†`, `‡`. Never split when the rest starts
  with a digit, `%`, or a currency.
- Put the marker back in the evidence content (`¹ Fixed for the first year`).

## N4. Text directly inside a `div` produces no block

**Where.** [html_parser.py:23-25](../../app/services/html_parser.py#L23-L25) (`_BLOCK_TAGS`).

**What happens.** Blocks come only from headings, `p`, `li`, `dt`, `dd`, `details`, tables,
accordion titles and cards. Text sitting directly in a `div` or `span` belongs to none of these,
so it is dropped.

**Confirmed.** `<div class="accordion-title">Fees</div><div class="accordion-content">Service fee 1% of loan amount</div>`
→ one block, `Fees`. The fee is gone.

**Not yet checked live.** The acquisition survey shows the bank pages render real content,
but not whether any of it is bare text in a `div`. Phase 0 measures it.

**Fix.** After the normal pass, collect text nodes that no block covers. Group each run by its
nearest block-level ancestor (`div`, `section`, `article`, accordion panel, `td` outside a
table), and emit one paragraph block per ancestor. Keep site-chrome detection so these don't
bring back the header and footer.

## N5. A current PDF can be skipped as historical because of another link's text

**Where.** [acquisition.py:327-335](../../app/services/acquisition.py#L327-L335)
(`_document_origin`), [pdf_admission.py:66-82](../../app/services/pdf_admission.py#L66-L82).

**What happens.**
- `nearby_text` is the whole text (up to 5,000 characters) of the first block that contains
  the link.
- When links sit in a table or list container, every PDF in it gets the same text. For a
  table, that is the whole table (and see N6: often without spaces between cells).
- Admission takes date ranges and "archive" or "previous terms" words from that shared text.
- Example: a table lists `01.01.2023–31.12.2023 · archived.pdf` and `from 01.03.2025 · current.pdf`.
  The only complete range has ended, so both PDFs are `historical`. With
  `skip_historical=True` (the default), the current one is skipped.
- A skip is not a warning. The only trace is `pdf_admission` in the audit report.

**Fix.**
- Build the context from the link's own table row, list item or paragraph: the nearest `tr`,
  `li`, `p` or `dd` around the anchor, then the block. Cap it at a few hundred characters.
- Add a `PDF_SKIPPED_HISTORICAL` warning (and `PDF_SKIPPED_IRRELEVANT`) with the matched
  basis, so skips appear in the run report.
- Prove the skips are right (Q4). Every PDF link on every seed is labelled by hand as
  `current`, `historical`, `future` or `irrelevant` (Phase 0). Admission must reproduce those
  labels:
  - **zero** current or future PDFs skipped: a hard gate in the tests;
  - every mismatch listed.

  `skip_historical` stays `True` only while the gate passes. The labelled set becomes a
  regression test.

## N6. Text runs together, creating false numbers

**Where.** [html_parser.py:623](../../app/services/html_parser.py#L623) (`_structured_text`).

**What happens.** Line breaks are added only after `p`, `div`, `section` and `article`. Headings,
table cells, table rows, `dt`/`dd` and `li` outside a list get nothing. When the HTML has no
whitespace between tags, their text runs together.

**Confirmed.**
- Card `<h3>Consumer loan</h3><p>Up to 5 000 000 AMD</p>` → text and `fields.title` are both
  `Consumer loanUp to 5 000 000 AMD`.
- Table block `Term | Amount / 12 | 500 000 AMD` → `TermAmount12500 000 AMD`; the scalar
  parser reads **12,500,000 AMD**.
- `Term | Rate | AMD | USD / 12 months | …` → scalar `USD12` (12 USD).

**Where the merged text goes.**
- The table block's text and scalars.
- PDF `nearby_text` (N5).
- The evidence section label: [extraction_evidence.py:85-88](../../app/services/extraction_evidence.py#L85-L88)
  uses the table block's first line, which for HTML with no whitespace between tags is the
  whole table. Every row's evidence then carries the whole table as its section.

**Fix.**
- Add a line break after headings, `tr`, `li`, `dt`, `dd`, `caption`, and `table`. Add a separator
  (` | `) between `td`/`th` cells.
- For a table's section label, use the heading path plus the table's caption or title. Don't
  use the table block's text.

## N7. Heading path carries over into later accordions and sections

**Where.** [html_parser.py:191](../../app/services/html_parser.py#L191) and the `headings`
stack in `_blocks_and_tables`.

**What happens.** The heading stack follows document order and is never reset when a container
ends. A heading inside one accordion panel stays in the path of everything after it until a
heading of the same or higher level appears.

**Confirmed.** Accordion 1 (`Mortgage`) has `<h4>Mortgage rates</h4>` and `Rate 10%`.
Accordion 2 (`Consumer`) and its `Rate 18%` both get `heading_path=('Mortgage rates',)`.
That path is the evidence `section`, so a consumer-loan rate is labelled as a mortgage rate.

**Fix.**
- Scope headings to their container. When a heading sits inside an accordion panel, card,
  `details`, `section` or `article`, pop it when the walk leaves that container.
- Add the accordion or card title to the path of its children, since it *is* their heading.

## N8. Nested tables and nested lists are duplicated or misplaced

**Where.** [html_parser.py:318](../../app/services/html_parser.py#L318) (`find_all("tr")`),
[html_parser.py:135-142](../../app/services/html_parser.py#L135-L142).

**Confirmed.**
- A table inside a cell:
  - The outer table gets `Loan | AMD12%USD8%`.
  - Then it gets `AMD | 12%` and `USD | 8%` as its own rows, under `Product | Terms`.
  - The inner table is emitted again as `t2`.
- A `li` inside a `li`: the outer block contains the inner items and each inner item is its own
  block, so the same value appears twice.
- A `p` inside a `dd`: the value appears in the `dd` block and again as a paragraph.

**Fix.**
- Collect only the table's own rows: `thead`, `tbody` and `tfoot` children, and `tr` children of
  the table. Leave out rows of nested tables.
- A nested table stays its own table. The outer cell text shows a reference such as
  `[table t2]` instead of the inner text.
- Skip a `li` whose parent list sits inside another `li`. Skip `p` inside `dd` and `dt`, as is
  already done for `li` and `details`.

## N9. Single-column tables have no data rows

**Where.** [table_normalizer.py:216-217](../../app/services/table_normalizer.py#L216-L217).

**Confirmed.** `Loan conditions / Rate 12% / Term up to 60 months` → title `Loan conditions`,
no rows, three notes (the title appears twice; see N10).

**Fix.** When the meaningful width is 1, don't use the full-width title/note rule. Use a
`<th>` or caption as the title, and make every other cell a row.

## N10. Table title is also added as a note

**Where.** [html_parser.py:410](../../app/services/html_parser.py#L410),
[table_normalizer.py:45](../../app/services/table_normalizer.py#L45),
[table_normalizer.py:59-66](../../app/services/table_normalizer.py#L59-L66).

**What happens.** The parser turns the first full-width row into `table.title`. The normalizer
rebuilds the table from the raw cells, sees the same row, and since a title already exists,
adds it as a note.

**Confirmed.** `title='Consumer loan tariffs'` plus note `Consumer loan tariffs`.

**Second problem.** `table.title or table.caption` drops the caption whenever a title exists.

**Fix.** One owner for table structure: the normalizer decides title, headers, sections and
notes from the cells. The parser passes caption and context title only (drop its
`title`/`headers`/`rows`/`notes` guessing, or stop reading them). Keep both caption and title.

## N11. Dates are parsed as number ranges

**Where.** [scalar_normalizer.py:112-126](../../app/services/scalar_normalizer.py#L112-L126).

**Confirmed.**
```
'Effective 2024-03-01'           -> range 2024..3          (date lost)
'Valid 01.03.2024 - 31.12.2024'  -> range 3.2024..31.12    (both dates lost)
```
Ranges are matched before dates, and a date overlapping a range is then discarded. Nothing
checks that the minimum is less than or equal to the maximum.

**Impact today.** Small: scalars only feed "has numbers" signals in
[discovery_prefilter.py:140](../../app/services/discovery_prefilter.py#L140) and block ranking.
Any later reader would get wrong values.

**Fix.** Match dates first. Add a date-range kind (or two dates) for `date – date`. Reject
numeric ranges where the minimum exceeds the maximum.

## N12. `0,125%` read as 125%; a line break inside a number drops the whole match

**Where.** [scalar_normalizer.py:9](../../app/services/scalar_normalizer.py#L9) (`_NUMBER`),
[scalar_normalizer.py:202-214](../../app/services/scalar_normalizer.py#L202-L214) (`_decimal`).

**Confirmed.**
- `"0,125%"` → **125%**. `_decimal` treats a comma followed by exactly three digits as a
  thousands separator.
- `"Term 12\n500 000 AMD"` → **nothing**. `[\s,]` inside a number accepts a line break, so the
  match is `12\n500 000`. `_decimal` removes only spaces, fails on the line break, and the
  whole match is dropped, including `500 000 AMD`.

**Fix.** Allow only spaces and no-break spaces inside a number, never a line break. Treat
`0,ddd` as a decimal. Tests for `1,000`, `1 000,50`, `0,125`, `12,5%`.

## N13. List-item pattern misreads decimals and dates; list merge rules are narrow

**Where.** [table_normalizer.py:18](../../app/services/table_normalizer.py#L18) (`_LIST_ITEM_RE`),
[table_normalizer.py:266-284](../../app/services/table_normalizer.py#L266-L284).

**Confirmed.** The pattern `\d+[.)]\s*` doesn't require a space after the marker.
`12.5% annual` → list item `5% annual`. `01.03.2025` → `03.2025`.

**List continuation.**
- A row is merged into the previous row's *last* cell when every other cell is carried from
  a rowspan and both last cells hold list items. This was written for one layout
  (`Section | Item | Terms`, where only the last column holds lists). A list in any other
  column is never merged.
- Deduplication runs before the merge, so a continuation row that matches an earlier row is
  dropped instead of merged.

**Fix.**
- Require whitespace after a numbered marker, and don't treat it as a marker when the next
  character is a digit.
- Merge per column: merge into column *k* when every other cell is carried and both cells in
  column *k* are lists.
- Run the merge check before deduplication.

## N14. `dt`/`dd` pairs are never joined

**Where.** [block_normalizer.py:28-31](../../app/services/block_normalizer.py#L28-L31)
(via `normalize_block`), [html_parser.py:139](../../app/services/html_parser.py#L139).

**Confirmed.** `<dl><dt>Interest rate</dt><dd>12%</dd></dl>` → two `key_value` blocks,
`Interest rate` and `12%`, both with empty `fields`. Fields are filled only when one element
contains `key: value`.

**Fix.** Emit one `key_value` block per `dt` plus its following `dd` elements, with
`fields={"key", "value"}` and both source refs. The same for two-column `div` rows with
label/value classes only if Phase 0 shows the bank uses them.

## N15. Missing Gemini key reported as `PDF_MODEL_FAILED`; OCR fallback skipped

**Where.** [pdf_extraction.py:433](../../app/services/pdf_extraction.py#L433),
[normalization.py:136-149](../../app/services/normalization.py#L136-L149).

**What happens.**
- A missing key raises `RuntimeError` before the model loop.
- `normalize()` catches it and records `PDF_MODEL_FAILED`, although `PDF_MODEL_REQUIRED`
  exists for this case.
- `_ocr_only` never runs, although it could recover scanned pages without a key.

**Fix.** Try `_ocr_only` first. If it recovers nothing, raise a specific
`PdfModelUnavailable` exception and map it to `PDF_MODEL_REQUIRED`.

## N16. Catch-all `except Exception` turns code bugs into model warnings

**Where.** [normalization.py:140](../../app/services/normalization.py#L140).

**What happens.** Any bug in the PDF branch (a validation error, a mapping mistake, a database
error in the cache lookup) becomes a `PDF_MODEL_FAILED` warning, and the run continues.
`NORMALIZATION_FAILED` is almost never raised, so a broken PDF branch looks like a flaky model.

**Fix.**
- Give the extractor its own exception hierarchy: `PdfModelUnavailable`,
  `PdfTranscriptionFailed` (all models failed, carrying the last cause).
- Catch only those in `normalize()`. Let everything else fail the stage as
  `NORMALIZATION_FAILED`.
- Also check that transport errors (timeouts, connection errors) reach the model fallback loop.
  Today it catches only `APIError`, `RuntimeError` and `ValueError`
  ([pdf_extraction.py:490](../../app/services/pdf_extraction.py#L490)).

## N17. PDF transcription cache key includes link metadata

**Where.** [pdf_extraction.py:155-165](../../app/services/pdf_extraction.py#L155-L165).

**What happens.**
- The cache fingerprint includes the whole admission result:
  - `temporal_status`, which depends on today's date;
  - keywords matched in `nearby_text`;
  - the origin heading.
- None of it goes into the prompt. The prompt uses only the page count and input mode.
- Identical PDF bytes are transcribed and paid for again when:
  - a nearby heading or sibling link changes;
  - a future-dated PDF becomes current;
  - the same PDF is linked from two pages with different surrounding text.

**Fix.** Fingerprint = PDF hash + schema version + prompt version + input-probe result.

**One-time cost.** Existing cache rows were written under the old fingerprint, so every PDF
is transcribed once more after this change. Every later fix to N5 or N26 is then free for
the cache.

**Status: deferred.** Not part of this round. While the old fingerprint stays, the N5 and N26
fixes change the admission result, so every PDF whose admission changes is transcribed once
more on the first run after deploy (see Q5).

## N18. PDF page-coverage check can never fail

**Where.** [gemini_pdf_extractor.py:205-253](../../app/services/gemini_pdf_extractor.py#L205-L253),
[pdf_extraction.py:634-643](../../app/services/pdf_extraction.py#L634-L643).

**What happens.**
- `_to_domain_response` creates an entry for every page before `_validate_response` runs, so
  the check always sees full coverage.
- A page Gemini skipped looks the same as an empty page.
- OCR fills only image-only pages. A page where the probe found a text layer but Gemini returned
  nothing raises no warning; only `quality_score` drops.

**Fix.** After transcription, compare with the probe. For each page with
`native_text_characters` above the threshold and no content, add a `PDF_PAGE_EMPTY` warning
naming the page. Remove the check that can never fail, or change it to count pages the model
actually mentioned.

## N19. PDF evidence only points at the page

**Where.** [pdf_extraction.py:705-740](../../app/services/pdf_extraction.py#L705-L740).

**What happens.** Every PDF table cell's source ref is the table, and every table's locator is
the page. HTML evidence goes down to the cell. A reviewer checking a PDF value has to scan the
whole page.

**Fix.** Give each PDF row and cell its own `source_item_id` (`…:table:0:row:3:cell:1`). Add
`table_index`, `row_index` and `column_index` to the locator if `SourceLocator` can take them
without a migration; otherwise keep them in the id only.

## N20. HTML page `quality_score` is always 1.0

**Where.** [normalization.py:68](../../app/services/normalization.py#L68).

**What happens.** Every HTML page claims perfect quality. PDFs use "share of pages with
content". The score is stored in `knowledge_documents` and `knowledge_chunks`, shown in
retrieval results and averaged in [run_metrics.py:307](../../app/services/run_metrics.py#L307).
Nothing makes a decision on it, so the harm is misleading reports and averages.

**Fix (Q3).** Measure the score against a record of what each page should contain.
1. **Ground truth (Phase 0).** For each of the 13 seeds, read the rendered page and record
   what normalization should produce:
   - the tables, with their titles, headers, sections and row counts;
   - the key values (rates, amounts, terms, fees) and where they appear;
   - accordion and card sections, and `dl` pairs;
   - PDF links.

   Save it as `data/seed-ground-truth.json`.
2. **Rules.** From that record, write down the structural checks that separate a good bundle
   from a bad one. Likely candidates:
   - share of expected tables found, with correct headers;
   - share of expected rows kept;
   - share of key values present verbatim in some block or cell;
   - no invented headers;
   - no text that no block covers;
   - no merged text across element boundaries.

   Each check needs to be one that can be computed without the ground truth at run time.
3. **Confirm the rules** before implementing (see Q3).
4. **Score** = the agreed checks, computed per page at normalization time, in `[0, 1]`. The
   ground truth checks that the score is low on the probe's bad cases and high on the fixed
   bundles.

## N21. `normalize()` has branches production never reaches

**Where.** [normalization.py:104-113](../../app/services/normalization.py#L104-L113) (no artifact
reader) and [normalization.py:126-135](../../app/services/normalization.py#L126-L135) (no PDF
extractor).

**What happens.** [runtime.py:147-158](../../app/runtime.py#L147-L158) always passes both. The
`None` branches exist only for tests that construct `StructuralNormalizationService()` with no
arguments.

**Fix.** Make both dependencies required. Update the three tests that build the service without
them to pass fakes.

## N22. Network payload normalization is not needed

**Where.** [normalization.py:152-158](../../app/services/normalization.py#L152-L158),
[api_payload_normalizer.py](../../app/services/api_payload_normalizer.py).

**What happens.** JSON payloads captured by the browser become extra documents with
`quality_score=1.0` and their own `INVALID_JSON` warning. The project doesn't use them.

**Fix (Q1: everywhere).**
- Remove payload normalization: the module, its test, the loop and `INVALID_JSON`.
- Remove payloads from the rest of the project as well:
  - capture in the browser renderer;
  - the config settings;
  - `PageArtifact.network_payloads`;
  - the input to the acquisition content hash;
  - the tests that build payloads.
- The acquisition content hash changes once. Acquisition item A10 (payload cap race) goes
  away. Update the acquisition plan to say so.

## N23. Table blocks are matched to tables by position

**Where.** [normalization.py:45-50](../../app/services/normalization.py#L45-L50) and the same
pattern in the parser's `_markdown` ([html_parser.py:819](../../app/services/html_parser.py#L819)).

**What happens.** The n-th table block is assumed to be the n-th table. That holds today because
the parser creates both together. Any future filtering of one but not the other would silently
link every later table to the wrong block.

**Fix.** Add `table_id` to `ContentBlock` in the parser and read it directly.

## N24. `AMBIGUOUS_TABLE` is defined but never raised

**Where.** [table_normalizer.py:91-110](../../app/services/table_normalizer.py#L91-L110).

**What happens.** When no header row is found, the normalizer invents headers
(`Section / Item / Terms`, `Column N`) and says nothing. Guessed headers are exactly when a
reviewer needs a warning.

**Fix.** Raise `AMBIGUOUS_TABLE` (with table id and reason) when headers are invented, when a
section or duplicate row is dropped, and when a full-width row can't be classified. This needs
`normalize_table` to return warnings alongside the table.

## N25. PDF table cells: numbers from uncleaned text; headers not normalized

**Where.** [pdf_extraction.py:715](../../app/services/pdf_extraction.py#L715),
[pdf_extraction.py:677-679](../../app/services/pdf_extraction.py#L677-L679),
[pdf_extraction.py:724-727](../../app/services/pdf_extraction.py#L724-L727).

**What happens.**
- Scalars are extracted from the raw cell, while `text` is cleaned. Everywhere else the order is
  clean then extract.
- PDF headers, table title and `heading_path` skip `normalize_text`, unlike the HTML path.

**Fix.** Extract from the cleaned text. Normalize headers, title and heading path.

## N26. PDF admission keywords use substring matching

**Where.** [pdf_admission.py:78-80](../../app/services/pdf_admission.py#L78-L80).

**What happens.** `atm` matches inside "treatment", `fee` inside "feedback". It rarely matters,
because any relevant term overrides; a PDF can only be wrongly skipped if its metadata has no
relevant term at all.

**Fix.** Match Latin terms on word boundaries. Match Armenian terms as word *starts*, since they
inflect (`վարկ`, `վարկի`, `վարկային`).

## N27. Small points

- **Image alt text is ignored.** A ✓ or ✗ icon in a tariff cell gives an empty cell. Use `alt`
  (or `title`) when an image is the only content of a cell.
- **`display: contents` is treated as hidden.** Such an element has no layout box, so
  [browser_renderer.py:262-280](../../app/services/browser_renderer.py#L262-L280) marks it
  hidden, and the parser then hides everything inside it. This is acquisition code; fix it
  there if Phase 0 finds any.
- **`_ocr_memo` grows for the life of the worker.** Bound it (LRU, a few hundred pages).
- **`â€¢` in `_LIST_ITEM_RE`** is a mis-decoded bullet. It points to an encoding problem
  upstream that was worked around instead of fixed. Find where the text is decoded, then drop
  the workaround.

## N28. OCR fill-in after Gemini has never run on real bank PDFs

This is the "is this path even reachable?" question: in the PDF flow, after `_normalize`,
"Any image-only pages left empty by Gemini? → yes → Tesseract".

**Where.** [pdf_extraction.py:188-203](../../app/services/pdf_extraction.py#L188-L203)
(`_pages_needing_ocr`), [pdf_extraction.py:309-335](../../app/services/pdf_extraction.py#L309-L335)
(`_apply_ocr`), [pdf_input_probe.py:22-29](../../app/services/pdf_input_probe.py#L22-L29).

**When it runs.** All three must hold:
- the probe calls the page `image_only`: under 20 characters of text layer, and at least one
  embedded image;
- Gemini returned nothing for that page;
- OCR is enabled, Tesseract is installed and the rasterizer is available. All three are true
  in Docker by default.

**Reachable in code: yes.** [test_ocr_fallback.py:197](../../tests/unit/test_ocr_fallback.py#L197)
covers it.

**In practice: it has never run.**
- **No image-only pages.** All 97 distinct bank PDFs stored on this machine were probed
  (end-to-end runs and acquisition temp folders; test fakes excluded). They have 360 pages:
  214 machine-readable, 145 mixed, 1 unknown, **0 image-only**.
- **No empty pages.** `tariff_rt.pdf_extraction_cache` holds 10 PDFs and 45 pages, and
  **0** of those pages came back empty from Gemini.
- **No OCR documents.** No PDF document in `tariff_rt` or `tariff_monitor` has an OCR
  extraction method.
- **Why.** Gemini gets the whole PDF and sees every page as an image. A scanned page is read
  by Gemini itself, so it is almost never left empty.

**Gaps in the trigger.**
- An `unknown` page has no text layer and no embedded image, for example text drawn as
  vector shapes. It is never sent to OCR, even when Gemini leaves it empty. There is one such
  page in the stored PDFs.
- A page with a text layer that Gemini leaves empty gets neither OCR nor a warning. That is
  covered by N18.
- When the branch does run, nothing counts it in the run report, so there's no way to tell
  that it ran.

**Fix (Q6: decided, keep and widen).**
- Keep it as a cheap, tested safety net for scanned PDFs.
- Send any page that is still empty after Gemini and has no usable text layer to OCR, whether
  it is `image_only` or `unknown`.
- Add an `ocr_pages` count to the run report.

The alternative was to delete the fill-in branch and keep OCR only for when every model has
failed (`_ocr_only`, N15). It was rejected on 2026-09-26.

## Checked, no change needed

- **A date range beats a historical keyword.** A link in an "archive" section whose text has a
  range covering today is `current`. An explicit range is stronger evidence than a section
  word. Keep it; N5 makes the range come from the link's own row.
- **A PDF titled only in Armenian, with no `վարկ` or `հիփոթեք`, is `ambiguous`.** That is safe:
  ambiguous PDFs are still transcribed.
- **Empty PDF documents that are failures, not skips.** `ARTIFACT_UNAVAILABLE`,
  `PDF_MODEL_REQUIRED` and `PDF_MODEL_FAILED` each carry a warning and their own
  `extraction_method`; `pdf_skipped` is the only deliberate one. After N5, skips get warnings
  too, so the run report shows both.
- **Rows with no direct text of their own are skipped.** That is correct: they hold only values
  carried from rowspans, and the row above already has them.

---

## Decisions

| # | Question | Answer | Status | Affects |
|---|---|---|---|---|
| Q1 | Remove network payloads only from normalization, or everywhere? | **Everywhere**: capture, config, domain field, content-hash input, tests. The completeness floor gains a text-only rule (≥ 3000 main characters with no table or PDF link), because the diaspora page passed only on payloads. | decided, **done** | N22, Phase 5 |
| Q2 | How should a section label be stored on table rows? | **A row field**: `section: str \| None` on `NormalizedTableRow`, put into the evidence text as `Section: …`. | decided | N2, Phase 2 |
| Q3 | What should HTML `quality_score` be? | **Measured against the seed baseline**: the share of the page's recorded structure (tables, titles, header rows, sections, row labels, footnotes, label blocks; no tariff values) still present. | decided, **done** | N20 |
| Q4 | Keep `skip_historical=True` after N5? | **Make sure the right PDFs are skipped**: 91 PDFs labelled by hand and accepted by the user; a 114-case gate test; skipping stays on. | decided, **done** | N5, Phase 4 |
| Q5 | Accept the one-time costs on the first run after deploy? | **No Gemini tokens for validation**: normalization needs none, so Phase 6 validates live without Gemini (`NoPdfExtractor`). The one-time re-extraction cost still applies to the first production run. | decided | Phase 6 |
| Q6 | Keep the OCR fill-in branch (widened to `unknown` pages, counted in the run report), or delete it? | **Keep and widen**: empty `image_only` and `unknown` pages go to OCR; OCR pages counted in the run report. | decided | N28, Phase 4 |

**What Q5 means.**
- Most fixes change evidence text, so evidence ids change and every page is extracted again
  once.
- The N5 and N26 fixes change the admission result, which is part of the PDF cache key while
  N17 is deferred. Every PDF whose admission changes is transcribed once more.
- Values that were lost or wrong before will now be found. That shows up as tariff changes and
  may open reviews, even though the bank changed nothing.

---

## Implementation phases

Order: the probe fixtures become tests first, then parser structure, then tables (which depend
on the parser's cell and header marks), then scalars, then PDFs, then the bundle and evidence.
Each phase ends green on `uv run pytest tests/unit tests/integration`.

### Phase 0: Preparation

- [x] Create branch `fix/normalization` from `integration/process-fixes`.
- [x] Run `uv run pytest tests/unit tests/integration` and record the baseline (count, known
      failures).
- [x] Turn every case in [data/probe_normalization.py](data/probe_normalization.py) into a unit
      test with the *correct* expected output, marked `xfail(strict=True)`. Each fix removes
      its `xfail`.
- [x] Record a live baseline without Gemini: for all 13 seeds, run acquisition (PDF downloads
      off), then HTML normalization, and save per seed to `data/normalization-survey-before.json`:
      - block count;
      - table count, rows and notes;
      - invented headers;
      - bare `div` text that no block covers (N4);
      - `dl`, nested table, `scope="row"` and `display: contents` occurrences.
- [x] **Seed ground truth (Q3).** For each seed, read the rendered page and record what
      normalization should produce in `data/seed-ground-truth.json`:
      - tables, with their titles, headers, sections and row counts;
      - key values (rates, amounts, terms, fees) and where they sit;
      - accordion and card sections, and `dl` pairs.
- [x] **PDF labels (Q4).** Download every PDF link on every seed (no Gemini). Label each one
      `current`, `historical`, `future` or `irrelevant` from its content and its place on
      the page. Record in `data/seed-pdf-labels.json`, with the reason for each label.
- [x] Run today's admission against the labels and record every mismatch. This measures N5 and
      N26 on real data.
- [x] **Confirm with the user:** the ground truth, the PDF labels, and the proposed
      quality-score rules (see [N20](#n20-html-page-quality_score-is-always-10)).
- [x] Q6 decided: keep and widen the OCR fill-in.
- [x] Get an answer to Q5.

#### Phase 0 notes (2026-09-26)

**State: done, except the two confirmations**, which don't block Phases 1–3. They block the
N20 quality score and the final sign-off of the Q4 gate.

**Test baseline** (`uv run pytest tests/unit tests/integration`, before any fix): 737 passed,
42 skipped, 1 failed, 3 errors. All four need a Gemini key and fail the same way on the parent
branch:
- `test_agent.py::test_agent_stream` fails;
- the three `test_server_e2e.py` tests error.

Treat them as environmental from here on.

**Regression tests.** [tests/unit/test_normalization_fixes.py](../../tests/unit/test_normalization_fixes.py)
has 21 `xfail(strict=True)` tests, one per confirmed case (N1–N4 and N6–N14). Each asserts the
*correct* output. `strict` makes a test fail as soon as a fix makes it pass, so every fix must
remove its marker.

**Survey tooling** ([survey/](survey/)). Everything runs offline from one live capture. No
Gemini is used, and the capture refuses to create a Gemini client.
- [capture_seeds.py](survey/capture_seeds.py): acquires all 13 seeds live, with PDF downloads
  on and a cap of 40. It saves each `PageArtifact` (rendered HTML included) and every PDF to
  `.cache/`, which is git-ignored (about 40 MB). Re-run it to refresh the capture; every other
  script reads the cache.
- [survey.py](survey/survey.py) `<label>`: structural counts per seed →
  `data/normalization-survey-<label>.json`.
- [dom_inventory.py](survey/dom_inventory.py): a plain BeautifulSoup dump of each page's tables,
  headings and text, used to write the ground truth.
- [check_ground_truth.py](survey/check_ground_truth.py) `<label>`: scores the current code
  against [data/seed-ground-truth.json](data/seed-ground-truth.json).
- [pdf_inventory.py](survey/pdf_inventory.py) and [check_pdf_labels.py](survey/check_pdf_labels.py)
  `<label>`: PDF context and admission against [data/seed-pdf-labels.json](data/seed-pdf-labels.json).
  The check rebuilds each PDF's link context with the current code, so it tests N5.

**What the live pages contain** ([data/normalization-survey-before.json](data/normalization-survey-before.json)):
- **Tables.** 35 tables and 923 rows. 24 tables have invented headers, but on these pages
  that is mostly correct: the terms tables really have no header row (the
  `Section | Item | Terms` layout).
- **Absent structures.** No nested tables, no `th[scope=row]`, no `dl`, and no `display:
  contents` symptoms. N8 (tables), N14 and the `display: contents` point are fixed for
  robustness only.
- **Nested lists.** There are 2,000 nested `li`, almost all in the site menus.
- **Uncovered text (N4, confirmed live).** 40 text nodes (2,678 characters) are in no block.
  Real content among them:
  - "Pledged property is subject to mandatory valuation… 13,…" (mortgage_online);
  - "The client will pay for the following services:" (commercial);
  - "Insurance Companies Cooperating with Ameriabank and Related Fees" (primary);
  - "Actual percentage rate" (renovation);
  - "Updated on 06.08.2026" (express, no-income).
- **Section rows (N2, confirmed live).** Sub-section rows ("Term and interest rate", "Term
  and interest rate in case of online refinancing") and product rows inside the shared
  "Express Home Mortgage Loan" table ("1. Express Home Purchase Loan (primary market)"
  through "4. …Renovation Loan") become notes. The construction and renovation rate rows
  are word for word the same, so the renovation rows are dropped as duplicates.
- **Footnotes.** The markers seen are `*`, `1`–`6` directly followed by an uppercase letter
  ("1These", "5This", "4 The"), and superscripts. The N3 marker rule must accept those and
  reject "5 000 000 AMD…".
- **Header rows (N1).** The credit-line card-type header row is bold, but has two empty
  trailing cells, so the "all bold" rule misses it. The overdraft one is detected.
- **Not a normalization bug.** Some tables have a column-header row in the middle of the body:
  "3.1. Currency | AMD | USD | EUR" and "Term | Refinancing | New loans". Rows below it get
  `Terms 1..3`, not the currency. The row itself is kept, so the evidence is there.
  Recorded, not fixed.

**Ground truth** ([data/seed-ground-truth.json](data/seed-ground-truth.json)):
- 348 checks over 13 seeds. Each is a table title, a header row, a label/value pair that must
  share a row, the section of that row, a footnote marker, or a block text.
- Three shared table templates (service fees, 2-column required documents, Express Home) are
  written once.
- **Before: 77 of 348 fail** ([data/ground-truth-check-before.json](data/ground-truth-check-before.json)):
  - sections (N2): about 60;
  - title repeated as note (N10): 5;
  - uncovered text (N4): 6;
  - credit-line header (N1): 1;
  - the four express tables not found, because their numbered first row became a note with
    marker `1.`.

**PDF labels** ([data/seed-pdf-labels.json](data/seed-pdf-labels.json)):
- 91 distinct PDFs: **27 current, 62 historical, 2 irrelevant**. The irrelevant ones are the
  website-profile terms, in English and Armenian.
- **Admission today** ([data/pdf-label-check-before.json](data/pdf-label-check-before.json)):
  - **Gate passes**: no current PDF is skipped.
  - 6 historical PDFs are still transcribed, because their context says "effective from
    24.10.2024 **till** 13.07.2025", and the date-range pattern knows `to`/`until`/`-`
    but not `till`.
  - Both irrelevant PDFs are transcribed.

  So on today's pages, N5's shared-context risk hasn't happened yet. Every PDF sits alone in
  its own `li`/`p`. The fix is still needed for tables with several PDF links.

**Open for the user.**
- Review the ground truth and the PDF labels.
- The quality-score rules will be proposed after Phase 2, when they can be measured on fixed
  and unfixed bundles.
- Q5 (one-time costs) is still open.

### Phase 1: HTML parser structure (N6, N4, N7, N8, N14, N23, N27 image alt)

- [x] N6: line breaks after headings, `tr`, `li`, `dt`, `dd`, `caption`, `table`; ` | `
      between cells. Test: card title and body split; table block text has no merged numbers.
- [x] N4: blocks for text that no block covers, grouped by nearest block-level ancestor, chrome
      excluded. Test: text-only accordion panel.
- [x] N7: scope headings to their container; accordion and card titles join their children's
      path. Test: two accordions, no carry-over.
- [x] N8: a table's own rows only; nested table referenced from the outer cell; skip nested
      `li`, `p` in `dd`/`dt`. Tests: nested table, nested list, `p` in `dd`.
- [x] N14: one `key_value` block per `dt` + `dd`, with key/value fields and both refs.
- [x] N23: `table_id` on `ContentBlock`; use it in `normalize()` and `_markdown`.
- [x] N27: image `alt`/`title` as cell text when the image is the only content.
- [x] Check `main_text` and the acquisition completeness floor still pass with the new blocks
      (`tests/unit/test_acquisition_completeness.py`).

#### Phase 1 notes (2026-09-26)

**State: done.** All items are implemented in
[html_parser.py](../../app/services/html_parser.py), plus two new optional `ContentBlock`
fields in [domain/acquisition.py](../../app/domain/acquisition.py).

**What changed**
- **N6.** `_structured_text` puts a line break around every block-level element (headings,
  `li`, `dt`/`dd`, `table`, `caption`, `div`, …), and ` | ` between the cells of a `tr`.
  A table block now reads `Term | Amount` / `12 | 500 000 AMD`, not
  `TermAmount12500 000 AMD`. HTML comments are skipped.
- **N4.** `div`, `section`, `article`, `main`, `aside`, `form`, `figure` and `figcaption`
  become paragraph blocks when they have text of their own outside child blocks.
  - The text is rendered with child blocks, lists, tables, controls and media left out
    (`_NOT_OWN_TEXT`).
  - A container inside an element whose block already covers it (`li`, `dt`, `dd`, `p`,
    `details`, `table`, `button`) is skipped.
  - These blocks are **not** registered as parents. Otherwise a wrapper `div` with one stray
    word would become the `parent_id` of everything inside it and change discovery grouping.
- **N7.** Each heading on the stack remembers the container that bounds it: the nearest
  `section`, `article`, `details`, `[role=tabpanel]`, accordion panel or card. It is dropped
  when the walk leaves that container.
  - Accordion titles enter the stack at level 0, bounded by their accordion, so they head
    their panel's blocks and nothing else.
  - On the bank pages the "Terms and conditions" `h2` shares its `section` with the tables,
    and the page `h1` is outside any section, so both stay where they belong.
  - Checked against the Phase 0 commit on four seeds: 26–47 blocks per seed changed path, and
    all the changes are corrections. Footer links lost "Terms and conditions > Construction
    loan"; hero cards lost "Loan calculator"; FAQ answers gained their question.
- **N8.** Table ids are assigned up front in document order (`table_refs`).
  - A table collects only its own rows (`tr` whose nearest `table` is itself).
  - A nested table appears in the outer cell as `[table tN]`.
  - `li` inside `li`, and `p` inside `dt`/`dd`, are not separate blocks.
- **N14.** A `dt` takes the visible `dd` siblings up to the next `dt`. The block text is
  `key: value`, and `ContentBlock.key_value = (key, value)`.
  [block_normalizer.py](../../app/services/block_normalizer.py) turns that into
  `fields={"key", "value"}`. Paired `dd`s are skipped. The block's locator points at the `dt`,
  and the `dd`s' link ids are merged in. A separate locator for the `dd` was not added: they
  are adjacent, and `SourceReference` takes one locator.
- **N23.** `ContentBlock.table_id`. Both
  [normalization.py](../../app/services/normalization.py) and the parser's `_markdown` read it.
  Artifacts stored before this change have no `table_id`, so normalization falls back to
  document order for them; the existing service test covers that path.
- **N27 (image alt).** A table cell whose text is empty takes its images' `alt`/`title`.

**Measured on the live capture**
([data/normalization-survey-phase1.json](data/normalization-survey-phase1.json)):
- Uncovered text: 40 nodes / 2,678 characters → **0**.
- Blocks: 1,982 → 2,054 (+72, the uncovered content).
- `main_chars` only grew, by 0.1–4.4% per seed. The completeness baseline fails on a drop,
  never on growth, so stored baselines stay valid.
- Ground truth: 77 → **70 failures**, all 7 fixed are uncovered-text blocks. The rest are
  table structure (Phase 2).

**Tests.** The 8 regression tests for N4, N6, N7, N8 and N14 are no longer `xfail`. There
are 3 new tests: image-only cell, table id after a skipped table, and container text not
being a parent. Suite: 748 passed. The only failures are the same 4 key-dependent ones as
the baseline.

**Follow-up fix (found by the Phase 2 PDF check).** At first, a container's own-text block
listed *every* link inside it. On mortgage_primary, a wrapper with one stray paragraph
("ATTENTION! YOUR FINANCIAL DATABASE…") became the "first block containing" all 8 PDF
links, so they got that paragraph as their link context: the N5 hazard. One more historical
PDF lost its date context. Now `_contained_link_ids` takes the same exclusions as the text,
so an own-text block claims only the links in its own text. The PDF check is back to
Phase 0 (gate pass, 6 historical transcribed), with a test.

**Knock-on effects for later phases**
- Page ids change, since they hash the parsed blocks.
- Block text changes, so evidence ids change. This is part of Q5's one-time cost.


### Phase 2: Table normalization (N1, N2, N3, N9, N10, N13, N24)

- [x] N10: the normalizer owns title, headers, sections and notes; the parser passes only
      caption and context title. Keep both caption and title.
- [x] N1: `<th>`/`<thead>` column headers only; `scope="row"` is a row header; drop or restrict
      the bold rule; combine stacked header rows; stop at the first data row.
      Tests: row-header table, bold first row, two header rows.
- [x] N2: full-width rows between data rows become section labels (per Q2); adjacent-only
      dedup within a section. Test: AMD/USD sections keep both fee rows.
- [x] N3: strict footnote markers; marker kept in evidence text. Tests: `5 000 000 AMD…` note
      unchanged; `¹ Fixed…` keeps its marker.
- [x] N9: single-column tables produce rows.
- [x] N13: numbered list marker needs whitespace and no following digit; per-column list merge;
      merge before dedup. Tests: `12.5% annual`, `01.03.2025`, list in column 2.
- [x] N24: `normalize_table` returns warnings; raise `AMBIGUOUS_TABLE` for invented headers,
      dropped rows and unclassified full-width rows. Carry them into the bundle warnings.

#### Phase 2 notes (2026-09-26)

**State: done.** The table normalizer is rewritten
([table_normalizer.py](../../app/services/table_normalizer.py)). The parser marks header
cells the HTML way, and there are new optional fields `TableCellArtifact.row_header`,
`TableCellArtifact.bold`, `TableArtifact.context_title` and `NormalizedTableRow.section`.

**What changed**
- **N10.** The normalizer owns title, headers, sections and notes, and no longer reads the
  parser's `headers` or `notes`.
  - The title joins the context title (or, for artifacts stored before this change, the
    parser's `title`), the caption, and the table's first full-width row.
  - A part is dropped only when a longer part contains it exactly (case-sensitive, leading
    numbering ignored). So "Express Home Purchase Loan (primary market)" gives way to
    "1. Express Home Purchase Loan (primary market)", while "Tariffs — Home Purchase Loan"
    keeps both parts.
  - The parser still computes its own title/headers/rows/notes, **only** for its Markdown
    artifact.
- **N1.**
  - **Parser:** `is_header` is `th` (not a row header) or anything in `thead`.
    `row_header` is `th[scope=row]`, or a `th` beside `td`s. The old "any `th` makes the
    whole row a header" rule is gone.
  - **Normalizer:** a header row is all column-header cells, at least two unless the table
    has one column. With no HTML header cells anywhere in the table, the first rows count
    when every non-empty cell is bold and the row has no numbers. That handles the
    credit-line card-type row: bold, with empty trailing cells, and it used to be missed.
  - Stacked header rows combine per column (`Rate / AMD`), and detection stops at the first
    data row.
- **N2.** A row whose single cell spans to the end is a *label* when the text reads like
  one: at most 100 characters after any leading numbering, no sentence punctuation, no
  numbers, no footnote marker, not a list item. There are two kinds:
  - **Column 0, full width:** a section, until the next one. The very first such row, before
    any data, is the table's own title.
  - **Column 1** (the item column), under a carried column-0 cell: a sub-section that ends
    when that carried cell ends. A single cell starting further right is a value under a
    carried item ("Fixed component 5% …"), never a label.

  `row.section` is `section > sub-section`. A label with no rows under it becomes a note.
  Deduplication now drops only a row identical to the row just above it in the same section,
  and reports it.
- **N3.** A footnote marker is:
  - superscript digits;
  - `*`, `†` or `‡`;
  - `1)`;
  - one or two digits directly followed by a capital letter (Latin, Armenian, Cyrillic,
    or an opening quote).

  "5 000 000 AMD…", "12 months…" and "1. Express…" have no marker.
- **Correction (made in Phase 5).** This phase's checklist was ticked for "marker kept in
  evidence text" (N3) and for Q2's "`Section: …` in the evidence text" (N2), but Phase 2
  only *stored* the marker and the section. Both reached the evidence text in Phase 5; see
  its notes.
- **N9.** A one-column table never uses the full-width title/note rule: a header cell is the
  header, and every other cell is a row.
- **N13.** List items need a bullet, or 1–2 digits + `.`/`)` + a space, so "12.5% annual",
  "01.03.2025" and "5.1.1.1." are no longer list items.
  - The list merge works on any column: one new cell, the other columns repeat the row above,
    and both cells are lists.
  - The merge runs before deduplication.
- **Carried spans.** A carried `colspan` cell is now blank in its extra columns, as a direct
  one always was.
- **N24.** `normalize_table_with_report()` returns the table plus its reasons: invented
  headers, and rows dropped as repeats. [normalization.py](../../app/services/normalization.py)
  turns them into one `AMBIGUOUS_TABLE` warning per table, with `source_id =
  page:<id>:<table id>`. `normalize_table()` still returns just the table.

**Measured on the live capture**
([survey](data/normalization-survey-phase2.json),
[ground truth](data/ground-truth-check-phase2.json)):
- **Ground truth: 70 → 0 failures out of 348.**
- **Sections produced:** exactly the expected ones and nothing else.
  - "1."–"4. Express Home … Loan" and "General requirements to loan facilities" in the shared
    Express table;
  - "Term and interest rate" and "… in case of online refinancing / refinance loans" in the
    main mortgage tables.
- **Notes:** 104 → 72, and **no note without a marker is left** (before, 12 were table titles
  or section labels).
- **Rows:** 923 → 900. The drop is bullet rows merged into their list, and sub-section rows
  that became sections. In the Express table, rows go up from 48 to 67, because the
  renovation rows are no longer dropped as duplicates of the construction rows.
- **No text lost:** checked per seed against the Phase 0 code. Every old cell's text appears
  in the new rows, sections, titles or notes. The "merged" cells the old code produced
  (numbered clauses 5.1.1–5.1.2 in one cell) came from the N13 bug and are now separate
  rows, as in the page.
- **Invented headers:** 23 tables. They are all genuinely header-less on these pages (the
  `Section | Item | Terms` layout, and 2-column key/value tables), and each now raises
  `AMBIGUOUS_TABLE`.
- **PDF gate:** unchanged (pass).

**Tests.** The 8 N1/N2/N3/N9/N10/N13 regression tests pass, and there are 13 new tests
(sub-section scope, value vs label, empty label → note, 7 marker cases, title joining,
the N24 warning end to end). Suite: 768 passed, with the same 4 key-dependent failures.

**Proposal for the quality score (N20, Q3), to confirm with the user**

Measured with [survey/quality_signals.py](survey/quality_signals.py) on the Phase 0 and
current code. Each rule can be computed from the page alone at normalization time:
1. **Text coverage.** The share of visible, non-chrome text characters that appear in some
   block, cell, title, section or note. Before: 0.957–1.0 (mortgage_online is lowest,
   because the valuation-fee paragraph was lost). After: 1.0.
2. **Table structure.** The share of tables with at least one data row. Invented
   `Section | Item | Terms` or `Column N` headers are **not** penalized: the ground truth
   shows 23 of 35 tables genuinely have no header row.
3. **Note hygiene.** The share of table notes that are real footnotes: they have a marker,
   or they read as sentences. A short, label-like note with no marker means a title or
   section was misfiled. Before: 12 such notes on 6 seeds. After: 0.
4. **Repeat rows.** Each row dropped as a repeat costs 0.02, up to 0.2.

Score = coverage × structure × note hygiene − repeat penalty, clamped to [0, 1], and 0 for
a page with no text. A "glued words" rule (text merged across elements) was tried and
dropped: it can't tell "loanUp" from "MyAmeria".


### Phase 3: Scalars (N11, N12)

- [x] N11: dates before ranges; date ranges as their own kind or two dates; reject
      minimum > maximum. Tests from the table in N11.
- [x] N12: no line breaks inside numbers; `0,ddd` is a decimal. Tests: `0,125%`,
      `Term 12\n500 000 AMD`, `1,000`, `1 000,50`, `12,5%`.
- [x] Check [discovery_prefilter.py](../../app/services/discovery_prefilter.py) ranking still
      behaves (it counts scalars).

#### Phase 3 notes (2026-09-26)

**State: done.** Changes are in [scalar_normalizer.py](../../app/services/scalar_normalizer.py).

**What changed**
- **N11.** Dates are matched before ranges. A `date – date` span gives two `DATE` scalars.
  The plan allowed a new date-range kind instead; two dates needed no model change.
  - "1 July 2026" (day before month name) is recognised too.
  - A numeric range with minimum > maximum is rejected, and its parts can still be read as
    single values.
  - Two-digit years ("01.10.24") are deliberately **not** read as dates: clause numbers
    like "1.1.10" would turn into dates.
- **N12.** Digit groups may be split by a space, no-break space, narrow no-break space or a
  comma, and never by a line break.
  - `_decimal` reads a single comma as a thousands separator only before exactly three
    digits with a non-zero integer part. So `1,000` → 1000, while `0,125` → 0.125 and
    `12,5` → 12.5.

**Measured on the live capture** (all blocks, against the Phase 0 code):
- **Dates:** 24 → 26. The new ones are "06.08.2026" and "01.07.2026", which N4 recovered.
- **Ranges:** 372 → 335. Every range that disappeared was false:
  - date fragments ("06.25 to 05.10" → 6.25..5.10);
  - a clause code ("72-03");
  - reversed amounts where "million" was cut off ("AMD 100,000 - AMD 20" → 100000..20).

  The new ranges are "13,000 - 30,000 AMD" (the valuation fee N4 recovered) and "2007-2023".
- **Not fixed.** "AMD 100,000 - AMD 20 million" is still not read as a range: the scalar
  parser has no "million"/"mln" multiplier. Scalars only feed discovery signals today, so
  this is noted rather than fixed.

**Tests.** The 5 N11/N12 regression tests pass (none left `xfail`), plus 5 new number and
date cases. The discovery prefilter tests pass unchanged. Suite: 751 unit tests passed.


### Phase 4: PDF admission and transcription (N5, N15, N16, N18, N19, N25, N26, N28)

- [x] N5: link context from the anchor's own `tr`/`li`/`p`/`dd`, capped; `PDF_SKIPPED_HISTORICAL`
      and `PDF_SKIPPED_IRRELEVANT` warnings. Test: the archived/current table example keeps
      `current.pdf`.
- [x] Q4 gate: a regression test built from `data/seed-pdf-labels.json`. Admission must skip
      no PDF labelled `current` or `future`. If the gate can't pass, stop and discuss before
      changing `skip_historical`.
- [x] N16: `PdfModelUnavailable` and `PdfTranscriptionFailed`; `normalize()` catches only those;
      transport errors reach the fallback loop. Test: a mapping bug fails the stage as
      `NORMALIZATION_FAILED`.
- [x] N15: no key → try OCR → otherwise `PDF_MODEL_REQUIRED`. Tests for both outcomes.
- [x] N18: `PDF_PAGE_EMPTY` for text-layer pages with no content; remove the check that can't
      fail.
- [x] N28 (per Q6): send empty `image_only` and `unknown` pages to OCR, and count OCR pages in
      the run report. Test: an empty `unknown` page is sent to OCR.
- [x] N19: row and cell ids for PDF tables in source refs.
- [x] N25: scalars from cleaned cell text; normalize PDF headers, title, heading path.
- [x] N26: word-boundary matching for Latin terms, word-start for Armenian.
- [x] N27: bound `_ocr_memo`.

#### Phase 4 notes (2026-09-26)

**State: done.** The only open point is the user's review of the PDF labels behind the Q4
gate. N17 stays deferred.

**What changed**
- **N5.** The parser records each link's `context_text`: the text of its nearest `tr`, `li`,
  `p`, `dd`, `dt` or heading, capped at 600 characters.
  `AcquisitionService._document_origin` uses it as the PDF's `nearby_text`, and falls back
  to the block text only when the link sits in none of those. Heading path and origin block
  are unchanged. Two new warning codes:
  - `PDF_SKIPPED_HISTORICAL`;
  - `PDF_SKIPPED_IRRELEVANT`.

  Each carries the admission basis in its message and lands in the manifest's
  `warning_codes`.
- **Q4 gate.**
  - [tests/unit/test_pdf_admission_gate.py](../../tests/unit/test_pdf_admission_gate.py)
    checks 114 labelled PDF occurrences: no `current` one may be skipped, and every
    `historical` one must be.
  - The inputs are in [tests/fixtures/pdf_admission_seed_labels.json](../../tests/fixtures/pdf_admission_seed_labels.json),
    rebuilt with [survey/export_pdf_gate_fixture.py](survey/export_pdf_gate_fixture.py).
  - `skip_historical` stays `True`: the gate passes.
- **N26.** Keywords match as words: English terms may take `s`/`es`, Armenian terms match as
  word starts (`վարկ` → `վարկային`), and path fragments keep their slashes. The date-range
  pattern also accepts "till" and "through". That one word is what left 6 superseded
  consumer-loan PDFs admitted.
- **N16.** A new hierarchy in [pdf_extraction.py](../../app/services/pdf_extraction.py):
  - `PdfExtractionError`, the base of three expected failures:
    - `PdfUnreadable`: the probe can't open the file; becomes `ARTIFACT_UNAVAILABLE`.
    - `PdfModelUnavailable`: becomes `PDF_MODEL_REQUIRED`.
    - `PdfTranscriptionFailed`: becomes `PDF_MODEL_FAILED`.
  - `normalize()` catches only `PdfExtractionError`. Anything else, including cache or
    database errors, fails the stage as `NORMALIZATION_FAILED`.
  - The model loop also treats `httpx.HTTPError`, `TimeoutError` and `ConnectionError` as
    model failures, so they reach the fallback models.
  - A cached response that doesn't fit the file is a cache miss, not an error.
- **N15.** With no key, `_ocr_only` is tried first, and only then is `PdfModelUnavailable`
  raised.
- **N18.** `empty_text_pages()`: pages the probe calls machine-readable or mixed that ended
  with no content. They raise `PDF_PAGE_EMPTY` with the page numbers. The old coverage check
  could never fail on a fresh response, so it now runs only on cached ones
  (`_covers_all_pages`).
- **N28 (Q6).** `_pages_needing_ocr` also takes `unknown` pages (no text layer and no image).
  Pages OCR filled raise `PDF_OCR_FILLED` with their numbers. `run_metrics` counts OCR per
  document, so a page filled inside a Gemini document was invisible before.
- **N19.** PDF table cells get their own `source_item_id`
  (`…:table:0:row:3:cell:1`). The locator is still the page: `SourceLocator` has no
  row/column fields, and adding them would need a migration.
- **N25.** Numbers are read from the cleaned cell text. PDF headers, title and heading path
  go through `normalize_text`.
- **N27.** The OCR memo is an LRU of 500 pages.

**Measured** ([data/pdf-label-check-phase4.json](data/pdf-label-check-phase4.json)):
- Gate: **pass**.
- Historical PDFs still transcribed: **6 → 0**. All 62 superseded PDFs are now skipped.
- Irrelevant PDFs transcribed: 2, unchanged. They are the website-profile terms, linked
  under "Consumer loan > Terms and conditions", so "loan" makes them relevant. Link metadata
  alone can't tell them apart.
- Ground truth: still 0/348.

**Tests.** There are 13 new tests in
[test_normalization_pdf_fixes.py](../../tests/unit/test_normalization_pdf_fixes.py), 3 new
ones in `test_ocr_fallback.py`, and the 114-case gate. Suite: 909 passed, with the same 4
key-dependent failures.

**Cost note (Q5).** N5 and N26 change the admission result for many PDFs, and admission is
part of the PDF cache key (N17 is deferred). Each such PDF is transcribed once more on the
first run after deploy. Six of them are now skipped, which saves their cost for good.


### Phase 5: Bundle and evidence (N20, N21, N22, N6 section label)

- [x] N6: table evidence section = heading path + caption/title, not the table block's text.
- [x] N20: implement the agreed quality-score rules (Q3), computed per page at normalization
      time. Test on the probe's bad cases (low score) and on the fixed seed bundles (high
      score).
- [x] N21: `artifact_reader` and `pdf_extractor` required; update the tests that build the
      service with no arguments.
- [x] N22: remove payload normalization, `INVALID_JSON` and its test.
- [x] N22 (Q1): remove payload capture from the browser renderer, the payload config settings,
      `PageArtifact.network_payloads`, the content-hash input, and the tests that build
      payloads. Mark acquisition item A10 as no longer applicable in
      [the acquisition plan](../acquisition/acquisition-fix-plan.md).
- [x] N27: find where the mis-decoded bullet comes from; fix the decoding and drop `â€¢`.
- [x] Update [docs/architecture.md](../../docs/architecture.md): new warning codes, the row
      section field, table ownership moved to the normalizer, payloads removed.

#### Phase 5 notes (2026-09-26)

**State: done except two items that need the user:**
- **N20 (quality score):** the rules are proposed in the Phase 2 notes and wait for
  confirmation.
- **N22 (Q1) acquisition half (payload capture):** blocked by a consequence found while
  doing it; see below.

**What changed**
- **Evidence** ([extraction_evidence.py](../../app/services/extraction_evidence.py)):
  - **N6.** A table's evidence `section` is its block's heading path plus the table title.
    It used to be the first line of the table block's flattened text: for HTML with no
    whitespace between tags that was the whole table, and otherwise usually the first
    header cell.
  - **N2 (Q2).** A row under an in-table section starts with `Section: <label>`.
  - **N3.** A note's evidence starts with its marker as the page shows it (`¹ Fixed for
    the first year`), so the model can tie `12%¹` to it.
  - Values stay verbatim, so the citation check is unaffected.
- **N21.** `StructuralNormalizationService` requires `artifact_reader` and `pdf_extractor`,
  and the two `None` branches are gone.
  - `scripts/demonstrate_normalization.py` really normalized without Gemini, so a
    `NoPdfExtractor` makes that explicit: it reports every PDF as `PDF_MODEL_REQUIRED`.
  - The tests that built the service with no arguments now pass a file store and
    `NoPdfExtractor`.
- **N22 (normalization half).** Deleted `api_payload_normalizer.py`, its test, the payload
  loop in `normalize()`, and `INVALID_JSON`. Nothing re-reads stored bundles, so removing
  the enum value is safe.
  - Source discovery still has code for API-sourced documents (`DiscoveryScope.API_PAYLOAD`
    in `discovery_prefilter.py` and `source_discovery.py`). It is now dead, and is left for
    the acquisition half.
- **N27.** No captured page contains a mis-decoded bullet. The `â€¢` came in with the
  first normalization commit, and today's decoding is sound: the static fetch decodes
  strictly with the response charset or UTF-8, and browser pages arrive as text. The
  workaround is removed.
- **Docs.** [docs/normalization.md](../../docs/normalization.md) and
  [docs/architecture.md](../../docs/architecture.md) now describe parser guarantees, table
  sections, headers and notes, the new warning codes, the admission context and gate, the
  PDF error types, OCR widening, required dependencies, and that payloads are not
  normalized. The acquisition text about capturing payloads stays until the acquisition
  half is decided.

**Blocked: N22 (Q1) acquisition half.** Removing payload capture changes the acquisition
completeness gate, which acquisition's own fix designed around payloads:
- **Floor.** It requires "tables, PDF links **or payloads**". `mortgage_diaspora` has no
  table and no PDF link, and passes only on its 17 payloads (acquisition scenario S02). It
  would fail on every run.
- **Baseline.** "A structure the page had and no longer has always fails". Every page whose
  stored baseline has payloads > 0 would fail "payloads N → 0" until an operator resets it.

So the gate has to change with the removal, and that is the user's decision.

**Measured.** Ground truth 0/348; PDF gate pass (0 historical transcribed); uncovered text
0. Suite: 909 passed, with the same 4 key-dependent failures.

**N20, done after the user's decision (2026-09-26): score against the seed baseline.** The
Phase 2 proposal (generic signals) was **not** what the user had decided in Q3. The decision
was to score each page against a baseline of what it should contain, so that is what is built:
- **Module:** [normalization_baseline.py](../../app/services/normalization_baseline.py) holds
  the models, `load_normalization_baseline()` and `score_page()`. The baseline itself is
  [app/config/normalization_baseline.json](../../app/config/normalization_baseline.json):
  13 pages and 330 checks, generated from the ground truth by
  [survey/export_normalization_baseline.py](survey/export_normalization_baseline.py).
- **Structure only, no tariff values** (my design choice, explained to the user). A table is
  found by its anchor, or by its title when the anchor quotes a value. A fact keeps its row
  label, its section, and "has a value". A block is kept only when it has no digits. So a
  rate change is a tariff change, not a quality drop. The offline ground-truth check keeps
  the values; exporting them too would be a one-flag change.
- **In the service:** `StructuralNormalizationService(baseline=…)` scores the page document
  (`passed / checks`). A page with no baseline gets `None` instead of the old claimed 1.0.
  Missing structure raises `BASELINE_MISMATCH`, which lists what is missing. `runtime.py`
  loads the shipped baseline.
- **Ground truth addition:** `mortgage_diaspora` had only figure facts, so it gained 4 label
  facts (its section headings and one FAQ question) and now has 7 checks. The shipped-baseline
  test caught this. Ground truth: 352 checks, 0 failures.
- **Scores on the 13 seeds**
  ([before](data/seed-scores-before.json) = Phase 0 code, [after](data/seed-scores-after.json)):

  | Seed | Before | After |
  |---|---|---|
  | mortgage_express | 0.0 (all 4 tables unfound: their numbered first row became a note) | 1.0 |
  | mortgage_renovation | 0.375 | 1.0 |
  | mortgage_secondary_market | 0.545 | 1.0 |
  | mortgage_primary | 0.553 | 1.0 |
  | mortgage_construction | 0.588 | 1.0 |
  | mortgage_online | 0.935 | 1.0 |
  | mortgage_commercial | 0.958 | 1.0 |
  | credit_line | 0.969 | 1.0 |
  | the other 5 | 1.0 | 1.0 |

  [seed-scores-stored-parse.json](data/seed-scores-stored-parse.json) also scores the blocks
  stored in the capture (old parser, new table normalizer): 0.94–1.0. That is what an artifact
  reused from before deploy would score within the freshness window.
- **Tests:** [test_normalization_baseline.py](../../tests/unit/test_normalization_baseline.py)
  has 6 tests:
  - full score;
  - a changed rate still scores 1.0;
  - lost section/block → 5/7 with the missing items named;
  - a missing table fails all its checks;
  - no baseline → `None`;
  - the shipped baseline covers every enabled seed and quotes no figures.

**N22 acquisition half, done after the user's decision (2026-09-26): remove capture, add a
text floor.**
- **Renderer:** [browser_renderer.py](../../app/services/browser_renderer.py) no longer
  listens to responses. `order_network_payloads`, `RenderedPage.network_payloads` and the
  byte budget are gone. Request routing is unchanged, so the page still loads its data
  requests.
- **Acquisition** ([acquisition.py](../../app/services/acquisition.py)): no payload storage,
  no `network_payloads` on the artifact, and no payload digests in `content_hash`.
- **Domain:** `NetworkPayload` and `AcquisitionInventory.payloads` are removed. Stored
  artifacts and baselines that still carry them load fine, because extra fields are
  ignored. `PAYLOAD_CAP_REACHED` stays as an enum value only, so old artifacts that carry
  that warning still validate.
- **Floor** (`completeness_floor_failures`): the main-text floor, **and** a table or a PDF
  link, **or** at least `ACQUISITION_MIN_MAIN_CONTENT_CHARS_WITHOUT_STRUCTURE` (new, default
  3000) characters of main text. `mortgage_diaspora` (3,294, no table or PDF) passes; a page
  rendered from its menus alone (75–1,179) still fails. Both reasons are listed when both
  apply.
- **Baseline** (`compare_inventory`): compares tables and PDF links only. A stored baseline's
  `payloads` count is ignored, so no page fails "payloads N → 0".
- **Config:** `ACQUISITION_MAX_NETWORK_PAYLOADS` and `…_BYTES` are removed. Environment
  settings ignore unknown variables, so an old `.env` still loads.
- **Also updated:** the demo scripts no longer write `network_payloads.json`; the
  acquisition scenario harness is updated (S02's criterion is now the new floor);
  [docs/acquisition.md](../../docs/acquisition.md), [docs/configuration.md](../../docs/configuration.md),
  [docs/architecture.md](../../docs/architecture.md), and acquisition item A10 is marked
  superseded.
- **Tests:** deleted three payload-order tests and the payload-cap test. Added a text-only
  page passing the floor and an old baseline with `payloads` being ignored.
  `uv run pytest tests/unit tests/integration`: 905 passed, with the same 4 key-dependent
  failures. `pytest -m browser`: 5 passed.
- **One-time effect.** Every page's `content_hash` changes once, because payload digests
  left it. It is a consistency tag, not the input to change detection.
- **Left as dead code on purpose.** Source discovery's handling of API-sourced documents
  (`DiscoveryScope.API_PAYLOAD`). Stored discovery decisions may name that scope, so
  removing the enum value would need a data check first.


### Phase 6: Validation

- [x] `uv run pytest tests/unit tests/integration`: all green, no `xfail` left from Phase 0.
- [x] `agents-cli lint`: clean.
- [x] Re-run the Phase 0 survey and save `data/normalization-survey-after.json`. Compare: no
      lost rows, no invented headers without a warning, no uncovered `div` text.
- [x] Compare the fixed bundles with `data/seed-ground-truth.json`: every expected table, row,
      section and key value present. Record the quality score per seed.
- [x] Re-run admission against `data/seed-pdf-labels.json`: no current or future PDF skipped.
- [x] Run one monitoring pass over all seeds on a scratch database copy, with the spend limits
      from `runtime-tests/cost_guard.py`. Record:
      - per seed: tariff changes, reviews opened, and warning codes;
      - every change, classified as a real bank change or a normalization fix (Q5).
      *Needs approval: spends Gemini budget.*
- [x] Run again right after. Extraction and PDF transcription must be all cache hits, and no
      new `tariff_changes` rows.
- [x] Update this document: status of every item, and the before/after survey.

#### Phase 6 notes (2026-09-26)

**State: offline validation done. The live run waits for approval, and the quality-score
column waits for N20.**

- **Tests:** `uv run pytest tests/unit tests/integration` gives 909 passed, 42 skipped,
  **no `xfail` left**. The only failures are the 4 environmental ones recorded in Phase 0,
  which need a Gemini key: `test_agent_stream` fails and 3 `test_server_e2e` tests error.
- **Lint:** `agents-cli lint`. Ruff check and format are clean. `ty` reports 40
  errors/warnings, the same count as the Phase 0 commit, and none in changed files. (The
  CLI's "47 diagnostics" includes info-level notes.)
- **Survey after** ([data/normalization-survey-after.json](data/normalization-survey-after.json))
  against [before](data/normalization-survey-before.json):

  | | Before | After |
  |---|---|---|
  | Uncovered visible text nodes | 40 (2,678 chars) | **0** |
  | Blocks | 1,982 | 2,054 |
  | Table rows | 923 | 900 (bullets merged into their list; sub-labels became sections; Express renovation rows no longer dropped) |
  | Notes | 104 | 72 (none is a misfiled title or section label) |
  | Tables with invented headers | 24 | 23 (each now reported as `AMBIGUOUS_TABLE`) |

- **Ground truth:** **77 → 0 failures of 348**
  ([before](data/ground-truth-check-before.json), [after](data/ground-truth-check-after.json)).
  The per-seed quality-score column is still to do: it needs the N20 rules.
- **PDF labels:** gate passes. Historical PDFs transcribed go from 6 to 0; irrelevant ones
  stay at 2 ([before](data/pdf-label-check-before.json), [after](data/pdf-label-check-after.json)).
- **Not run: the live monitoring pass and its immediate re-run.** They spend Gemini budget
  and need the user's approval (Q5).
  - Expect the first run to re-extract every page, since evidence text changed.
  - Expect it to re-transcribe PDFs whose admission changed, since N17 is deferred.
  - It may record tariff changes for values that were lost or mislabelled before.

#### Phase 6 live check without Gemini (2026-09-26)

The user decided that validation spends **no Gemini tokens**. Normalization needs none: PDFs go
to `NoPdfExtractor`. So the two live items above were done in that form, instead of a Gemini
monitoring pass.

- **Captures.** All 13 seeds were captured live **twice**, back to back, with the current code:
  - `SURVEY_CACHE=…/.cache-live-1` and `…/.cache-live-2`, running
    [capture_seeds.py](survey/capture_seeds.py);
  - browser render on, PDFs downloaded, the Gemini client refused.

  Both captures were then compared with [live_check.py](survey/live_check.py) →
  [data/live-check-2026-09-26.json](data/live-check-2026-09-26.json).
- **Results, all 13 seeds:**
  - acquired in `browser` mode and passed the new completeness floor (diaspora on its text);
  - **quality score 1.0 in both runs**;
  - **identical page ids, content hashes and normalized page documents** across the two
    fetches, so a re-run finds every content-addressed cache and records no change;
  - every linked PDF already labelled, and none labelled current skipped.
- **Warnings, as expected:**
  - `AMBIGUOUS_TABLE` for the 23 header-less tables;
  - `PDF_MODEL_REQUIRED` for each admitted PDF, because nothing is transcribed without
    Gemini;
  - no `BASELINE_MISMATCH`.
- **Ground truth on the fresh capture:** 0 of 352 failures
  ([data/ground-truth-check-live-2026-09-26.json](data/ground-truth-check-live-2026-09-26.json)).
- **PDF gate on the fresh capture:** pass; 0 historical PDFs transcribed; the same 2
  irrelevant ones ([data/pdf-label-check-live-2026-09-26.json](data/pdf-label-check-live-2026-09-26.json)).
- **Quality scores per seed:** see the N20 table in the Phase 5 notes (Phase 0 code
  0.0–1.0; now 1.0 on all).
- **Not validated here: Gemini PDF transcription itself.** Its code paths are covered by unit
  tests. The first production run still pays the one-time costs described under Q5:
  - every page is extracted again, since evidence text changed;
  - PDFs whose admission changed are transcribed again (N17 is deferred);
  - tariff changes may be recorded for values that were lost or mislabelled before.


### Deferred

- [ ] N17: PDF cache fingerprint = PDF hash + schema version + prompt version + probe. Test:
      same bytes, different link text and date → cache hit. Deferred by the user on
      2026-09-26. Revisit if re-transcription after page-text changes shows up in spend.
