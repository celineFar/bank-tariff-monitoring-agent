# S07: PDF failures are reported correctly, and bugs are not hidden

**What it checks.** Each expected PDF failure becomes the right warning, and a bug in the PDF path fails normalization instead of passing as a model hiccup.

**Plan items.** N15, N16, N21.

**Steps.** On the Express page's PDFs: (1) a Gemini PDF service with no key and no OCR engine; (2) a file that is not a PDF; (3) an extractor that raises `KeyError`; (4) `NoPdfExtractor`.

**Pass criteria.** (1) one `PDF_MODEL_REQUIRED` per admitted PDF; (2) `ARTIFACT_UNAVAILABLE`; (3) normalization raises `KeyError`; (4) only `PDF_MODEL_REQUIRED`; 0 Gemini attempts.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S07.json](results/S07.json).

On the Express page (3 PDF links, all admitted):

| Case | Expected | Got |
|---|---|---|
| Gemini PDF service, no key, no OCR engine | one `PDF_MODEL_REQUIRED` per admitted PDF | PDF_MODEL_REQUIRED, PDF_MODEL_REQUIRED, PDF_MODEL_REQUIRED |
| A file that is not a PDF | `ARTIFACT_UNAVAILABLE` | ARTIFACT_UNAVAILABLE |
| An extractor that raises `KeyError` (a bug) | normalization fails | raised KeyError |
| `NoPdfExtractor` (offline tools) | `PDF_MODEL_REQUIRED` | PDF_MODEL_REQUIRED |

No case reached the Gemini client (0 attempts).

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 0.9 s |

Round 1: PASS, the same outcomes (0 Gemini calls, $0.00, 0 bank requests, 0 renders, 0.0 MB, 0.8 s).
