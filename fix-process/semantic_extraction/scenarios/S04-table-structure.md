# S04: Tables keep their header hierarchy

**What it checks.** Normalized tables carry column paths: Overdraft and Credit line card tiers, Mortgage Primary and Secondary Market currencies.

**Plan items.** SE1, SE3.

**Steps.** Run `fix-process/normalization/survey/check_ground_truth.py` with the column-path facts added in Phase 2.

**Pass criteria.** Every column-path fact passes; no existing ground-truth fact regresses.

**Gemini.** None.

## Result: **not run**
