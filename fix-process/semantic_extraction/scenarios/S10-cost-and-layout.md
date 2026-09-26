# S10: Cost per offering and the full-mode call layout

**What it checks.** Prompt tokens per offering in full and budgeted mode; the 3-call against the 6-call layout (Q10); implicit prefix caching.

**Plan items.** SE6, SE9, Q10.

**Steps.** From the usage recorded in S06 and the budgeted-mode pass, plus prompt sizes computed offline for both layouts.

**Pass criteria.** Budgeted mode uses at most 50% of full mode's input tokens; the chosen layout is recorded with its cost and label accuracy; `cached_content_token_count` is recorded.

**Gemini.** Within S06's budget.

## Result: **PASS** (offline sizes, live cache figure)

- **Layout (Q10): three calls.** Full-mode prompt characters over the 13 seeds with all PDFs:
  2,979,690 with three calls against 5,654,874 with one call per field group (1.90×). The
  three-call layout stays.
- **Budgeted against full:** prompt characters 1,046,431 against 2,952,002 with all PDFs
  (**35%**; recall 85%), 862,345 against 1,676,558 page only (**51%**; recall 96%). The
  page-only ratio sits at the 50% line because small offerings send everything in both modes.
- **Live input:** S06 full mode used 1,383,023 input and 137,554 output tokens for 13
  offerings with all PDFs, about $0.12 per offering (records tokenize at ≈2.1 characters per
  token, denser than the 3.5 estimated).
- **Implicit prefix caching works:** in the Primary confirmation run 72,557 of 196,385 input
  tokens (37%) were served from cache (`cached_content_token_count`, now recorded in usage).
- The budgeted live pass was not run (budget).
