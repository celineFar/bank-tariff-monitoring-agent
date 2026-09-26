# S01: Offline test suite for acquisition

**What it checks.** The acquisition code paths behave as designed without touching the bank: unit tests, local-Chromium DOM tests (fixture pages, no network) and the Postgres integration tests for snapshots and baselines.

**Plan items.** All plan items with tests (A1-A12, A15).

**Steps.** Run the acquisition-related test files with `pytest`, including the `browser` tests and the Postgres tests against the scratch test database.

**Pass criteria.** Every selected test passes; none is skipped for a missing browser or database.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S01.json](results/S01.json).

143 tests passed, 0 skipped, across 13 files: the acquisition, identity, completeness,
freshness, failure-mapping, URL, parser, pipeline and monitoring-node unit tests; the local
Chromium DOM tests (fade-in without `<h1>`, `display:none` stays hidden, never-visible content
parses empty, interaction cap, navigating button stays on the page); and the two Postgres
integration tests (snapshots; baseline drop, reset and audit event), run against the scratch
test database.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 16.5 s |
