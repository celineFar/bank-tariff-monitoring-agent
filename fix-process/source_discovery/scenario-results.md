# Source discovery: scenario results

2026-09-26, branch `fix/source-discovery`. Scenarios in [scenarios/](scenarios/), runner
[scenarios/run_scenarios.py](scenarios/run_scenarios.py), raw results in
[scenarios/results/](scenarios/results/). No scenario calls Gemini; S03 and S04 read the
recorded Phase 7 Gemini run.

| # | Scenario | Result |
|---|---|---|
| S01 | [Offline test suite](scenarios/S01-offline-test-suite.md) | **PASS** (195 passed, 0 skipped) |
| S02 | [Deterministic defects gone on the live pages](scenarios/S02-confirmed-bugs-fixed.md) | **PASS** |
| S03 | [Sibling products told apart](scenarios/S03-offering-identity.md) | **FAIL**: Express table right on 4 of 4; 28 of 29 own tables; 7 cross-sell leaks (was 29) |
| S04 | [PDF selection from links](scenarios/S04-pdf-selection.md) | **FAIL**: 0 own PDFs lost; 4 wrong keeps (website-profile ×3, flexible mortgage) |
| S05 | [Cache re-run free; one new block, one item](scenarios/S05-cache.md) | **PASS** |
| S06 | [Dated offer expires without a call](scenarios/S06-dated-campaign.md) | **PASS** |
| S07 | [Retry, split, keep the rest, next model](scenarios/S07-bad-response.md) | **PASS** |
| S08 | [RAG index holds only selected content](scenarios/S08-projection.md) | **PASS** |

**The two failures are Gemini judgements the plan's code cannot force**: which cross-sell
card or link belongs to the offering. Both improved a lot against the baseline and neither
loses the offering's own material (0 own PDFs lost, the only wrong own table is one of 29).
See the Phase 7 notes in the plan for the options.

## Findings

- **F1: Gemini rejects nested constraints in the response schema.** The first Phase 7 run
  failed with `400 INVALID_ARGUMENT` on every discovery call: the member-exception model
  (Phase 3) carried a `pattern` and length limits on top of the item's own. No unit test could
  see this (they use fakes). Fixed by moving those checks into `_check_response`; a test now
  keeps constraints out of that schema.
- **F2: one batch can run away.** In round 2 one batch answered with ~260,000 characters of
  repeated text, twice. Retry and split recovered it, but it cost $0.21. Fixed with
  `SOURCE_DISCOVERY_CLASSIFIER_MAX_OUTPUT_TOKENS` (default 8192).
- **F3: an offering's name does not say which variants it covers.** Round 1 called the
  Express page's construction and renovation tables, and the online page's secondary-market
  tariffs, `related`. Fixed by giving the classifier the page's main heading and the text
  under it.
