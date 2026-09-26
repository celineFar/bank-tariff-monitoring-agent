# Source discovery

Source discovery is the hybrid boundary between structural normalization and tariff
extraction. It classifies which normalized material belongs to the requested product,
what information role it plays, its relevance and authority, and whether it appears
current or time-bounded. It does not extract tariff values.

For the end-to-end audit, the canonical webpage is rendered in the root
`selection_decisions.md` and `selection_diff.md`. Linked normalized documents remain
independent under `source-discovery/documents/`: `index.md` records their selection
state and each PDF receives its own `*.selection_decisions.md` and
`*.selection_diff.md`. The retained content is also written as
`selected_webpage.md` and per-document `selected_*.md` files. These are
human-readable renderings of `selected_sources.json`, the filtered structured bundle
passed to semantic extraction.

## PDF link selection (before transcription)

Source discovery starts before normalization. `PdfLinkSelectionService` takes every
linked PDF that deterministic admission lets through (off-topic metadata and, by
default, superseded editions are skipped without any model) and asks a tool-free
Gemini classifier, in one call per offering, to label each from its link metadata
alone (file name, document name, link text and title, heading path, nearby text,
effective periods):

- `current_product`: the offering's own terms, information leaflet, or tariff;
- `shared_terms`: terms that apply to it among other loans (the loan fee schedule,
  the floating-rate procedure, a lending campaign that covers it);
- `related_product`: another product's or an uncovered variant's document;
- `generic_bank_information`: bank-wide material that is not lending terms;
- `unclear`: the link does not say.

Only `current_product`, `shared_terms` and `unclear` PDFs are read and transcribed.
The pipeline records the stage as `pdf_selection`, the audit as
`2_pdf_link_selection.md`, and caches decisions in `pdf_link_selections` by offering,
policy and prompt version, model, and a fingerprint of the link metadata, so an
unchanged link is never asked about again. It uses the discovery models and fallback
chain. In discovery, every transcribed PDF is then checked once on its content,
whatever its link label: the website's profile terms are linked as "Terms and
Conditions" under a loan's own terms, and an undated "special offer" link led to a
campaign that ended on 31.12.2025. Its blocks and tables inherit that document
decision. A PDF the link step dropped has no content and keeps the link decision
(`link_selection`). Historical or future status from explicit dates still excludes a
PDF from current terms.

## Cross-sell cards

A small content section (at most 600 characters) that links to another catalog
offering's seed page, and not to this offering's own, is that offering's cross-sell
card and is decided `related_product` by rule, with no model call. The pipeline gives
the `OfferingContext` the catalog's other offerings for this (they are not sent in the
prompt). On the 13 seed pages the rule finds exactly the 16 cross-sell cards.

## Cost-aware execution

`SourceDiscoveryService.plan()` performs all work that can happen before a model call:

1. Build document, page-section, and table classification units.
2. Group children so one decision can be inherited by many blocks.
3. Apply deterministic rules for the canonical product document, hidden content,
   the site's navigation, header and footer (blocks the HTML parser marks
   `site_chrome`, kept in their own group so a footer never joins a content
   section), the unheaded page header above the first heading, and linked
   documents with no content (skipped before transcription, or failed).
4. Reuse exact assessments whose content fingerprints and discovery versions match.
   Fingerprints are built from content, never from positional block or table ids,
   so a block inserted near the top of a page does not invalidate every section.
5. Attach a prior assessment as a non-authoritative hint when the structure is stable
   but content changed. The structural fingerprint includes the parent's text (the
   accordion or card title); a fingerprint that occurs twice on one page gets no
   prior, because the stored one may belong to the other section.
6. Pack only unresolved units into bounded model batches.

An unchanged source therefore needs no repeated semantic assessment. A changed item
is reassessed without discarding useful information about its stable page position.
Cache identity includes product, offering, content fingerprint, policy version,
prompt version, and configured model name. The offering is part of it because
"current product" and "related product" are relative: the Express mortgage table
is the current product on the Express page and a sibling on the primary-market
page.

The PostgreSQL cache is owned by migrations `003_source_discovery.sql` and
`019_source_discovery_offering_scope.sql`. It stores only
validated structured assessments. The model cannot access the repository or SQL.

## ADK classifier

`AdkSourceDiscoveryClassifier` is a narrow tool-free ADK agent with a Pydantic output
schema. It receives only the bounded batches produced by the plan. Every batch
carries the `OfferingContext` (offering id, display name, catalog names, seed URL,
page title, and the page's main heading with the text under it) that the product
association is judged against. The offering covers every variant its page heading
and text name (primary and secondary market; purchase, construction and renovation;
residential and commercial property); `related_product` is for products the page
presents as separate offers. The PDF link selection receives the same context.
Every batch also carries `as_of`, the page's retrieval date: without it the model
called "effective from 14.07.2026" future on 26.09.2026. Every model runs at
temperature 0 with thinking off; how thinking is switched off depends on the model
(`thinking_budget=0`, or `thinking_level=MINIMAL` for `gemini-3.5-flash-lite`, which
rejects a zero budget), recorded in `app/services/model_pricing.py`.
Each call is capped at `SOURCE_DISCOVERY_CLASSIFIER_MAX_OUTPUT_TOKENS` (default
8192): a runaway answer is cut, fails validation, and is retried or split. The
nested member-exception model deliberately carries no pattern or length limits:
Gemini rejects the whole request (400) when it does, so `_check_response` enforces
them. Source text is
explicitly treated as untrusted evidence. The classifier must return exactly one
known source ID per requested item; the application service rejects missing,
duplicate, or invented IDs.

Retries have one owner: the Google SDK makes a single attempt, and the classifier's
application-level loop retries status codes 429, 500, 502, 503, and 504 with
exponential backoff and jitter (at most `SOURCE_DISCOVERY_CLASSIFIER_MAX_ATTEMPTS`
calls per batch per model). Authentication and permission failures are not
retried. An answer that breaks the contract (invalid JSON, a missing, repeated or
invented id, an exception naming a member the item did not show) is asked once
more; if it is still invalid, the batch is split in halves, down to single items.
Batches run concurrently (`SOURCE_DISCOVERY_MAX_CONCURRENT_BATCHES`), every valid
batch is saved as soon as it is checked, and results keep batch order. A model that
cannot answer one item validly even alone and asked twice raises
`DiscoveryResponseError`.

After a model exhausts retryable failures, or raises `DiscoveryResponseError`, the
run restarts complete discovery with the next `SOURCE_DISCOVERY_FALLBACK_MODEL_NAMES`
entry. This applies to the worker's pipeline and to the demonstration alike: a
provider error on any configured model — including the permanent 404 a retired
model id answers — moves the run to the next model rather than failing the offering
with `source.model_failed`. A failure in the application's own code is not handed
over. Each model keeps its own assessment cache namespace and is the `model_name`
stored with the rows it produced, so whole-run fallback avoids mixing model
decisions within one accepted result. The worker logs every model transition; the
demonstration also announces them on the console and records failures, retries,
usage, and cost per model in `model_attempts.json`.

Because the classifier's output is schema-bound rather than free prose, this
stage runs on its own cheap model instead of the global `MODEL_NAME`:
`SOURCE_DISCOVERY_MODEL_NAME` defaults to `gemini-3.1-flash-lite`, falls back to
`MODEL_NAME` only when explicitly unset, and runs with thinking disabled.
`gemini-2.5-flash-lite` held this slot until the provider stopped serving it to
new users on 2026-09-22 (it answers 404). The fallback is `gemini-3.5-flash-lite`,
whose output rate is $2.50, so this stage's price ceiling is `2.50`.

## Temporal status

The classifier extracts explicit effective periods. Content with no date is
`unknown`, not `possibly_stale`: `possibly_stale` and `future` need
`temporal_evidence`, a quote from the item showing it, and an answer whose quote is
missing or not found in the item becomes `unknown`. So does one whose quote carries
dates that contradict it ("effective from 14.07.2026" read as future on
26.09.2026). A "last updated" stamp is not an effective period. Dated periods then decide the status on
the run's `as_of` date (the acquisition's retrieval date) for fresh and cached
assessments alike, with the same rule PDF admission uses: current when a period
covers the day, historical (`possibly_stale`) when all ended, future when all start
later, time-bounded otherwise. A cached "valid until 31.10.2026" therefore becomes
stale on 1 November without a new model call.

Before live execution, every primary and fallback model is checked against
`SOURCE_DISCOVERY_MAX_PRICE_PER_MILLION_TOKENS_USD` (default `2.50`). If either
its current input or output price exceeds the ceiling, the run stops before
making an API request.

Children inherit the validated container assessment, but a page section's children
are not inherited blind. Each section item lists its member blocks with short ids
(`m1`, `m2`, ...) and their full text; a section too long for one item
(`SOURCE_DISCOVERY_MAX_CHARS_PER_ITEM`) is split into consecutive parts
("Terms and conditions (part 2 of 5)") instead of being cut, so every member's
text reaches the classifier. The classifier may return `member_exceptions` for
members that differ from their section (a cross-sell card or a footer line); those
members get the exception's association, role, relevance and reason, and the
exception is stored with the section's assessment so a cache hit reproduces it.
An exception naming a member the item did not show is rejected. Table items show
the headers, the label of every row, and then as many full rows as fit. A linked
document's blocks and tables inherit the document-level decision. The final result
contains an assessment for every block, and a member's own assessment decides
whether it is selected: a section's references never re-select a member the
classifier excluded.

## Source selection

`select_sources()` (`app/services/source_selection.py`) turns the assessments into
one `SourceSelection`: each selected block or table with the assessment that
decides it, and the documents that have selected content. Semantic extraction
(`build_selected_source_bundle`) and the RAG projection read the same selection.
Irrelevant, possibly stale and future material is excluded. A block's or table's own
assessment decides it; a section's or document's references count only for items
without one. The projection further leaves out units labelled as another product,
navigation, or a superseded or future version, never puts the offering's own
content and generic bank material in one chunk, and stamps every chunk's metadata
with the product associations, temporal statuses, authorities and best precedence
of its units. When one item has several selected assessments, the precedence
decides:

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
`source_discovery_result.json`, `assessments.json`, `source_selection.json`, and
`actual_usage_and_cost.json`. It also writes `classification_results.md`, a readable
review grouped into relevant, possibly relevant, irrelevant, and deterministic/reused
decisions. The report lists direct units only and summarizes inherited children. A
failed execution retains its numbered directory and writes `failure.json`; a rerun
uses the next number.

Handled provider/API failures exit with status code 1 and print a concise status plus
the `failure.json` path. Dependency tracebacks are suppressed for these expected
operational failures; unexpected programming errors still retain normal tracebacks.


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
- `Child items covered by inheritance`: individual blocks and tables that do not need separate LLM calls because they inherit a grouped assessment.

For this run, 30,941 normalized child items were condensed into only 40 semantic candidates.

---

### `deterministic_assessments.json`

Source components classified without using an LLM.

In case_008, it contains nine assessments.

Examples of material that can be classified deterministically include:

- the canonical product-page document;
- the site's navigation, header and footer, and the unheaded page header;
- content known to be hidden;
- linked documents with no content (skipped before transcription, or failed).

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
- `scope`: level assessed, such as `document`, `section`, or `table` (`api_payload` appears only in rows written before network payloads were removed).
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
- `source_type`: page or PDF document.
- `title`: best available title for the unit.
- `heading_path`: structural headings surrounding the content.
- `context_text`: representative content from the complete unit.
- `mime_type`: source media type.
- `extraction_method`: browser, HTML parser, JSON parser, or `gemini_pdf:<model>`.
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
  "model_name": "gemini-2.5-flash-lite",
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

There are no final LLM classifications or final source selection in this directory because this demonstration intentionally stops immediately before Gemini invocation.
