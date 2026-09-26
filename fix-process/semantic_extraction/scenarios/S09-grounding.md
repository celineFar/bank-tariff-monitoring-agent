# S09: A value must be in its citation

**What it checks.** Number grounding (SE18).

**Plan items.** SE18.

**Steps.** A fake extractor returns `21%` citing a quote with no 21, then the same value citing the rate row.

**Pass criteria.** The first goes to repair, then review; the second is accepted. A quote that differs from the evidence only by a non-breaking space is accepted.

**Gemini.** None (fake extractor).

## Result: **PASS**

Raw result: [results/S09.json](results/S09.json). `8 passed, 28 deselected, 2 warnings in 1.90s`: a `21%` citing
"Interest rate" is rejected (then repair, then review); the same value citing the rate text is
accepted; a quote differing only by a non-breaking space is accepted; the quote reader
covers `AMD 3-150 million`, `3,000,000`, `50.000`, `12,5%`, years in months and split
boundaries.
