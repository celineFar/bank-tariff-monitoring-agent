# S05: A browser failure fails; static HTML is never used instead

**What it checks.** When the browser cannot start, or cannot load the page, the acquisition fails with a typed code and no artifact, even though static HTML was fetched.

**Plan items.** A4 (Q1), A8.

**Steps.** Against `overdraft`: (a) point Playwright at an empty browsers directory so Chromium cannot launch; (b) set the navigation timeout to 10 ms so navigation fails.

**Pass criteria.** (a) `source.browser_unavailable`; (b) `source.browser_failed`. In both, no `PageArtifact` is returned.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S05.json](results/S05.json).

- **(a)** With Playwright pointed at an empty browsers directory, Chromium could not
  launch. Result: `source.browser_unavailable`, with no artifact. The static page had been
  fetched (1 request) but was not used.
- **(b)** With a 10 ms navigation timeout, navigation failed. Result: `source.browser_failed`
  (renderer reason `NAVIGATION`), with no artifact.

Before the fix, (a) escaped as a raw Playwright error reported as `source.validation_failed`,
and both would have fallen back to static HTML if it looked "useful".

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 2 | 2 | 0.0 MB | 5.6 s |
