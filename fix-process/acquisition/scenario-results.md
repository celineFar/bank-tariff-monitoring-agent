# Acquisition scenarios: results

Run 2026-09-26 on `integration/process-fixes`, against the live bank site and a scratch
database (`tariff_acquisition_scenarios`). Each scenario is described, with its result and
cost, in [scenarios/](scenarios/); raw results are in
[scenarios/results/](scenarios/results/). The fixes under test are in
[acquisition-fix-plan.md](acquisition-fix-plan.md).

**Result: 9 of 10 pass. Total Gemini cost: $0.00 (0 calls).** The one failure (S04) is caused
by dead PDF links on the bank's site. The code handled them correctly, but they expose a
design issue (F1).

## Scenarios

| # | Scenario | Result | Gemini | Bank requests | Renders | Data | Time |
|---|---|---|---|---|---|---|---|
| [S01](scenarios/S01-offline-test-suite.md) | Offline test suite (143 tests, incl. local Chromium and Postgres) | **PASS** | $0 | 0 | 0 | 0 MB | 17 s |
| [S02](scenarios/S02-live-all-seeds.md) | All 13 seeds render completely | **PASS** | $0 | 13 | 13 | 29.7 MB | 181 s |
| [S03](scenarios/S03-page-identity-stable.md) | Page ids stable across two fetches | **PASS** | $0 | 13 | 13 | 29.7 MB | 184 s |
| [S04](scenarios/S04-pdf-downloads-and-cap.md) | PDFs downloaded; the cap is never silent | **FAIL** (bank's dead links; behaviour correct) | $0 | 41 | 3 | 13.9 MB | 60 s |
| [S05](scenarios/S05-browser-failure-no-fallback.md) | Browser failure fails; no static fallback | **PASS** | $0 | 2 | 2 | 0 MB | 6 s |
| [S06](scenarios/S06-static-html-fails-floor.md) | Static HTML fails the floor on every seed | **PASS** | $0 | 13 | 0 | 0 MB | 24 s |
| [S07](scenarios/S07-baseline-drop-and-reset.md) | Sharp drop fails until the operator resets | **PASS** | $0 | 3 | 3 | 4.7 MB | 42 s |
| [S08](scenarios/S08-freshness-reuse-rules.md) | Reuse serves only complete acquisitions | **PASS** | $0 | 6 | 3 | 2.4 MB | 40 s |
| [S09](scenarios/S09-pipeline-records-acquisition.md) | The run records how and when the page was acquired | **PASS** | $0 | 2 | 1 | — | 15 s |
| [S10](scenarios/S10-url-safety.md) | Unsafe URLs refused before any request | **PASS** | $0 | 0 | 0 | 0 MB | 0 s |
| | **Total** | **9 / 10** | **$0.00** | **93** | **38** | **80.4 MB** | **9.5 min** |

How cost was measured:
- **Gemini**: acquisition makes no model calls. The harness proved this for every
  scenario: it ran with no API key and replaced the Gemini client constructor with one that
  raises and counts (0 attempts), and S09's `model_call_usage` table stayed empty.
- **Bank requests**: requests from the HTTP client (static pages and PDFs). A browser render
  makes its own requests (scripts, styles, data), which are not counted here; each render
  is counted in "Renders".
- **Data**: raw and rendered HTML, payloads and PDFs held in memory (S09 did not measure it).

## What the scenarios show

- **The six blind seeds are fixed.** All 13 seeds render in the browser with real tariff
  structure (S02). Before the fix, 6 were read from menus and footer text.
- **The completeness gate works in both directions.** Chrome-only static HTML is rejected on
  13/13 seeds with reasons (S06). A sharp drop against a page's baseline fails and keeps
  failing until an operator runs the reset script, which is audited (S07). The same failure
  reaches the run record through the real pipeline (S09).
- **No silent fallback.** A browser that cannot start, or cannot load the page, fails the
  offering with its own code (S05).
- **Unchanged pages keep their identity.** Page ids, content hashes and inventories were
  identical across two passes over all 13 seeds (S03), so extractions stay cached.
- **Reuse is safe and visible.** A reused acquisition costs 0 requests and is marked on the
  run. Partial and failed acquisitions are never stored for reuse (S08, S09).
- **Unsafe URLs never produce a request** (S10).

## Findings

**F1: A permanently dead PDF link turns off reuse for its page (design, low).**
`mortgage_online` and `mortgage_construction` link to three historical-terms PDFs that
return 404 on the bank's site. The code records each as `acquisition.linked_document_failed`,
which is correct. But the A5 rule treats any failed download as a partial acquisition and
never stores it for reuse, so these two seeds are refetched in full on every run, even within
the freshness window. There is no Gemini cost (transcription is cached by PDF hash), only
repeated bank traffic. Candidate fix: treat `source.not_found` as permanent. It stays a
warning, but doesn't block reuse; timeouts, transport errors and 5xx still would.
**Needs your decision.**

**O1: The main-text floor has little margin on the static side (observation).** Static
`credit_line` has 1,238 main characters against a floor of 1,500. The rule that reliably
rejected static pages was "no tables, PDF links or payloads", which held on 13/13. No change
suggested now. The floor is a second line, and the structure rule does most of the work.

## Not covered by these scenarios

- **A redirect through a non-allowlisted host, and a button that really navigates, on the live
  site.** Neither occurs on the bank's pages. Both are covered by unit tests and a local
  Chromium test (S01).
- **More than 25 data payloads on one page.** The maximum seen is 22. The cap-after-sort rule
  is covered by a unit test with 30 payloads in two arrival orders (S01).
- **Anything after acquisition.** Normalization, extraction and publication need Gemini, and
  are left for their own phase.

## Re-running

```bash
uv run python fix-process/acquisition/scenarios/run_scenarios.py            # all
uv run python fix-process/acquisition/scenarios/run_scenarios.py S07 S08    # some
```

The runner needs the local Postgres container (port 5434) and Chromium. S07–S09 rebuild the
`tariff_acquisition_scenarios` database from the migrations each time. S01 uses
`tariff_acquisition_test`.
