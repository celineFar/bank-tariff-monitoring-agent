# Deliverable 11 — Document processing: digital PDF path and scanned-page fallback

**PASS — 4/4 criteria**

## Steps

1. Probed real sample case-001-pdf-en-consumer-finance: 1 page(s), mode=machine_readable, native text on page 1 = 879 chars, images on page 1 = False.
2. Probed real sample case-003-pdf-hy-consumer-finance-online: 13 page(s), mode=mixed, native text on page 1 = 3091 chars, images on page 1 = True.
3. Probed real sample case-004-pdf-en-consumer-finance: 1 page(s), mode=machine_readable, native text on page 1 = 874 chars, images on page 1 = False.
4. Probed real sample case-006-pdf-hy-mortgage-purchase-primary: 6 page(s), mode=machine_readable, native text on page 1 = 2311 chars, images on page 1 = False.
5. Probed real sample case-008-pdf-en-consumer-finance: 1 page(s), mode=machine_readable, native text on page 1 = 888 chars, images on page 1 = False.
6. Built a rendered scanned page (8874 bytes) with no text layer and probed it with the same deterministic prober.
7.     scanned page: mode=image_only, native text = 0 chars, images detected = True.
8. The probe result is what routes the document: a page with no text layer cannot be parsed directly and is transcribed from the page image instead.

## Notes

- This project has no tesseract OCR stage. Scanned pages are transcribed by Gemini's multimodal PDF reading, which is the fallback the probe routes to. The OCR_* variables in .env are dead configuration that no code reads.
- Run `uv run python scripts/demonstrate_pdf_extraction.py <case> --execute-llm` to see the actual transcription; that spends credits.

## Success criteria

| | Criterion | Expected | Observed |
| --- | --- | --- | --- |
| PASS | real samples are available | at least one real bank PDF is probed, not only a synthetic one | 5 sample PDF(s) under data/extraction-review-cases |
| PASS | digital PDFs take the direct path | a PDF with a text layer is classified machine_readable or mixed | machine_readable=['case-001-pdf-en-consumer-finance', 'case-004-pdf-en-consumer-finance', 'case-006-pdf-hy-mortgage-purchase-primary', 'case-008-pdf-en-consumer-finance'], mixed=['case-003-pdf-hy-consumer-finance-online'] |
| PASS | scanned page is detected | a page with no text layer is classified image_only, not machine_readable | mode=image_only |
| PASS | no text is invented for a scanned page | the prober reports zero native characters rather than guessing | chars=0, images=True |
