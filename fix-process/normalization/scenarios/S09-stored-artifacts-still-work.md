# S09: Artifacts and baselines stored before the fixes still work

**What it checks.** Data written by the old code still loads and normalizes: acquisition artifacts from before the fixes (old parse, network payloads, no table ids) and an acquisition baseline that records a payload count.

**Plan items.** N23 (positional fallback), N22 (payload fields ignored), freshness reuse safety.

**Steps.** Normalize the 13 artifacts of the Phase 0 capture (`.cache/`, stored with the pre-fix code) through the current service. Read the overdraft baseline from the scratch `tariff_acquisition_scenarios` database (read-only) and compare it with today's inventory.

**Pass criteria.** 13/13 load and normalize; every table block is linked to its table; the stored baseline has `payloads: 17` and today's page does not fail against it.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S09.json](results/S09.json).

**Stored artifacts.** All 13 artifacts of the Phase 0 capture load and normalize. They were
written by the pre-fix code, carry `network_payloads` and an inventory `payloads` count, and
their table blocks have no table id.
- Every table block is linked to its table through the positional fallback
  (35 of 35).
- Their quality scores (0.94–1.0) reflect the old parser's blocks. That is what an
  acquisition reused from before deploy would score within the freshness window (1 hour).

**Stored baseline.** The overdraft baseline in `tariff_acquisition_scenarios` was recorded
before capture was removed: `{'tables': 3, 'payloads': 17, 'pdf_links': 10, 'main_chars': 13218}`. Compared with today's inventory
`{'main_chars': 13305, 'tables': 3, 'pdf_links': 10}`, it gives **no failure reasons** (`[]`). The old
payload count is ignored, so no page fails "payloads 17 → 0".

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 1.9 s |

Round 1: PASS (0 Gemini calls, $0.00, 0 bank requests, 0 renders, 0.0 MB, 1.9 s).
