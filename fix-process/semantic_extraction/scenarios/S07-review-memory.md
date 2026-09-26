# S07: A review decision is asked once

**What it checks.** Review decision memory (SE12).

**Plan items.** SE12.

**Steps.** With a fake extractor that returns a field failing validation the same way every time: run, resolve the review, run again; then change the cited evidence and run a third time.

**Pass criteria.** Run 2 creates no review and no model call for that field and writes `review_decision_reused`; run 3 opens a new review.

**Gemini.** None (fake extractor).

## Result: **PASS**

Raw result: [results/S07.json](results/S07.json).
`test_se12_a_review_decision_is_asked_once_and_reused_until_evidence_changes` with fakes: run
1 opens a grounding review; with the decision remembered, run 2 has no review, reuses it
(matched by prompt), and makes **0 model calls**; a changed evidence text re-opens it. The
Postgres storage is covered by `tests/integration/test_semantic_extraction_memory_postgres.py`.
`review_decision_reused` audit events are written by the pipeline (code path, not run live).
