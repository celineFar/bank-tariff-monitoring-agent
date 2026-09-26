# R03: review sets on the 13 seeds' real extraction results

**Checks.** On real extraction results, the evidence set of every review signal stays
within the bounds (RV9) and holds the passages the reviewer needs.

**Input.** The 13 captured seeds (`.cache-live-2`), re-extracted offline from
`fix-process/semantic_extraction/.cache/extraction-cache.json` (the Gemini answers the
semantic-extraction validation paid for). Calls missing from the cache are not made
(`forbid_gemini`), so the run costs $0.

**Run.** `uv run python fix-process/reviews/scenarios/run_review_sets.py`

**Pass when.**
- every signal has an evidence set with 1–2 units;
- no unit shows more than 30 table rows, or more than 5 section blocks / 3,000 characters;
- every `extraction_invalid` / `source_applicability` set holds the field's valid citations;
- every `missing_required_field` set comes from the field's extraction call (`why=batch`);
- the model payload of every review has ≤ 5 excerpts of ≤ 600 characters.

**Result.** _pending (Phase 5)_
