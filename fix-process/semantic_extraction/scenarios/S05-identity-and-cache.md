# S05: Evidence identity and the cache hold

**What it checks.** Evidence IDs and the extraction cache key survive changes that do not change what the model sees.

**Plan items.** SE10, SE11.

**Steps.** Normalize a seed, insert a paragraph above its tariff table and change an unrelated block, rebuild the evidence; then run extraction twice with a counting fake extractor, and read the live re-run from `data/extraction-check-after.json`.

**Pass criteria.** The tariff table's evidence IDs are unchanged; in budgeted mode, the calls whose units did not change are cache hits; a second identical run makes 0 extraction calls (live re-run: 0 calls, $0).

**Gemini.** None (the live re-run uses the cache only).

## Result: **not run**
