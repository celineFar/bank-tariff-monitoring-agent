# S02: The deterministic defects are gone on the live pages (the probe)

**What it checks.** On the 13 captured seed pages, with this branch's parser and candidate
builder: no Gemini item contains a site-chrome block (SD9), no item is shown to the
classifier only in part (SD3, SD17), and no two candidates on one page share a structural
fingerprint (SD11).

**Plan items.** SD3, SD9, SD11, SD17.

**Steps.** Run [../survey/probe_discovery.py](../survey/probe_discovery.py) (output in
[results/S02-probe-output-now.txt](results/S02-probe-output-now.txt)).

**Pass criteria.** 13 seeds; 0 items with site chrome; 0 items seen only in part; 0 shared
structural fingerprints within a page.

**Gemini.** None.

## Result: **PASS**

Raw result: [results/S02.json](results/S02.json).

| | Before ([probe-output-before.txt](../data/probe-output-before.txt)) | Now |
|---|---|---|
| Gemini items with a site-chrome block | 4 per page, 52 in all | **0** |
| Items the classifier sees only in part | 1–5 per page | **0** |
| Structural fingerprints shared within a page | 1 per page | **0** |

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 41.1 s |
