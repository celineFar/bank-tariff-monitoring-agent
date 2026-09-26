# S04: Gemini selects the offering's PDFs from their links

**What it checks.** In the recorded Phase 7 run (round 2), the PDF link selection keeps every
PDF labelled `current_product` or `shared_terms` and drops every one labelled
`related_product` or `irrelevant`.

**Plan items.** SD2, SD4, Q1.

**Steps.** Read [../data/discovery-check-after.json](../data/discovery-check-after.json) (55
admitted links on the 13 seeds, labels in
[../data/seed-discovery-labels.json](../data/seed-discovery-labels.json)).

**Pass criteria.** No own or shared PDF dropped; no sibling or irrelevant PDF kept.

**Gemini.** None in the scenario; the recorded selector calls cost $0.010 (12 calls).

## Result: **FAIL** (one of two criteria met)

Raw result: [results/S04.json](results/S04.json).

- **No own or shared PDF dropped** (0 of 40).
- **4 wrong keeps**: the website-profile terms (`web-info-eng.pdf` on the consumer-loan and
  credit-line pages, `web-info.pdf` on the online-finance page) and the flexible-mortgage
  programme terms on the primary page. The website-profile PDF is linked as "Terms and
  Conditions" under the loan's own terms section; from the link alone it looks like the
  loan's terms.
- **44 of 55 links transcribed, against 55 before**: 11 fewer transcriptions per full run.
  Before, all four wrong keeps (and the Express terms on four pages) became the offering's
  top-precedence official terms without any check; now only these four reach content, as
  `current_product` link decisions.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 0.0 s |
