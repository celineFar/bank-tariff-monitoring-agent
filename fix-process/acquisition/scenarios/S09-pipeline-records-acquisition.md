# S09: The run records how and when the page was acquired

**What it checks.** Through the real `TariffPipeline`, each offering execution records `source_retrieved_at` and `acquisition_reused`, and an incomplete acquisition fails the offering with its code and reasons in the audit. The harness stops each run right after acquisition, before normalization, where Gemini would start.

**Plan items.** A12, A6, A8, the pipeline side of A3.

**Steps.** Scratch database, `overdraft`. Run 1: a fresh acquisition. Run 2: within the window. Run 3: the browser disabled. Normalization is replaced by a stub that stops the run.

**Pass criteria.** Runs 1 and 2 record `source_retrieved_at`, with `acquisition_reused` false and then true (same time), and stop at normalization. Run 3 fails at acquisition with `source.incomplete_content`, with the reasons in the audit payload. `model_call_usage` stays empty.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S09.json](results/S09.json).

Three runs through the real `TariffPipeline`, with `overdraft` on the scratch database:

| Run | Stopped at | Code | `source_retrieved_at` | `acquisition_reused` |
|---|---|---|---|---|
| 1, fresh | normalization (harness stop) | `source.parsing_failed` (the stub) | 07:14:52 UTC | false |
| 2, within the window | normalization (harness stop) | `source.parsing_failed` (the stub) | 07:14:52 UTC (same) | **true** |
| 3, browser disabled | **acquisition** | **`source.incomplete_content`** | — | — |

Run 3's audit payload carries the reasons `["main_chars 433 < 1500", "no tables, PDF links
or payloads"]`. `model_call_usage` has **0 rows**: no model was reached. The
`source.parsing_failed` on runs 1 and 2 is the harness stopping the run before normalization,
not a product failure.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 2 | 1 | 0.0 MB | 14.6 s |
