# S06: Static HTML alone fails the floor on every seed

**What it checks.** With the browser disabled, the chrome-only static HTML that used to pass the usefulness check is rejected, with reasons.

**Plan items.** A3 floor (U1 + U2).

**Steps.** Disable the browser and acquire all 13 seeds.

**Pass criteria.** 13/13 fail with `source.incomplete_content`, each with reasons (`main_chars ... < 1500` and/or `no tables, PDF links or payloads`).

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S06.json](results/S06.json).

With the browser disabled, **13/13 seeds failed with `source.incomplete_content`**, every one with
both reasons: `main_chars N < 1500` and `no tables, PDF links or payloads`. Static main text
ranged from 178 to 1,238 characters.

Observation: `credit_line` has 1,238 main characters, only 262 below the floor. The rule that
reliably rejects static pages is "no tables, PDF links or payloads", which held on all 13. Under
the old check (500 visible characters anywhere), all 13 would have been accepted.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 13 | 0 | 0.0 MB | 24.4 s |
