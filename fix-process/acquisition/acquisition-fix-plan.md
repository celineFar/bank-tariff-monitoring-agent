# Acquisition: problem report and fix plan

Date: 2026-09-26 · Status: **implemented on branch `fix/acquisition`** (Phases 0–7;
Phase 8 minus the live Gemini runs). Q1–Q4 are decided (see [Decisions](#decisions)).
Existing databases need migrations `017` and `018` applied by hand (migrations run
automatically only when the database is first created).

## How this was checked

- **Code.** The acquisition code is identical on `test/schema-coverage-across-seeds` and
  `adk-native-runtime`; only `failure_mapping.py` differs slightly on `main`. Line references
  point at the current branch.
- **Data.** Read-only queries against the `tariff_rt` database: `knowledge_documents`,
  `knowledge_chunks`, `semantic_extraction_batches`, `tariff_snapshots`,
  `acquisition_snapshots`.
- **Live runs.** The real `AcquisitionService` (static fetch + Playwright), run against the live
  bank site with PDF downloads off and nothing written to the database:
  - the Overdraft page fetched twice back to back (identity check, A1);
  - all 13 seeds once ([data/seed-survey-2026-09-26.json](data/seed-survey-2026-09-26.json)).

  "Main content" below means visible text with `header`, `nav`, `footer`, ARIA landmark
  regions, scripts and hidden elements removed.

## The seed survey in one table

| Seed | Mode used | Static main text | Final main text | Tables | PDF links | XHR |
|---|---|---|---|---|---|---|
| consumer_standard | **static** | 368 | 368 | 0 | 0 | 0 |
| overdraft | browser | 353 | 13,136 | 3 | 10 | 17 |
| credit_line | browser | 1,179 | 19,630 | 3 | **16** | 13 |
| online_consumer_finance | **static** | 75 | 75 | 0 | 0 | 0 |
| mortgage_online | **static** | 143 | 143 | 0 | 0 | 0 |
| mortgage_primary | browser | 97 | 41,246 | 3 | **15** | 19 |
| mortgage_diaspora | **static** | 103 | 103 | 0 | 0 | 0 |
| mortgage_secondary_market | browser | 698 | 40,313 | 3 | **13** | 15 |
| mortgage_commercial | browser | 732 | 25,108 | 2 | 9 | 13 |
| mortgage_express | **static** | 84 | 84 | 0 | 0 | 0 |
| mortgage_no_income_verification | **static** | 103 | 103 | 0 | 0 | 0 |
| mortgage_renovation | browser | 587 | 45,254 | 3 | **16** | 14 |
| mortgage_construction | browser | 549 | 47,785 | 4 | **18** | 13 |

What it shows:

- **6 of 13 seeds are monitored from navigation chrome.** The browser render was thrown away
  (A2), the static page was used instead (A4), and the usefulness check passed it (A3). Those
  six artifacts contain no tables, no PDFs and no payloads.
- **Static HTML never has a table or a PDF link, on any seed.** Its 8.5–9.6k visible
  characters are the site header, menus and footer. Main content is 75–1,179 characters.
- **Static HTML passes today's usefulness check on all 13** (`visible_text >= 500`).
- **5 of the 7 working seeds have more than 10 PDF links** (13–18). The rest are dropped
  silently (A7). consumer_standard, once rendered correctly, has 12.

### After the fix (same day, [data/seed-survey-2026-09-26-after.json](data/seed-survey-2026-09-26-after.json))

| | Before | After |
|---|---|---|
| Seeds read in browser mode | 7 / 13 | **13 / 13** |
| Seeds read from site chrome only (0 tables, 0 PDFs, 0 payloads) | 6 | **0** |
| Seeds passing the completeness floor | (no real floor) | **13 / 13** |
| Page id stable across two back-to-back fetches | no | **yes** (overdraft, consumer_standard) |
| Seeds with more PDF links than get downloaded | 7 (cap 10) | **0** (cap 40) |

---

## Summary

| ID | Problem | Severity | Evidence | Fix | Status |
|---|---|---|---|---|---|
| A2 | Browser visibility marking erases the whole page on pages without an `<h1>` | **critical** | 6/13 seeds, live | Wait for the real content; don't treat a mid-fade wrapper as hidden | proposed |
| A3 | Usefulness check counts site chrome, so empty pages pass | **critical** | 13/13 static pages pass | Completeness gate: floor + baseline, fail until reset | **decided** (Q2, Q3) |
| A4 | Static fallback accepted when the browser fails or renders "insufficient" | **critical** | 6/13 seeds, live | Remove the fallback | **decided** (Q1) |
| A1 | Page identity changes on every fetch (per-request ASP.NET tokens) | high | 2 live fetches; 13/23 fields differed between identical runs | Hash parsed content only | **decided** (Q4) |
| A7 | PDF and click caps truncate silently | high | 5/13 seeds over the PDF cap | Raise the cap, warn and record when hit | proposed |
| A5 | Degraded or partial acquisitions are cached and reused | high | code | Don't store degraded artifacts for reuse | proposed |
| A6 | `PageArtifact.warnings` is never read | medium | code | Carry warnings into the manifest and audit | proposed |
| A8 | Uncaught Playwright errors; failure codes collapse | medium | code | Wrap all browser errors; add specific codes | proposed |
| A13 | Positional block, table and row ids feed evidence ids | medium | code | Not pursued (Q4) | **deferred** |
| A9 | Page URL checked before the clicks, content read after | medium | code (not seen live) | Re-check URL after the loop; block navigation | proposed |
| A10 | Payload cap applied in arrival order (race) | low | code (max seen 19 of 25) | Cap after the deterministic sort | proposed |
| A11 | Browser redirect hops not checked; docs overstate it | low | code + Playwright docs | Check each hop, or fix the docs | proposed |
| A12 | Freshness reuse is invisible on the run | low | code | Record reuse on the run and say so in chat | proposed |
| A14 | Docs say `content_hash` drives change detection; it doesn't | low | code | Fix the docs | proposed |
| A15 | Small points: port not checked; "needs browser" regex matches every page; two separate fetches | low | code + survey | See item | proposed |
| X1 | *(outside acquisition)* Semantic extraction and PDF transcription run without `temperature=0` | related | code | Set `temperature=0` | noted |

**Suggested order:** A2 → A3 + A4 + A6 (one change: "a degraded acquisition must not pass
silently") → A1 → A7 → A5 → A8 → the rest. A2 alone restores six seeds, but without A3/A4 the
next rendering problem would again pass silently.

---

## A1. Page identity changes on every fetch

**What happens.** `page_content_hash`
([acquisition.py:313-338](../../app/services/acquisition.py#L313-L338)) includes the SHA-256
of the raw HTML bytes and of the rendered HTML. The bank's ASP.NET pages carry three hidden
fields that change on every request: `__VIEWSTATE`, `__EVENTVALIDATION` and
`__RequestVerificationToken`. So the page id `page:<hash[:16]>`
([normalization.py:61](../../app/services/normalization.py#L61)) changes on every fetch. That id
is part of every evidence id
([extraction_evidence.py:94](../../app/services/extraction_evidence.py#L94)), and evidence ids
are part of every extraction cache key
([extraction_planner.py:265-278](../../app/services/extraction_planner.py#L265-L278)).

**Evidence.**
- Two live fetches of Overdraft, back to back. Blocks (127), tables (3), links (80), images,
  controls and locators were identical, and so were the payload bodies. The raw and rendered
  HTML differed only in those three fields. The page ids differed (`ca0b0f9e…` vs `08fef546…`).
- `tariff_rt`: 3 Overdraft runs with identical chunk hashes got 3 different page ids. Each run
  wrote new extraction-cache entries, with the same schema, prompt and model.
- Snapshots from the 17:21 and 17:37 runs on 2026-09-22 (identical page text): **13 of 23
  extracted fields differ** (`eligibility` found vs missing, `credit_limit` 3 values vs 1,
  `effective_rate` `unknown` vs `fixed`, …). Both snapshots were rejected, so nothing was
  published. Had they been accepted, change detection would have reported 13 false changes.

**Fix.** Drop `raw_sha256` and `rendered_sha256` from the `page_content_hash` material. The
parsed blocks, tables, links, images and controls stay in it. The raw and rendered bytes stay
stored as artifacts for audit; they only stop naming the page.

**Tests.**
- Two acquisitions whose HTML differs only in a hidden `__VIEWSTATE` value → same
  `page_content_hash`. (`test_content_hash_is_stable_for_identical_source` only covers
  byte-identical input.)
- A changed visible block → different hash.
- Live check: fetch Overdraft twice, and the page ids match.

**Effect.** A one-off cache miss on the first run after deploy, then identical pages reuse
their extractions.

## A2. Browser visibility marking erases the whole page

**What happens.** The renderer marks each element `data-acquisition-visible="true"/"false"`
([browser_renderer.py:68-104](../../app/services/browser_renderer.py#L68-L104),
[220-245](../../app/services/browser_renderer.py#L220-L245)). Opacity 0 counts as hidden
([line 79](../../app/services/browser_renderer.py#L79)). The parser treats any ancestor marked
`"false"` as hiding everything under it
([html_parser.py:592](../../app/services/html_parser.py#L592)).

The site wraps the whole page in an ASP.NET `<form id="Form">` and fades it in from opacity 0
(an `animsition` page transition). The only wait for that fade is `_PRIMARY_CONTENT_REVEALED`
([browser_renderer.py:203](../../app/services/browser_renderer.py#L203)). It waits for the
first `<h1>` to become opaque, and **returns true at once when there is no `<h1>`**. On those
pages, marking runs mid-fade: the form is marked hidden, the 524 elements inside it marked
visible don't matter, and the parser sees nothing.

**Evidence.** A consumer_standard render: the browser's own `innerText` has 6,915 characters,
but the parsed `visible_text` has 0 characters and 0 blocks, and the form is marked `false`.
With that one mark removed, the same render parses to 22,282 characters, 3 tables and 12 PDF
links. All 6 failing seeds have no `<h1>`. Two other pages without an `<h1>` succeeded: they
won the race.

**Fix.**
1. Wait for the content, not for an `<h1>`: wait until no ancestor of the main text container
   has an effective opacity below 0.99, with a bounded timeout. Use the element holding the
   most text, or the page's `form`/`main`, as the target. Keep the `<h1>` check as one signal
   among others, not the only one.
2. Don't treat opacity alone as hidden when marking. `display`, `visibility`, `hidden` and
   zero-size already cover real hiding; opacity is almost always a transition. Otherwise
   require opacity 0 to persist after the wait.
3. The render must still pass the completeness check (A3), so a future variant of this fails
   loudly instead of falling back.

**Tests.** A fixture page with no `<h1>` whose wrapper starts at opacity 0 and fades in after
300 ms: the parsed text must be non-empty. Live check: re-run the survey, and all 13 seeds
should report mode `browser` with at least one table.

## A3. Usefulness check brainstorm

### What the check does today

`_is_useful` is `len(visible_text) >= 500 or any table`
([acquisition.py:236-239](../../app/services/acquisition.py#L236-L239)). It makes four
decisions:

| # | Decision | Where |
|---|---|---|
| 1 | Does this page need the browser? | `_requires_browser`, [line 229](../../app/services/acquisition.py#L229) |
| 2 | Is static HTML good enough when the browser is off or has failed? | [lines 104, 119](../../app/services/acquisition.py#L104) |
| 3 | Is the rendered result better than static? | [lines 129, 141](../../app/services/acquisition.py#L129) |
| 4 | Final gate: is there anything at all? | [line 146](../../app/services/acquisition.py#L146) |

### Why it can't catch the failure

1. **It measures the whole page, and the whole page is mostly chrome.** Every seed has
   8.5–9.6k characters of header, menus and footer, 17 times the threshold, before any
   tariff content.
2. **It asks "is there some text?", not "is the content we monitor here?"** Tables, PDF
   links and payloads are where the tariffs are. The check ignores PDFs and payloads, and
   treats a single table of any kind as enough.
3. **It is absolute and knows nothing about the page.** It can't tell that Overdraft
   normally has 3 tables and 10 PDFs and today has none. A partial render, a soft 404 or a
   maintenance page all look "useful".
4. **One number serves four decisions.** "Does this page need a browser" and "is this
   acquisition complete" are different questions.
5. **Its result is thrown away.** When the fallback fires, the warning is never read (A6),
   and the result is cached (A5).

### Options

| Option | How it works | Would it have caught today's six? | Weaknesses |
|---|---|---|---|
| **U1. Measure main content only** | Count text outside `header`/`nav`/`footer`/ARIA landmarks and hidden inputs. Threshold between today's worst render (13k) and best static page (1.2k), e.g. 3,000. | Yes (75–368 vs ≥3,000) | Still a fixed number; a soft 404 with a long apology passes; relies on the site's landmark markup |
| **U2. Require tariff structure** | At least one table, or at least one same-host PDF link, or a payload. Optionally: number tokens with `%`/`AMD`. | Yes (0/0/0 on all six) | Domain rule; an offering described only in prose would fail. None of the 13 is like that today |
| **U3. Compare with the last good acquisition of the same URL** | Store an inventory per URL (main chars, tables, PDF links, payloads, headings). Flag the new artifact as **degraded** if a count falls sharply, e.g. tables 3 → 0, PDFs −50%, main text −60%. | Yes, once a baseline exists | Needs a baseline store that a degraded run can't overwrite (`acquisition_snapshots` is replaced every run); the first run has no baseline; a real redesign by the bank looks like degradation, so it needs a resolution path (Q3) |
| **U4. Per-seed expectations in `seed_catalog.yaml`** | e.g. `expect: {min_tables: 2, min_pdf_links: 5}` | Yes | Manual upkeep; drifts |
| **U5. Remove the static fallback** | When the browser is on, a browser failure fails the offering. Static is used only when the browser is disabled by config (dev). | Yes (they fail instead) | Coverage drops while the browser is broken. Static coverage is worthless on all 13 seeds anyway |

### Recommendation

- **Split the check into two questions.**
  - "Does it need a browser?" goes away: when the browser is enabled, always render. The
    regex matches all 13 seeds anyway (A15).
  - "Is it complete?" becomes a single gate, applied to whatever artifact acquisition
    produced.
- **The gate:**
  1. **U1 + U2 as an absolute floor, used on every run.** There must be main content above a
     threshold *and* at least one tariff structure (table, PDF link or payload).
  2. **U3 as a regression check against the last good inventory** for that URL, once one
     exists.
  3. **U5**: no static fallback when the browser is enabled.
- **A failed gate is a typed acquisition failure** (`source.incomplete_content`, see A8),
  never a warning. It is not stored for reuse, and its reasons are recorded (for example,
  `tables 3→0; pdf_links 10→0`).
- **Where it lives.** Keep it deterministic, in acquisition. The baseline lives in its own
  table (or a column on `acquisition_snapshots` that only a passing acquisition writes), so a
  degraded run can't become the next run's baseline.

**Decided:** this recommendation, with Q3 set to "fail until reset". See
[Decisions](#decisions) for the baseline lifecycle and the reset command.

## A4. Static fallback accepted when the browser fails

**What happens.** Three branches accept static HTML whenever `_is_useful(raw_parsed)`:
- the browser is disabled ([acquisition.py:103-109](../../app/services/acquisition.py#L103-L109));
- the browser raised an error ([118-124](../../app/services/acquisition.py#L118-L124));
- the render was "insufficient" ([141-144](../../app/services/acquisition.py#L141-L144)).

The artifact is labelled `mode=static` with a warning, and processing continues.

**Downstream.** Required fields come back `not_stated`, so a reviewer is asked about a
browser glitch. If a snapshot is accepted, any missing optional field is recorded as a change
to "no value". The next good run then records the reverse change.

**Fix (Q1: remove).** With the browser enabled, any browser failure or empty render fails
the offering. Also, `test_empty_browser_render_uses_useful_static_page` in
[test_acquisition.py](../../tests/unit/test_acquisition.py) currently tests the flawed
behaviour and must be rewritten.

## A5. Degraded or partial acquisitions are cached and reused

**What happens.** `FreshnessGatedAcquisitionService` stores every successful acquisition
([acquisition_freshness.py:71](../../app/services/acquisition_freshness.py#L71)). A static
fallback, or an artifact with failed PDF downloads, is served again for
`ACQUISITION_FRESHNESS_HOURS` without retrying. The readability check
([line 111](../../app/services/acquisition_freshness.py#L111)) only covers the PDFs that were
downloaded, so it can't notice one that is missing. This contradicts the class's own rule that
reuse is never a fallback for a failed acquisition.

**Fix.** Store for reuse only if the artifact passed the completeness gate (A3) and has no
failed linked downloads. Otherwise don't store it, and leave the previous good one in place
only if the window still covers it. Add an explicit `degraded: bool` (or a reasons list) to
`PageArtifact` rather than inferring it from warning strings.

**Tests.** A fallback or partial artifact → `snapshots.save` is not called, and the next
acquire fetches again.

## A6. `PageArtifact.warnings` is never read

**What happens.** Acquisition writes warnings ("browser rendering failed", "linked document
l12 was not downloaded: source.timeout", …). Nothing reads them: the run's warning list
contains only normalization warnings
([monitoring_pipeline.py:351](../../app/services/monitoring_pipeline.py#L351)).

**Fix.** Make acquisition warnings typed codes (like `NormalizationWarningCode`), and add them
to `SourceManifest.warning_codes` and the audit metadata. After A3/A4, the fallback cases
become failures; what remains as warnings are genuine partial outcomes, such as one PDF
failing among many.

## A7. Silent truncation: PDF cap and click cap

**What happens.**
- `max_linked_documents = 10`
  ([config/models.py:205](../../app/config/models.py#L205)). The loop stops at the cap with
  no warning ([acquisition.py:257](../../app/services/acquisition.py#L257)). **5/13 seeds have
  13–18 PDF links today**, so up to 8 documents per seed are never seen, and which ones
  depends on page order.
- `max_interactions = 100`: reaching it isn't recorded, and `RenderedPage.interactions` is
  discarded.

**Fix.**
- Raise `max_linked_documents` to 40. The config allows up to 50; the busiest seed has 18.
  Cost is contained: PDF admission already skips irrelevant and historical documents before
  Gemini, and transcription is cached by PDF hash.
- Emit a typed warning (A6) whenever either cap is reached. Record the click count on the
  artifact.

**Question folded into the defaults.** If the cap is hit, should the acquisition be degraded
(A5, not reused) or just carry a warning? Proposed: **warning only**, since the cap is a
cost bound, not a failure.

## A8. Uncaught Playwright errors; failure codes collapse

**What happens.**
- `chromium.launch` ([browser_renderer.py:322](../../app/services/browser_renderer.py#L322))
  and every `page.evaluate` in the click loop raise raw Playwright errors. Only `goto` is
  wrapped. `AcquisitionService` catches only `BrowserRenderingError`.
- In `failure_mapping`, unknown errors fall through to `source.validation_failed`, and all
  three `AcquisitionFailure` reasons plus every `BrowserRenderingError` map to
  `source.parsing_failed` ([failure_mapping.py:76-77](../../app/services/failure_mapping.py#L76-L77)).

A missing Chromium binary therefore reports as a data-validation failure.

**Fix.**
- Wrap launch and the whole interaction phase, and translate errors into
  `BrowserRenderingError` (reasons `UNAVAILABLE`, `INTERACTION`).
- Add `SourceFailureCode`s: `source.browser_unavailable`, `source.browser_failed`,
  `source.incomplete_content` (the A3 gate).

**Tests.** A fake renderer raising a Playwright-like error → a typed failure with the right
code. Each reason maps to its own code.

## A9. Page URL checked before the clicks, content read after

**What happens.** `final_url` is checked against the allowlist before the click loop
([browser_renderer.py:398](../../app/services/browser_renderer.py#L398)). `page.content()` is
read after it. Buttons labelled "learn more" or "details" are clicked. If one navigates by
JavaScript, the loop crashes (A8), or another page's content is stored under the seed URL. Not
seen live: all clicks on Overdraft were in-page tabs.

**Fix.**
- Record `page.url` again after the loop, and fail if it changed.
- Also abort main-frame navigations after the first load, in the route handler
  (`request.is_navigation_request()` and `request.frame == page.main_frame`).

## A10. Payload cap applied in arrival order

**What happens.** Capture stops at `max_network_payloads` in arrival order
([browser_renderer.py:273](../../app/services/browser_renderer.py#L273)). The deterministic
`(url, digest)` sort only runs afterwards, so past the cap the surviving set is a race, and
duplicate captures count toward the cap. The survey's maximum is 19 against a cap of 25.

**Fix.** Capture everything that fits a byte budget, deduplicate, sort, then cap. Warn when
the cap is hit (A6).

## A11. Browser redirect hops not checked

**What happens.** Playwright calls a route handler only for the first URL of a redirect
chain. Page resources that redirect to a non-allowlisted host are still fetched, and for the
main navigation only the final URL is checked. The static fetch does check every hop.
[docs/architecture.md:311](../../docs/architecture.md#L311) claims both do. The risk is low,
since the source is the bank's own host.

**Fix.** Check `response.request.redirected_from` chains in the response handler and fail
the render on any off-allowlist hop, or correct the docs. Proposed: check the chain for the
main document, fix the docs for page resources.

## A12. Freshness reuse is invisible on the run

**What happens.** When a stored acquisition is reused, only a trace attribute records it
([acquisition_freshness.py:63](../../app/services/acquisition_freshness.py#L63)). A "no
changes" answer from an up-to-an-hour-old fetch looks the same as a fresh check.

**Fix (proposed default, no bypass).** Keep the window. Record `acquisition_reused` and the
original `retrieved_at` on the offering execution. The chat reply then says "checked against
the page as fetched at 14:05".

## A13. Positional block, table and row ids feed evidence ids

**What happens.** Ids are page positions: `b{n}`, `t{n}`, `l{n}`, and table rows
`t{n}:row:{i}` ([html_parser.py:144, 159, 239](../../app/services/html_parser.py#L144)). The
evidence id hashes `(document_id, source_item_id, content)`, so a block inserted near the top
of the page renames every passage after it.

**But** after A1, the page's document id is still a hash of all of the page's content, so
*any* edit renames every passage on the page anyway. Positional ids only matter if the
document id stops changing on edits. That is Q4.

**Decided (Q4): not pursued.** The page id stays a content hash (A1). Revisit if
re-extraction on small edits becomes a measured problem.

## A14. Docs say `content_hash` drives change detection

[docs/architecture.md:325](../../docs/architecture.md#L325) and the comment at
[domain/acquisition.py:220](../../app/domain/acquisition.py#L220) both say it does.
`content_hash` is only used to check that normalization, discovery and extraction saw the same
input ([semantic_extraction.py:368](../../app/services/semantic_extraction.py#L368)). Change
detection compares field values
([snapshot_lifecycle.py:492](../../app/services/snapshot_lifecycle.py#L492)). Fix the text;
also update [docs/acquisition.md](../../docs/acquisition.md) for A1, A3 and A4.

## A15. Small points

- **Port not checked.** `validate_source_url` accepts any port:
  `https://ameriabank.am:8443/` passes ([urls.py](../../app/security/urls.py)). Allow
  only the default 443.
- **The "needs browser" regex matches every page.** It matches any `aria-expanded="false"`,
  and all 13 seeds have that (survey). With A3's recommendation, the browser always renders
  when enabled, and the regex goes.
- **Raw and rendered HTML come from two separate fetches** and can capture different
  versions of the page. Accept this, and document that raw HTML is kept for audit only.

## X1. Outside acquisition: extraction runs without `temperature=0`

Discovery, intent resolution and RAG answers set `temperature=0`. Semantic extraction
([semantic_extraction.py:266](../../app/services/semantic_extraction.py#L266)) and PDF
transcription ([gemini_pdf_extractor.py:78](../../app/services/gemini_pdf_extractor.py#L78))
don't. After A1, cache hits cover unchanged pages. But when a page really changes, every
re-run batch can give different answers for unchanged fields, which show up as false changes.
`temperature=0` reduces this but doesn't eliminate it. This belongs to the extraction stage,
so it is recorded here only.

---

## Decisions

Decided 2026-09-26.

| Q | Question | Options | Decided |
|---|---|---|---|
| Q1 | Static fallback when the browser is enabled | remove / keep behind the completeness gate / keep but never cache | **Remove.** A browser failure fails the offering (`source.browser_failed` / `source.browser_unavailable`). Static HTML is used only when `ACQUISITION_BROWSER_ENABLED=false` (dev), and even then it must pass the gate. |
| Q2 | Completeness gate design | U1+U2 floor + U3 baseline / U1+U2 only / U4 per-seed expectations | **U1+U2 floor on every run, plus the U3 baseline regression check.** |
| Q3 | When the baseline check fires | fail, adopt after N consistent runs / human review / fail until reset | **Fail until reset.** The offering keeps failing with `source.incomplete_content` and its reasons until an operator resets the baseline. |
| Q4 | Page document identity | content hash (A1 only) / URL-based id + content-addressed evidence (A1 + A13) | **Content hash, A1 only.** A13 is not pursued. |

### What the decisions imply

**Q1: code.**
- The three fallback branches in `AcquisitionService.acquire`
  ([acquisition.py:102-144](../../app/services/acquisition.py#L102-L144)) collapse to one rule:
  browser enabled → render, or fail; browser disabled → use static HTML, which must pass the
  gate.
- `_requires_browser` and both regexes are deleted (A15).
- `test_empty_browser_render_uses_useful_static_page` becomes "an empty render fails with
  `source.incomplete_content`".

**Q2 + Q3: baseline lifecycle.**
- **What is stored.** One row per seed URL, in a new table `acquisition_baselines` (or
  columns that only the gate writes; not `acquisition_snapshots`, which is replaced every
  run). It holds an inventory `{main_chars, tables, pdf_links, payloads}`, the run and time
  it came from, and `reset_by`/`reset_at` when set by hand.
- **Written only by an acquisition that passes both checks.** On the first run for a URL,
  the floor alone decides, and a pass becomes the baseline.
- **Updated on every passing run.** Normal growth (a new PDF) moves the baseline forward.
  Only a sharp drop fails.
- **Drop thresholds, to confirm when implementing.** Any category that was ≥1 falls to 0;
  or PDF links fall ≥50%; or main content falls ≥60%. These are starting values. The survey
  gives today's inventories, so they can be checked against real pages before merging.
- **Reset.** An operator script next to the other operator tools in `scripts/`:
  `uv run python -m scripts.reset_acquisition_baseline <offering_id>`. (`app/cli.py` is the
  chat CLI only.) It clears the row, so the next passing run sets a new baseline, and it
  writes an audit event. It is an operator action only: never a model tool, and never
  reachable from the chat agent (AGENTS.md: no raw database tools for the model).
- **How it shows up.** The failure reasons (for example, `tables 3→0; pdf_links 10→0`) go
  into the offering execution and the audit. The chat reply for a failed offering names the
  reason and says that a reset is needed if the page really changed.

**Q4.** Only A1 is implemented. Any real edit to a page re-extracts every batch quoting that
page. That is the cost accepted in exchange for a small change. X1 (`temperature=0`) limits
the resulting variance. Revisit A13 if re-extraction on small edits becomes a measured cost
or noise problem.

### Proposed defaults, not asked

A7: raise the cap to 40, warning only. A11: check the main document's redirect chain, fix the
docs for page resources. A12: no bypass; record reuse on the run.

---

## Implementation phases

Each phase ends with its tests passing and can be merged on its own. The order follows the
severity above: Phase 1 restores the six blind seeds, and Phase 2 makes sure the next failure
of that kind can't pass silently.

Rules for every phase:
- Tests first, where a test can show the bug.
- Run `uv run pytest tests/unit tests/integration` and `agents-cli lint` before closing the
  phase.
- Update [docs/acquisition.md](../../docs/acquisition.md) and
  [docs/architecture.md](../../docs/architecture.md) in the same phase that changes
  behaviour, not at the end (AGENTS.md).
- Tick items here as they land.

### Phase 0: Preparation

- [x] Create a branch from `adk-native-runtime` (the acquisition code is identical there).
- [x] Add a `browser` pytest marker in `pyproject.toml` for tests that start a local
      Chromium. No network: fixture pages are loaded with `page.set_content()`.
- [x] Turn the survey into a script, `scripts/survey_acquisition.py`. For every seed it
      prints mode, main-content characters, tables, PDF links, payloads and warnings, with
      PDF downloads off and nothing written to the database. Phases 1, 2, 4 and 8 re-run it.
- [x] Keep [data/seed-survey-2026-09-26.json](data/seed-survey-2026-09-26.json) as the
      "before" record.

### Phase 1: The browser sees the whole page (A2)

- [x] Add a `browser` test with a fixture page like the failing seeds: an ASP.NET-style
      `<form>` wrapper at opacity 0 that fades in after 300 ms, no `<h1>`, and a table
      inside. Run the renderer's JavaScript steps against it, then `HtmlArtifactParser`. It
      must fail today with empty `visible_text`.
- [x] Replace `_PRIMARY_CONTENT_REVEALED`
      ([browser_renderer.py:203](../../app/services/browser_renderer.py#L203)) with a
      content-ready wait:
  - [x] Pick the content root: the `main`, `form` or top-level `body` child with the most
        `innerText`.
  - [x] Wait until the root and all its ancestors have computed opacity ≥ 0.99, bounded by
        `min(5 s, navigation timeout)`.
  - [x] Keep the `<h1>` check as an extra signal, never as a reason to skip the wait.
- [x] Stop treating `opacity: 0` as hidden in `_PREPARE_ACQUISITION_DOM`,
      `_PERFORM_ONE_INTERACTION` and `_FINALIZE_ACQUISITION_DOM`
      ([line 79](../../app/services/browser_renderer.py#L79)). `display`, `visibility`,
      `hidden` and zero-size still count as hidden.
- [x] Add a `browser` test: a tab panel hidden with `display:none` that is never clicked
      stays hidden. Real hiding must still work.
- [x] Add a `browser` test: a page whose content never becomes visible still produces an
      empty parse. Phase 2's gate must see that, not have it masked.
      *Deviation:* modelled with `visibility:hidden`. Once opacity no longer counts as
      hiding, a page stuck at opacity 0 parses as visible; that is accepted, since
      opacity is used for transitions, not for hiding content.
- [x] Re-run the survey. **Done when all 13 seeds render in `browser` mode with ≥ 1 table**,
      and consumer_standard shows its 3 tables and 12 PDF links.
      *Result:* 13/13 in `browser` mode; consumer_standard has 3 tables and 12 PDF links.
      12/13 have ≥ 1 table. mortgage_diaspora is a campaign landing page with no table
      and no PDF link in its DOM at all; it passes on its 17 data payloads.

### Phase 2: No silent fallback; typed failures (A4, A3 floor, A8, A6)

Failure codes (A8):
- [x] Add `SourceFailureCode.BROWSER_UNAVAILABLE`, `BROWSER_FAILED` and
      `INCOMPLETE_CONTENT` (`source.browser_unavailable`, `source.browser_failed`,
      `source.incomplete_content`) in [domain/monitoring.py](../../app/domain/monitoring.py).
      No migration is needed; failure codes are unconstrained strings.
- [x] In `PlaywrightBrowserRenderer.render`, wrap `chromium.launch` → `UNAVAILABLE`, and the
      whole settle, click and capture phase → a new `INTERACTION` reason, both as
      `BrowserRenderingError`.
- [x] In [failure_mapping.py](../../app/services/failure_mapping.py), map each
      `AcquisitionFailure` and `BrowserRenderingFailure` reason to its own code. Stop
      routing them to `source.parsing_failed`.
- [x] Tests in `test_failure_mapping.py`: one per reason. A Playwright-like error raised
      from a fake renderer becomes `source.browser_failed`, not
      `source.validation_failed`.

Completeness floor (A3: U1 + U2):
- [x] Add `main_text` to `ParsedHtml` in
      [html_parser.py](../../app/services/html_parser.py): visible text outside
      `header`, `nav`, `footer`, `[role=navigation|banner|contentinfo]` and hidden inputs.
- [x] Add an `AcquisitionInventory` model (`main_chars`, `tables`, `pdf_links`,
      `payloads`) to [domain/acquisition.py](../../app/domain/acquisition.py), computed for
      every artifact and stored on `PageArtifact`.
- [x] Add `AcquisitionSettings.min_main_content_chars` (starting value 3,000) and remove
      `min_static_text_chars`. Check the value against the Phase 1 survey: every good render
      must clear it with margin.
      *Deviation:* set to **1,500**. The thinnest real render (mortgage_diaspora) has
      3,294 main characters, with no margin over 3,000; static-only pages topped out at
      1,179. `.env` and `.env.example` updated.
- [x] Implement the floor: `main_chars >= min_main_content_chars` **and**
      `tables + pdf_links + payloads >= 1`. A failure raises
      `AcquisitionError(INCOMPLETE_CONTENT)` with its reasons (for example,
      `main_chars 368 < 3000; tables 0; pdf_links 0; payloads 0`).

Remove the fallback (A4, Q1):
- [x] Rewrite `AcquisitionService.acquire`
      ([acquisition.py:89-150](../../app/services/acquisition.py#L89-L150)):
  - [x] With the browser enabled: always render. A renderer error →
        `AcquisitionError(BROWSER_FAILED)`, keeping the renderer's reason. The rendered
        artifact must pass the floor.
  - [x] With the browser disabled: use the static parse, which must pass the floor.
  - [x] With the browser enabled but no renderer configured: `BROWSER_UNAVAILABLE`.
- [x] Delete `_requires_browser`, `_INTERACTIVE_HTML`, `_APP_SHELL_HTML` and `_is_useful`
      (A15).
- [x] Rewrite `test_empty_browser_render_uses_useful_static_page` as "an empty render fails
      with `INCOMPLETE_CONTENT`". Update `test_insufficient_static_content_requires_browser`
      and the other tests in [test_acquisition.py](../../tests/unit/test_acquisition.py).
- [x] Add a test: the renderer raises → a typed failure, and the static HTML is not used.

Warnings reach the run (A6):
- [x] Replace the free-text `PageArtifact.warnings` with typed codes
      (`AcquisitionWarningCode`: `linked_document_failed`, `linked_document_cap_reached`,
      `interaction_cap_reached`, `payload_cap_reached`), each with an optional detail.
- [x] Add them to `SourceManifest.warning_codes` and the audit metadata in
      [monitoring_pipeline.py:351](../../app/services/monitoring_pipeline.py#L351).
- [x] Test: an acquisition with one failed PDF download → its code appears in the
      manifest's warning codes.
- [x] Update the docs for the no-fallback rule and the floor.
- [x] Re-run the survey. **Done when all 13 seeds pass the floor**, and a forced renderer
      failure fails the offering with `source.browser_failed`.

### Phase 3: Baseline regression, reset, and no degraded reuse (A3: U3, Q3, A5)

Baseline storage:
- [x] Migration `migrations/017_acquisition_baselines.sql`: table `acquisition_baselines`
      with `url_key` (PK), `source_url`, `offering_id`, `inventory` (jsonb), `run_id`,
      `recorded_at`, `reset_by`, `reset_at`, plus the `*_yerevan` generated columns (see
      `009_yerevan_wall_times.sql`).
      *Deviation:* no `offering_id`/`run_id` columns: the baseline belongs to the URL,
      and the reset audit event carries the offering id. A reset keeps the row with a
      NULL inventory rather than deleting it, so `reset_by`/`reset_at` survive as history.
- [x] `PostgresAcquisitionBaselineRepository` in `app/repositories/` with `get`, `record`
      and `reset`, and a protocol in
      [repositories/contracts.py](../../app/repositories/contracts.py).

The check:
- [x] Implement the regression check as a pure function
      `compare_inventory(baseline, current) -> tuple[str, ...]` that returns failure reasons.
      Starting rules: any category ≥ 1 falls to 0; `pdf_links` falls ≥ 50%; `main_chars`
      falls ≥ 60%. Put the thresholds in `AcquisitionSettings`.
- [x] Check the thresholds against the Phase 1 and Phase 2 survey: two runs of the same seed
      must never trip them.
- [x] Unit tests: an unchanged inventory passes; tables 3→0 fails; PDFs 16→7 fails; PDFs
      16→17 passes; no baseline → the floor alone decides.

Wiring (a completeness gate wrapping acquisition, next to the freshness gate in
[runtime.py](../../app/runtime.py)):
- [x] After a fresh acquisition: floor (Phase 2) → baseline check → on a pass, record the
      new baseline; on a failure, raise `INCOMPLETE_CONTENT` with the reasons and leave the
      baseline untouched.
- [x] A reused acquisition (freshness window) is not re-checked and does not update the
      baseline.
- [x] A missing baseline row is recorded from the first passing run.

Reset (Q3):
- [x] `scripts/reset_acquisition_baseline.py <offering_id>`: resolves the seed URL from
      the seed catalog, deletes the baseline row, and writes an audit event with the
      operator's name. It is never registered as a tool.
- [x] The failure message for `INCOMPLETE_CONTENT` from the baseline check names the reset
      command, so the chat reply and the audit say what to do.

No degraded reuse (A5):
- [x] In `FreshnessGatedAcquisitionService`, call `snapshots.save` only for artifacts that
      passed the gate and have no `linked_document_failed` warning.
- [x] Tests in `test_acquisition_freshness.py`: a partial artifact is not stored, and the
      next acquire fetches again. A gate failure is not stored.
- [x] Integration test (Postgres): record → regression failure leaves the row unchanged →
      reset → the next run records a new baseline.
- [x] Update `docs/architecture.md` (new table, new gate, reset script).
- [x] **Done when:** a simulated drop (fixture with tables removed) fails with the reasons;
      the reset script clears it; the next run passes and records a new baseline.

### Phase 4: Stable page identity (A1)

- [x] Test first, in [test_acquisition_identity.py](../../tests/unit/test_acquisition_identity.py):
      two acquisitions whose HTML differs only in `__VIEWSTATE`, `__EVENTVALIDATION` and
      `__RequestVerificationToken` get the same `page_content_hash`. It fails today.
- [x] Test: a changed visible block → a different `page_content_hash`.
- [x] Remove `raw_sha256` and `rendered_sha256` from `_page_content_hash`
      ([acquisition.py:313-338](../../app/services/acquisition.py#L313-L338)). Keep the raw
      and rendered artifacts stored.
- [x] Update `test_content_hash_is_stable_for_identical_source` if it relies on the removed
      material.
- [x] Fix the docs: [docs/architecture.md:325](../../docs/architecture.md#L325) and the
      comment at [domain/acquisition.py:220](../../app/domain/acquisition.py#L220) (A14).
      `content_hash` is a cross-stage consistency tag, not the change-detection input.
- [x] Live check: acquire Overdraft twice and compare page ids.
- [x] **Done when** two live fetches give the same page id, and a second monitoring run on
      an unchanged page makes no semantic-extraction Gemini calls (`model_call_usage` shows
      cache hits only).

### Phase 5: No silent truncation (A7, A10)

- [x] Raise `max_linked_documents` to 40 in
      [config/models.py:205](../../app/config/models.py#L205), and `.env` if set there.
- [x] Emit `linked_document_cap_reached` (with the count skipped) when the cap stops the
      loop ([acquisition.py:257](../../app/services/acquisition.py#L257)). Test with 12 links
      and a cap of 10.
- [x] Record `interactions` on `PageArtifact`, and emit `interaction_cap_reached` when
      `max_interactions` is hit.
- [x] Payloads: remove the arrival-order cap at
      [browser_renderer.py:273](../../app/services/browser_renderer.py#L273). Capture under a
      total byte budget, then deduplicate, sort and cap in `order_network_payloads`. Emit
      `payload_cap_reached` when it cuts.
- [x] Test: 30 captures in two different arrival orders → the same kept set.
- [ ] Re-run the survey with PDF downloads on for one seed with more than 10 links (for
      example, mortgage_construction, 18), and check the PDF-admission and transcription
      cost in `model_call_usage` before and after.
      *Not done:* PDF downloads alone cost nothing; the cost is in the Gemini
      transcription, which only a monitoring run incurs. Folded into Phase 8's live run.
- [x] **Done when** no seed loses PDFs silently, and a cap hit shows in the manifest.
      *Note:* the earlier "13–18 PDF links" counted duplicate links to the same PDF.
      Distinct URLs: 7 seeds have 11–17, all under the new cap of 40.

### Phase 6: Browser hardening (A9, A11, A15)

- [x] Block main-frame navigations after the first load in `route_request`
      (`request.is_navigation_request()` and `request.frame == page.main_frame`).
- [x] Re-check `page.url` against the start URL after the click loop; if it changed, raise
      `BrowserRenderingError(NAVIGATION)`.
- [x] `browser` test: a button whose click sets `location.href` → the render fails with a
      typed error, never with another page's content.
      *Deviation, found by the test:* aborting a main-frame navigation still commits
      Chromium's error page and destroys the document being read. Blocked navigations
      after load are answered with an empty **204** instead, which makes the browser keep
      the current page. The test asserts the page stays and its content is read.
- [x] Walk `response.request.redirected_from` for the main document, validate every hop,
      and fail with `DISALLOWED_REDIRECT`. Add a unit test with a fake response chain.
- [x] Correct [docs/architecture.md:311](../../docs/architecture.md#L311): page-resource
      redirect hops are not individually checked.
- [x] `validate_source_url` ([urls.py](../../app/security/urls.py)): reject an explicit
      non-443 port. Add a case to `test_source_urls.py`.
- [x] Document that raw HTML and rendered HTML come from two separate fetches, and that raw
      HTML is kept for audit only.

### Phase 7: Reuse is visible (A12)

- [x] Add `acquisition_reused: bool` and the original `acquisition_retrieved_at` to the
      offering execution record. This needs a migration if they are columns; nothing if they
      go in existing jsonb metadata. Prefer the metadata unless it is queried.
      *Done as columns* (`migrations/018_offering_source_freshness.sql`:
      `source_retrieved_at`, `acquisition_reused`): `offering_executions` has no jsonb
      metadata, and the chat reads them. The row mapper reads them softly, so a database
      without 018 still lists executions.
- [x] Set them from `FreshnessGatedAcquisitionService`. Return reuse information alongside
      the artifact instead of relying on the trace attribute.
- [x] Have the chat's run summary mention it ("checked against the page as fetched at
      14:05"). Find where the monitoring node builds the reply in
      [monitoring_node.py](../../app/services/monitoring_node.py).
      Done as a deterministic `OfferingOutcome.source_note`, plus one instruction line
      in [agent.py](../../app/agent.py) telling the model to report it.
- [x] Test: two runs within the window → the second is marked reused, with the first run's
      `retrieved_at`.

### Phase 8: Validation

- [x] `uv run pytest tests/unit tests/integration`: all green.
      772 passed. Not counted: `test_build_extraction_review_bundle.py` already failed to
      import on `adk-native-runtime` (`app.domain.discovery` doesn't exist);
      `test_agent_stream` needs a Gemini key; `test_server_e2e` can't resolve the Docker
      hostname `db` from the host.
- [x] `uv run pytest -m browser`: all green locally.
- [x] `agents-cli lint`: clean.
      ruff check and format are clean. codespell is clean except for the untracked
      `demo/mirror/` bank HTML, which predates this work. `ty` diagnostics went from 45 to
      44, none in changed files.
- [x] Re-run the survey and save it as `data/seed-survey-<date>.json`. Expected: 13/13 in
      `browser` mode, every seed passes the floor, no silent caps.
- [ ] Run one real monitoring pass over all seeds against a scratch database copy (the
      `tariff_rt` pattern), with the spend limits from `runtime-tests/cost_guard.py`. Record
      per seed: outcome, failure code if any, tables, PDFs, and warning codes.
      *Not run yet:* it spends Gemini budget. Waiting for approval.
- [ ] Run it again immediately after the window expires (or with
      `ACQUISITION_FRESHNESS_HOURS=0`). Page ids must be unchanged, extraction must be all
      cache hits, and no `tariff_changes` rows should be written.
      *Not run yet* (same reason). The page-id half is verified live without Gemini:
      overdraft and consumer_standard, fetched twice each, kept their ids.
- [x] Update this document: set every item's status, and record the before/after survey in
      the summary.

### Follow-ups outside acquisition

- [ ] X1: set `temperature=0` on semantic extraction
      ([semantic_extraction.py:266](../../app/services/semantic_extraction.py#L266)) and PDF
      transcription ([gemini_pdf_extractor.py:78](../../app/services/gemini_pdf_extractor.py#L78)).
      This belongs to the extraction plan; do it after Phase 4, so the effect of each change
      can be measured separately.
- [ ] A13: revisit only if Phase 8 or later runs show re-extraction on small page edits
      costing noticeable spend or producing false changes.
