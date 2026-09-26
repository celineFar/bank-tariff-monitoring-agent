# S01: The offline test suite is green

**What it checks.** `uv run pytest tests/unit tests/integration` with `TEST_DATABASE_URL` set, and every `xfail` added in Phase 0 removed.

**Plan items.** All phases.

**Steps.** Run the suite against the scratch database `tariff_acquisition_test`.

**Pass criteria.** No failures other than the four tests that need a Gemini key (`test_agent_stream`, three `test_server_e2e` tests); no `xfail` marker left for an SE item.

**Gemini.** None.

## Result: **PASS**

Run 2026-09-26, branch `fix/semantic-extraction`. Raw result: [results/S01.json](results/S01.json).

- `1 failed, 1040 passed, 5 skipped, 18 warnings, 3 errors in 153.61s (0:02:33)`.
- The one failure and three errors are the four tests that need a Gemini key
  (`test_agent_stream`, three `test_server_e2e` tests); no other failure.
- `xfail` markers left in `test_semantic_extraction_fixes.py`: **0** (20 at Phase 0).
