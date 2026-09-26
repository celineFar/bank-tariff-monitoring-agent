# S08: Evidence built from real bundles is labelled and stable

**What it checks.** The evidence the extraction model reads is built correctly from real pages: rows under an in-table section start with `Section: …`, footnotes show their marker, a table's section label is its heading path and title (never the table's flattened text), and evidence ids are identical across two captures.

**Plan items.** N2 (Q2), N3, N6 (section label), cache stability.

**Steps.** Normalize both live captures, select every source with a fixed discovery result (no Gemini classifier), build the evidence catalog, compare.

**Pass criteria.** Identical evidence ids across the two captures for all 13 seeds; section labels at most 200 characters; `Section:` rows present on a mortgage page; markers shown on notes.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S08.json](results/S08.json).

- **Evidence ids are identical across the two captures for all 13 seeds**, so the
  extraction cache hits on a re-run.
- **351 row items start with a `Section:` line.** They are on the four mortgage pages
  that carry the shared Express table and the "Term and interest rate" sub-sections. Other
  pages have no in-table sections.
- **72 of 72 footnote items show their marker** as the page does.
- **Table section labels are at most 129 characters:** heading path + table title,
  never the flattened table.

Example row evidence:
```
Section: Term and interest rate
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed | 3.4.2. Fixed | 3.4.3. Fixed
```
Example note evidence: `¹ These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of th…`

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 4.0 s |

### Round 1: FAIL: finding F1

The evidence content was the same as now. But the evidence ids of `consumer_standard`
differed between the two captures, for the reason described in S04 (a late footer module
changed the page id, which every evidence id hashes). The other 12 seeds matched
(0 Gemini calls, $0.00, 0 bank requests, 0 renders, 0.0 MB, 2.9 s). Fixed by leaving site chrome out of the page id.
