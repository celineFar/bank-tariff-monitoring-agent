# S03: Every current-product fact reaches the call that extracts it

**What it checks.** Evidence selection, replayed on the 13 seeds with `survey/probe_evidence_recall.py`, page only and `--pdfs`.

**Plan items.** SE2, SE5, SE6, SE8.

**Steps.** Run the probe in `full` and in `budgeted` mode; compare with `data/probe-output-before.txt`.

**Pass criteria.** `full`: 100% of current-product ground-truth facts reach every call that extracts their field. `budgeted`: at least 95%, and no sibling-product fact in the offering's own block.

**Gemini.** None.

## Result: **PASS**

Raw result: [results/S03.json](results/S03.json); probe outputs
`data/probe-output-s03-*.txt`.

| Mode | Evidence | Current-product facts sent | Sizes |
|---|---|---|---|
| full | page | **153/153** | calls per offering 3-3; batch evidence chars 3187-63839; prompt chars per call 14126-84595; prompt chars per offering 48219-249276 (total 1761143) |
| budgeted | page | **147/153** (96%) | calls per offering 3-3; batch evidence chars 1623-16000; prompt chars per call 11339-31607; prompt chars per offering 37616-88974 (total 946930) |
| full | page + 10 stored PDFs | **158/158** | calls per offering 3-3; batch evidence chars 3187-90747; prompt chars per call 14126-119454; prompt chars per offering 48219-353853 (total 2431166) |
| budgeted | page + 10 stored PDFs | 146/158 (92%) | calls per offering 3-3; batch evidence chars 1623-16000; prompt chars per call 11339-32355; prompt chars per offering 37616-90053 (total 998802) |

Sibling-product facts in the offering's own block: 0 in every run (they are rendered in
the marked "other products" block, or excluded). Before the fix: 119/152 (78%).
