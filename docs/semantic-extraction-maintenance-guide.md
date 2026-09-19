# Semantic extraction: architecture, behavior, and improvement guide

This document explains the semantic-extraction subsystem as it exists today, the
guarantees it provides, what it deliberately does not yet do, and how to extend it
safely. It is intended as a maintenance and implementation guide. For commands and
artifact names, see [semantic-extraction.md](semantic-extraction.md).

## 1. Purpose and pipeline boundary

Semantic extraction converts the evidence accepted by source discovery into typed
loan-product data. Its responsibility is semantic mapping:

```text
selected normalized evidence
        |
        v
bounded field packets
        |
        v
Gemini extraction into exact field contracts
        |
        v
deterministic adaptation and validation
        |
        +--> valid LoanProduct or PartialLoanProduct
        |
        +--> invalid fields in the extraction review queue
```

It does not acquire pages, download PDFs, parse PDF bytes, decide whether a source is
relevant, persist a publishable tariff snapshot, compare snapshots, or make a final
business decision about contradictory sources.

The layer consumes two inputs:

1. `NormalizedSourceBundle`, containing normalized webpage, PDF, table, note, and
   source-location data.
2. `SourceDiscoveryResult`, containing relevance, product association, authority,
   temporal status, effective periods, information role, and precedence decisions.

The source-discovery selection is reapplied defensively before evidence is built. A
caller cannot simply pass rejected blocks alongside an accepted discovery result and
have them silently reintroduced.

## 2. Why this is not ordinary text-to-JSON prompting

A single prompt containing an entire product page would be simpler, but it would make
the following failures difficult to detect:

- evidence from a related product could redefine the current product;
- a long rate table could crowd required documents or eligibility out of the context;
- one invalid field could invalidate an otherwise useful product;
- citations could refer to text the model did not receive;
- a cached response could be reused after the schema or evidence changed;
- conditional values could be flattened into misleading global values.

The implementation therefore divides responsibility between deterministic Python and
a bounded, tool-free ADK agent. Gemini performs semantic interpretation only. Python
controls evidence selection, contracts, validation, caching, failure handling, and
audit output. The agent has no browser, filesystem, database, shell, or network tool.

## 3. Domain contract

The principal domain object is `LoanProduct`. Every extracted field is wrapped in an
`ExtractedValue` with:

- `value`: the typed value, when one is available;
- `status`: `found`, `not_stated`, `ambiguous`, or `conflicting`;
- `evidence`: hydrated citations back to original source locators;
- `explanation`: an optional bounded explanation.

The wrapper enforces these basic invariants:

- `found` requires both a value and evidence;
- `not_stated` permits neither a value nor evidence;
- `ambiguous` and `conflicting` require evidence.

Important financial fields use structured types rather than display strings:

- money can be an absolute currency range, salary multiple, property-value
  percentage, or other documented formula;
- nominal and effective/APR rates preserve bounds, basis, rate type, formulas, and
  conditions;
- terms use minimum and maximum months;
- fees retain amount/rate, currency, conditions, and product-versus-general-service
  scope;
- income verification and creditworthiness assessment are separate requirement
  policies;
- mortgage-specific down-payment and LTV values retain their conditions.

Umbrella products have a typed variant catalog. A variant has a stable snake-case
`variant_id`, name, and optional purpose. Variant-specific facts refer to that ID in a
`Condition`. This allows one `Consumer Finance` product to retain distinct goods,
services, and solar branches without pretending they are unrelated products.

The following formerly flat fields are now structured conditional values:

- repayment methods;
- age ranges;
- application channels;
- required documents;
- collateral and explicit non-applicability.

The customer-facing canonical product name is separate from
`formal_terms_names`. Consequently, a linked document titled “Information summary of
the terms and conditions ...” does not rename the webpage product.

## 4. Evidence catalog and provenance

The evidence catalog is built deterministically from source-discovery-approved
normalized content. Each evidence item retains:

- an immutable evidence ID;
- document and normalized source-item IDs;
- complete content used for extraction;
- source URL and source type;
- original page, table, JSON-path, or PDF-page locator;
- section context;
- authority and precedence;
- current/unknown/historical/future temporal classification;
- current/related/generic product association;
- detected effective periods and conditions.

The evidence ID is the model-visible citation key. The model returns that ID plus a
short quote. Python later replaces it with a complete `EvidenceCitation`. Citations
are therefore not free-form URLs supplied by the model.

## 5. Planning and evidence packets

The planner groups fields into bounded packets:

1. identity, including canonical name, formal terms names, variants, category, and
   purpose;
2. core financial terms;
3. fees and repayment;
4. eligibility and related conditions;
5. required documents;
6. product-type-specific details.

Required documents deliberately have their own packet. Document lists often appear in
both the webpage and one or more PDFs and are easily under-extracted when sharing a
small packet with unrelated eligibility fields.

For every field, deterministic keyword and role matching reserves space for its best
evidence before contextual evidence fills the remaining capacity. Ranking favors:

- the current product over related or generic products;
- the canonical page for customer-facing product identity;
- appropriate information roles;
- higher-precedence current evidence.

Known sibling mortgage variants and historical/future material are excluded from a
canonical current-product packet. Lower-ranked accepted evidence is not deleted from
the overall evidence catalog; it remains available for later verification and conflict
analysis.

Every packet has a fingerprint derived from its fields, scope, evidence content, and
source metadata. This is a core cache boundary.

## 6. ADK extraction call

The ADK agent receives:

- the canonical URL and target scope;
- the requested fields;
- the bounded evidence packet;
- an exact Pydantic-generated JSON Schema for each requested field;
- instructions to treat source text as untrusted data;
- rules for conditions, variants, citations, missing values, ambiguity, and conflict.

The agent returns one `ModelFieldResult` per requested field. `value_json` is a JSON
string so the outer ADK response schema stays portable while each inner field can have
a different precise domain schema.

The prompt requires conditional subranges to remain explicit. For example, if a loan
term is 6–60 months but terms above 48 months are limited to certain purchases, the
expected representation is conceptually:

```json
[
  {
    "value": {"min_months": 6, "max_months": 48},
    "conditions": []
  },
  {
    "value": {"min_months": 49, "max_months": 60},
    "conditions": [
      {"dimension": "purpose", "value": "documented eligible purposes"}
    ]
  }
]
```

The field-level condition is part of the fact. It is not merely an explanatory note.

## 7. Deterministic contract adaptation

Models sometimes find the correct fact but serialize it in a nearby shape. Before
canonical validation, a deterministic adapter handles a limited set of known
representational differences, including:

- moving absolute amount bounds into `absolute.range`;
- converting term units to months;
- converting fractional percentage notation to percentage points;
- converting condition strings to typed `Condition` objects;
- structuring repayment, age, channel, document, and collateral values;
- normalizing common rate and fee aliases;
- deduplicating identical required documents without changing their order.

This adapter must not invent a missing fact, choose between contradictory facts, or
change a supported value merely to make it look plausible. Both the raw model response
and adapted response are retained in audit output.

## 8. Validation stages

Validation is field-local wherever possible. The principal checks are:

### 8.1 Response completeness

The response must contain exactly one result for every requested field and no extra
fields.

### 8.2 Batch-local citation integrity

Every evidence ID must have been present in that exact packet. The quoted text must be
a normalized verbatim substring of that evidence. A correct-looking answer with an
out-of-packet citation is rejected.

### 8.3 Pydantic domain validation

The field value must satisfy the exact type, enum, range, union discriminator, and
model invariants. Fields are validated independently, so one malformed rate does not
discard a valid amount or term.

### 8.4 Product-scope validation

A found value cannot be supported only by related-product or out-of-scope evidence.
When canonical product-name evidence is available, the product name must cite the
canonical product page rather than only a linked document.

### 8.5 Suspicious-omission checks

For important fields, `not_stated` is rejected when the same current-product packet
contains a strong field-specific marker. This does not fabricate a value; it triggers
a bounded second attempt.

### 8.6 Condition-preservation checks

Conditional alternatives cannot all be returned without conditions when their cited
evidence contains conditional cues. A documented term restriction above a numeric
threshold must appear as a separate conditional upper subrange. Similar checks apply
to conditional documents, collateral, application channels, ages, repayment, down
payment, and LTV.

### 8.7 Domain distinctions

Income verification cannot be inferred solely from a statement about creditworthiness
assessment. This avoids turning related but different concepts into the same Boolean.

## 9. Bounded repair

If a field fails schema, citation, or semantic-completeness validation, the service can
make one bounded repair call. The repair receives only:

- the original field result;
- exact validation paths and messages;
- the exact required JSON Schema;
- the original packet evidence.

It is instructed to preserve supported facts and repair only structure or citation.
It cannot expand retrieval, cite a new evidence ID, or re-extract the whole product.
The repaired field is validated through the same path as the original.

This repair is not the future verification repair described in the project design. It
does not determine whether a well-formed claim is true. It only repairs an extraction
contract or grounding failure.

## 10. Partial success, review, and systemic failure

Successfully validated fields are retained even when sibling fields fail.

If every field needed for assembly validates, the result contains a complete
`LoanProduct`. If one or more fields remain invalid, the result contains:

- `status = completed_with_review`;
- a `PartialLoanProduct` containing valid fields;
- invalid raw field output;
- validation paths and messages;
- model and batch identifiers;
- associated evidence IDs;
- machine-readable and Markdown review queues.

Invalid responses are not cached.

Total termination is reserved for systemic failures, such as invalid inputs or
configuration, unavailable source evidence, authentication failure, or every model
batch failing before any usable response exists. A single malformed field is not a
systemic failure.

## 11. Cache behavior

A batch is reusable only when all of the following match:

- product;
- semantic schema version;
- prompt version;
- model name;
- selected-evidence fingerprint.

Only wholly validated batch responses are stored. Cached responses are validated again
when read, so incompatible legacy records are ignored. Schema and prompt version 5
invalidate earlier flat-string semantic contracts. PDF parsing, normalization, and
source-discovery caches are independent and do not need to be invalidated by a purely
semantic contract change.

## 12. Current conflict behavior

The extractor is instructed to distinguish conditions from conflicts:

- different values for different currencies, variants, borrower types, channels,
  programs, or effective periods are conditional values;
- multiple plausible readings of the same evidence are `ambiguous`;
- incompatible values from authoritative sources for the same product, scope, and
  time are `conflicting`.

A `conflicting` result must cite evidence. The conflicting sources remain independent;
their PDFs and webpage blocks are not merged into a synthetic source.

The important limitation is that `conflicting` is currently a valid semantic status.
It does not automatically become an `ExtractionReviewItem`, and by itself it does not
necessarily change the run to `completed_with_review`. The extraction review queue is
currently for malformed, ungrounded, incomplete, or failed model output—not for an
otherwise well-formed business conflict.

The current layer also does not deterministically decide that a product PDF wins over
a webpage, that the newest date always wins, or that one source is stale. It preserves
authority, temporal, effective-period, association, and precedence metadata so a later
verification/conflict-resolution component can make that decision transparently.

This behavior is intentional for safety: silently resolving a disagreement during
extraction would hide the disagreement from audit and could publish the wrong tariff.

## 13. What is not yet implemented

Semantic extraction is useful but is not the complete tariff-decision system. The
following capabilities remain downstream or incomplete:

### 13.1 Atomic claim generation

`LoanProduct` fields have not yet been deterministically expanded into atomic claims
such as “AMD maximum amount is 10,000,000” or “the 49–60 month branch applies only to
specific purposes.” Atomic claims are necessary for localized verification and repair.

### 13.2 Independent semantic verification

There is no independent verifier deciding whether each well-formed claim is supported,
contradicted, ambiguous, or insufficiently evidenced. Current quote checks establish
textual grounding, not full semantic entailment.

### 13.3 Deterministic numeric and unit grounding

Pydantic checks mathematical ranges, but a complete verifier should separately confirm
that claim numbers, currencies, units, inclusivity, and `from`/`up to` semantics occur
compatibly in the evidence.

### 13.4 Cross-source conflict resolution

The system preserves source authority and dates but does not yet implement a decision
table for overlapping effective periods, superseding documents, current webpage versus
current PDF disagreements, or equally authoritative conflicts.

### 13.5 Business-conflict HITL routing

There is no durable HITL workflow that turns `conflicting` or high-risk `ambiguous`
fields into assigned review tasks with approve/reject/override decisions and an audit
history.

### 13.6 Verification-level repair

The existing repair fixes extraction contracts. A later repair must receive one failed
atomic claim, the verifier's reason, and only the relevant evidence, then pass the
corrected claim through verification again.

### 13.7 Completeness policy by product subtype

Some suspicious-omission checks exist, but the system does not yet have a complete,
versioned policy describing required or expected concepts for every mortgage,
consumer-finance, overdraft, credit-line, and campaign subtype.

### 13.8 Cross-field consistency

More deterministic checks are needed for relationships such as:

- condition `variant_id` values must exist in the variant catalog;
- term, amount, rate, and fee branches should use compatible condition dimensions;
- LTV and down-payment combinations should be internally coherent where the product
  contract makes that relationship explicit;
- nominal-versus-APR relationships should produce warnings rather than universal hard
  failures;
- a document marked required for a variant should not silently become global.

### 13.9 Production persistence and observability

The final system still needs complete persistence of claims, verifier decisions,
repairs, human decisions, snapshots, and changes, plus metrics for extraction failure,
review rate, cache reuse, token cost, and field-level quality.

## 14. Recommended improvement sequence

The safest implementation order is:

1. **Atomic claim generator.** Deterministically walk the typed product and emit stable
   claim IDs, values, conditions, and evidence references.
2. **Deterministic verifier signals.** Add evidence existence, quote, number, currency,
   unit, bound, condition, product-association, and effective-period checks.
3. **Bounded semantic verifier.** Give Gemini one atomic claim and its evidence, without
   the extractor's reasoning, and require a small verdict enum.
4. **Conflict resolver.** Apply an explicit authority/effective-date decision table.
   Never treat precedence as permission to hide an unresolved conflict.
5. **Verification repair.** Repair one claim once, then re-run every verifier signal.
6. **HITL router.** Route unresolved current-authority conflicts, genuine ambiguity,
   unrepresentable conditions, critical low-authority fields, and repeated repair
   failures.
7. **Snapshot gate.** Permit only verified, non-blocked claims into publishable tariff
   snapshots and change detection.
8. **Evaluation suite.** Maintain multi-URL gold cases covering umbrellas, variants,
   historical documents, PDF/web overlap, conditional ranges, and deliberate source
   conflicts. Measure field correctness, condition preservation, citation validity,
   conflict recall, and false-review rate separately.

## 15. Relationship to RAG

RAG and semantic extraction solve different problems:

- normalization and chunking create stable searchable evidence units;
- the knowledge store versions and indexes those chunks;
- retrieval selects a small evidence-bearing set for a bank, product, and field scope;
- semantic extraction maps supplied evidence into typed product facts;
- verification decides whether those facts are safe to accept.

It is reasonable to implement or improve the RAG chunking, indexing, and retrieval
path now. The semantic domain contract and provenance model are sufficiently defined
to tell RAG what metadata it must preserve. In particular, every chunk should retain
document version, source URL, page/section locator, product association, temporal
status, and content checksum.

RAG must not become an authority resolver. Retrieval rank means “useful for this
query,” not “true,” “current,” or “preferred over a conflicting official source.” It
must also return `INSUFFICIENT_EVIDENCE` rather than asking extraction to infer from a
weak result.

Proceeding with RAG does not mean the complete subsystem is production-ready. Before
retrieved facts can become publishable tariffs, the atomic claim, verification,
conflict-resolution, repair, and HITL stages described above still need to be built.

## 16. Key implementation files

- `app/domain/semantic_extraction.py`: domain contracts and statuses.
- `app/services/extraction_evidence.py`: evidence catalog construction.
- `app/services/extraction_planner.py`: field grouping and bounded evidence selection.
- `app/services/semantic_extraction.py`: ADK invocation, adaptation, validation,
  bounded repair, caching, and product assembly.
- `scripts/demonstrate_semantic_extraction.py`: standalone audit demonstration.
- `scripts/demonstrate_end_to_end.py`: complete human-readable pipeline audit.
- `docs/semantic-extraction.md`: operational usage and artifact guide.
- `docs/rag-retrieval.md`: retrieval contract and ranking.
- `docs/knowledge-store.md`: document/chunk persistence and vector indexing.

