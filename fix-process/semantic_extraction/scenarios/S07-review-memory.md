# S07: A review decision is asked once

**What it checks.** Review decision memory (SE12).

**Plan items.** SE12.

**Steps.** With a fake extractor that returns a field failing validation the same way every time: run, resolve the review, run again; then change the cited evidence and run a third time.

**Pass criteria.** Run 2 creates no review and no model call for that field and writes `review_decision_reused`; run 3 opens a new review.

**Gemini.** None (fake extractor).

## Result: **not run**
