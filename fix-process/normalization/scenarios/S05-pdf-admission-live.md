# S05: The right PDFs are skipped on the live pages

**What it checks.** On today's capture, metadata admission skips every superseded PDF and no current one, and each skip is reported as a warning.

**Plan items.** N5, N26, Q4.

**Steps.** For every PDF link in `.cache-scenario-1/`, run admission as of the label date and compare with `data/seed-pdf-labels.json`. Then normalize every page with a Gemini PDF service that has no key, and count the `PDF_SKIPPED_*` warnings.

**Pass criteria.** No PDF labelled current is skipped; no PDF labelled historical is admitted; one skip warning per skipped PDF.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S05.json](results/S05.json).

Today's capture has 117 PDF links (91 distinct files), and **every file was
already labelled**.
- **62 links skipped, all labelled historical.**
- **No link labelled current is skipped. No link labelled historical is admitted.**
- Normalization raised exactly one `PDF_SKIPPED_HISTORICAL` / `PDF_SKIPPED_IRRELEVANT`
  warning per skipped link (62).
- **Still admitted: the 3 links to the 2 website-profile PDFs labelled irrelevant**
  (`web-info-eng.pdf` twice, `web-info.pdf`). They are linked under "Consumer loan > Terms
  and conditions", so "loan" makes them relevant. Link metadata can't tell them apart. This
  costs 2 transcriptions; it is not a skipped current PDF.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 36.4 s |

No new downloads: it reads the PDFs S03 downloaded.

Round 1: PASS, the same counts (0 Gemini calls, $0.00, 0 bank requests, 0 renders, 0.0 MB, 33.8 s).
