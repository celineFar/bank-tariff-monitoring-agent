# R04: stored old-format reviews still work

**Checks.** The 4 Overdraft reviews in the dev database were written before this fix
(`evidence.items`, a full evidence copy, no `set`). They must still build a review view
and a CLI rendering, and a decision on one must still resolve its evidence reference.

**Run.** Read-only: load the 4 rows and their snapshots from the dev database
(`tariff_monitor`, never written), then build the view and the CLI text with the new code.

**Pass when.** All 4 build without errors and show the same passages as before
(the old path), and `ReviewDecisionService` resolves an evidence reference from `items`.

**Result.** **PASS** (2026-09-26), read-only on `tariff_monitor`. Report:
`results/R04-R05-stored.json`.

All 4 stored Overdraft reviews (`missing_required_field` for `product_name`,
`repayment` ×2, `eligibility`; 262 copied items each) build a pause view and a
terminal display with the new code; an override reference resolves from `items`, and
the decision service sees all 262 passages. For comparison, the view the code before
this fix built (`be049e5`, rebuilt from git) carried 20 excerpts, 9.1–12.3 kB; the new
view carries 2–5 seed excerpts, 1.3–3.2 kB.

*Limitation.* These rows predate the record format (SE1): their passages are
`Headers: … Row: …` renderings with weak labels, and the section path of every Overdraft
passage names "Overdraft", a product-name term. Their units are therefore coarse (the
25-row card-type table plus one section or table) but within bounds. New rows are built
from record-format evidence and stored sets.
