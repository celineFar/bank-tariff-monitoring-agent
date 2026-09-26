# S01: The offline test suite is green

**What it checks.** `uv run pytest tests/unit tests/integration` with `TEST_DATABASE_URL` set, and every `xfail` added in Phase 0 removed.

**Plan items.** All phases.

**Steps.** Run the suite against the scratch database `tariff_acquisition_test`.

**Pass criteria.** No failures other than the four tests that need a Gemini key (`test_agent_stream`, three `test_server_e2e` tests); no `xfail` marker left for an SE item.

**Gemini.** None.

## Result: **not run**
