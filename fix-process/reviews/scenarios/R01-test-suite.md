# R01: the test suite

**Checks.** Every item's regression test in `tests/unit/test_review_fixes.py` passes
(no `xfail` left) and the rest of the suite stays green.

**Run.**

```bash
uv run pytest tests/unit tests/integration -q
```

**Pass when.** The only failures are the known Gemini-key tests
(`test_agent`/`test_agent_engine_app`/`test_server_e2e`, which need a live key).

**Result.** _pending (Phase 5)_
