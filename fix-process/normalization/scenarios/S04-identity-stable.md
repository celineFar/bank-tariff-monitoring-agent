# S04: Unchanged pages keep their identity and output

**What it checks.** Two captures a few minutes apart produce the same page ids and byte-identical normalized page documents, so every content-addressed cache downstream (discovery, extraction, embeddings) hits and no false change is recorded.

**Plan items.** N6/N7/N8 (deterministic blocks), N23 (table ids), N22 (content hash without payloads).

**Steps.** Capture all 13 seeds live a second time into `.cache-scenario-2/`, normalize both captures, compare per seed.

**Pass criteria.** 13/13 seeds: same page id, identical normalized page document (JSON), same warning codes.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S04.json](results/S04.json).

**13 of 13 seeds** had the same page id, a byte-identical normalized page document and the
same warnings in both captures.

The late footer notice behind F1 was present in both captures this time, so this round alone
does not exercise the race. **S11** does that deterministically on the real pages: removing
the notice module leaves every page id unchanged.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 137 | 13 | 29.27 MB | 227.3 s |

### Round 1: FAIL: finding F1

12 of 13 seeds matched (0 Gemini calls, $0.00, 137 bank requests, 13 renders, 29.27 MB, 218.5 s). **`consumer_standard` did not.**
- The two renders differed by one site-footer module, a notice ("Dear User, If you find any
  discrepancies in the website materials in Armenian, English and Russian…").
- In the first capture it was **not in the DOM**: it loads late, and that render finished
  first. Across all captures that day it was missing in 1 of 52 renders.
- The module sits inside the site `<footer>`, so it is chrome: `main_text`, the quality score
  and the tables were identical.
- But `page_content_hash` counted every parsed block, chrome included. So the page id
  changed, and with it every evidence id on the page. That page would have been extracted
  again on that run.

**Fix** (commit "Page identity leaves out the site header, navigation and footer"): the
parser reports which blocks, tables, links, images and controls sit in the header,
navigation or footer (`ParsedHtml.chrome_ids`), and the page hash leaves them out. A changed
tariff still renames the page; a late footer module or a menu edit does not. There are 3 new
tests in `test_acquisition_identity.py`, and 2 of them fail on the old code.
