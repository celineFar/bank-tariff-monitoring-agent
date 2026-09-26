# S10: What the first production run will pay for PDFs

**What it checks.** With N17 deferred, the PDF cache key still includes link metadata. This counts, for today's PDFs, how many are skipped, how many stored transcriptions would be reused, and how many would be transcribed again, without making any call.

**Plan items.** N17 (deferred), N5/N26 cost effect, Q5.

**Steps.** For every distinct PDF in today's capture, build the extraction plan with the current code and compare its cache fingerprint with the stored transcription in `tariff_rt` (read-only).

**Pass criteria.** Informational: passes if it runs with 0 Gemini attempts. The numbers are the forecast.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS (forecast)**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S10.json](results/S10.json).

For the 91 distinct PDFs linked today, planned with the current code:

| | PDFs |
|---|---|
| Skipped by admission (superseded) | 62 |
| Admitted | 29 |
| … with a stored transcription | 9 |
| … reusable from the cache as the key is today | **1** |
| … would be transcribed on the first production run | **28** (125 pages) |

These 8 stored transcriptions are **invalidated only
by the cache key**: Loan_tariffs_eng.pdf, insured-properties.pdf, Floating_Agreement_eng.pdf, mortgage_personal_express_eng.pdf, terms_mortgage_lending_campaign_eng.pdf, mortgage_personal_purchase_eng.pdf, Overdraft_unsecured_eng.pdf, unsecured_overdraft_eng.pdf. The key includes the
link-context admission result, which the N5 fix changed; that is the deferred N17.

**Estimated cost of that first run's PDF transcription: about $0.15–$0.21.** No usage is
recorded for any PDF transcription (the database holds only cache hits), so this is estimated:
- stored responses average about 690 output tokens per page;
- Gemini reads about 258 input tokens per PDF page, plus the prompt, per call;
- `gemini-3.1-flash-lite` costs $0.25 / $1.50 per million input/output tokens;
- 125 pages over 28 calls gives about 70–75k input and 90–125k output tokens.

Of that, the 8 invalidated transcriptions (about 30 pages) are the part N17 would save,
roughly $0.05 once. After the first run, every PDF is cached again.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 27.8 s |

Round 1: PASS, the same forecast (0 Gemini calls, $0.00, 0 bank requests, 0 renders, 0.0 MB, 27.6 s).
