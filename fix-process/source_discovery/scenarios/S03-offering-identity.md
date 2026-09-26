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

## Result: **FAIL** (two of three criteria met)

Raw result: [results/S03.json](results/S03.json).

- **Express table: `related` on all four pages** (it was `current` on all four before).
- **Own tables: 28 of 29 current.** The construction page's "Loan for construction of
  commercial real estate" table is still called `related`, although the page says the
  offering is "for residential purposes, as well as for commercial use".
- **Leaks: 29 → 7**, but not 0. The seven are cross-sell cards Gemini still reads as the
  offering: "Online mortgage" on the construction page, "Mortgage from secondary market" on
  the renovation page, "Construction loan" on the online and secondary-market pages, and the
  secondary-market card on the online page (debatable: the online offering covers the
  secondary market, the card advertises a different loan).

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 0.1 s |
