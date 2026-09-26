# S11: A late footer module does not rename the page

**What it checks.** Finding F1 without waiting for the race: on the real rendered pages, removing the late-loading footer notice ("Dear User, If you find any discrepancies…") leaves the page id unchanged, while an edit to the page's own content still changes it.

**Plan items.** Acquisition A1 (page identity), refined for F1; the extraction cache.

**Steps.** For every page of `.cache-scenario-1/` that carries the notice, compute `page_content_hash` from its rendered HTML, from the same HTML with the notice module removed, and from the HTML with one content word changed.

**Pass criteria.** On every such page: the same id without the notice; a different id after the content edit.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Run 2026-09-26, after the F1 fix, branch `fix/normalization`. Raw result: [results/S11.json](results/S11.json).

10 of today's pages carry the late-loading footer notice. On **every one**:
- with the notice module removed from the real rendered HTML, the page id is **unchanged**;
- with one word of the main content changed ("Annual" → "Yearly"), the page id **changes**.

On the code before the fix, removing the notice changed the consumer-loan page's id. Checked
by hand on the same page: old code "same page id: False", new code "True".

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 18.8 s |
