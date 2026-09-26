# S03: Every current-product fact reaches the call that extracts it

**What it checks.** Evidence selection, replayed on the 13 seeds with `survey/probe_evidence_recall.py`, page only and `--pdfs`.

**Plan items.** SE2, SE5, SE6, SE8.

**Steps.** Run the probe in `full` and in `budgeted` mode; compare with `data/probe-output-before.txt`.

**Pass criteria.** `full`: 100% of current-product ground-truth facts reach every call that extracts their field. `budgeted`: at least 95%, and no sibling-product fact in the offering's own block.

**Gemini.** None.

## Result: **not run**
