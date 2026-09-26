# R06: the ranking-miss event

**Checks.** A decision whose evidence reference is outside the units the review showed
writes `review_citation_outside_shown_units` (RV13); one inside does not.

**Run.** `uv run pytest tests/unit/test_review_fixes.py -k rv13 -v`, plus the in-units
case in the same file.

**Pass when.** Exactly one audit event for the outside citation, none for the inside one,
with the review id, the field and the cited evidence id.

**Result.** _pending (Phase 5)_
