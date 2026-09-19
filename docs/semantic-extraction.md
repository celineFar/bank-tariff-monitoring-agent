# Semantic extraction

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
- the evidence catalog and raw per-batch structured responses for auditability;
- review items for invalid fields, including their raw model result, validation paths,
  evidence IDs, batch ID, and model name.

Amounts retain their real representation: absolute currency ranges, salary
multiples, property-value percentages, or other formulas. Rates retain range,
fixed/variable/mixed type, annual/monthly basis, and conditions. Mortgage,
overdraft, credit-line, and ordinary consumer-loan details are discriminated types.

## Deterministic/model split

Python builds an evidence catalog only from selected discovery assessments, restores
complete normalized blocks and table rows, and carries a table's surrounding tab and
product heading into every row. The planner gives every requested field a reserved
evidence quota before filling the remaining packet, ranks canonical/current-product
evidence above generic material, and excludes sibling-product and known variant
sections from the canonical product packet. Packet fingerprints include this scope
metadata. Gemini receives only unresolved bounded packets through a tool-free ADK
agent.

After the model responds, Python validates fields independently. Missing, duplicate,
or extra fields; out-of-batch evidence IDs; non-verbatim quotes; malformed JSON; and
canonical Pydantic type failures become review items without discarding valid sibling
fields. A `found` value cannot exist without evidence; `not_stated` cannot contain a
value or evidence. Evidence-aware checks additionally reject `not_stated` when the
same packet contains a strong current-product field label, reject values supported
only by sibling/variant evidence, and detect condition-specific down-payment or LTV
alternatives flattened into unconditional values. A suspicious or malformed field
receives one targeted repair call containing field-specific evidence; only that field
is replaced, and a still-invalid repair enters the review queue. If review items
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
schema and prompt version 3 intentionally invalidate the earlier scope-unaware cache.

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
