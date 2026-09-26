# S01: Offline test suite for source discovery

**What it checks.** The source-discovery code paths behave as designed without Gemini: every
regression test from Phase 0, the new tests of Phases 1–7, and the suites that consume
discovery (selection, projection, pipeline, PDF extraction, config), including the Postgres
tests for the offering-scoped cache (migration 019), `pdf_link_selections` (migration 020) and
`knowledge_chunks`.

**Plan items.** SD1–SD18, Phase 7 "all green, no `xfail` left".

**Steps.** Run 13 test files with `pytest`, with `TEST_DATABASE_URL` pointing at the scratch
`tariff_acquisition_test` database on the dev container.

**Pass criteria.** Every test passes and none is skipped.

**Gemini.** None.

## Result: **PASS**

2026-09-26, branch `fix/source-discovery`. Raw result: [results/S01.json](results/S01.json).

195 passed across 13 files, nothing skipped; the Postgres tests ran against
`tariff_acquisition_test`.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 40.0 s |
