# Normalization scenarios: results

Run 2026-09-26 on `fix/normalization`, against the live bank site and read-only copies of stored
data. There were two rounds:
- **Round 1:** all ten scenarios.
- **Round 2:** all ten again, after fixing finding F1, plus a new scenario, S11, that tests
  F1 directly.

The fixes under test are in [normalization-fix-plan.md](normalization-fix-plan.md). Each
scenario is described, with its result, earlier rounds and cost, in [scenarios/](scenarios/).
Raw results are in [scenarios/results/](scenarios/results/), produced by
[scenarios/run_scenarios.py](scenarios/run_scenarios.py).

**Result: 11 of 11 pass. Total Gemini cost: $0.00 (0 calls), across both rounds.**

In round 1, S04 and S08 failed on one finding (F1): a footer notice on the consumer-loan page
loads late, and page identity counted site chrome, so an unchanged page got a new id. That is
now fixed, and S11 proves it on the real pages.

## Scenarios

| # | Scenario | Result | Gemini | Bank requests | Renders | Data | Time |
|---|---|---|---|---|---|---|---|
| [S01](scenarios/S01-offline-test-suite.md) | Offline test suite (388 tests, incl. Postgres) | **PASS** (round 1: FAIL on my criterion) | $0 | 0 | 0 | 0 MB | 17 s |
| [S02](scenarios/S02-confirmed-bugs-fixed.md) | Every confirmed bug is gone on its original reproduction (12 checks) | **PASS** | $0 | 0 | 0 | 0 MB | 3 s |
| [S03](scenarios/S03-live-seeds-score.md) | All 13 live seeds normalize completely: score 1.0, ground truth 0/352 | **PASS** | $0 | 137 | 13 | 29.3 MB | 238 s |
| [S04](scenarios/S04-identity-stable.md) | Unchanged pages keep their identity and output across two captures | **PASS** (round 1: FAIL, F1) | $0 | 137 | 13 | 29.3 MB | 227 s |
| [S05](scenarios/S05-pdf-admission-live.md) | The right PDFs are skipped on the live pages (117 links) | **PASS** | $0 | 0 | 0 | 0 MB | 36 s |
| [S06](scenarios/S06-real-gemini-pdfs-replayed.md) | Real Gemini PDF transcriptions normalize correctly (replayed, 9 PDFs) | **PASS** | $0 | 0 | 0 | 0 MB | 8 s |
| [S07](scenarios/S07-pdf-failures-without-gemini.md) | PDF failures become the right warnings; bugs are not hidden | **PASS** | $0 | 0 | 0 | 0 MB | 1 s |
| [S08](scenarios/S08-evidence-from-real-bundles.md) | Evidence from real bundles is labelled and stable | **PASS** (round 1: FAIL, F1) | $0 | 0 | 0 | 0 MB | 4 s |
| [S09](scenarios/S09-stored-artifacts-still-work.md) | Artifacts and baselines stored before the fixes still work | **PASS** | $0 | 0 | 0 | 0 MB | 2 s |
| [S10](scenarios/S10-first-run-pdf-cost.md) | What the first production run will pay for PDFs | **PASS** (forecast) | $0 | 0 | 0 | 0 MB | 28 s |
| [S11](scenarios/S11-late-footer-keeps-page-id.md) | A late footer module does not rename the page (F1, 10 pages) | **PASS** | $0 | 0 | 0 | 0 MB | 19 s |
| | **Total (latest results)** | **11 / 11** | **$0.00** | **274** | **26** | **58.5 MB** | **9.7 min** |

**Cost of both rounds together: $0.00 of Gemini (0 calls).**

| Round | Bank requests | Renders | Data | Time |
|---|---|---|---|---|
| Round 1 | 274 | 26 | 58.5 MB | 9.5 min |
| Round 2 | 274 | 26 | 58.5 MB | 9.7 min |
| **Both** | **548** | **52** | **117 MB** | **19 min** |

Round 1's time includes S01's first attempt.

How cost was measured:
- **Gemini.** Every scenario ran with no API key, and the Gemini client constructor was
  replaced by one that counts the attempt and raises. There were 0 attempts in either round.
- **Bank requests.** Requests from the HTTP client: static page fetches and PDF downloads.
  A browser render makes its own requests (scripts, styles), which are not counted; each
  render is counted in "Renders". Only S03 and S04 touch the bank: two full captures per
  round.
- **Data.** Rendered HTML and PDFs held for the captures.
- **Databases.** Read-only access to `tariff_rt` (stored transcriptions) and
  `tariff_acquisition_scenarios` (a stored baseline). S01's tests use the scratch
  `tariff_acquisition_test` database.

## Was Gemini needed? No.

- **Page normalization never calls a model.** Parsing, tables, sections, footnotes, numbers,
  PDF admission, warnings, quality scores and page identity are all deterministic.
- **Linked PDFs do use Gemini, for transcription**, but only its *output* matters to
  normalization. S06 replays 9 real transcriptions by `gemini-3.1-flash-lite`, stored earlier
  in `tariff_rt`, through the real extraction service. That tests conversion, per-cell
  citations, clean headers, scores and warnings at $0.
- What is not re-tested live is the model call itself (prompt, retries, fallback models).
  That code did not change beyond the error types, which S07 and the unit tests cover.

## What the scenarios show

- **The confirmed bugs are fixed on their original reproductions** (S02), and **the live
  pages come out complete**: every seed scores 1.0 against its baseline, and the ground
  truth has 0 failures on today's pages (S03).
- **Unchanged pages keep their identity.** Page ids, normalized pages and evidence ids are
  identical across two captures on all 13 seeds (S04, S08), even when a footer module loads
  late (S11). A re-run hits every content-addressed cache.
- **The right PDFs are skipped.**
  - 62 superseded PDF links are skipped, each with a warning, and no current one is skipped
    (S05).
  - The remaining cost is the website-terms PDF, which is transcribed because it is linked
    under "Consumer loan"; link metadata can't tell.
- **Real Gemini output normalizes correctly.** 9 PDFs, 450 table cells, and every cell cites
  its own row and cell (S06).
- **Failures are honest.** No key, a broken file, or a bug in the PDF path each gives the
  right outcome, and a bug fails the stage instead of hiding as a model warning (S07).
- **Evidence is labelled.** 351 rows carry their `Section:` line and all 72 footnotes show
  their marker. No table is labelled with its own flattened text any more (S08).
- **Old data still works.** Artifacts stored before the fixes normalize, and a baseline that
  still counts payloads does not fail a page (S09).
- **First production run for PDFs** (S10): 28 of 29 admitted PDFs (125 pages) would be
  transcribed, for about **$0.15–$0.21**, estimated from stored output sizes and list prices,
  not measured. 8 of those are only invalidated by the cache key (the deferred N17), which is
  about $0.05 once.

## Findings

**F1: a late-loading footer module renamed the page. Fixed.** Found by S04 and S08 in round 1.
- **What happened.** The consumer-loan page's footer notice ("Dear User, If you find any
  discrepancies…") sometimes arrives after the render has finished: it was missing in 1 of 52
  renders that day.
- **Why it mattered.** Page identity (`page_content_hash`, acquisition A1) hashed every
  parsed block, chrome included. So the page got a new id, every evidence id on it changed,
  and the page would have been extracted again on that run.
- **Fix.** The parser now reports the ids of everything in the site header, navigation and
  footer (`ParsedHtml.chrome_ids`), and the page hash leaves them out. A changed tariff still
  renames the page; a late footer module or a menu edit does not.
- **Evidence.** 3 new tests in `tests/unit/test_acquisition_identity.py`, 2 of which fail on
  the old code, and S11 on the real pages.
- **One-time effect.** Every page's id changes once more, on the first run after deploy (part
  of the Q5 one-time cost).
- Documented in `docs/acquisition.md`, `docs/architecture.md` and the acquisition plan (A1).

**F2: Postgres integration tests skip silently without `TEST_DATABASE_URL`** (S01). The
suite results recorded in the fix plan counted them as skipped. With the variable set, the
full suite passes (951 tests; 5 optional-OCR skips; only the 4 tests that need a Gemini key
fail). The acquisition harness read the database password from a repo-root `.env` that no
longer exists; this harness reads it from the database container's environment, in memory
only.

**Known, not new:**
- the two website-profile PDFs (`web-info*.pdf`) are still transcribed (S05);
- the first production run pays the one-time PDF re-transcription (S10, N17 deferred);
- block and link ids are still positional (acquisition A13, deferred), so a late module in
  the *header* would still shift the ids that follow it. Only footer modules were seen
  loading late.

## How to re-run

```
uv run python fix-process/normalization/scenarios/run_scenarios.py            # all eleven
uv run python fix-process/normalization/scenarios/run_scenarios.py S06 S11    # a subset
```

S03 captures into `.cache-scenario-1/` and S04 into `.cache-scenario-2/` (both git-ignored).
S05–S08, S10 and S11 read those captures, and S09 reads the Phase 0 capture in `.cache/`.
Run S03 and S04 first on a fresh machine.
