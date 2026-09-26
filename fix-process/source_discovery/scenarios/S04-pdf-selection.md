# S04: Gemini selects the offering's PDFs from their links

**What it checks.** The two PDF steps together: the recorded Phase 7 link selection, then the
Phase 8 content check of every PDF it kept. Every PDF labelled `current_product` or
`shared_terms` must end up as the offering's terms; none labelled `related_product`,
`irrelevant` or `historical` may.

**Plan items.** SD2, SD4, Q1.

**Steps.** Read [../data/discovery-check-after.json](../data/discovery-check-after.json) (55
admitted links on the 13 seeds) and [../data/pdf-content-check-phase8.json](../data/pdf-content-check-phase8.json)
(the 44 kept PDFs, checked on their text layer with the current prompt); labels in
[../data/seed-discovery-labels.json](../data/seed-discovery-labels.json).

**Pass criteria.** No own or shared PDF dropped; no sibling or irrelevant PDF kept.

**Gemini.** None in the scenario; the recorded selector calls cost $0.010 and the content
check $0.025.

## Result: **PASS** (Phase 8, 2026-09-26)

Raw result: [results/S04.json](results/S04.json).

- **No own or shared PDF lost** (0 of 40).
- **The website-profile PDF (3 links) is excluded** by the content check: its content is the
  bank's website terms, although its link says "Terms and Conditions" under the loan's terms.
- **The content check also caught an expired document the bank still links**:
  `renovation_loan_special_offer_eng.pdf` says "Term of the Campaign From April 8, 2025 until
  and including December 31, 2025". Its label was corrected to `historical`.
- `terms_flexible_mortgage_eng.pdf` is the primary-market mortgage's own terms under a
  developer condition (Q11); its label was corrected to `current_product`.
- 44 of 55 links transcribed (55 before); 40 kept as the offering's terms.

Phase 7 result (link selection only): FAIL, 4 wrong keeps.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 0.0 s |
