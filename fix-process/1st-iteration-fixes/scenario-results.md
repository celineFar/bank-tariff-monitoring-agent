# First iteration: live validation results

2026-09-27, branch `fix/1st-iteration` at `e94fe2e` plus the P8 fix (`First iteration P8
fix`), on the local stack (API on port 8081). Baseline: the same day's first run on
`09e5181`, recorded in [`tests/eval/seed_url_eval_2026-09-27.json`](../../tests/eval/seed_url_eval_2026-09-27.json).
Both rounds' answers are in [data/phase8_answers.json](data/phase8_answers.json).

## Monitoring runs

Both families through `POST /api/v1/runs` (runs `5b1fca1c` consumer loans, `a788b367`
mortgages), prompt version 7, repair budget 6, `SCHEDULE_ENABLED=false`.

| Offering | Baseline (09e5181) | After the fixes |
|---|---|---|
| Consumer Loans | review (1: income verification) | review (1: `loan_amount`, "alternative values share the same conditions") |
| Overdraft | published | published |
| Credit Line | published | published |
| Online Consumer Finance | published | published (see R1) |
| Online Mortgage | published | published |
| Primary Market Mortgage | review (2) | **published** |
| Mortgage Loan for Diaspora | review (1: repayment not stated) | **published** |
| Secondary Market Mortgage | failed, then review (4) after two retries | **published** |
| Commercial Mortgage | review (8, one schema failure) | review (1: `creditworthiness_assessment_required`, broken JSON twice) |
| Express Mortgage | published | published |
| Mortgage without Income Verification | review (4) | review (2: `repayment`, `fees`, not stated by the page) |
| Renovation Mortgage | failed, then review (1) after two retries | **published** |
| Construction Mortgage | failed (credit), then review (1) | **published** |
| **Total** | 5 published, 22 reviews, 3 failed | **10 published, 4 reviews, 0 failed** |

- **Target (≤ 1 review per offering, none from F7–F11 causes):** met for 12 of 13;
  No Income Verification has 2, both genuine source omissions that the new
  `confirm_not_stated` decision (F13) resolves in one step each. Commercial's one review is
  an F11 residual (below).
- The 22 old reviews were superseded automatically (newer reviews and publications of the
  same offerings); the admin abort call was not needed. 4 reviews are pending, all from
  this run.
- **Human step still open:** the 4 reviews need a reviewer in `./tariff-chat` ("review
  them"). Expected decisions: No Income Verification `repayment` and `fees` → type
  `not_stated`; Commercial `creditworthiness_assessment_required` → override with the
  value as a JSON object (the candidate's content is right, its JSON is not); Consumer
  Loans `loan_amount` → check the two AMD variants' conditions (scoring vs outside
  scoring) and override with distinguishing conditions.

## Cost (model_call_usage ledger, list prices)

| Item | Cost |
|---|---:|
| Consumer loans run | $0.538 |
| Mortgage run | $1.090 |
| Interpreter re-recording (Phase 6, 7 calls) | ≈ $0.03 |
| 15 questions, first try (failed on the P8 bug) | $0.188 |
| 15 questions, after the fix | $0.209 |
| **Total for the iteration's live checks** | **≈ $2.06** |

PDF transcriptions were all cache hits; discovery made only a few new calls. **F19
works:** every pipeline ledger row of both runs carries its run and offering, so cost per
run is now a query (`GROUP BY run_id`).

## The 15 questions

Deterministic `fact_coverage` (tests/eval/fact_coverage.py) mean: **0.56 → 0.87**.

| # | Question | Baseline | After | Note |
|---|---|---|---|---|
| 1 | Lowest consumer AMD rate | partial | **incorrect** | "Online Consumer Finance 0.0%" from the generic leaflet (R1); coverage disclosed "3 of 4 ranked" |
| 2 | Largest mortgage amount | incorrect | **correct** | AMD 150M; "7 of 9 ranked", Commercial and No Income Verification named as awaiting review (F1) |
| 3 | Longest mortgage term | partial | **correct** | 360 months; missing offerings named |
| 4 | Credit Line fees | correct | correct | per-fee citations, no collateral fees (F15, F17) |
| 5 | Primary collateral | abstained | **correct** | now published (F7, F10, F11/F12) |
| 6 | OCF purpose and terms | partial | partial | all key terms now asked (F3), but generic leaflet values mixed in (R1) |
| 7 | Overdraft amount | correct | correct | |
| 8 | Credit Line term | correct | correct | |
| 9 | Express application fee | correct abstention | **correct** | "the bank's published tariff does not state an application fee", with the documents checked (F5) |
| 10 | Diaspora rate | abstained | **correct** | AMD/USD/EUR rates and APRs; no validity note |
| 11 | Primary down payment and collateral | abstained | **correct** | |
| 12 | Overdraft nominal rate | correct | correct | |
| 13 | Credit Line APR | correct | correct | |
| 14 | OCF amount | correct | **incorrect** | leaflet's "Purchase of goods: max 6,000,000" shown beside the online 1,500,000 (R1) |
| 15 | Primary term | abstained | **correct** | |

**12 correct, 1 partial, 2 incorrect** (baseline: 7 correct incl. one correct abstention,
3 partial, 1 incorrect, 4 abstained). Every answer put the answer first: no catalog
intro (F6). No answer offered a monitoring run when review was the cause (F4).

## Findings

- **P8 bug (fixed).** The first question round failed on all 15: the read path re-verifies
  each stored citation and required the stored locator to equal the captured one, and F16
  adds `section`. Fixed in the P8 fix commit. The Postgres integration tests catch it
  (4 failed without the fix); they had been skipped because `TEST_DATABASE_URL` was unset.
  They now run against a scratch `tariff_monitor_test` database in the dev container:
  1,290 passed with it.
- **R1 (new, for the next iteration): the generic installment leaflet is read as Online
  Consumer Finance's own tariff.** Both runs selected the same 58 leaflet passages
  (`Leaflet_consumer_finance_eng.pdf`, linked from the OCF page) as current-product
  evidence. The baseline extraction happened to use only the page (AMD 50,000–1,500,000);
  the prompt-7 extraction added the leaflet's goods/services/solar variants (up to
  6,000,000; 0%–21.5%). F2 then gave those rates the inferred AMD. This is a
  source-discovery scoping question (the leaflet covers installment finance in general,
  the page the online product), not a result of the quote rules. Options: a seed-catalog
  note that OCF is the online channel only, or source discovery treating the leaflet as a
  related product for OCF.
- **R2 (F11 residual).** Commercial's `creditworthiness_assessment_required` came back as
  broken JSON in the answer and again in its repair. The repair path works (the same run
  repaired `income_verification_required`), but this nested value defeats the
  JSON-in-a-string format twice. Decision D3 chose no schema change; if it recurs, typed
  value objects for the requirement-policy fields are the fix.
- **R3 (new review kind).** Consumer Loans' `loan_amount` failed "alternative values share
  the same conditions" (two AMD ranges whose conditions do not tell them apart). A
  genuine validation catch; the reviewer supplies the distinguishing condition.
- **F14** (citation on the wrong row) did not recur: Secondary Market published with no
  review.
- **F9 risk** (banners disagreeing with tables) did not raise any `conflicting` review.
