# OCR fallback demonstration

Scanned PDFs go through the project's PDF extraction service. Gemini is made to
fail, and the service falls back to its real tesseract OCR. The recovered text is
written to Markdown, so you can open each scan and its result side by side. The
same PDFs also go through the real Gemini path, and both results are scored
against the known text of each page.

```
OCR-fallback/
├── run.sh                 runs a script from this folder in the project's worker image
├── ocr_fallback_demo.py   the demonstration (--engine ocr | gemini)
├── score.py               scores every output against the ground truth
├── make_samples.py        renders the scanned samples and their ground truth
├── samples/
│   ├── loan-summary.pdf          2 pages: key-value list, one ruled table
│   ├── mortgage-tariffs.pdf      2 pages: merged-header table, stamp, sideways page
│   └── *.truth.json              every printed line, and every tariff row
└── output/
    ├── <sample>.ocr.md / .json     OCR fallback result (Gemini made to fail)
    ├── <sample>.gemini.md / .json  Gemini result, with its raw response
    └── comparison.md               the scores, row by row
```

All values in the samples are synthetic, not observed Ameriabank tariffs.

## Run

```bash
cd Presentation-demonstrations/OCR-fallback
./run.sh                    # OCR fallback on both samples: free, offline
./run.sh --engine gemini    # real Gemini baseline: about $0.003 per sample
./run.sh score.py           # writes output/comparison.md
```

`run.sh` uses the existing `worker` service from `docker-compose.yml`. That means
the same image and the same `.env`, with tesseract 5.5 (`hye` + `eng`) and the
`ocr` extra already installed. It needs no database. Only this folder is mounted,
so the application code is the copy inside the image: after changing `app/`, run
`docker compose build worker` first. Any `OCR_*` variable set in your shell
overrides `.env` for that run.

## What is real and what is simulated

Simulated, in OCR mode only: `AdkGeminiPdfExtractor`, the class that calls
Gemini, is replaced by a stand-in. It raises `google.genai.errors.ServerError`
503 on every call, the same error type a real Gemini outage raises.

Real (production code, unmodified):

- `GeminiPdfExtractionService.extract`
- metadata admission and the input probe (every page is `image_only`, with 0 text characters)
- the Gemini model sequence from `.env`
- catching the failure and deciding to fall back to `_ocr_only`
- `PdfiumPageRasterizer`, `TesseractOcrTranscriber` and the confidence floor
- the normalized blocks the pipeline would pass downstream

In Gemini mode nothing is simulated.

## Results

`output/comparison.md` holds the full scores and a row-by-row breakdown.

| Sample | Engine | Tariff values correct | Wrong numbers | Number recall | Word F1 | Cost |
|---|---|---|---|---|---|---|
| loan-summary | OCR | 11/13 | 1 | 92% | 0.90 | $0 |
| loan-summary | Gemini | 13/13 | 0 | 100% | 0.98 | $0.0028 |
| mortgage-tariffs | OCR | 13/28 | 9 | 56% | 0.52 | $0 |
| mortgage-tariffs | Gemini | 28/28 | 0 | 100% | 0.95 | $0.0031 |

Wall time is similar for both engines, about 6 to 13 seconds per document.

### Assessment

**Gemini is clearly the better transcriber, which is why it is the primary path.**
OCR is not a competing approach here. It exists so that a Gemini outage doesn't
stop the pipeline, and it's configured so that it can't do harm while it fills in.

**Where OCR is good.** On a simple, well-aligned key-value layout it is close to
Gemini (loan-summary page 1 is almost word for word).

**How OCR fails.**

- **It produces wrong numbers that look plausible.** On loan-summary, `0 AMD` was
  read as `2 AMD`. On mortgage-tariffs, tesseract reads the `%` sign as `96`
  several times, so `11.5%` becomes `11.596` and `20%` becomes `2096`. A missing
  value is visible; a misread one is not.
- **Stamps and ruled tables break it.** The stamp over the right-hand column
  removed three of the six conditions. Table borders turn into noise characters.
- **Confidence doesn't predict number accuracy.** Loan-summary page 2 had a mean
  confidence of 80.6 and still contained a wrong number. Mortgage page 1 had 76.7,
  above the floor of 60, and contained 9 wrong numbers.
- **The confidence floor works where it can.** The sideways page scored 38.1, and
  the stage emitted nothing for it instead of emitting nonsense.

This is what the pipeline's design assumes. Any value cited from an OCR block
raises an `ocr_evidence` review (`app/services/snapshot_lifecycle.py`), so
`11.596` would stop at a person instead of becoming a published rate.

**Where Gemini is weaker: structure, not text.** Every number is right, but in
the mortgage rate table Gemini put the market group in a column of its own and
supplied only four headers for five columns. The pipeline pads the gap with
`Column 5`, so as structured, `11.5%` sits under "Տոկոսադրույք* USD" rather than
AMD. The row scores above check labels and column order, not headers, so they
don't show this; it's a real risk for which currency a rate gets attributed to.

Separately, the pipeline's normalized document keeps paragraphs and tables in
separate lists. So a footer printed below a table appears above it in the
Gemini Markdown. That comes from the pipeline, not from Gemini.

**Limits of this comparison.** There are two synthetic samples, one font, and one
Gemini run at temperature 0. That's enough to show the failure modes, not to put
a precise number on either engine.

**Cheap improvements for the fallback, if it ever needs to carry more weight:**

- detect page rotation with tesseract's orientation detection (`osd` data is
  already in the image) before reading the page
- run a table-aware page segmentation mode on pages with ruled lines

## Presenting it

1. Open `samples/mortgage-tariffs.pdf`. Point out that it is a scan: you can't
   select any text. Show the stamp and the sideways page.
2. Run `./run.sh`. The log shows three things in order: the probe classifies each
   page `image_only`, the simulated Gemini failure, then the service's own
   `All gemini pdf models failed ... recovered N page(s) with ocr:tesseract:5.5.0`.
3. Open `output/mortgage-tariffs.ocr.md` next to the PDF. Point out the `11.596`
   misreads, the right-hand column lost under the stamp, and page 2 held back
   by the confidence floor.
4. Open `output/comparison.md`. Gemini is better, OCR produces plausible wrong
   numbers, and that is why every OCR-sourced value goes to human review.
5. Optional: `OCR_MIN_CONFIDENCE=80 ./run.sh` drops mortgage page 1 as well,
   showing that the floor decides what OCR may emit. Run `./run.sh` again to
   restore the outputs.
