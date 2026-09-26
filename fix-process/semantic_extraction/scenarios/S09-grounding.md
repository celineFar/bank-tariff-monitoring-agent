# S09: A value must be in its citation

**What it checks.** Number grounding (SE18).

**Plan items.** SE18.

**Steps.** A fake extractor returns `21%` citing a quote with no 21, then the same value citing the rate row.

**Pass criteria.** The first goes to repair, then review; the second is accepted. A quote that differs from the evidence only by a non-breaking space is accepted.

**Gemini.** None (fake extractor).

## Result: **not run**
