# IXS01: the test suite

**Checks.** The whole unit and integration suite passes with the indexing changes,
including the PostgreSQL tests.

**Run.**
```bash
TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_acquisition_test \
  uv run pytest tests/unit tests/integration -q
```

**Pass when.** Everything passes except the 4 tests that need a live Gemini key
(`test_agent_stream` and the 3 `test_server_e2e` tests); no `xfail` is left in
`tests/unit/test_indexing_fixes.py` or `tests/integration/test_indexing_fixes_postgres.py`.

**Baseline (Phase 0, 2026-09-26).** 1064 passed, 5 skipped; 1 failed + 3 errors (the
4 known Gemini-key tests).

**Result.** _Filled in Phase 6._
