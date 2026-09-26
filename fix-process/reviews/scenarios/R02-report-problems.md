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

**Result.** **PASS** (2026-09-26). One test per problem in `tests/unit/test_review_fixes.py`,
all passing:

| Report ref | Test |
|---|---|
| P2 | `test_rv1_not_stated_signal_is_seeded_from_the_fields_call` |
| P3 | `test_rv5_failed_value_is_extraction_invalid_with_its_candidate` (unknown ID in `unknown_ids`, not in units) |
| P4/B6 | `test_rv4_rate_change_review_links_the_new_values_citations` |
| B1/D2 | `test_rv5_failed_value_is_extraction_invalid_with_its_candidate`, `test_rv5_selecting_geminis_value_resolves_the_field` |
| B4 | `test_rv6_resolving_the_ocr_review_keeps_the_rate_signal`, plus Postgres `test_two_reasons_on_one_field_of_one_snapshot_both_stay_pending` |
| B5/D4 | `test_rv4_review_stores_the_signals_evidence_set_not_the_catalog` |
| P6/D5 | `test_rv8_current_tariffs_payload_has_no_evidence_or_values`, `test_rv8_history_payload_keeps_values_but_not_evidence` |
| B7 | `test_rv12_model_call_during_a_run_records_the_run` |
| B8 | `test_cli_review_shows_units_with_numbered_rows_and_marked_seeds` (a 950-character passage printed whole) |

The B4 fix needed one more change the report did not see: sibling reviews of one field
superseded each other in the database (migration 022).
