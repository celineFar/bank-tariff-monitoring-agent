# R02: the report's confirmed problems are fixed

**Checks.** Each problem the report confirmed with a reproduction, re-run on the new code:

| Report ref | Check |
|---|---|
| P2 | a `not_stated` field's review shows the rows its extraction call read, not the first 20 entries |
| P3 | a made-up evidence ID is listed as unknown and never becomes a reference |
| P4/B6 | a `large_rate_change` review links the new value's citations |
| B1/D2 | a value that failed a check is `extraction_invalid`, with Gemini's value as candidate |
| B4 | approving the OCR review of a field keeps its `large_rate_change` signal |
| B5/D4 | a new review row stores references, not the evidence catalog |
| P6/D5 | `get_current_tariffs` returns no evidence or values |
| B7 | a chat model call made during a run records the run id |
| B8 | the CLI shows a passage whole (up to 4,000 characters) |

**Run.** `uv run pytest tests/unit/test_review_fixes.py -v` (each check is one test there),
plus the CLI rendering tests for B8.

**Result.** _pending (Phase 5)_
