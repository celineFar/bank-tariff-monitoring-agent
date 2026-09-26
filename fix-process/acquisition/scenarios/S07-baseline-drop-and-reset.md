# S07: A sharp drop fails until an operator resets the baseline

**What it checks.** The completeness gate records a baseline from a good acquisition, fails a sharp drop without moving the baseline, and accepts the page again only after the real reset script runs.

**Plan items.** A3 baseline (U3), Q3.

**Steps.** Scratch database, `overdraft`, downloads off. (1) Acquire: baseline recorded. (2) Raise the stored baseline's PDF links to 25 so the live page (10) is a 60% drop. (3) Acquire: must fail. (4) Run `python -m scripts.reset_acquisition_baseline overdraft`. (5) Acquire: must pass and record the live inventory.

**Pass criteria.** (1) passes and records; (3) fails with `source.incomplete_content`, reason `pdf_links 25 -> 10 (-60%)`, baseline unchanged; (4) exits 0 and writes an `acquisition.baseline_reset` audit event; (5) passes, the baseline is the live inventory and keeps `reset_by`.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S07.json](results/S07.json).

1. First acquisition of `overdraft` passed and recorded the baseline
   `{main_chars 13218, tables 3, pdf_links 10, payloads 17}`.
2. The stored baseline's `pdf_links` was raised to 25.
3. The next acquisition **failed** with `source.incomplete_content`, reason
   `pdf_links 25 -> 10 (-60%)`, and the message names the reset command. The baseline was
   left at 25.
4. `python -m scripts.reset_acquisition_baseline overdraft --operator scenario-S07` exited 0,
   printed the cleared inventory, left the baseline empty, and wrote one
   `acquisition.baseline_reset` audit event (by `scenario-S07`, previous `pdf_links` 25).
5. The next acquisition passed and recorded the live inventory as the new baseline;
   `reset_by = scenario-S07` stayed on the row as history.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 3 | 3 | 4.72 MB | 41.6 s |
