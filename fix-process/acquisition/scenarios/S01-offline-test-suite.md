# S01: Offline test suite for acquisition

**What it checks.** The acquisition code paths behave as designed without touching the bank: unit tests, local-Chromium DOM tests (fixture pages, no network) and the Postgres integration tests for snapshots and baselines.

**Plan items.** All plan items with tests (A1-A12, A15).

**Steps.** Run the acquisition-related test files with `pytest`, including the `browser` tests and the Postgres tests against the scratch test database.

**Pass criteria.** Every selected test passes; none is skipped for a missing browser or database.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Re-run 2026-09-26 after the F1 fix (`733c4ba`), branch `integration/process-fixes`. Raw result: [results/S01.json](results/S01.json).

145 tests passed, 0 skipped (143 in the first run, plus the two F1 tests: a 404 is a
`linked_document_missing` warning, and such an acquisition is still stored and reused).

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 17.4 s |

### Earlier run

PASS: 143 tests, 16.5 s, $0.
