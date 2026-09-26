# S09: The run records how and when the page was acquired

**What it checks.** Through the real `TariffPipeline`, each offering execution records `source_retrieved_at` and `acquisition_reused`, and an incomplete acquisition fails the offering with its code and reasons in the audit. The harness stops each run right after acquisition, before normalization, where Gemini would start.

**Plan items.** A12, A6, A8, the pipeline side of A3.

**Steps.** Scratch database, `overdraft`. Run 1: a fresh acquisition. Run 2: within the window. Run 3: the browser disabled. Normalization is replaced by a stub that stops the run.

**Pass criteria.** Runs 1 and 2 record `source_retrieved_at`, with `acquisition_reused` false and then true (same time), and stop at normalization. Run 3 fails at acquisition with `source.incomplete_content`, with the reasons in the audit payload. `model_call_usage` stays empty.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Re-run 2026-09-26 after the F1 fix (`733c4ba`), branch `integration/process-fixes`. Raw result: [results/S09.json](results/S09.json).

Same outcome as the first run: runs 1 and 2 record the same `source_retrieved_at`, with
`acquisition_reused` false and then true, and stop at the harness's normalization stub. Run 3
fails at acquisition with `source.incomplete_content`, with its reasons in the audit payload.
`model_call_usage` has 0 rows.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 2 | 1 | 0.0 MB | 16.2 s |

### Earlier run

PASS, same outcome. Cost: 2 bank requests, 1 render, 15 s, $0.
