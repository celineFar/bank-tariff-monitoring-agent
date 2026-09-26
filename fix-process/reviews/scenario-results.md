# Review fix: scenario results

Date: 2026-09-26 · Branch: `fix/reviews` · Plan: [review-fix-plan.md](review-fix-plan.md).
All scenarios ran offline or read-only; no model call was made ($0).

| Scenario | What it checks | Result |
|---|---|---|
| [R01](scenarios/R01-test-suite.md) | Test suite | **PASS**: 1064 passed, 5 skipped, 0 xfailed; only the 4 known Gemini-key tests fail |
| [R02](scenarios/R02-report-problems.md) | The report's confirmed problems (P2, P3, P4/B6, B1/D2, B4, B5/D4, P6/D5, B7, B8) | **PASS**: one passing test each |
| [R03](scenarios/R03-seed-review-sets.md) | Review sets on the seeds' real catalogs | **PASS** (input changed, see below): 0 bound violations in 120 reviews and 68 cited sets; labelled value shown in 46/48 missing-field reviews |
| [R04](scenarios/R04-old-reviews.md) | The 4 stored old-format reviews | **PASS**: all build; view 20 → 2–5 excerpts, 9–12 kB → 1.3–3.2 kB |
| [R05](scenarios/R05-tool-payload.md) | Model-facing tool payloads | **PASS**: `get_current_tariffs` 265,845 → 755 bytes; `get_tariff_history` 796,542 → 10,919 bytes |
| [R06](scenarios/R06-ranking-miss.md) | Ranking-miss audit event | **PASS** |

## What the validation changed

- **R03 found a ranking weakness and it was fixed.** On the first run, 6 of 48
  missing-field reviews did not show the labelled value: equal label scores were broken
  by page order (a navigation section or FAQ before the tariff table), and headline or
  calculator sections, which name many fields, outscored the table. `field_evidence_set`
  now breaks ties by source precedence, then tables first, and gives the second slot to
  the best table when the best unit is not one: 46 of 48. The 2 left are one seed whose
  table calls the amount "Financing limit" (no field term matches).
- **R03 input changed.** The plan expected real extraction results for all 13 seeds
  from the extraction cache; the cache holds one seed's answers and the budget is spent.
  Part A uses that seed's real answers; Part B uses every seed's real catalog with an
  extractor that finds nothing, which exercises the largest sets.

## Scripts

- `scenarios/run_review_sets.py`: R03 (replays the seeds; needs the dev database only
  for stored PDF transcriptions, read-only).
- `scenarios/run_stored_reviews.py`: R04 and R05 (read-only connection to `tariff_monitor`;
  rebuilds the pre-fix view from git commit `be049e5` for comparison).
- Reports: `scenarios/results/`.

## Not done

- **No live chat run.** A review was not taken end to end in `./tariff-chat` against a
  real run: that needs Gemini spend (source discovery, extraction) and the budget is
  spent. The pieces are covered by unit tests (node pause payload, CLI rendering and
  input, decision service) and Postgres tests (repository, migration 022).
- **Migration 022 is not applied to the dev database.** It is applied by the test
  database runs; applying it to `tariff_monitor` is part of deployment.
