# Source discovery

Source discovery is the hybrid boundary between structural normalization and tariff
extraction. It classifies which normalized material belongs to the requested product,
what information role it plays, its relevance and authority, and whether it appears
current or time-bounded. It does not extract tariff values.

## Cost-aware execution

`SourceDiscoveryService.plan()` performs all work that can happen before a model call:

1. Build document, page-section, table, and API-payload classification units.
2. Group children so one decision can be inherited by many blocks or JSON leaves.
3. Apply deterministic rules for the canonical product document, hidden content,
   repeated global navigation, and reusable HTML template payloads.
4. Reuse exact assessments whose content fingerprints and discovery versions match.
5. Attach a prior assessment as a non-authoritative hint when the structure is stable
   but content changed.
6. Pack only unresolved units into bounded model batches.

An unchanged source therefore needs no repeated semantic assessment. A changed item
is reassessed without discarding useful information about its stable page position.
Cache identity includes product, content fingerprint, policy version, prompt version,
and configured model name.

The PostgreSQL cache is owned by migration `003_source_discovery.sql`. It stores only
validated structured assessments. The model cannot access the repository or SQL.

## ADK classifier

`AdkSourceDiscoveryClassifier` is a narrow tool-free ADK agent with a Pydantic output
schema. It receives only the bounded batches produced by the plan. Source text is
explicitly treated as untrusted evidence. The classifier must return exactly one
known source ID per requested item; the application service rejects missing,
duplicate, or invented IDs.

Children inherit the validated container assessment. The final result still contains
an assessment for every block, while the model operates on a much smaller set of
classification units.

## API and network payloads

Captured API payloads are part of discovery because they may contain terms absent
from static HTML. They are assessed at payload scope, not one call per JSON leaf.
Known presentation-template payloads are rejected deterministically. Relevant or
ambiguous payloads receive compact representative content, with individual JSON-path
blocks inheriting the result.

## Extraction context

Python converts assessments into a bounded `ExtractionContext`. Irrelevant material
is excluded, while relevant and possibly relevant material is ordered using this
precedence:

1. product-specific official terms;
2. product terms/pricing/fees tables;
3. official product content;
4. official FAQ;
5. official campaign content;
6. other or marketing material.

Lower-ranked evidence is retained so later extraction and verification can surface
conflicts rather than silently selecting one value.

## Preflight inspection

The demonstration command deliberately stops before the classifier:

```bash
uv run python scripts/demonstrate_source_discovery.py \
  .temp/acuisition_test/case_008 --product mortgage
```

It writes `source_discovery/preflight/` inside the case:

- `summary.txt`: rule/cache/model-selection counts and prompt character budget;
- `discovery_plan.json`: complete canonical plan;
- `deterministic_assessments.json`: decisions made without Gemini;
- `cache_hits.json`: exact reusable decisions;
- `llm_candidates.json`: unresolved normalized components;
- `llm_batches.json`: exact structured batches that would be sent;
- `cost_estimate.json`: stored price, token assumptions, and estimated input/output
  cost; this is not an invoice or an actual usage record;
- `selected_for_llm.md`: readable rendering of the selected model context.

Without an execution flag, the script uses no classifier and cannot make a Gemini
call. Model-specific prices are stored in `app/services/model_pricing.py` and should
be updated when the provider changes rates.

To execute the classifier explicitly, set `GEMINI_API_KEY` and add
`--execute-llm`. Live outputs go to a new `llm_run_NNN/` directory and never
overwrite `preflight/` or a previous live run. The live directory adds
`source_discovery_result.json`, `assessments.json`, `extraction_context.json`, and
`actual_usage_and_cost.json`.


---
# Source Discovery Content Explanation

The preflight directory contains the complete source-discovery plan created before any Gemini request:

```text
preflight/
├── summary.txt
├── discovery_plan.json
├── deterministic_assessments.json
├── cache_hits.json
├── llm_candidates.json
├── llm_batches.json
└── selected_for_llm.md
```

This particular directory is a preview. It shows what source discovery decided deterministically, what still requires semantic classification, and exactly what would be sent to the LLM.

No Gemini request was made.

### `summary.txt`

A quick overview of the source-discovery plan.

This is the best file to open first.

For case_008, it reports:

- Product being investigated: `mortgage`
- Canonical product URL
- Acquisition content hash
- Discovery policy and prompt versions
- Configured model
- Number of deterministic decisions
- Number of cache hits
- Number of candidates requiring the LLM
- Number and total size of prospective LLM batches
- Number of previous structural assessments available as hints
- Number of normalized child items covered through grouping

The individual fields mean:

- `MODE: PREFLIGHT ONLY`: the script stopped before model invocation.
- `Product`: the product family against which relevance is assessed.
- `Canonical URL`: the primary product page.
- `Input acquisition hash`: identifies the acquisition result from which normalization and discovery were derived.
- `Policy version`: version of the deterministic discovery rules.
- `Prompt version`: version of the semantic-classification instructions.
- `Configured model`: model that would classify unresolved candidates.
- `Deterministic assessments`: components classified using Python rules.
- `Exact cache hits`: previously classified, byte-for-byte equivalent components.
- `Candidates selected for LLM`: unresolved semantic classification units.
- `LLM batches that would be sent`: candidates packed into bounded requests.
- `Characters selected for LLM`: total characters across all prospective requests, not token count.
- `Changed-layout prior hints`: previous assessments available for structurally equivalent but content-changed components. Despite the label, these are normally stable-layout/content-changed hints.
- `Child items covered by inheritance`: individual blocks or JSON leaves that do not need separate LLM calls because they inherit a grouped assessment.

For this run, 30,941 normalized child items were condensed into only 40 semantic candidates.

---

### `deterministic_assessments.json`

Source components classified without using an LLM.

In case_008, it contains nine assessments.

Examples of material that can be classified deterministically include:

- the canonical product-page document;
- repeated global navigation;
- content known to be hidden;
- reusable HTML presentation templates;
- obvious non-product payloads.

A typical assessment contains:

```json
{
  "source_id": "document::page:a522...",
  "document_id": "page:a522...",
  "scope": "document",
  "product_association": "current_product",
  "role": "product_description",
  "relevance": "relevant",
  "authority": "official_product_content",
  "temporal_status": "current",
  "effective_periods": [],
  "conditions": [],
  "reason": "Canonical product page identity is known...",
  "decision_source": "rule",
  "inherited_from": null,
  "input_fingerprint": "...",
  "structural_fingerprint": "...",
  "source_refs": [...]
}
```

Important fields:

- `source_id`: unique discovery identifier for the assessed unit.
- `document_id`: normalized document containing the unit.
- `scope`: level assessed, such as `document`, `section`, `table`, or `api_payload`.
- `product_association`: whether it concerns the current product, another product, navigation, or generic bank information.
- `role`: its information function, such as pricing, fees, eligibility, FAQ, or navigation.
- `relevance`: `relevant`, `possibly_relevant`, or `irrelevant`.
- `authority`: how authoritative the material is.
- `temporal_status`: whether it appears current, time-bounded, possibly stale, or unknown.
- `effective_periods`: explicit validity or campaign dates, when detected.
- `conditions`: qualifiers such as “for salary customers” or “when applying online.”
- `reason`: explanation of the classification.
- `decision_source`: why this decision exists. Here it will normally be `rule`.
- `inherited_from`: parent source when an assessment was inherited.
- `input_fingerprint`: hash of the component’s content and relevant structure.
- `structural_fingerprint`: hash of its structural position independently of changing content.
- `source_refs`: references back to normalization and ultimately acquisition evidence.

These decisions will be combined with cached and LLM-produced assessments later.

---

### `cache_hits.json`

Previously stored semantic assessments that can be reused exactly.

A cache hit requires all relevant identity dimensions to match:

- Product
- Content fingerprint
- Policy version
- Prompt version
- Configured model

If the content and configuration are unchanged, the system does not need to ask the LLM to classify that candidate again.

In this preflight, the file contains:

```json
[]
```

That is expected because the demonstration script deliberately uses an empty in-memory repository. It simulates a cold first run and does not connect to the production PostgreSQL cache.

In a real persisted rerun, this file could contain the previously accepted assessments, and those sources would not appear in the LLM batches.

---

### `llm_candidates.json`

The complete internal representations of components that could not be classified confidently using deterministic rules or an exact cache hit.

For case_008, it contains 40 candidates.

Candidates may represent:

- a page section;
- a table;
- an entire linked document;
- a network/API payload;
- another grouped structural unit.

A typical candidate contains:

```json
{
  "source_id": "page:a522...::section::60c4...",
  "document_id": "page:a522...",
  "scope": "section",
  "source_type": "page",
  "title": "Real estate loan for primary market",
  "heading_path": [
    "Real estate loan for primary market"
  ],
  "context_text": "...",
  "mime_type": "text/html",
  "extraction_method": "browser",
  "quality_score": null,
  "member_source_ids": ["..."],
  "all_members_hidden": false,
  "has_scalar_candidates": true,
  "source_refs": [...],
  "content_fingerprint": "...",
  "structural_fingerprint": "...",
  "selection_reason": "..."
}
```

Important fields:

- `source_id`: ID used when requesting and receiving a classification.
- `document_id`: parent normalized document.
- `scope`: classification-unit level.
- `source_type`: page, PDF document, or API payload.
- `title`: best available title for the unit.
- `heading_path`: structural headings surrounding the content.
- `context_text`: representative content from the complete unit.
- `mime_type`: source media type.
- `extraction_method`: browser, HTML parser, JSON parser, PDF text extraction, OCR, etc.
- `quality_score`: extraction-quality measurement when available.
- `member_source_ids`: child blocks that will inherit the resulting classification.
- `all_members_hidden`: whether all underlying blocks were marked hidden.
- `has_scalar_candidates`: whether normalization detected values such as rates, amounts, dates, terms, or percentages.
- `source_refs`: evidence references back to the original source.
- `content_fingerprint`: identity used for exact cache reuse.
- `structural_fingerprint`: identity used to find assessments from the same stable page position.
- `selection_reason`: explanation of why and how the candidate was created.

This file is intentionally large because it retains internal metadata, references, fingerprints, and member relationships.

It is not the exact payload sent to Gemini.

---

### `llm_batches.json`

The exact structured batches that would be sent to the ADK classifier.

This is the most important machine-readable file when inspecting LLM cost and input boundaries.

For case_008:

- 40 candidates were selected;
- they were divided into six batches;
- each batch respects the configured character and item limits.

A batch looks approximately like:

```json
{
  "id": "batch_000",
  "product": "mortgage",
  "items": [
    {
      "source_id": "...",
      "scope": "section",
      "source_type": "page",
      "title": "Real estate loan for primary market",
      "heading_path": ["Real estate loan for primary market"],
      "content": "...",
      "mime_type": "text/html",
      "extraction_method": "browser",
      "quality_score": null,
      "prior_assessment": null
    }
  ]
}
```

Important batch fields:

- `id`: stable identifier for the model request.
- `product`: product against which every item must be assessed.
- `items`: classification units included in that request.

Important item fields:

- `source_id`: ID the model must return unchanged.
- `scope`: whether this is a section, table, document, or payload.
- `source_type`: page, document, or API origin.
- `title`: contextual label.
- `heading_path`: structural location on the page.
- `content`: bounded representative text supplied to the model.
- `mime_type`: source content type.
- `extraction_method`: how the material was obtained.
- `quality_score`: confidence or quality signal, when available.
- `prior_assessment`: previous classification for the same structural location after its content changed.

The following internal data is deliberately not sent to the model:

- filesystem paths;
- database access;
- raw SQL;
- full acquisition artifacts;
- source-reference locator objects;
- cache fingerprints;
- child inheritance lists;
- network or browser tools.

The classifier receives only the bounded semantic evidence needed to make the classification.

---

### `selected_for_llm.md`

A human-readable rendering of `llm_batches.json`.

It presents each prospective batch and item as Markdown:

```markdown
## batch_000

### `page:...::section::...`

- Scope: `section`
- Source type: `page`
- Title: Real estate loan for primary market
- Heading path: Real estate loan for primary market
- MIME: `text/html`
- Extraction method: `browser`
- Prior structural assessment: no

```text
60-360 months
AMD 3-150 million
12.9%
...
```
```

Use this file to manually answer:

- Why was this component selected?
- Is the candidate clearly related to the current product?
- Is enough heading context preserved?
- Did grouping combine the correct blocks?
- Is irrelevant navigation still reaching the LLM?
- Is the text sufficient to identify pricing, eligibility, fees, FAQ, or campaign material?
- Is sensitive or unnecessary internal metadata being sent?
- Are batches too large or candidates too fragmented?

This is generally the best file for manually reviewing what Gemini would see.

The content corresponds to `llm_batches.json`; it does not include the larger internal metadata contained in `llm_candidates.json`.

---

### `discovery_plan.json`

The complete source-discovery preflight result in one file.

It combines:

- run identity;
- product and canonical URL;
- acquisition hash;
- policy, prompt, and model versions;
- deterministic assessments;
- exact cache hits;
- unresolved LLM candidates;
- bounded LLM batches;
- inheritance statistics.

Its structure is approximately:

```json
{
  "product": "mortgage",
  "canonical_url": "https://ameriabank.am/...",
  "input_content_hash": "a522...",
  "policy_version": "1",
  "prompt_version": "1",
  "model_name": "gemini-3.7-flash",
  "deterministic_assessments": [...],
  "cache_hits": [],
  "llm_candidates": [...],
  "batches": [...],
  "inherited_item_count": 30941
}
```

This is the machine-readable primary output of preflight planning. The other files are convenient focused views of portions of this object.

Because it embeds both the complete candidates and their batches, it is much larger than the other files.

---

### How the files relate

```text
normalized_bundle.json
        │
        ▼
Deterministic grouping and rules
        │
        ├── deterministic_assessments.json
        │
        ├── cache_hits.json
        │
        └── unresolved candidates
                 │
                 ├── llm_candidates.json
                 │
                 ▼
           bounded batching
                 │
                 ├── llm_batches.json
                 └── selected_for_llm.md

Everything above is also collected in discovery_plan.json.
summary.txt provides the counts.
```

Most importantly:

- `deterministic_assessments.json` contains decisions requiring no LLM.
- `cache_hits.json` contains reusable previous decisions.
- `llm_candidates.json` contains full internal candidate metadata.
- `llm_batches.json` contains the exact prospective structured model inputs.
- `selected_for_llm.md` is the readable version of those inputs.
- `discovery_plan.json` is the complete combined preflight object.
- `summary.txt` is the quick overview.

There are no final LLM classifications or final extraction context in this directory because this demonstration intentionally stops immediately before Gemini invocation.
