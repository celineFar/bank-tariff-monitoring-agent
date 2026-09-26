# S03: All 13 live seeds normalize completely

**What it checks.** A fresh live capture of every seed, normalized through the production path (the blocks and tables acquisition stored, the shipped seed baseline), has all the structure a person recorded for it.

**Plan items.** N20 (quality score), N1–N14 on real pages, N22 (new completeness floor), ground truth.

**Steps.** Acquire all 13 seeds live with the production composition (browser render, PDF downloads on, cap 40) into `.cache-scenario-1/`. Normalize each with `StructuralNormalizationService` (baseline on; PDFs to `NoPdfExtractor`). Run the ground-truth check (352 checks) on the same capture.

**Pass criteria.** 13/13 acquired in `browser` mode; every page scores 1.0 against its baseline (no `BASELINE_MISMATCH`); the ground truth has 0 failures.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S03.json](results/S03.json).

- All 13 seeds were acquired in `browser` mode.
- **Every page scores 1.0** against its seed baseline; there is no `BASELINE_MISMATCH`.
- **Ground truth: 0 of 352 checks failed.**
- `mortgage_diaspora` (no table, no PDF) passes the new completeness floor on its text
  alone.

The warnings are the expected ones:
- `AMBIGUOUS_TABLE` for header-less tables;
- `PDF_MODEL_REQUIRED` for each admitted PDF, because nothing is transcribed without Gemini.

| Seed | Mode | Main text | Tables | Rows | PDF documents | Score | Warnings |
|---|---|---|---|---|---|---|---|
| consumer_standard | browser | 18,615 | 3 | 36 | 12 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| credit_line | browser | 19,797 | 3 | 36 | 11 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| mortgage_commercial | browser | 25,291 | 2 | 58 | 8 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| mortgage_construction | browser | 48,449 | 4 | 172 | 15 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| mortgage_diaspora | browser | 3,298 | 0 | 0 | 0 | 1.0 | — |
| mortgage_express | browser | 8,497 | 4 | 40 | 3 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| mortgage_no_income_verification | browser | 4,915 | 1 | 12 | 1 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| mortgage_online | browser | 29,098 | 3 | 79 | 15 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| mortgage_primary | browser | 41,564 | 3 | 128 | 13 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| mortgage_renovation | browser | 45,621 | 3 | 160 | 13 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| mortgage_secondary_market | browser | 40,626 | 3 | 127 | 11 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| online_consumer_finance | browser | 7,778 | 3 | 20 | 5 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |
| overdraft | browser | 13,305 | 3 | 32 | 10 | 1.0 | AMBIGUOUS_TABLE, PDF_MODEL_REQUIRED |

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 137 | 13 | 29.27 MB | 238.2 s |

Bank requests are the static page fetches plus the PDF downloads. A browser render makes its own requests, which are not counted; each render is counted once.

Round 1: PASS, with the same scores and ground truth (0 Gemini calls, $0.00, 137 bank requests, 13 renders, 29.27 MB, 242.4 s).
