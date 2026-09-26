# S10: Cost per offering and the full-mode call layout

**What it checks.** Prompt tokens per offering in full and budgeted mode; the 3-call against the 6-call layout (Q10); implicit prefix caching.

**Plan items.** SE6, SE9, Q10.

**Steps.** From the usage recorded in S06 and the budgeted-mode pass, plus prompt sizes computed offline for both layouts.

**Pass criteria.** Budgeted mode uses at most 50% of full mode's input tokens; the chosen layout is recorded with its cost and label accuracy; `cached_content_token_count` is recorded.

**Gemini.** Within S06's budget.

## Result: **not run**
