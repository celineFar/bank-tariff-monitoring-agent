# Semantic extraction

Semantic extraction turns the evidence selected by source discovery into the typed
loan-product facts used by later claim generation and verification. It does not fetch
sources or decide which documents are relevant.

## Inputs and outputs

The service consumes the same `NormalizedSourceBundle` used by source discovery plus
a completed `SourceDiscoveryResult`. The discovery result supplies relevance,
authority, temporal status, role, conditions, and precedence. The normalized bundle
supplies the full content and original `SourceLocator`; the shorter discovery prompt
excerpt is deliberately not treated as extraction evidence.

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

Python builds an evidence catalog only from non-irrelevant discovery assessments,
restores complete normalized blocks and table rows, ranks evidence by role and
authority, groups related fields, enforces packet limits, fingerprints packets, and
checks the exact cache. Gemini receives only unresolved bounded packets through a
tool-free ADK agent.

After the model responds, Python validates fields independently. Missing, duplicate,
or extra fields; out-of-batch evidence IDs; non-verbatim quotes; malformed JSON; and
canonical Pydantic type failures become review items without discarding valid sibling
fields. A `found` value cannot exist without evidence; `not_stated` cannot contain a
value or evidence. If review items remain, the run is `completed_with_review` and no
full `LoanProduct` is claimed. Total termination is reserved for systemic failures,
including configuration/input failures and every model batch failing before a usable
response exists. This step does not yet decide whether a supported claim is ultimately
publishable—that belongs to verification and repair.

## Cache

`semantic_extraction_batches` stores only fully validated structured batch responses. Reuse requires an
exact match on product, schema version, prompt version, model name, and evidence
fingerprint. Invalid responses are never written, and invalid legacy entries are
ignored when read. Any selected evidence change or deliberate schema/prompt version
bump therefore causes only the affected field group to run again.

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
