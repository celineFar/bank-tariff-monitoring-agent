# S08: Reuse serves only complete acquisitions

**What it checks.** Within the window a complete acquisition is served again without touching the bank and marked `reused`; a partial one (a PDF failed to download) and a failed one are never stored.

**Plan items.** A5, A12.

**Steps.** Scratch database, `overdraft`. (a) Acquire, then acquire again. (b) Clear the stored snapshot; acquire with a PDF downloader whose byte limit makes every PDF fail (cap 2); then acquire again. (c) Acquire with the browser disabled (fails the floor).

**Pass criteria.** (a) first is fetched and stored, second is `reused` with 0 bank requests and 0 renders; (b) two `linked_document_failed` warnings, nothing stored, the next acquire fetches again; (c) fails, nothing stored.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S08.json](results/S08.json).

- **(a)** The first acquisition was fetched (1 static request, 1 render) and stored. The
  second, seconds later, was served from the store: `reused = true`, same `retrieved_at`,
  **0 bank requests, 0 renders**.
- **(b)** With a PDF downloader limited to 1 kB and cap 2, both PDFs failed
  (`linked_document_failed: … source.size_rejected`), alongside the cap warning. **Nothing was
  stored.** The next acquisition fetched and rendered again (1 request, 1 render).
- **(c)** With the browser disabled, the acquisition failed the floor
  (`source.incomplete_content`), and nothing was stored.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 6 | 3 | 2.36 MB | 40.0 s |
