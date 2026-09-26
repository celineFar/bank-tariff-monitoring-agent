# S05: The cache holds: a re-run is free, and one new block reclassifies one item

**What it checks.** Running discovery and PDF link selection again with the same caches
makes no Gemini call (recorded Phase 7 run); and on the real primary-mortgage page, a block
inserted near the top, which renumbers every later block, sends only its own item to the
classifier (SD10).

**Plan items.** SD1 (cache scope), SD10, Phase 7 cache re-run.

**Steps.** Read `cache_rerun` from [../data/discovery-check-after.json](../data/discovery-check-after.json);
then run discovery twice on `mortgage_primary` with a counting fake classifier, the second
time with a new unheaded paragraph after the main heading and every block id shifted by one.

**Pass criteria.** 0 discovery and 0 selector calls in the re-run; exactly one item sent after
the insertion.

**Gemini.** None.

## Result: **PASS**

Raw result: [results/S05.json](results/S05.json).

- Recorded re-run: **0 discovery calls, 0 selector calls**, 279 assessments reused.
- Insertion: 20 items on the first run; **1 item** (the new paragraph's own) after the
  insertion. Before SD10 every section's fingerprint changed and all 20 were sent again.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 1.1 s |
