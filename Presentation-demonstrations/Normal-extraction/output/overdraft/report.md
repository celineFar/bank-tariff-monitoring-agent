# Normal tariff extraction

Generated 2026-09-28 07:25 UTC by `extraction_demo.py --cold` against the demonstration stack (Compose project `tariff-demo`). Offering: `consumer_loan/overdraft`.

## Run: fetch, read, extract, validate, publish

Cleared the cached model output (`--cold`): 3 `pdf_link_selections`, 3 `pdf_extraction_cache`, 29 `source_discovery_assessments`, 3 `semantic_extraction_batches` rows.
Submitted run `c0b8cacd` through `POST /api/v1/runs`.

Progress, as polled:

| Elapsed | Run | Stage |
|---|---|---|
| 0s | `queued` | `-` |
| 2s | `running` | `acquisition` |
| 23s | `running` | `pdf_selection` |
| 25s | `running` | `normalization` |
| 65s | `running` | `source_discovery` |
| 70s | `running` | `semantic_extraction` |
| 83s | `running` | `publication` |
| 85s | `succeeded` | `published` |

Run `c0b8cacd` ended after 85s.

## What the run read and what it cost

|  |  |
|---|---|
| Sources discovered | 11 |
| Documents read (PDFs) | 4 |
| Retrieved | 2026-09-28T07:25:11.143278+00:00 |
| Reused an earlier fetch | no |

Gemini, by stage:
| Stage | Model | Calls | Reused from cache | Tokens in / out | Cost |
|---|---|---|---|---|---|
| `discovery.pdf_link_selection` | gemini-3.1-flash-lite | 1 | 0 | 1,153 / 197 | $0.0006 |
| `pdf.transcription` | gemini-3.1-flash-lite | 3 | 0 | 6,930 / 11,703 | $0.0193 |
| `discovery.classification` | gemini-3.1-flash-lite | 4 | 0 | 17,941 / 4,405 | $0.0111 |
| `semantic.extraction` | gemini-3.7-flash | 4 | 0 | 90,514 / 7,188 | $0.0948 |
| **Total** |  | 12 | 0 |  | **$0.1258** |


## Admission

Snapshot `57a41b24` is `accepted`: 21 fields validated, 0 review signals, 66 typed facts projected.
Compared with the previous accepted snapshot `479e2bba`: 10 field change(s): application_channel, effective_rate, eligibility, fees, interest_rate, linked_account_or_card, loan_amount, repayment, required_documents, special_conditions.
Both snapshots were extracted from byte-identical documents, so these are differences between two extractions of the same text (wording, ordering, a rate type), not a new tariff.

## The business view

The card is in [card.md](card.md): values, the conditions they apply under, and the quoted source of each.

## A question, answered from the stored data

Question: “What is the nominal interest rate of the Overdraft?” (`POST /api/v1/tariffs/query`)
Status `answered`, operation `single`, as of 2026-09-28T07:25:11.143278Z, 6 facts.
| Field | Value | Applies when | Citation |
|---|---|---|---|
| `rate.nominal.maximum` | 21.0% | program: scoring-based loans or loans to workers of specific industries; other: currency … | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.maximum` | 20.0% | card tier: Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Masterca… | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.maximum` | 21.0% | card tier: Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master … | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.minimum` | 15.0% | program: scoring-based loans or loans to workers of specific industries; other: currency … | “In particular, the nominal interest rate for AMD denominated loans ma…” |
| `rate.nominal.minimum` | 20.0% | card tier: Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Masterca… | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |
| `rate.nominal.minimum` | 21.0% | card tier: Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master … | “Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital…” |


## Pipeline audit files

Copied from the worker; `4_extraction_evidence.md` highlights every cited quote inside its source.
- [0_run_context.md](audit/0_run_context.md)
- [2_normalization_diff.md](audit/2_normalization_diff.md)
- [2_normalized_webpage.md](audit/2_normalized_webpage.md)
- [2_pdf_link_selection.md](audit/2_pdf_link_selection.md)
- [3_selected_sources.md](audit/3_selected_sources.md)
- [3_source_selection_decisions.md](audit/3_source_selection_decisions.md)
- [3_source_selection_diff.md](audit/3_source_selection_diff.md)
- [4_extraction_evidence.md](audit/4_extraction_evidence.md)
- [4_pre_validation.md](audit/4_pre_validation.md)
- [4_review_queue.md](audit/4_review_queue.md)

## Checks

|  | Check | Observed |
|---|---|---|
| PASS | the run succeeded | run `succeeded`, offering `succeeded` at `published` |
| PASS | published without human review | snapshot `accepted`, 21 validated fields, 0 review signals, 0 reviews |
| PASS | the API serves this snapshot as current | `GET /tariffs/current`: snapshot `57a41b24`, freshness `fresh` |
| PASS | every value has evidence | 64 found facts, 0 without evidence |
| PASS | every citation has a quote and a locator | 181 citations, 0 missing quote or locator |
| PASS | every quote is in the source text it cites | 181 of 181 found verbatim |
| PASS | every figure appears in the source text it cites | 33 of 33 numeric values |
| PASS | the question is answered from this snapshot | `answered`, 6 facts, all cited, as of 2026-09-28T07:25:11.143278Z |

RESULT: PASS
