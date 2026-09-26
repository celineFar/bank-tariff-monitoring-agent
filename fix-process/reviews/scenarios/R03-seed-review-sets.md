# R03: review sets on the 13 seeds' real extraction results

**Checks.** On real extraction results, the evidence set of every review signal stays
within the bounds (RV9) and holds the passages the reviewer needs.

**Input.** The 13 captured seeds (`.cache-live-2`) with stored assessments and PDF
transcriptions. Part A: seeds whose calls are all in
`fix-process/semantic_extraction/.cache/extraction-cache.json`. Part B: every seed with
an extractor that finds nothing. No Gemini client can be built (`forbid_gemini`): $0.

**Run.** `uv run python fix-process/reviews/scenarios/run_review_sets.py`

**Pass when.**
- every signal has an evidence set with 1–2 units;
- no unit shows more than 30 table rows, or more than 5 section blocks / 3,000 characters;
- every `extraction_invalid` / `source_applicability` set holds the field's valid citations;
- every `missing_required_field` set comes from the field's extraction call (`why=batch`);
- the model payload of every review has ≤ 5 excerpts of ≤ 600 characters.

**Result.** **PASS, with a changed input** (2026-09-26). Report:
`results/R03-review-sets.json`.

*Input changed.* The live extraction cache holds only 3 answers (one seed's three
calls), not the 13 seeds the plan assumed, and the S06 reports keep values without
citations. With the $2 budget spent, the scenario runs in two parts, both at $0:

- **Part A, real Gemini answers:** `mortgage_primary` (all 3 calls from the cache).
  3 reviews, all `extraction_invalid` (`formal_terms_names`, `ltv_pct`,
  `income_verification_required`), each with Gemini's value as the candidate and one
  unit of the cited table/section (7–8 passages shown, 47–83 omitted). Pause views
  1.8–5.0 kB. **0 bound violations.**
- **Part B, 13 seeds, extractor finds nothing:** 117 `missing_required_field`
  reviews over real catalogs of 52–443 passages. **0 bound violations** (≤ 2 units,
  tables ≤ 30 shown, sections ≤ 3,000 characters beyond the seeds, every set seeded
  from its call, pause views ≤ 5 excerpts of ≤ 600 characters, ≤ 4.9 kB). 68 cited
  sets built from the passages holding each labelled value: **0 violations**.

*Recall* (does the review show a passage holding the labelled value, for the 48
labelled required fields whose value is in the catalog):

| | shown | not shown |
|---|---|---|
| First run | 42 | 6 |
| After the tie-break change below | **46** | 2 |

The 6 first-run misses were all `interest_rate`/`loan_amount` landing on a
calculator, navigation section or FAQ: equal label scores were broken by page order,
and headline sections, which name many fields, outscored the tariff table. Fixed in
`field_evidence_set`: ties go to higher source precedence, then to tables; and when
the best unit is not a table and no second unit is within the rank gap, the second
slot goes to the best table. The 2 remaining misses are `online_consumer_finance`,
whose table calls the amount "Financing limit" (no field term matches; Q4's accepted
risk, visible through `?`, `all` and the RV13 event). The other 20 labelled fields
with numbers are optional fields that raise no review when not stated.
