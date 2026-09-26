# S04: Tables keep their header hierarchy

**What it checks.** Normalized tables carry column paths: Overdraft and Credit line card tiers, Mortgage Primary and Secondary Market currencies.

**Plan items.** SE1, SE3.

**Steps.** Run `fix-process/normalization/survey/check_ground_truth.py` with the column-path facts added in Phase 2.

**Pass criteria.** Every column-path fact passes; no existing ground-truth fact regresses.

**Gemini.** None.

## Result: **PASS**

Raw result: [results/S04.json](results/S04.json). `check_ground_truth.py` on
`.cache-live-2`: **0 of 372 checks failed**, including the
15 column-path cell facts (Overdraft and Credit line card tiers, Primary and
Secondary currencies, the no-income campaign's refinancing/new-loan columns) and the
headline key/value blocks added in Phase 2. The same 20 new facts fail on the Phase 1 code.
