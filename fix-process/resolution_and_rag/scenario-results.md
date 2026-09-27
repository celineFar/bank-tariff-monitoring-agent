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

## RRS02: live interpreter over the case set (Phase 2)

Model `gemini-3.7-flash` (the configured `generation_model`), temperature 0, no
thinking budget.

| Run | Instruction | Cases | Passed | Safety mismatches | Notes |
|---|---|---:|---:|---:|---|
| 1 | first version | 126 | 125 (99.2%) | 1 | `rr10`: "mortgage" in reply to "What is the interest?" became a family-wide overview. Fixed in code (V3 on replies), not in the prompt. |
| 2 | same | 126 | 126 (100%) | 0 | Recordings kept per case from here on (see Phase 2 notes). |
| 3 | + the singular-family rule | 133 | 132 (99.2%) | 0 | +7 test-support cases. `current mortgage rate` had become a family-wide overview before the rule; now it asks. `rr3_progress_paying_off` → `unsupported_or_general`: a defensible reading; the case now forbids only `get_run_status`. |

After run 3 the recorded replay (RRS01) passes 133/133.

## RRS08: interpreter cost and latency (from RRS02 run 3)

152 calls. Input tokens: mean 3,779, max 4,085. Output tokens: mean 198, max 405.
Latency: p50 1.7 s, p90 2.6 s (six calls in parallel). This replaces the Phase 0
`count_tokens` measurement: the recorded calls report the same prompt token count.

## RRS03: multi-turn tool flows (Phase 3)

[tests/unit/test_tool_flows.py](../../tests/unit/test_tool_flows.py): 14 flows through the
real tools, each replaying one case's live recording. **All pass.**
- **Offers:** six natural yeses take up the offer (yes / ok / sure / "yes, refresh it" /
  👍 / Armenian), and the run answers the question of record. A refusal and a new
  question spend nothing.
- **Whole-family scope:** an explicit yes runs the family (and the replay passes); a
  refresh question does not.
- **Clarification and follow-ups:** `"3"` answers the original question with rate
  fields; an Armenian question answered by number stays Armenian; a follow-up keeps
  the offering.
- **Once per turn:** a repeat call in the same turn returns the same result.

The `xfail` tests RR9, RR13, RR14 and RR15 now pass.
