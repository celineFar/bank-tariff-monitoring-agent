# Semantic extraction: scenario results

Run 2026-09-26 on branch `fix/semantic-extraction`. Details and raw results in
[scenarios/](scenarios/). Gemini spend for validation: **≈ $1.96 of the $2 budget**
(S06 $1.557, Primary confirmation $0.215, 16 PDF transcriptions $0.093, the SE3
transcription trial ≈ $0.075, model probes and schema tests ≈ $0.02).

| # | Scenario | Result |
|---|---|---|
| S01 | Offline test suite | **PASS**: 1,040 passed; only the 4 Gemini-key tests fail; 0 `xfail` left |
| S02 | Confirmed bugs fixed | **PASS**: all reproductions behave as the plan asks |
| S03 | Evidence recall | **PASS**: full 100% (page and PDFs); budgeted 96% page only |
| S04 | Table structure | **PASS**: 0 of 372 ground-truth checks fail (15 column-path facts) |
| S05 | Identity and cache | **PASS**: 54/54 table IDs stable; live re-run 0 calls, $0 |
| S06 | Live extraction vs labels | **PASS**: 104/120 match (87%), no wrong values; two bugs found and fixed |
| S07 | Review memory | **PASS**: asked once, reused with 0 calls, re-opened on change |
| S08 | Failure handling | **PASS**: per-call fallback; `execution_failed` with the other calls cached |
| S09 | Grounding | **PASS** |
| S10 | Cost and layout | **PASS**: 3 calls = 0.53× of 6; budgeted 35–51% of full; 37% prefix-cache hits |

**Found by validation, fixed:**
- the product-name anchor rule rejected the page's own heading (7 mortgage offerings);
- a 20-citation limit rejected whole answers in full mode (raised to 50; 100 makes Gemini
  refuse the schema with HTTP 400);
- the checker ignored numbers written in text (formulas, descriptions, numeric strings).

**Known, not fixed here:**
- the field labels are Claude's draft, not confirmed by the user (`../note.md`);
- the budgeted mode has no live run (budget);
- PDF page coverage varies between transcription runs (hand-off, `../note.md`);
- the live run capped repairs at 1 per offering (production default 3).
