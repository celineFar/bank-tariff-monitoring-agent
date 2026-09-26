# S03: Page ids are stable across fetches

**What it checks.** An unchanged page gets the same `page:` id on every fetch, so its extractions stay cached.

**Plan items.** A1.

**Steps.** Acquire all 13 seeds a second time, right after S02, and compare `page_content_hash` (and, for information, `content_hash`) with S02.

**Pass criteria.** 13/13 identical `page_content_hash`. A `content_hash` difference is reported, not failed: it can come from a data payload that really changed between fetches.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S03.json](results/S03.json).

Second pass, about three minutes after S02: **13/13 identical `page_content_hash`**,
and also 13/13 identical `content_hash` and inventory. The data payloads were
byte-identical between the passes too, so nothing in the acquisition varies between
fetches of an unchanged page. Before the fix, every fetch produced a new page id (the
per-request ASP.NET tokens were hashed).

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 13 | 13 | 29.67 MB | 183.8 s |
