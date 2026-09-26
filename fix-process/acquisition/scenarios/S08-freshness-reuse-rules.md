# S08: Reuse serves only complete acquisitions

**What it checks.** Within the window a complete acquisition is served again without touching the bank and marked `reused`; a partial one (a PDF failed to download) and a failed one are never stored.

**Plan items.** A5, A12.

**Steps.** Scratch database, `overdraft`. (a) Acquire, then acquire again. (b) Clear the stored snapshot; acquire with a PDF downloader whose byte limit makes every PDF fail (cap 2); then acquire again. (c) Acquire with the browser disabled (fails the floor).

**Pass criteria.** (a) first is fetched and stored, second is `reused` with 0 bank requests and 0 renders; (b) two `linked_document_failed` warnings, nothing stored, the next acquire fetches again; (c) fails, nothing stored.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Re-run 2026-09-26 after the F1 fix (`733c4ba`), branch `integration/process-fixes`. Raw result: [results/S08.json](results/S08.json).

Same outcome as the first run, which matters after F1: a download that fails for a reason
other than 404 still blocks reuse.
- **(a)** First acquisition fetched and stored; the second `reused`, with 0 bank requests
  and 0 renders.
- **(b)** Two `linked_document_failed: … source.size_rejected` warnings; **nothing stored**;
  the next acquisition fetched again.
- **(c)** Browser disabled: `source.incomplete_content`, nothing stored.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 6 | 3 | 2.36 MB | 38.6 s |

### Earlier run

PASS, same outcome. Cost: 6 bank requests, 3 renders, 2.4 MB, 40 s, $0.
