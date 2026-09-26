# R01: the test suite

**Checks.** Every item's regression test in `tests/unit/test_review_fixes.py` passes
(no `xfail` left) and the rest of the suite stays green.

**Run.**

```bash
uv run pytest tests/unit tests/integration -q
```

**Pass when.** The only failures are the known Gemini-key tests
(`test_agent`/`test_agent_engine_app`/`test_server_e2e`, which need a live key).

**Result.** **PASS** (2026-09-26). `uv run pytest tests/unit tests/integration` with the local
test database: **1064 passed, 5 skipped, 0 xfailed**; the only failures are the 4 known
Gemini-key tests (`test_agent_stream`, 3 × `test_server_e2e`). Baseline before the fix:
1041 passed. No `xfail` is left in `tests/unit/test_review_fixes.py` (18 tests).
