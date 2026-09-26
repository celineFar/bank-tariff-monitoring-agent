# S04: PDFs are downloaded, and the cap is never silent

**What it checks.** With the new cap of 40, the seeds with the most PDF links download all of them; with a low cap, the cut is a typed warning naming how many were skipped.

**Plan items.** A7, A6.

**Steps.** (a) Acquire `mortgage_online` and `mortgage_construction` with downloads on and cap 40. (b) Acquire `overdraft` with the cap lowered to 5.

**Pass criteria.** (a) Every distinct PDF link downloaded, no cap warning, no download failure. (b) Exactly 5 downloaded and one `acquisition.linked_document_cap_reached` warning naming the skipped count.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **FAIL (criterion); behaviour correct**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S04.json](results/S04.json).

- **(b) Cap:** `overdraft` with cap 5 downloaded exactly 5 of its 10 PDFs and carried one
  warning, `acquisition.linked_document_cap_reached: 5 of 10 linked documents not downloaded
  (cap 5)`. Passes.
- **(a) Full download:** `mortgage_online` downloaded 15 of 17 and `mortgage_construction` 15
  of 16, with no cap warning. The missing three are **dead links on the bank's site**: each
  failed with `source.not_found` and was recorded as an
  `acquisition.linked_document_failed` warning. Checked directly: all three return HTTP 404.
  All are historical-terms PDFs under `Portals/0/files/Personal/Loans/previous-loans/`, and
  one URL carries the bank's own typo (`mortage_personal_construction_ed70_eng.pdf`).

The criterion "every PDF link downloaded, no failure" assumed every link works, so the
scenario fails as written. The code did what it should: it downloaded everything that exists
and recorded each dead link as a typed warning.

**Finding F1 (design).** Because a failed download marks the acquisition as partial (A5), and
these links are permanently dead, **every acquisition of `mortgage_online` and
`mortgage_construction` is partial, so the freshness window never applies to them**: each run
refetches the page and all its PDFs. There is no Gemini cost (transcription is cached by PDF
hash), only repeated bank traffic. A permanent 404 should probably not count as "partial" the
way a timeout or 5xx does. Candidate fix: exclude `source.not_found` from the partial rule, and
keep it as a warning.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 41 | 3 | 13.93 MB | 59.6 s |
