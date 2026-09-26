# Semantic extraction

For a detailed architecture explanation, current conflict behavior, known limitations,
and improvement roadmap, see
[semantic-extraction-maintenance-guide.md](semantic-extraction-maintenance-guide.md).

Semantic extraction turns the evidence selected by source discovery into the typed
loan-product facts used by later claim generation and verification. It does not fetch
sources or decide which documents are relevant.

## Inputs and outputs

The service consumes the source-discovery-selected `NormalizedSourceBundle` plus a
completed `SourceDiscoveryResult`. In the end-to-end audit this bundle is persisted as
`source-discovery/selected_sources.json` and rendered as `selected_webpage.md` and
per-document `selected_*.md` files. The service reapplies the deterministic selection
filter defensively, so callers cannot accidentally reintroduce rejected content. The
discovery result supplies relevance, product association, authority, temporal status,
effective periods, role, conditions, and precedence. These attributes remain attached
to every extraction evidence item. The selected normalized bundle supplies full content and original
`SourceLocator`; the shorter discovery prompt excerpt is not extraction evidence.

The output is a `SemanticExtractionResult` containing:

- a run status of `completed` or `completed_with_review`;
- one rich `LoanProduct` when all fields validate, otherwise a partial product made
  only from independently validated fields;
- an explicit state for every field: `found`, `not_stated`, `ambiguous`, or
  `conflicting`;
- hydrated evidence citations containing immutable evidence ID, quote, source URL,
  source type, section, authority, and original locator;
- the evidence catalog plus raw and contract-normalized per-batch responses for
  auditability;
- review items for invalid fields, including their raw model result, validation paths,
  evidence IDs, batch ID, and model name.

Amounts retain their real representation: absolute currency ranges, salary
multiples, property-value percentages, or other formulas. Rates retain range,
formula, fixed/variable/mixed type, annual/monthly basis, and conditions. Percentages
use percentage points (`10` means 10%). Fees retain product/general-service scope.
Income verification and creditworthiness assessment are separate conditional
requirement policies. Mortgage, overdraft, credit-line, and ordinary consumer-loan
details are discriminated types. Umbrella products also retain a typed variant catalog.
Formal PDF/terms titles are separate from the canonical customer-facing product name.
Repayment methods, age ranges, application channels, required documents, and
collateral are structured conditional values, so a variant-only document or a
variant-only no-collateral rule cannot silently become global.

## Deterministic/model split

Python builds an evidence catalog only from selected discovery assessments, in reading
order.

- **Table rows are records.** Each value names its column path (header levels and
  qualifier rows such as `Currency: AMD`); a continuation row carries the rate type
  above it; the notes the row cites come with it.
- **Headline cards** ("Loan amount: AMD 3-150 million") are key/value blocks.
- **Evidence IDs** hash the source, the structural path and the text, never the page
  hash or positions, so an unchanged table keeps its IDs.

`SEMANTIC_EXTRACTION_EVIDENCE_MODE` chooses what Gemini reads:
- `full` (default): the offering's whole selected evidence in three calls; related
  products' items go in a marked block.
- `budgeted`: items chosen by whole-word label matches (headings, row labels, column
  paths), within `SEMANTIC_EXTRACTION_BUDGET_CHARS` per call, with per-field shares.

Nothing is cut mid-item: full mode fails loudly above
`SEMANTIC_EXTRACTION_MAX_PACKET_CHARS`.

The field set follows the seed catalog's offering `category`. The target scope is the
offering's names and page, with no URL-specific rules. Gemini runs as a tool-free ADK
agent on `MODEL_NAME`:
- at temperature 0, with thinking set by `SEMANTIC_EXTRACTION_THINKING_BUDGET`
  (default `0`) and an output cap of `SEMANTIC_EXTRACTION_MAX_OUTPUT_TOKENS`;
- one SDK attempt; the application retries with backoff, and asks once more after an
  empty, cut or unparseable answer;
- calls run concurrently (`SEMANTIC_EXTRACTION_MAX_CONCURRENT_CALLS`);
- a call the primary model cannot answer goes to the next model of
  `SEMANTIC_EXTRACTION_FALLBACK_MODEL_NAMES`, for that call only.

Every call carries the exact JSON Schema of its fields. Condition dimensions come
from a closed set.

After the model responds, Python validates fields independently. Missing, duplicate
or extra fields become review items without discarding valid sibling fields, as do:
- out-of-batch evidence IDs and quotes absent from the cited evidence (compared
  whitespace-insensitively);
- numbers of a value absent from its quotes;
- alternatives that share their conditions;
- values supported only by related-product evidence;
- a category other than the catalog's;
- a term threshold rule not split into its own conditional range;
- a product name not anchored to the canonical page.

A `found` value cannot exist without evidence; `not_stated` cannot contain a value or
evidence.

A deterministic adapter first reshapes known serialization variants. It moves a
condition written as a key (a rate's `currency`) into `conditions`, and never infers
meaning. The audit output keeps both the raw and adapted response. Anything still
invalid gets one bounded repair call (the original result, the field schema, the
validation paths, only the original packet), capped per run by
`SEMANTIC_EXTRACTION_MAX_REPAIRS_PER_RUN` (default `3`) and spent on the required
tariff fields first. A field still invalid enters the review queue, unless a
remembered review decision for the same call or the same result answers it. If
review items remain, the run is `completed_with_review` and no full `LoanProduct` is
claimed. Total termination is reserved for systemic failures: configuration or input
failures, an evidence packet above the ceiling, or a call that failed on every model.

## Cache

`semantic_extraction_batches` is keyed by the fingerprint of exactly what a call
sends: model, generation settings, instruction and prompt. Every fresh answer is
stored with its validation outcome (`accepted` or `review`). A stored answer is
reused as it is and not repaired again, so an unchanged failing field costs no call.
The schema and prompt versions stay in the lookup as a manual invalidation switch.
Any change to what a call's model sees, and nothing else, makes that call run
again.

`review_decision_memory` keeps each committed field decision against the call and
the result it was about (see `docs/native-hitl-review.md`).

## Demonstration

First produce a successful source-discovery result. Then inspect what would be sent
without invoking Gemini:

```powershell
uv run python scripts/demonstrate_semantic_extraction.py `
  .temp/acuisition_test/case_008
```

The script automatically selects the latest successful numbered source-discovery
run. Use `--source-discovery-result PATH` to choose one explicitly. Preflight files
are written under `semantic_extraction/preflight` and include the complete plan,
evidence catalog, field batches, human-readable exact model input, cost estimate, and
summary.

To execute Gemini:

```powershell
uv run python scripts/demonstrate_semantic_extraction.py `
  .temp/acuisition_test/case_008 --execute-llm
```

Each live attempt gets a new `semantic_extraction/llm_run_NNN` directory, so it never
overwrites preflight or an earlier model run. Execution runs add
`semantic_extraction_result.json`, `partial_result.json`, `batch_results.json`,
`pre_validation.json`, the color-coded `pre_validation.md`, `review_queue.json`,
`review.md`, `extraction_results.md`, and `model_attempts.json`. `loan_product.json`
is added only for a fully validated result. Exhausted retryable requests move
through the configured fallback sequence; handled failures produce `failure.json`
without an application traceback.

The end-to-end demonstration writes corresponding audit files under
`semantic-extraction/`. Red field cards need human review, orange cards are valid
ambiguous/conflicting states, and green cards passed canonical validation.
