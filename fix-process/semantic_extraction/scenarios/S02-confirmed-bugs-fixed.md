# S02: Every confirmed bug now behaves correctly

**What it checks.** The reproductions listed under "How this was checked" in the plan: the stale raw response (SE13), the malformed term (SE16), the normalizer cases (SE15), the `age`-in-`mortgage` completeness failure (SE14), unconditional rate alternatives (SE17), a citation without the value (SE18).

**Plan items.** SE13–SE18.

**Steps.** Run each reproduction against the fixed code (the Phase 0 regression tests, plus the same cases on real seed evidence where one exists).

**Pass criteria.** Each case gives the behaviour the plan asks for.

**Gemini.** None (fake extractor).

## Result: **not run**
