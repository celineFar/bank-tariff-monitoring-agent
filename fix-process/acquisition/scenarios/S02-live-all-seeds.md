# S02: Every seed renders completely

**What it checks.** Each of the 13 enabled seeds is acquired live, rendered in the browser, and passes the completeness floor with real tariff structure.

**Plan items.** A2 (content-ready wait), A3 floor, A4 (no fallback), A8.

**Steps.** Acquire all 13 seeds once with the production composition (PDF downloads off, no database).

**Pass criteria.** 13/13 in `browser` mode; each has main content >= 1,500 and at least one table, PDF link or payload; no acquisition failure.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S02.json](results/S02.json).

All 13 seeds rendered in `browser` mode and passed the floor. No warnings.

| Seed | Main text | Tables | PDF links | Payloads | Clicks |
|---|---|---|---|---|---|
| consumer_standard | 18,502 | 3 | 12 | 22 | 7 |
| overdraft | 13,218 | 3 | 10 | 17 | 6 |
| credit_line | 19,665 | 3 | 11 | 13 | 7 |
| online_consumer_finance | 7,711 | 3 | 5 | 22 | 4 |
| mortgage_online | 27,869 | 3 | 17 | 19 | 10 |
| mortgage_primary | 40,870 | 3 | 14 | 19 | 10 |
| mortgage_diaspora | 3,294 | 0 | 0 | 17 | 0 |
| mortgage_secondary_market | 39,992 | 3 | 12 | 15 | 10 |
| mortgage_commercial | 24,825 | 2 | 9 | 13 | 9 |
| mortgage_express | 8,360 | 4 | 3 | 20 | 5 |
| mortgage_no_income_verification | 4,774 | 1 | 1 | 22 | 4 |
| mortgage_renovation | 44,878 | 3 | 14 | 14 | 10 |
| mortgage_construction | 47,725 | 4 | 16 | 13 | 11 |

The thinnest page is `mortgage_diaspora`: a campaign landing page with no table and no PDF link
in its DOM, which passes on its 17 data payloads and 3,294 characters of main text (floor
1,500). Before the fix, 6 of these 13 were read from static HTML with no tables, PDFs or
payloads.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 13 | 13 | 29.67 MB | 180.9 s |
