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

## Result: **FAIL** (two small misses; final Phase 8 pass, 2026-09-26)

Raw result: [results/S03.json](results/S03.json). Now read from the final Gemini pass with the
final code and labels ([../data/discovery-check-final.json](../data/discovery-check-final.json)).

- **Express table: `related` on all four pages** (it was `current` on all four before).
- **The construction page's commercial table is now `current`**, after the catalog alias
  (Q10).
- **Leaks: 29 → 1.** The cross-sell cards are decided by rule; the one leak is a card's
  heading on the construction page, which sits in the section above the card.
- **Own tables: 28 of 29.** The consumer-loan page's "Loan service fees" table came back
  `related` in this run (it was `current` in the baseline and in Phase 7 round 2).

Phase 7 result: FAIL, 7 leaks and the construction commercial table.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 0.1 s |
