# S06: Live extraction matches the field labels

**What it checks.** Full-mode extraction with `gemini-3.7-flash` on the 13 seeds (pages and replayed PDFs), scored by `survey/check_extraction_labels.py` against `data/seed-extraction-labels.json`.

**Plan items.** SE1–SE26 end to end.

**Steps.** Run the checker with `--extractor gemini --pdfs --max-usd 1.5 --label after`.

**Pass criteria.** Agreed with the user once the labels are confirmed. Proposed: at least 85% `match` over labelled fields, and no `wrong_value` on interest rate, effective rate or loan amount caused by a wrong column or currency.

**Gemini.** Up to $1.50.

## Result: **not run**
