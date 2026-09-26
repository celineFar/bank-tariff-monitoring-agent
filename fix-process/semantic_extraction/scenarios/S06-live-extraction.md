# S06: Live extraction matches the field labels

**What it checks.** Full-mode extraction with `gemini-3.7-flash` on the 13 seeds (pages and replayed PDFs), scored by `survey/check_extraction_labels.py` against `data/seed-extraction-labels.json`.

**Plan items.** SE1–SE26 end to end.

**Steps.** Run the checker with `--extractor gemini --pdfs --max-usd 1.5 --label after`.

**Pass criteria.** Agreed with the user once the labels are confirmed. Proposed: at least 85% `match` over labelled fields, and no `wrong_value` on interest rate, effective rate or loan amount caused by a wrong column or currency.

**Gemini.** Up to $1.50.

## Result: **PASS** (after re-scoring and one confirmed fix)

Run 2026-09-26 with `gemini-3.7-flash`, full mode, pages + all labelled PDFs (26, of which
16 transcribed for this run), repairs capped at 1 per offering to fit the budget. Raw
results: [../data/extraction-check-after.json](../data/extraction-check-after.json),
re-scored [../data/extraction-check-after-rescored.json](../data/extraction-check-after-rescored.json),
confirmation [../data/extraction-check-after-primary-confirm.json](../data/extraction-check-after-primary-confirm.json).

| | Fields |
|---|---|
| Labelled fields | 120 on 13 seeds |
| Live run as scored | 96 match, 8 wrong_value, 16 review |
| **Re-scored** (checker fix below) | **104 match (87%)**, 0 wrong_value, 16 review |

Pass bar (proposed, adopted, see `../note.md`): ≥ 85% match and no rate or amount
`wrong_value` from a wrong column or currency. **Met: 87%, and no wrong values.**

**The 8 `wrong_value` were checker artefacts, not extraction errors:** down payments stored as
numeric strings (`"10"`), rates stated as formulas ("Fixed component 5.25% + variable
component") and a fee's AMD 20,000 minimum in its description. The checker ignored numbers
in text; it now reads them (never in conditions), and re-scoring the stored values makes all
eight match.

**The 16 reviews:**
- 7 × `product_name` on mortgage pages: **a validator bug found by this run.** The anchor
  rule required a product-name *term* in the cited canonical-page item and rejected the page
  heading "Real estate loan for primary market". Fixed (any canonical-page item anchors);
  regression test `test_se19_product_name_anchored_by_the_page_heading_is_accepted`.
- 8 × fields of `documents_and_details` on Primary and Secondary Market: the whole answer
  failed the response schema, twice. The likely cause, a citation list longer than the
  20-citation limit, is fixed (limit 50; Gemini refuses the schema at 100, HTTP 400, found
  while fixing). **Confirmed live on Mortgage Primary: 10/11 match** (was 6/11); the call's
  first answer again failed the schema and the one retry (SE24) succeeded.
- 1 × Overdraft `fees`: its quotes lacked the fees' numbers (SE18 working as intended).
- 1 × Secondary Market `category`: quote not in the evidence; 1 × Primary `ltv_pct` in the
  confirmation run, same cause. Genuine model-quote misses, sent to review.

**Cost:** S06 $1.557 (50 calls, 1.38M input tokens, 3 calls refused at the guard); the
Primary confirmation $0.215 (37% of its input tokens served from Gemini's prefix cache).
**Not run:** the budgeted-mode live pass (budget exhausted); budgeted mode is measured offline
(S03, S10).
