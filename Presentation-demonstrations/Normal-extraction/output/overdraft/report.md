# Normal tariff extraction

Generated 2026-09-29 01:44 UTC by `extraction_demo.py --cold` against the demonstration stack (Compose project `tariff-demo`). Offering: `consumer_loan/overdraft`.

## Run: fetch, read, extract, validate, publish

Cleared the cached model output (`--cold`): 3 `pdf_link_selections`, 5 `pdf_extraction_cache`, 59 `source_discovery_assessments`, 9 `semantic_extraction_batches` rows.
Submitted run `8a2fdd20` through `POST /api/v1/runs`.

Progress, as polled:

| Elapsed | Run | Stage |
|---|---|---|
| 0s | `queued` | `acquisition` |
| 2s | `running` | `acquisition` |
| 23s | `running` | `pdf_selection` |
| 25s | `running` | `normalization` |
| 65s | `running` | `source_discovery` |
| 72s | `running` | `semantic_extraction` |
| 83s | `succeeded` | `published` |

Run `8a2fdd20` ended after 83s.

## What the run read and what it cost

|  |  |
|---|---|
| Sources discovered | 11 |
| Documents read (PDFs) | 4 |
| Retrieved | 2026-09-29T01:44:03.852631+00:00 |
| Reused an earlier fetch | no |

Gemini, by stage:
| Stage | Model | Calls | Reused from cache | Tokens in / out | Cost |
|---|---|---|---|---|---|
| `discovery.pdf_link_selection` | gemini-3.1-flash-lite | 1 | 0 | 1,153 / 197 | $0.0006 |
| `pdf.transcription` | gemini-3.1-flash-lite | 3 | 0 | 6,930 / 11,703 | $0.0193 |
| `discovery.classification` | gemini-3.1-flash-lite | 4 | 0 | 17,941 / 4,418 | $0.0111 |
| `semantic.extraction` | gemini-3.7-flash | 3 | 0 | 67,843 / 7,512 | $0.0791 |
| **Total** |  | 11 | 0 |  | **$0.1100** |


## Admission

Snapshot `3bb3d6cc` is `accepted`: 21 fields validated, 0 review signals, 63 typed facts projected.
Compared with the previous accepted snapshot `57a41b24`: 11 field change(s): age_requirements, application_channel, effective_rate, fees, formal_terms_names, interest_rate, linked_account_or_card, loan_amount, repayment, required_documents, special_conditions.
Both snapshots were extracted from byte-identical documents, so these are differences between two extractions of the same text (wording, ordering, a rate type), not a new tariff.

## The business view

The card is in [card.md](card.md): values, the conditions they apply under, and the quoted source of each.

## A question, answered from the stored data

Question: “What is the nominal interest rate of the Overdraft?” (`POST /api/v1/tariffs/query`)
Status `answered`, operation `single`, as of 2026-09-29T01:44:03.852631Z, 4 facts.
| Field | Value | Applies when | Citation |
|---|---|---|---|
| `rate.nominal.maximum` | 21.0% | other: applications for scoring-based loans or loans to workers of specific industries | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.minimum` | 21.0% | card tier: Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master … | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.minimum` | 20.0% | card tier: Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Masterca… | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.minimum` | 15.0% | other: applications for scoring-based loans or loans to workers of specific industries | “³ Other terms can be applied for applications for scoring-based loans…” |


## Pipeline audit files

Copied from the worker to `pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/`; `4_extraction_evidence.md` highlights every cited quote inside its source.
- [0_run_context.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/0_run_context.md)
- [2_normalization_diff.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/2_normalization_diff.md)
- [2_normalized_webpage.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/2_normalized_webpage.md)
- [2_pdf_link_selection.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/2_pdf_link_selection.md)
- [3_selected_sources.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/3_selected_sources.md)
- [3_source_selection_decisions.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/3_source_selection_decisions.md)
- [3_source_selection_diff.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/3_source_selection_diff.md)
- [4_extraction_evidence.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/4_extraction_evidence.md)
- [4_pre_validation.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/4_pre_validation.md)
- [4_review_queue.md](../../pipeline-audit/run_8a2fdd20-75d1-4532-961a-3eff3eeb05b3/overdraft/4_review_queue.md)

## Checks

|  | Check | Observed |
|---|---|---|
| PASS | the run succeeded | run `succeeded`, offering `succeeded` at `published` |
| PASS | published without human review | snapshot `accepted`, 21 validated fields, 0 review signals, 0 reviews |
| PASS | the API serves this snapshot as current | `GET /tariffs/current`: snapshot `3bb3d6cc`, freshness `fresh` |
| PASS | every value has evidence | 61 found facts, 0 without evidence |
| PASS | every citation has a quote and a locator | 155 citations, 0 missing quote or locator |
| PASS | every quote is in the source text it cites | 155 of 155 found verbatim |
| PASS | every figure appears in the source text it cites | 31 of 31 numeric values (1 zeros stated in words) |
| PASS | the question is answered from this snapshot | `answered`, 4 facts, all cited, as of 2026-09-29T01:44:03.852631Z |

Zero in words: `fee.early_repayment` = 0 (no conditions) from “Other amounts payable > Early repayment fee: N/A”.
RESULT: PASS
