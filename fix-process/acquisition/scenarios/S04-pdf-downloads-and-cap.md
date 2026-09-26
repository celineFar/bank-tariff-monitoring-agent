# S04: PDFs are downloaded, and the cap is never silent

**What it checks.** With the new cap of 40, the seeds with the most PDF links download every PDF that exists; a dead link is a `linked_document_missing` warning that does not stop the page being reused; with a low cap, the cut is a typed warning naming how many were skipped.

**Plan items.** A7, A6, A5 and its follow-up F1.

**Steps.** (a) Acquire `mortgage_online` and `mortgage_construction` with downloads on and cap 40. (b) Acquire `overdraft` with the cap lowered to 5. (c) On the scratch database, acquire `mortgage_construction` (which has a dead link) through the freshness and completeness gates, then again.

**Pass criteria.** (a) Every PDF that exists downloaded; the only warnings are `acquisition.linked_document_missing`, one per dead link; no cap warning. (b) Exactly 5 downloaded and one `acquisition.linked_document_cap_reached` warning naming the skipped count. (c) The first acquisition is stored despite its dead link; the second is `reused` with 0 bank requests and 0 renders.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Re-run 2026-09-26 after the F1 fix (`733c4ba`), branch `integration/process-fixes`. Raw result: [results/S04.json](results/S04.json).

- **(a) Full download:** `mortgage_online` downloaded 15 of 17 and `mortgage_construction` 15
  of 16. The missing three are dead links on the bank's site (HTTP 404, historical-terms
  PDFs under `previous-loans/`). Each is now an `acquisition.linked_document_missing`
  warning; there is no `linked_document_failed` and no cap warning.
- **(b) Cap:** `overdraft` with cap 5 downloaded exactly 5 of 10, with the warning
  `acquisition.linked_document_cap_reached: 5 of 10 linked documents not downloaded (cap 5)`.
- **(c) Reuse despite a dead link (F1):** the first acquisition of `mortgage_construction`
  carried its `linked_document_missing` warning and **was stored**. The second was served
  from the store: `reused = true`, **0 bank requests, 0 renders**. Before the fix, this page
  was refetched in full, with every PDF, on every run.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 58 | 4 | 18.82 MB | 83.4 s |

### Earlier run

**FAIL (criterion).** The three dead links failed with `source.not_found` as
`acquisition.linked_document_failed` warnings, and the criterion assumed every link worked.
The code behaved correctly, but a failed download marked the acquisition as partial, so
these two pages could never be reused (finding F1). Cost: 41 bank requests, 3 renders,
13.9 MB, 60 s, $0 Gemini.
