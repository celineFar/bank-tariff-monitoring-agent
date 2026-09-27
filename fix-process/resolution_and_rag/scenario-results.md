# Resolution and RAG: scenario results

## Baselines (Phase 0, `180ea9f`)

- **Test suite:** 1107 passed, 5 skipped; 1 failed + 3 errors, the 4 known tests that
  need a Gemini key (`test_agent_stream` and the 3 `test_server_e2e` tests). Postgres
  tests ran with `TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_acquisition_test`.
- **Case set, keyword resolver:** 85/126 cases pass (67%), with 4 safety mismatches
  and 3 crashes. The Gemini fallback was a failing stub (its production failure
  behaviour), so a few cases that reach Gemini could pass live. Per case:
  [baseline-case-set.txt](baseline-case-set.txt), from
  [probes/baseline_case_set.py](probes/baseline_case_set.py).
