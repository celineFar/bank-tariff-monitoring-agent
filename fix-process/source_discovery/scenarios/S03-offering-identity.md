# S03: With the offering named, sibling products are told apart

**What it checks.** In the recorded Phase 7 Gemini run (round 2), the "Express Home Mortgage
Loan" table is `related_product` on the four mortgage pages that show it; every table that
belongs to the offering stays current; and no sibling cross-sell section is called current.

**Plan items.** SD1, SD3; Phase 7 "every sibling-product table and section labelled
related_product".

**Steps.** Read [../data/discovery-check-after-final-labels.json](../data/discovery-check-after-final-labels.json)
(the round 2 run, scored on the final labels) and the baseline scored the same way
([../data/discovery-check-before-final-labels.json](../data/discovery-check-before-final-labels.json)).

**Pass criteria.** Express table `related` on all four pages; all own tables current,
unknown or generic; no `leak` on a page block.

**Gemini.** None in the scenario; the recorded run cost $0.33 (see the Phase 7 notes).

## Result: **FAIL** (two of three criteria met; Phase 8 re-run 2026-09-26)

Raw result: [results/S03.json](results/S03.json). Now read from
[../data/discovery-check-after-crosssell-rule-final-labels.json](../data/discovery-check-after-crosssell-rule-final-labels.json):
round 2's recorded Gemini answers with the Phase 8 cross-sell rule applied to the 16
sections it now decides, no Gemini call.

- **Express table: `related` on all four pages** (it was `current` on all four before).
- **Leaks: 29 → 0.** The seven cross-sell cards Gemini still read as the offering are now
  decided by the cross-sell rule (a small section linking to another offering's page).
- **Own tables: 28 of 29 current.** The construction page's "Loan for construction of
  commercial real estate" table is still `related`, also in a Phase 8 re-check of that page
  with the current prompt ([../data/discovery-check-phase8-construction.json](../data/discovery-check-phase8-construction.json),
  $0.009). Gemini's reason: it is "distinct from the 'Construction Mortgage' offering". The
  catalog names the offering "Construction Mortgage" while the page says it covers
  "residential purposes, as well as … commercial use"; see the Phase 8 notes.

Phase 7 result (before the rule): FAIL, 7 leaks.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 0.1 s |
