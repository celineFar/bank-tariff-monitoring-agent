# First iteration: fix plan

Date: 2026-09-27 · Branch: `fix/1st-iteration` (from `integration/process-fixes` at
`09e5181`) · Status: **in progress** (see each phase's notes). Sources: the seed-URL evaluation
[`tests/eval/seed_url_eval_2026-09-27.json`](../../tests/eval/seed_url_eval_2026-09-27.json)
(15 questions against live ameriabank.am ground truth) and the review diagnosis of the
same day (22 pending reviews traced to their causes). Four solution choices were asked
and answered; they are recorded in [Decisions](#decisions).

## Scope

Everything the first live end-to-end evaluation found wrong, from source discovery to
the chat answer:

- source discovery's page-header rule ([source_discovery.py](../../app/services/source_discovery.py));
- semantic extraction's prompt, response validation, field checks and repair budget
  ([semantic_extraction.py](../../app/services/semantic_extraction.py),
  [domain/semantic_extraction.py](../../app/domain/semantic_extraction.py));
- review policy and decisions ([review_resolution.py](../../app/services/review_resolution.py),
  [review_decisions.py](../../app/services/review_decisions.py), [cli.py](../../app/cli.py));
- projection and the structured query service
  ([structured_projection.py](../../app/services/structured_projection.py),
  [structured_tariff_query.py](../../app/services/structured_tariff_query.py));
- the request interpreter and the agent instruction
  ([intent_resolution.py](../../app/services/intent_resolution.py),
  [tools/resolution.py](../../app/tools/resolution.py), [agent.py](../../app/agent.py));
- operations: acquisition retries, cost attribution, the scheduler
  ([acquisition.py](../../app/services/acquisition.py),
  [model_call_usage.py](../../app/services/model_call_usage.py), [worker.py](../../app/worker.py)).

**Out of scope:** changing any model; the 22 reviews pending in the dev database (they
are decided by a human after the re-run, Phase 7); the tariff content conflicts on
Ameria's own site (hero vs. table), which the system should report, not resolve.

## How this was checked

- **Live run, 2026-09-27.** Both families monitored through `POST /api/v1/runs`, three
  failed mortgages retried, then the 15 questions asked once each through ADK `POST /run`
  in fresh sessions. Result: 5 of 13 offerings published, 8 held by 22 reviews; 7 of 15
  answers correct, no fabricated value. Cost: $2.39 ingestion, $0.29 for the questions.
- **Ground truth.** All 13 seed pages (rendered from the site's content API) and 27
  linked PDFs, every quote re-checked against the saved text
  (scratchpad `groundtruth/`, summarized in the evaluation file's `cases[].expected`).
- **Review causes.** Each of the 22 reviews was traced through the pipeline audit
  archive (`artifacts/pipeline-audit/run_*/<offering>/`): source-selection decisions,
  extraction evidence, pre-validation answers. The two failing Commercial answers were
  re-validated locally against `ExtractionBatchResponse` to get the exact error.
- **Repairs.** From `logs/worker.log`: 20 repair calls, 16 accepted, 4 failed (all
  `income_verification_required`, F10).

## Summary

| ID | Problem | Found in | Severity | Status |
|---|---|---|---|---|
| F1 | Family rankings omit offerings with no published data and do not say so | Q1, Q2, Q3 | **high** | planned |
| F2 | A single-currency offering's rate is stored without a currency | Q1 | medium | planned |
| F3 | "Terms" is interpreted as loan length only | Q6 | medium | planned |
| F4 | After an abstention the agent offers monitoring whatever the cause | Q5, Q9, Q10, Q11, Q15 | medium | planned |
| F5 | "Not published by the bank" is indistinguishable from "not captured" | Q9 | medium | planned |
| F6 | The catalog intro opens every new conversation | all | low | planned |
| F7 | Long or "…"-stitched citation quotes fail validation | 10 reviews | **high** | planned |
| F8 | One invalid field discards the whole extraction call | 8 reviews (Commercial) | **high** | planned |
| F9 | The page-header rule discards the hero banner | 2 reviews (+ hidden values on 4 offerings) | **high** | planned |
| F10 | The income-verification check rejects Ameria's wording | 3 reviews, 4 failed repairs | **high** | planned |
| F11 | Broken JSON in `value_json` goes straight to review | 3 reviews | medium | planned |
| F12 | Repair budget and priority skip the fields that become reviews | Primary, Secondary | medium | planned |
| F13 | A required field the source omits can never be resolved | 3 reviews (Diaspora, No-income) | **high** | planned |
| F14 | A citation points at the wrong evidence item | 1 review (Secondary) | low | watch |
| F15 | Every fee carries the whole fee field's citations | Q4 | medium | planned |
| F16 | Citations name internal ids, not sections a person can find | Q1, Q3, Q4 | low | planned |
| F17 | Collateral/vehicle service fees are listed for an unsecured credit line | Q4 | low | planned |
| F18 | A transient page-fetch failure fails the offering | Secondary, Renovation | medium | planned |
| F19 | Pipeline model calls are recorded without a run id | cost ledger | low | planned |
| F20 | A schema failure is logged only as "1 error(s)" | Commercial | low | planned |
| F21 | The daily scheduler cannot be switched off | operations | low | planned |

F7, F8, F9, F10 and F11 together remove 18 of the 22 reviews; F13 resolves 3 more with a
single human confirmation each; F14 is the remaining one.

## F1. Family rankings omit offerings with no published data

**Problem.** `_rank` ([structured_tariff_query.py:533](../../app/services/structured_tariff_query.py#L533))
works only on facts of offerings with an active profile, and `not_ranked` is the
difference between those facts and the ranked ones (line 625). An in-scope offering
with no active profile (pending review, failed run, never monitored) appears nowhere.
Q2 answered AMD 100M as the largest mortgage amount from 2 of 9 offerings (truth: AMD
150M, six offerings); Q3 named 2 of the 8 offerings at 360 months; Q1 dropped Consumer
Loans silently.

**Fix (decision D2: rank what exists, disclose the gap).**
- The ranking result carries `coverage`: every in-scope offering of `plan.offering_ids`
  with its state: `ranked`, `no_value` (published, field not disclosed), `not_comparable`
  (value in another unit or currency group), `awaiting_review` (with the pending count),
  `run_failed` (last failure code), or `never_monitored`.
- `not_ranked` keeps its meaning but names every non-ranked offering with its reason.
- `answer` text leads with "ranked N of M"; the agent instruction requires the answer to
  say how many offerings were ranked and to name each missing one with its reason.
- The same coverage block for `compare` and `overview` when an explicitly requested
  offering has no data.
- State comes from repositories the service already has access to (active profiles,
  pending reviews, latest offering execution); no model call.

**Test.** Unit: a 9-offering plan with 2 profiles returns `coverage` with 7 non-ranked
entries and correct reasons. Eval: Q2 and Q3 answers name the missing offerings.

## F2. A single-currency offering's rate has no currency

**Problem.** Online Consumer Finance's 17% (`rate.nominal.*`) is stored with
`currency = NULL` because the hero banner prints no currency next to the rate; its
amount facts are AMD. In an AMD ranking the fact sits in a group of its own and is
listed as `not_ranked` (Q1).

**Fix (decision D5).** At projection, when a rate or fee fact has no currency condition
and every amount/credit-limit fact of the same snapshot carries exactly one and the same
currency, inherit that currency and record `currency_source: "inferred_from_amount"` in
the fact's conditions. Any other case stays `NULL` and is reported by F1 as
`not_comparable` with reason `currency_not_stated`.

**Test.** Unit: projection of the captured OCF extraction yields AMD rate facts with the
inference marker; a two-currency offering is left untouched.

## F3. "Terms" is read as loan length only

**Problem.** "What purpose and terms does the Online Consumer Finance cover?" was
planned as `identity.purpose` + `term.*` only; the answer omitted amount, rate, APR,
collateral and repayment.

**Fix.** In the request interpreter's instructions and the planner's field bounds: a
broad word (terms, conditions, details, "what does it offer") without a named field
maps to the offering's key-field set: amount, nominal and effective rate, term,
collateral, repayment, main fees. "Repayment term" / "loan term" / "how long" keep
mapping to `term.*`. Add the Q6 phrasing and two paraphrases to the recorded
interpretation cases.

**Test.** `tests/fixtures/interpretation_cases.py` gains the cases; re-record with
`scripts/record_interpretations.py` (paid, about 3 interpreter calls).

## F4. The next step after an abstention ignores the cause

**Problem.** Q5, Q10, Q11 and Q15 abstained because the offering was held in review,
and Q9 because the bank publishes no application fee, yet each answer offered a new
monitoring run (a run had just completed). The tool result says only `missing` or
`insufficient_evidence` with a generic reason.

**Fix.** Every non-answered `TariffQueryResult` carries a `reason_code`:
`awaiting_review` (with count), `run_failed` (failure code), `never_monitored`,
`not_stated_in_source` (F5), `field_not_extracted`. The agent instruction maps them:
review → offer to review the pending candidates; not stated → say the bank does not
publish it; never monitored / failed / stale → offer monitoring.

**Test.** Unit per reason code; eval Q5, Q9, Q10.

## F5. "Not published" vs. "not captured"

**Problem.** The Express Mortgage fee list was extracted (disbursement fee N/A, other
fees) and contains no application fee, but the answer said only "no accepted evidence".

**Fix.** When the requested field is a member of a list field that was `found` (fees,
required documents, collateral alternatives) and no item matches, return
`insufficient_evidence` with `reason_code = not_stated_in_source` and cite the list's
evidence (the fee section), so the answer can say "the published fee list contains no
application fee" with a source. A scalar field whose extraction status is `not_stated`
gets the same code.

**Test.** Unit with the Express projection; eval Q9 wording.

## F6. The catalog intro opens every new conversation

**Problem.** `resolve_request` sends `catalog_intro` whenever the session has not shown
it ([tools/resolution.py:191](../../app/tools/resolution.py#L191)), and the instruction
tells the agent to use it on the first turn, so every answer starts with the catalog and
a pending-review notice.

**Fix (decision D4: intro only on greetings).** Send `catalog_intro` only for
greeting / capability intents (`list_supported_products`, a greeting, or an empty
question). For a tariff question, the answer comes first; a pending-review note is added
only when a pending review concerns an offering in the answer's scope (one line).

**Test.** Unit on `resolve_request` output by intent; eval: no intro in the 15 answers.

## F7. Long or stitched citation quotes

**Problem.** The loan-to-value (LTV) section is several paragraphs long and the model
quotes all of it. The prompt asks for "a short verbatim quote"
([semantic_extraction.py:129](../../app/services/semantic_extraction.py#L129)); the
1,500-character limit exists only in `ModelCitation.quote`
([domain/semantic_extraction.py:496](../../app/domain/semantic_extraction.py#L496)).
Primary and Secondary shortened the quote with "…" and failed the verbatim check
(line 2176); Commercial exceeded 1,500 characters on both models (F8).

**Fix.**
- Prompt: "one quote per value, at most 300 characters, copied exactly; never use '...'
  or '…'; cite several short quotes rather than one long one." Bump
  `SEMANTIC_EXTRACTION_PROMPT_VERSION` to 7.
- Validation: a quote containing "..." or "…" is split at the ellipsis; if every segment
  is verbatim in the same evidence item, the citation is replaced by one citation per
  segment (the stored quotes stay the source's own text, via `source_span`). Otherwise it
  fails as today.
- A quote longer than the old limit that is verbatim in its evidence is kept whole:
  `ModelCitation.quote` allows 10,000 characters. (Revised in Phase 0: trimming was
  dropped. Model-facing citations are already cut to 300 characters for display,
  and a stored quote must stay the source's own text.)

**Test.** Unit with the captured Primary and Secondary LTV answers (both pass); a quote
whose segments come from different evidence items still fails.

## F8. One invalid field discards the whole extraction call

**Problem.** `ExtractionBatchResponse.model_validate_json` is all-or-nothing
([semantic_extraction.py:468](../../app/services/semantic_extraction.py#L468)). In both
Commercial attempts the only error was `results[3].evidence[0].quote:
string_too_long`, and all 8 fields of the `documents_and_details` call became reviews.

**Fix.** Parse the response envelope first (`results` as a list of raw objects), then
validate each result on its own. A result that fails is routed to the one-field repair
(F12) and, if still invalid, to review; the other fields proceed. The call is retried
only when the envelope itself is unusable (not JSON, wrong field set).

**Test.** Unit: the two captured Commercial raw answers yield 7 validated fields and 1
field for repair.

## F9. The page-header rule discards the hero banner

**Problem.** `CandidateLayout.PAGE_HEADER` ("Unheaded blocks above the page's first
heading are the site header", [source_discovery.py:583](../../app/services/source_discovery.py#L583))
drops Ameria's hero banner, which sits above the first heading and states the rate,
term, amount, APR and down payment. No Income Verification lost its term and amount (it
has no PDF); Primary, Commercial and Construction lost banner values their PDFs
repeated.

**Fix.** A page-header block that carries a tariff label with a value (a `Label: value`
line whose value has a number with %, months/years, a currency code or million/mln) is
classified as `CONTENT` and goes to the source-discovery classifier like any other block.
Language switches, phone numbers and menus keep the rule.

**Test.** Unit on the captured No Income Verification page: the five hero blocks reach
selection. Source-discovery cache keys change for affected pages (expected).

## F10. The income-verification check rejects Ameria's wording

**Problem.** The check accepts only fixed phrases such as "proof of income" or "income
verification" ([semantic_extraction.py:2138](../../app/services/semantic_extraction.py#L2138)).
Ameria writes "Proof of employment and/or other income", so correct values fail on every
offering that uses it, and the repair call can never pass (4 of 4 failed repairs).

**Fix.** Replace the marker tuple with one pattern for explicit income documentation:
`proof of (employment and/or )?(other )?income`, `income (verification|document|
statement|certificate)`, `(salary|employment) (statement|certificate|reference)`,
`documentary proof of income`. The intent of the check (no inference from
creditworthiness text) is unchanged.

**Test.** Unit: the three captured candidates pass; a creditworthiness-only passage
still fails.

## F11. Broken JSON in `value_json`

**Problem.** `value_json` is JSON written inside a string. On nested values the model
closed the list and dropped the final `}` (Primary and Secondary
`income_verification_required`, Secondary `creditworthiness_assessment_required`); the
content was right, the result went to review with "invalid value_json".

**Fix (decision D3: repair call, no schema change).** A result whose `value_json` does
not parse is sent to the one-field repair call with the parse error and its own previous
answer; the missing bracket is never guessed. It counts against the repair budget (F12).

**Finding (Phase 0).** This is already what the code does: `_decode_value` raises, so
`_field_semantic_issues` makes the field a repair candidate. On 2026-09-27 Primary's
repair was refused by the F10 check, and Secondary's two JSON fields were skipped because
the budget of 3 was spent first (F12). F11 therefore needs no code change; a guard test
keeps the behaviour.

**Test.** Unit with a fake extractor: an unparseable `value_json` triggers a repair for
that field (guard, passes today).

## F12. Repair budget and priority

**Problem.** `max_repairs_per_run = 3` per offering extraction, allocated by
`_REPAIR_PRIORITY` ([semantic_extraction.py:1752](../../app/services/semantic_extraction.py#L1752)),
which lists rates, amount, term, fees, category and product name only. Repairs succeeded
16 of 16 times where the check was sound, but on Primary and Secondary the budget was
spent before the fields that later became reviews got one.

**Fix (decision D6).** Raise the default to 6 per offering and log skipped fields by
name. A repair costs about $0.01–0.02 on `gemini-3.7-flash`. (Revised in Phase 0: the
planned reordering was dropped. Every field with an issue becomes a review that blocks
publication, so "would-be reviews first" orders nothing; the existing priority stays.)

**Test.** Unit: the default is 6 in settings and environment; with budget 0 the warning
names the skipped field.

## F13. A required field the source omits can never be resolved

**Problem.** For `missing_required_field` the policy allows only `reject_all` or an
evidence-cited `override` ([review_resolution.py:656](../../app/services/review_resolution.py#L656)).
Diaspora's repayment method and No Income Verification's repayment method and fees are
not published, so there is nothing to cite, and rejecting discards the offering's
correct rates, amount and term.

**Fix (decision D1: add "confirm not stated").**
- `ReviewDecisionType.CONFIRM_NOT_STATED`, allowed only for `missing_required_field`.
- It requires a reason; the reviewer is shown the passages the extraction read (already
  in the review's evidence set).
- Applying it records the field as `not_stated` with `confirmed_not_stated = true` on
  the validated field (a new flag, default false) and the reason as its explanation.
  `extraction_is_acceptable` and signal detection accept a confirmed required field;
  the snapshot then activates like any approval. The answer path reports it as
  `not_stated_in_source` (F4/F5).
- `review_decision_memory` remembers it, so the next run with the same extraction answer
  does not ask again (existing mechanism).
- CLI: a new choice in the review prompt; the ADK pause schema accepts the new value.

**Test.** Unit on the decision service and policy; integration: a Diaspora-like snapshot
with one `missing_required_field` review activates after the confirmation.

## F14. A citation points at the wrong evidence item (watch)

Secondary `property_market`: the quote "Real estate loan for secondary market" is the
page heading (`b17`), which also validated `product_name`; the second citation points at
table row `t1:row:1`, which does not contain it (inferred: the review keeps only the
first quote). F7's per-citation handling and F8's per-field validation make this a
one-field repair. No separate change; re-check after Phase 7.

## F15. Every fee carries the whole fee field's citations

**Problem.** The fee projector emits each fee with the whole extracted `fees` field
([structured_projection.py:183](../../app/services/structured_projection.py#L183)), so
each fee fact cites all 14 fee evidence items (Q4).

**Fix.** Keep, per fee item, the citations whose quote contains that fee's number or
description (the same number matching `_quote_numbers` uses); fall back to the field's
citations only when none match. (Revised in Phase 0: the fallback is not marked;
`TariffFact` has no place for it and the answer is unchanged either way.)

**Test.** Unit with the Credit Line projection: each fee cites 1–2 items.

## F16. Citations are not readable by a person

**Problem.** Answers cite `t1:row:4`, `#Tab1_57832` or an XPath locator; a person cannot
find the row on the page.

**Fix.** Carry the section path the normalizer already builds (for example "Consumer
loan > Terms and conditions > Credit line unsecured", table row label) into
`fact_evidence.locator` as `section` and `row_label`, and PDF page as `page`; the
model-facing citation shows `section` / `row_label` / `page` and never the raw id.

**Test.** Unit on the citation payload; eval answers cite a tab or page.

## F17. Unrelated general service fees on an unsecured product

**Problem.** Credit Line's answer lists "release/substitution of the collateral", a
vehicle plate change and similar items from the bank-wide loan-service table.

**Fix (decision D7).** Keep general service fees, but when the offering's extraction
states no collateral (the field is absent or not stated, as for Credit Line), omit
general-service items whose description concerns collateral, pledges, security interests
or vehicles. Product-scope fees are never filtered.

**Test.** Unit with the Credit Line projection.

## F18. A transient page-fetch failure fails the offering

**Problem.** Secondary Market and Renovation failed at acquisition twice (browser
failure, one during a DNS outage in the worker) and succeeded on the third try.

**Fix.** Retry acquisition once within the run, after a short backoff, when it fails
with `BROWSER_FAILED`, `BROWSER_UNAVAILABLE` or `INCOMPLETE_CONTENT`. (Revised in
Phase 0: Secondary Market's first failure was `INCOMPLETE_CONTENT` on a page that
rendered fully later, so it is retried too; one retry bounds the cost.)

**Test.** Offline acquisition scenario with a fake browser that fails once.

## F19. Pipeline model calls have no run id

**Problem.** `active_run_id` reads the run from the ADK session state
([model_call_usage.py:338](../../app/services/model_call_usage.py#L338)); the pipeline's
own ADK calls (discovery, PDF transcription, extraction) run in separate sessions, so
every pipeline ledger row has `run_id = NULL` and cost per run is not measurable.

**Fix.** The pipeline sets a context variable with `run_id` and `offering_id` for each
offering; the usage recorder falls back to it when the session has none.

**Test.** Unit: a recorded pipeline call carries both ids.

## F20. Schema failures are logged only as a count

**Fix.** Log each validation error's location and type (for example
`results[3].evidence[0].quote string_too_long`), never the input value, in the warning
and in the pipeline audit's pre-validation report.

## F21. The daily scheduler cannot be switched off

**Fix.** `SCHEDULE_ENABLED` (default `true`); when `false` the worker still claims API
runs and sweeps embeddings but adds no cron job. Document it in
[docs/configuration.md](../../docs/configuration.md).

## Decisions

| ID | Question | Decision | By |
|---|---|---|---|
| D1 | How to resolve a required field the source omits | New review decision "confirm not stated" (F13) | user |
| D2 | Rankings with unpublished in-scope offerings | Rank what exists and disclose every missing offering with its reason (F1) | user |
| D3 | Broken JSON in `value_json` | Send it to the one-field repair call; no schema change (F11) | user |
| D4 | Catalog intro | Only on greetings and capability questions (F6) | user |
| D5 | Currency of a single-currency offering | Inherit from the snapshot's amount facts when they carry exactly one currency, marked as inferred (F2) | plan |
| D6 | Repair budget | 6 per offering, existing priority kept (F12) | plan |
| D7 | General service fees on unsecured products | Omit collateral/vehicle items when the extraction states no collateral (F17) | plan |
| D8 | Stitched quotes | Split at the ellipsis and accept only when every segment is verbatim in the same evidence item (F7) | plan |

## Implementation phases

Each phase ends with `uv run pytest tests/unit tests/integration` green. Paid steps are
marked **(paid)** with an estimate at the repository's list prices.

### Phase 0: Preparation

- [x] Create branch `fix/1st-iteration` from `integration/process-fixes` (`09e5181`).
- [x] Run `uv run pytest tests/unit tests/integration` and record the baseline.
- [x] Copy the needed captures into `fix-process/1st-iteration-fixes/data/` (no model
      cost): the two Commercial raw answers, the Primary/Secondary LTV and JSON-string
      candidates, the three income-verification candidates, the No Income Verification
      normalized page, the Credit Line and Express projections, OCF's extraction.
- [x] Add one `xfail(strict=True)` regression test per item F1–F13, F15–F21 asserting
      the target behaviour on those captures.
- [x] Check each `xfail` fails today with `--runxfail`.

**Phase 0 notes (done).**

- **Baseline.** `uv run pytest tests/unit tests/integration`: 1,199 passed, 59 skipped,
  1 failed, 3 errors. The four are live-environment tests, not regressions:
  `tests/integration/test_agent.py::test_agent_stream` needs a Gemini key in the shell,
  and the three `test_server_e2e.py` tests need a server that can start. Later phases
  compare against this.
- **Captures** (`data/`): `snapshots_2026-09-27.json.gz` (all 13 snapshots' semantic
  extraction, gzipped from 8.7 MB), `reviews_2026-09-27.json` (the 22 pending reviews),
  `commercial_documents_and_details_raw_{1,2}.json` (the two answers that failed the
  schema), `no_income_verification_normalized_webpage.md`. Loader:
  `tests/fixtures/first_iteration.py` (`captured_accepted_snapshot` rebuilds an
  accepted `SnapshotAttempt`; replaying it through today's projector reproduces the
  defects: OCF rates without currency, 14 citations per Credit Line fee, no section).
- **Tests:** `tests/unit/test_first_iteration_fixes.py`, 30 tests. 25 are
  `xfail(strict=True)` and each fails for the missing fix (checked with `--runxfail`);
  5 are guards that pass today and must keep passing (F2 two-currency, F6 catalog
  question, F10 creditworthiness-only passage, F11 repair of broken JSON, F17 mortgage
  collateral fees). The F13 policy test calls `pytest.xfail` while the enum member is
  missing; it becomes a normal test once F13 lands.
- **Plan corrections found while reading the code** (recorded in the items above): F11
  needs no code change (broken JSON is already repaired; the reviews came from F10 and
  F12); F12's reordering was dropped; F7 keeps long verbatim quotes instead of trimming;
  F15's fallback is unmarked; F17 keys on "extraction states no collateral"; F18 also
  retries `INCOMPLETE_CONTENT`; F13 adds a `confirmed_not_stated` flag.
- **Names the later phases must provide** (the tests import them):
  `StructuredTariffQueryService(..., offering_states=)`, `OfferingDataState`,
  `TariffQueryResult.reason_code`, `metadata["coverage"]`, `parse_batch_response`,
  `ReviewDecisionType.CONFIRM_NOT_STATED`, `ValidatedFieldResult.confirmed_not_stated`,
  `model_facing_result` (tools/reads), `acquire_with_retry`, `pipeline_usage_scope`,
  `SchedulerSettings.enabled`.

### Phase 1: Extraction validation (F8, F7, F10, F20)

- [x] F8: parse the envelope, validate each result separately; route an invalid result
      to repair, then review; retry the call only for an unusable envelope.
- [x] F7: prompt rule (one quote per value, ≤ 300 characters, no ellipses); bump
      `SEMANTIC_EXTRACTION_PROMPT_VERSION` to 7 in `.env.example` and config defaults.
- [x] F7: split ellipsis quotes into verbatim segments of the same evidence item; keep
      an over-long verbatim quote whole (trimming dropped, see F7).
- [x] F10: replace the marker tuple with the explicit-income pattern.
- [x] F20: log validation error locations and types; show them in `4_pre_validation.md`.
- [x] Remove the matching `xfail` marks; run the suite.

**Phase 1 notes (done).**

- **What changed** (all in [semantic_extraction.py](../../app/services/semantic_extraction.py)
  unless named):
  - `parse_batch_response` replaces the all-or-nothing `model_validate_json` in
    `AdkSemanticExtractor._extract_once`. Invalid results are dropped and returned as
    `ExtractorOutput.dropped` (field + `ValidationIssue`s); `_CallOutcome` carries them;
    `extract()` keys them by `(batch.id, field)` and `_cardinality_issues` turns a dropped
    field's schema errors into its repair and review issues (instead of "field is
    missing"). The call is still retried when the envelope is unusable.
  - `_schema_error_summary` formats errors as `results[3].evidence[0].quote
    string_too_long` (no input values), used in the call error and in a warning per
    dropped field. The audit's `4_pre_validation.md` shows them through the review
    items' validation issues and the raw outputs' error text; no audit code changed.
  - `_expand_stitched_quotes` runs on fresh, cached and repaired responses before
    validation.
  - `_EXPLICIT_INCOME` (a regex) replaces the income marker tuple.
  - [domain/semantic_extraction.py](../../app/domain/semantic_extraction.py):
    `ModelCitation.quote` max length 1,500 → 10,000.
  - Prompt: one quote per value, at most 300 characters, never `...`/`…`.
    `SEMANTIC_EXTRACTION_PROMPT_VERSION` 6 → 7 in `environment.py`, `models.py` and
    `.env.example`. **The local `.env` still says 6** and overrides the default: set it
    to 7 before the Phase 8 live run (the prompt text change alone already changes the
    cache fingerprint, so this is for the record, not for correctness).
  - [docs/semantic-extraction.md](../../docs/semantic-extraction.md) describes
    per-result parsing, quote splitting and the income check.
- **F12 early.** The repair loop now names skipped fields in its warning (it was
  rewritten for F8), so `test_f12_skipped_repairs_are_logged_by_field` passes already;
  its `xfail` was removed here. The budget default stays for Phase 2.
- **Tests.** `test_f7_*` (3), `test_f8_*` (2, one added: a dropped field reaches review
  with its schema error while the call's other fields are kept), `test_f10_*`,
  `test_f20_*` pass. Full suite: 1,212 passed, 59 skipped, 18 xfailed; the only
  non-passing tests are the 4 baseline live-environment ones.
- **Flaky test seen once:** `tests/unit/test_monitoring_node.py::test_a_run_owned_by_
  another_process_is_followed_not_executed` failed in one full run and passed in the
  next full run and 3 isolated runs of its module. Nothing in Phase 1 touches the
  monitoring node; it is timing-sensitive under load.

### Phase 2: Repairs (F11, F12)

- [x] F11: an unparseable `value_json` becomes a repair candidate carrying the parse
      error. (Already the behaviour; kept by the guard test, no code change.)
- [x] F12: default `SEMANTIC_EXTRACTION_MAX_REPAIRS_PER_RUN=6`; log skipped fields by
      name. (The reordering was dropped, see F12.)
- [x] Remove the matching `xfail` marks; run the suite.

**Phase 2 notes (done).**

- **F11:** no code change. `test_f11_an_unparseable_value_is_sent_to_the_repair_call`
  (a guard since Phase 0) shows a broken `value_json` gets a repair call.
- **F12:** the default is 6 in [environment.py](../../app/config/environment.py),
  [models.py](../../app/config/models.py) and `.env.example`, and in
  [docs/configuration.md](../../docs/configuration.md),
  [docs/semantic-extraction.md](../../docs/semantic-extraction.md) and the maintenance
  guide. `tests/unit/test_config.py::test_defaults_match_the_approved_architecture`
  pinned 3 and now pins 6. The skipped-field log line landed in Phase 1.
- **The local `.env` pins `SEMANTIC_EXTRACTION_MAX_REPAIRS_PER_RUN=3`** and overrides the
  new default. Set it to 6 (or remove the line) before the Phase 8 live run, together
  with `SEMANTIC_EXTRACTION_PROMPT_VERSION=7` (Phase 1 note).
- **Cost bound:** at about $0.01–0.02 per repair, 6 repairs add at most about $0.12 per
  offering, $1.56 for all 13 in the worst case; on 2026-09-27 the worst offering needed
  7 (Secondary: 3 repaired, 4 skipped).
- Full suite: as after Phase 1 plus the F12 default test; only the 4 baseline
  live-environment tests fail.

### Phase 3: Source discovery (F9)

- [ ] F9: a page-header block with a tariff `Label: value` goes to the classifier as content.
- [ ] Re-run the source-discovery offline scenarios in
      [../source_discovery/scenarios/](../source_discovery/scenarios/) and check no
      navigation block is newly selected.
- [ ] Remove the `xfail` mark; run the suite.

### Phase 4: Review decision (F13)

- [ ] Add `ReviewDecisionType.CONFIRM_NOT_STATED` (domain, validation, `review_policy`
      for `missing_required_field` only).
- [ ] Apply it in the decision service: field recorded `not_stated` with reviewer,
      reason and time; snapshot activates when every review is decided.
- [ ] Add a migration if the stored decision type is constrained in SQL.
- [ ] CLI: new choice in the review prompt; the pause schema accepts it.
- [ ] `review_decision_memory` stores and replays it.
- [ ] Update [docs/native-hitl-review.md](../../docs/native-hitl-review.md) and
      [docs/review-quarantine.md](../../docs/review-quarantine.md).
- [ ] Remove the `xfail` marks; run the suite.

### Phase 5: Projection and query service (F1, F2, F4, F5, F15, F16, F17)

- [ ] F1: `coverage` block and reasoned `not_ranked` for rank, compare and overview.
- [ ] F2: currency inheritance with the `inferred_from_amount` marker.
- [ ] F4: `reason_code` on every non-answered result.
- [ ] F5: `not_stated_in_source` for list fields without a matching item and for
      `not_stated` scalars, citing the list's evidence.
- [ ] F15: per-fee citations by number/description match, fallback marked.
- [ ] F16: `section`, `row_label`, `page` in `fact_evidence.locator` and the citation payload.
- [ ] F17: collateral/vehicle service fees omitted for unsecured offerings; bank-wide label.
- [ ] Run `scripts/audit_structured_projection.py` on the dev database (no model cost).
- [ ] Update [docs/tariff-query-services.md](../../docs/tariff-query-services.md) and
      [docs/indexing-projection.md](../../docs/indexing-projection.md).
- [ ] Remove the `xfail` marks; run the suite.

### Phase 6: Interpreter and agent (F3, F4, F6)

- [ ] F3: broad "terms/conditions/details" maps to the key-field set; add Q6 and two
      paraphrases to `tests/fixtures/interpretation_cases.py`.
- [ ] F4: agent instruction maps each `reason_code` to its next step (review, "not
      published", or monitoring).
- [ ] F6: `catalog_intro` only for greeting/capability intents; pending-review note only
      when it concerns the answer's scope.
- [ ] F1: agent instruction requires "ranked N of M" and names each missing offering.
- [ ] **(paid, ≈ $0.05)** Re-record interpretations with `scripts/record_interpretations.py`.
- [ ] Remove the `xfail` marks; run the suite.

### Phase 7: Operations (F18, F19, F21)

- [ ] F18: one in-run acquisition retry with backoff for transient failure codes.
- [ ] F19: context variable with `run_id`/`offering_id` set by the pipeline; the usage
      recorder falls back to it.
- [ ] F21: `SCHEDULE_ENABLED` setting; document in
      [docs/configuration.md](../../docs/configuration.md).
- [ ] Update [docs/architecture.md](../../docs/architecture.md) (scheduler switch,
      acquisition retry, ledger attribution).
- [ ] Remove the `xfail` marks; run the suite.

### Phase 8: Live validation

- [ ] Rebuild and restart the stack (`docker compose up --build -d`), worker included.
- [ ] Reject or supersede the 22 old pending reviews from the 2026-09-27 run so they do
      not mix with the new run (human decision; `POST /api/v1/reviews/abort-pending`).
- [ ] **(paid, ≈ $2.5)** Run both families through `POST /api/v1/runs` (the prompt
      version bump invalidates the extraction cache).
- [ ] Record per offering: published / reviews (by reason) / failed; target is at most
      1 review per offering, and none from F7–F11 causes.
- [ ] A human decides the remaining reviews in `./tariff-chat` ("review them"),
      using "confirm not stated" where the source omits the field.
- [ ] Check ledger rows now carry `run_id` (F19) and read the cost per run.
- [ ] **(paid, ≈ $0.30)** Re-run the 15 seed-URL questions (scratchpad runner or
      `agents-cli eval generate --dataset tests/eval/datasets/seed-url-ground-truth.json`).
- [ ] Grade with the deterministic metric (`fact_coverage`, no model cost); optionally
      **(paid, ≈ $0.30)** the LLM judge with `tests/eval/seed_url_eval_config.yaml`.
- [ ] Compare with the 2026-09-27 baseline (`metadata.baseline_2026_09_27`): Q2, Q3,
      Q5, Q6, Q10, Q11, Q15 should move to correct; Q1 should mention 17% and 15%.
- [ ] Write `scenario-results.md` here and update this plan's Summary statuses.
- [ ] Stop the worker or set `SCHEDULE_ENABLED=false` if the stack stays up unattended.

## Deployment (not part of this plan: needs human approval)

`agents-cli deploy` only after the Phase 8 results are reviewed and approved.
