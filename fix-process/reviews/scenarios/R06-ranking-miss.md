# R06: the ranking-miss event

**Checks.** A decision whose evidence reference is outside the units the review showed
writes `review_citation_outside_shown_units` (RV13); one inside does not.

**Run.** `uv run pytest tests/unit/test_review_fixes.py -k rv13 -v`, plus the in-units
case in the same file.

**Pass when.** Exactly one audit event for the outside citation, none for the inside one,
with the review id, the field and the cited evidence id.

**Result.** **PASS** (2026-09-26). `test_rv13_override_citing_outside_the_shown_units_is_audited`
(one `review_citation_outside_shown_units` event with review id, reason, field, cited
evidence id and shown unit keys) and `test_rv13_override_citing_a_shown_passage_is_not_audited`
(no event). Postgres: `test_snapshot_keeps_selected_sources_markdown_and_decision_audit_events`
shows the event written in the decision's transaction.
