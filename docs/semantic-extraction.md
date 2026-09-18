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

- one rich `LoanProduct` with shared and product-specific fields;
- an explicit state for every field: `found`, `not_stated`, `ambiguous`, or
  `conflicting`;
- hydrated evidence citations containing immutable evidence ID, quote, source URL,
  source type, section, authority, and original locator;
- the evidence catalog and raw per-batch structured responses for auditability.

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

After the model responds, Python rejects missing or extra fields, unknown evidence
IDs, and citation quotes absent from their cited evidence. Pydantic then parses each
value into the canonical domain type. A `found` value cannot exist without evidence;
`not_stated` cannot contain a value or evidence. This step does not yet decide whether
a supported claim is ultimately publishable—that belongs to verification and repair.

## Cache

`semantic_extraction_batches` stores structured batch responses. Reuse requires an
exact match on product, schema version, prompt version, model name, and evidence
fingerprint. Any selected evidence change or deliberate schema/prompt version bump
therefore causes only the affected field group to run again.

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
overwrites preflight or an earlier model run. Successful runs add
`semantic_extraction_result.json`, `loan_product.json`, `batch_results.json`,
`extraction_results.md`, and `model_attempts.json`. Exhausted retryable requests move
through the configured fallback sequence; handled failures produce `failure.json`
without an application traceback.
