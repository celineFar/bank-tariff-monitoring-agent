# S02: Every confirmed bug is gone on its original reproduction

**What it checks.** The HTML fixtures that reproduced the confirmed bugs before any fix (`data/probe_normalization.py`) now produce the correct output, and the saved pre-fix output still shows each bug, so the comparison is real.

**Plan items.** N1, N2, N3, N4, N6, N7, N8, N9, N10, N13, N14.

**Steps.** Run the probe script on the current code and compare with `data/probe-output-before.txt`, one check per bug.

**Pass criteria.** For each of the 12 checks: the bug is visible in the saved output, and absent (the correct output present) now.

**Gemini.** None. The harness runs with no API key and replaces the Gemini client constructor with one that counts the attempt and raises, so any model call would fail the scenario and show in its cost.

## Result: **PASS**

Latest run 2026-09-26 (second round, after the F1 fix `Page identity leaves out the site header, navigation and footer`), branch `fix/normalization`. Raw result: [results/S02.json](results/S02.json).

All 12 checks pass: every bug still shows in the pre-fix output, and is gone now. The
current output is saved as [results/S02-probe-output-now.txt](results/S02-probe-output-now.txt).

| Confirmed problem | Visible before | Now |
|---|---|---|
| N6 merged table text | yes | **fixed** |
| N6 card title | yes | **fixed** |
| N1 row-header table | yes | **fixed** |
| N3 amount kept in note | yes | **fixed** |
| N10 title not repeated | yes | **fixed** |
| N9 single column rows | yes | **fixed** |
| N13 no false list items | yes | **fixed** |
| N8 nested table | yes | **fixed** |
| N2 sections | yes | **fixed** |
| N7 heading leak | yes | **fixed** |
| N4 bare div text | yes | **fixed** |
| N14 dt/dd pair | yes | **fixed** |

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data held | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 2.6 s |

Round 1: PASS, the same 12 checks (0 Gemini calls, $0.00, 0 bank requests, 0 renders, 0.0 MB, 2.5 s).
