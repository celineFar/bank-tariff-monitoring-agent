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
collateral are structured conditional values, so a solar-only document or a
service-only no-collateral rule cannot silently become global.

## Deterministic/model split

Python builds an evidence catalog only from selected discovery assessments, restores
complete normalized blocks and table rows, and carries a table's surrounding tab and
product heading into every row. The planner gives every requested field a reserved
evidence quota before filling the remaining packet, ranks canonical/current-product
evidence above generic material, and excludes sibling-product and known variant
sections from the canonical product packet. Packet fingerprints include this scope
metadata. Gemini receives only unresolved bounded packets through a tool-free ADK
agent on the configured `MODEL_NAME`, with thinking set by
`SEMANTIC_EXTRACTION_THINKING_BUDGET` (default `0`, disabled) because the response
contract is schema-bound. Every packet carries the exact Pydantic-derived JSON Schema
for each requested field. Required documents have their own packet so all
current-product webpage and PDF document lists can be unioned without losing
evidence capacity to other fields.

After the model responds, Python validates fields independently. Missing, duplicate,
or extra fields; out-of-batch evidence IDs; non-verbatim quotes; malformed JSON; and
canonical Pydantic type failures become review items without discarding valid sibling
fields. A `found` value cannot exist without evidence; `not_stated` cannot contain a
value or evidence. Evidence-aware checks additionally reject `not_stated` when the
same packet contains a strong current-product field label, reject values supported
only by sibling/variant evidence, and detect condition-specific down-payment or LTV
alternatives flattened into unconditional values. The same checks cover conditional
documents, collateral, channels, ages, repayment methods, and term ranges. A term rule
that begins above a stated threshold must be split into a separate conditional range,
and a canonical product name must cite the canonical product page when that evidence
is available. A suspicious or malformed field
first passes through a deterministic shape adapter for known serialization variants.
The audit output preserves both the raw and adapted response. Anything still invalid
receives one bounded repair call containing the original result, exact field schema,
validation paths, and only the original packet evidence; only that field is replaced,
and a still-invalid repair enters the review queue. Repairs are additionally capped
per run by `SEMANTIC_EXTRACTION_MAX_REPAIRS_PER_RUN` (default `3`), so a batch that
keeps failing its own contract falls through to human review instead of issuing an
unbounded number of paid calls; fields left unrepaired because the budget was spent
are reviewed like any other invalid field. If review items
remain, the run is `completed_with_review` and no
full `LoanProduct` is claimed. Total termination is reserved for systemic failures,
including configuration/input failures and every model batch failing before a usable
response exists. This step does not yet decide whether a supported claim is ultimately
publishable—that belongs to verification and repair.

## Cache

`semantic_extraction_batches` stores only fully validated structured batch responses. Reuse requires an
exact match on product, schema version, prompt version, model name, and evidence
fingerprint. Invalid responses are never written, and invalid legacy entries are
ignored when read. Any selected evidence change or deliberate schema/prompt version
bump therefore causes only the affected field group to run again. Semantic extraction
schema and prompt version 5 intentionally invalidate the earlier flat-string
contracts.

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
