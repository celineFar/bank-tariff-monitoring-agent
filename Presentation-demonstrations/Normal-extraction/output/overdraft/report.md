# Normal tariff extraction

Generated 2026-09-28 08:33 UTC by `extraction_demo.py --no-run` against the demonstration stack (Compose project `tariff-demo`). Offering: `consumer_loan/overdraft`.

## Run: the latest accepted one (no new run)

Reporting run `d93c4414`; nothing was fetched or extracted now.

## What the run read and what it cost

|  |  |
|---|---|
| Sources discovered | 11 |
| Documents read (PDFs) | 4 |
| Retrieved | 2026-09-28T08:32:41.130193+00:00 |
| Reused an earlier fetch | no |

Gemini, by stage:
| Stage | Model | Calls | Reused from cache | Tokens in / out | Cost |
|---|---|---|---|---|---|
| `pdf.transcription` | gemini-3.1-flash-lite | 2 | 1 | 5,660 / 10,376 | $0.0170 |
| `discovery.classification` | gemini-3.1-flash-lite | 4 | 0 | 17,618 / 4,433 | $0.0111 |
| `semantic.extraction` | gemini-3.7-flash | 4 | 0 | 91,885 / 7,474 | $0.0969 |
| **Total** |  | 10 | 1 |  | **$0.1250** |


## Admission

Snapshot `5fdc76b4` is `accepted`: 21 fields validated, 0 review signals, 68 typed facts projected.
Compared with the previous accepted snapshot `57a41b24`: 12 field change(s): age_requirements, application_channel, effective_rate, eligibility, fees, formal_terms_names, interest_rate, linked_account_or_card, loan_amount, repayment, required_documents, special_conditions.

## The business view

The card is in [card.md](card.md): values, the conditions they apply under, and the quoted source of each.

## A question, answered from the stored data

Question: “What is the nominal interest rate of the Overdraft?” (`POST /api/v1/tariffs/query`)
Status `answered`, operation `single`, as of 2026-09-28T08:32:41.130193Z, 6 facts.
| Field | Value | Applies when | Citation |
|---|---|---|---|
| `rate.nominal.maximum` | 21% | card tier: Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master … | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.maximum` | 20% | card tier: Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Masterca… | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.maximum` | 21% | program: scoring-based loans or loans to workers of specific industries; other: currency … | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.minimum` | 21% | card tier: Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master … | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.minimum` | 20% | card tier: Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Masterca… | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.minimum` | 15% | program: scoring-based loans or loans to workers of specific industries; other: currency … | “³ Other terms can be applied for applications for scoring-based loans…” |


## Pipeline audit files

Copied from the worker to `pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/`; `4_extraction_evidence.md` highlights every cited quote inside its source.
- [0_run_context.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/0_run_context.md)
- [2_normalization_diff.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/2_normalization_diff.md)
- [2_normalized_webpage.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/2_normalized_webpage.md)
- [2_pdf_link_selection.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/2_pdf_link_selection.md)
- [3_selected_sources.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/3_selected_sources.md)
- [3_source_selection_decisions.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/3_source_selection_decisions.md)
- [3_source_selection_diff.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/3_source_selection_diff.md)
- [4_extraction_evidence.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/4_extraction_evidence.md)
- [4_pre_validation.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/4_pre_validation.md)
- [4_review_queue.md](../../pipeline-audit/run_d93c4414-6a1f-4816-9ceb-dcfa60b79194/overdraft/4_review_queue.md)

## Checks

|  | Check | Observed |
|---|---|---|
| PASS | the run succeeded | run `succeeded`, offering `succeeded` at `published` |
| PASS | published without human review | snapshot `accepted`, 21 validated fields, 0 review signals, 0 reviews |
| PASS | the API serves this snapshot as current | `GET /tariffs/current`: snapshot `5fdc76b4`, freshness `fresh` |
| PASS | every value has evidence | 66 found facts, 0 without evidence |
| PASS | every citation has a quote and a locator | 138 citations, 0 missing quote or locator |
| PASS | every quote is in the source text it cites | 138 of 138 found verbatim |
| PASS | every figure appears in the source text it cites | 38 of 38 numeric values (2 zeros stated in words) |
| PASS | the question is answered from this snapshot | `answered`, 6 facts, all cited, as of 2026-09-28T08:32:41.130193Z |

Zero in words: `fee.early_repayment` = 0 (no conditions) from “Other amounts payable > Early repayment fee: N/A”.
Zero in words: `fee.other` = 0 (channel: online) from “There are no extra fees when applying online.”.
RESULT: PASS
