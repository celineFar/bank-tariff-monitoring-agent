# S06: A dated offer expires without a new Gemini call

**What it checks.** On the real online consumer-finance page, whose offer "is valid from
15.04.26 to 12.01.27", a cached assessment becomes `possibly_stale` the day after the end
date, from the stored effective period alone (SD5).

**Plan items.** SD5.

**Steps.** A fake classifier answers every item `current` with that period. Discover on
2026-09-26, then again on 2027-01-13 with the same cache.

**Pass criteria.** All Gemini-decided items `current` on the first date and `possibly_stale`
on the second; no new call for the second.

**Gemini.** None.

## Result: **PASS**

Raw result: [results/S06.json](results/S06.json). On 2027-01-13 every item is
`possibly_stale` and none is selected except the page's own document-level rule; 0 new
calls.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 0.4 s |
