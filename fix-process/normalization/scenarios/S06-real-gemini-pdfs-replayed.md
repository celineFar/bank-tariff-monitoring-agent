# S06: Real Gemini PDF transcriptions normalize correctly (replayed, $0)

**What it checks.** The PDF branch turns real Gemini output into correct normalized documents: tables whose cells cite themselves (not just the page), clean headers, coverage-based quality scores, and a warning for any text page the model left empty.

**Plan items.** N18, N19, N25, N16 (cached path), N28 (OCR routing).

**Steps.** Load the stored transcriptions from `tariff_rt.pdf_extraction_cache` (read-only; 11 PDFs transcribed earlier by `gemini-3.1-flash-lite`). Run the real `GeminiPdfExtractionService` with a replay repository that serves them by PDF hash, on the matching PDFs of today's capture, inside `StructuralNormalizationService`. A replay miss would need a model call, which the guard refuses and counts.

**Pass criteria.** 0 Gemini attempts; every replayed PDF becomes a `gemini_pdf:` document; every table cell cites its own row and cell; every header is clean.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S06.json](results/S06.json).

- `tariff_rt` holds 10 distinct stored transcriptions by
  `gemini-3.1-flash-lite`, and 9 of them are PDFs linked from today's pages.
- All of them were served from the replay; **there were 0 Gemini attempts**. There were
  34 replay hits, because PDFs shared across pages are normalized once per
  page.
- Every one became a `gemini_pdf:` document with quality score 1.0.
- **Every table cell cites its own row and cell** (`…:table:N:row:R:cell:C`) instead of just
  the page, and every header is clean.
- **No `PDF_PAGE_EMPTY`:** Gemini filled every page with a text layer.
- **No `PDF_OCR_FILLED`:** none of these PDFs has an image-only page.

| PDF | Name | Tables | Cells | Cells citing themselves | Score | Warnings |
|---|---|---|---|---|---|---|
| 7b405d165676 | Loan service fees | 1 | 24 | 24 | 1.0 | — |
| c9465a0d1c77 | 6.1.1.2. where the address of the pledged real estate is inc | 1 | 10 | 10 | 1.0 | — |
| eca03d247e60 | On the Procedure for Setting, Calculation and Revision of th | 1 | 14 | 14 | 1.0 | — |
| 175e5d151b3d | Terms of express Home Mortgage Loan (Purchase, Construction  | 7 | 144 | 144 | 1.0 | — |
| af53ff31bab9 | Terms of residential and commercial real estate mortgage len | 2 | 21 | 21 | 1.0 | — |
| db6b470de92a | Terms of the loan for purchase of residential real estate fr | 6 | 122 | 122 | 1.0 | — |
| 0367c52044e0 | Mortgage lending terms and conditions for purchase of reside | 4 | 14 | 14 | 1.0 | — |
| 3472fe8d3966 | Informational summary of unsecured overdraft | 6 | 62 | 62 | 1.0 | — |
| 64566c7add62 | Lending terms for individuals / Card overdrafts | 1 | 39 | 39 | 1.0 | — |

This answers whether Gemini is needed to test normalization: it is not. Page normalization
never calls a model. The PDF branch does (transcription), but its conversion, citations,
warnings and scores can be tested on real Gemini output replayed from storage, at $0.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 8.3 s |

Round 1: PASS, the same documents (0 Gemini calls, $0.00, 0 bank requests, 0 renders, 0.0 MB, 8.4 s).
