# Gemini boundary

[← Guide](../README.md) · Related: [codebase map](../codebase-map/README.md), [config, security, ops](../codebase-map/5-config-security-ops.md), [architecture.md](../../docs/architecture.md)

Open this in the Markdown preview (`Ctrl+Shift+V`). Every link opens the file at the line.

Gemini is called in **seven places**. Each call gets a fixed prompt and a strict output
schema, and code checks every answer before anything depends on it. The rest of the app
(downloads, admission, normalization, validation, change detection, review routing,
persistence, scheduling) is plain Python and calls no model.

- [1 · Models in use, and how to change them](#1--models-in-use-and-how-to-change-them)
- [2 · Gemini boundary map](#2--gemini-boundary-map)

---

## 1 · Models in use, and how to change them

### Which model each call uses

Values are the defaults in [.env.example](../../.env.example). Your local [.env](../../.env) overrides them.

| Call | Env var (model) | Default | Env var (fallbacks) | Default fallbacks | Price cap (USD / 1M tokens) |
|---|---|---|---|---|---|
| Chat agent (`root_agent`) | [`MODEL_NAME`](../../app/config/environment.py#L26) | `gemini-3.7-flash` | none (SDK retries only) | — | none |
| Request interpreter | [`MODEL_NAME`](../../app/config/environment.py#L26) | `gemini-3.7-flash` | none | — | none |
| PDF link selection | [`SOURCE_DISCOVERY_MODEL_NAME`](../../app/config/environment.py#L107) | `gemini-3.1-flash-lite` | [`SOURCE_DISCOVERY_FALLBACK_MODEL_NAMES`](../../app/config/environment.py#L108) | `gemini-3.5-flash-lite` | [`SOURCE_DISCOVERY_MAX_PRICE_PER_MILLION_TOKENS_USD`](../../app/config/environment.py#L111) = 2.5 |
| PDF transcription | [`PDF_EXTRACTION_MODEL_NAME`](../../app/config/environment.py#L62) | `gemini-3.1-flash-lite` | [`PDF_EXTRACTION_FALLBACK_MODEL_NAMES`](../../app/config/environment.py#L63) | *(empty)* | [`PDF_EXTRACTION_MAX_PRICE_PER_MILLION_TOKENS_USD`](../../app/config/environment.py#L64) = 1.5 |
| Source discovery classifier | [`SOURCE_DISCOVERY_MODEL_NAME`](../../app/config/environment.py#L107) | `gemini-3.1-flash-lite` | [`SOURCE_DISCOVERY_FALLBACK_MODEL_NAMES`](../../app/config/environment.py#L108) | `gemini-3.5-flash-lite` | 2.5 (the same cap) |
| Semantic extraction | [`MODEL_NAME`](../../app/config/environment.py#L26) | `gemini-3.7-flash` | [`SEMANTIC_EXTRACTION_FALLBACK_MODEL_NAMES`](../../app/config/environment.py#L123) | `gemini-3.8-flash` | none |
| Embeddings (documents and queries) | [`EMBEDDING_MODEL_NAME`](../../app/config/environment.py#L27) | `gemini-embedding-001` | none | — | none |

One API key serves every call: [`GEMINI_API_KEY`](../../app/config/environment.py#L25) → [`ModelSettings.api_key`](../../app/config/models.py#L62).

`MODEL_NAME` drives three calls: the chat agent, the request interpreter and semantic
extraction. `SOURCE_DISCOVERY_MODEL_NAME` drives both source-discovery calls, PDF link
selection and the section classifier. If it is empty, it falls back to `MODEL_NAME`
([runtime.py:170](../../app/runtime.py#L170)).

### How a setting reaches the code

```text
.env / env var ─► EnvironmentSettings (flat) ─► load_settings() ─► grouped Settings ─► build_application_container()
```

| Step | Where |
|---|---|
| Flat env fields and their defaults | [EnvironmentSettings](../../app/config/environment.py#L10) |
| Comma-separated fallback lists → tuples | [parse_csv_tuple](../../app/config/environment.py#L149) |
| Flat → grouped: `models` | [loader.py:40-44](../../app/config/loader.py#L40) → [ModelSettings](../../app/config/models.py#L61) |
| Flat → grouped: `pdf_extraction` | [loader.py:83-84](../../app/config/loader.py#L83) → [PdfExtractionSettings](../../app/config/models.py#L219) |
| Flat → grouped: `source_discovery` | [loader.py:154-155](../../app/config/loader.py#L154) → [SourceDiscoverySettings](../../app/config/models.py#L319) |
| Flat → grouped: `semantic_extraction` | [loader.py:170](../../app/config/loader.py#L170) → [SemanticExtractionSettings](../../app/config/models.py#L368) |
| Fallback-list rules (at most 5, unique) | [PdfExtractionSettings.validate_fallback_models](../../app/config/models.py#L233), [SourceDiscoverySettings.validate_fallback_models](../../app/config/models.py#L343), [SemanticExtractionSettings.validate_fallback_models](../../app/config/models.py#L389) |
| Chat agent reads the model at import | [agent.py `MODEL`](../../app/agent.py#L24) |
| Request interpreter wired | [runtime.py:147](../../app/runtime.py#L147) |
| PDF transcription wired | [runtime.py:159](../../app/runtime.py#L159) (the model list is built in [GeminiPdfExtractionService.\_\_init\_\_](../../app/services/pdf_extraction.py#L173)) |
| Source-discovery model list and price check | [runtime.py:169-178](../../app/runtime.py#L169) |
| Source discovery, one service per model | [runtime.py:180](../../app/runtime.py#L180) |
| PDF link selection, one classifier per model | [runtime.py:211](../../app/runtime.py#L211) |
| Semantic-extraction model list | [runtime.py:240](../../app/runtime.py#L240), services [runtime.py:246](../../app/runtime.py#L246) |
| Embedding client and providers | [runtime.py:268](../../app/runtime.py#L268), [runtime.py:303-323](../../app/runtime.py#L303) |
| Primary first, repeats removed | [model_sequence](../../app/services/model_pricing.py#L141) |

### Change a model: steps

1. **Check the price.** Look the model up in [MODEL_PRICE_CATALOG](../../app/services/model_pricing.py#L18).
   PDF transcription and source discovery call [enforce_model_price_cap](../../app/services/model_pricing.py#L150)
   at startup, and [get_model_price](../../app/services/model_pricing.py#L129) raises for a model with
   no price entry for today. **A model missing from the catalog stops the app from starting**
   if it is used for either of those two calls. Add a [ModelPrice](../../app/services/model_pricing.py#L8)
   entry with its dates, taken from the linked pricing page.
2. **Check how the model turns thinking off.** The structured calls send either `thinking_budget=0`
   or `thinking_level=MINIMAL`. Models that accept only `MINIMAL` go in
   [MINIMAL_THINKING_LEVEL_MODELS](../../app/services/model_pricing.py#L121). A model in the wrong
   group answers HTTP 400 on every call. [uses_minimal_thinking_level](../../app/services/model_pricing.py#L124)
   is read by [StructuredAdkClassifier](../../app/services/discovery_classifier.py#L147),
   [AdkGeminiPdfExtractor](../../app/services/gemini_pdf_extractor.py#L88) and
   [AdkSemanticExtractor](../../app/services/semantic_extraction.py#L338). The
   [request interpreter](../../app/services/intent_resolution.py#L235) always sends `thinking_budget=0`.
3. **Set the env var** in `.env` (the table above). A fallback list is comma-separated, e.g.
   `SOURCE_DISCOVERY_FALLBACK_MODEL_NAMES=gemini-3.5-flash-lite,gemini-3.6-flash`.
4. **Restart** the chat process and the worker. [agent.py](../../app/agent.py#L24) reads `MODEL_NAME`
   once, at import. Docker Compose reads `.env` through [`env_file`](../../docker-compose.yml#L5).
5. **Expect cache misses.** Every model cache is keyed by model name, so the first run on a new
   model pays for every call again:
   PDF link choices ([key](../../app/services/pdf_link_selection.py#L213)),
   PDF transcriptions ([lookup](../../app/services/pdf_extraction.py#L494)),
   discovery assessments ([save](../../app/services/source_discovery.py#L360)),
   extraction answers ([prompt_fingerprint](../../app/services/semantic_extraction.py#L603)).
   Answers can differ between models, so changes that appear on that first run may be model
   differences, not tariff changes.
6. **Update the pinned defaults** if you changed a default rather than your `.env`:
   [environment.py](../../app/config/environment.py#L26), [models.py](../../app/config/models.py#L63),
   [.env.example](../../.env.example), and the assertions in
   [tests/unit/test_config.py](../../tests/unit/test_config.py#L13). Then run
   `uv run pytest tests/unit tests/integration`.

**The embedding model needs more care:**

- Vectors are 768-wide: [EMBEDDING_DIMENSIONS](../../app/domain/knowledge.py#L21), requested per call as
  `output_dimensionality` ([documents](../../app/services/embedding_providers.py#L121), [queries](../../app/services/embedding_providers.py#L199)).
  The columns are fixed at `vector(768)` in [002](../../migrations/002_rag_knowledge_store.sql#L54),
  [011](../../migrations/011_structured_tariff_read_model.sql#L88) and [012](../../migrations/012_embedding_cache.sql#L7).
  A model that cannot return 768 dimensions needs a migration.
- Vector search only reads vectors stored under the current model ([`embedding_model = :model_id`](../../app/repositories/structured_tariff_query.py#L568)).
  Vectors from any other model count as missing ([missing units query](../../app/repositories/structured_tariff_query.py#L736)).
  The [worker sweep](../../app/worker.py#L234) re-embeds them in batches of
  [`EMBEDDING_SWEEP_BATCH`](../../app/config/environment.py#L84). Until it finishes, answers use lexical search only.
- Documents and queries must use the same model. [StructuredUnitEmbeddingService](../../app/services/structured_unit_embeddings.py#L50) refuses to start otherwise.

### Settings changes that take effect without a model change

Some settings change what a model answers, so they are part of the cache key or version:

| Setting | Effect |
|---|---|
| [`PDF_EXTRACTION_PROMPT_VERSION`](../../app/config/environment.py#L61), [`PDF_EXTRACTION_SCHEMA_VERSION`](../../app/config/environment.py#L60) | bump after editing the transcription prompt or schema; old transcriptions stop being reused |
| [`SOURCE_DISCOVERY_PROMPT_VERSION`](../../app/config/environment.py#L95), [`SOURCE_DISCOVERY_POLICY_VERSION`](../../app/config/environment.py#L94) | the same for discovery; the policy version also keys PDF link choices |
| [`PDF_LINK_PROMPT_VERSION`](../../app/services/pdf_link_selection.py#L43) (a constant, not an env var) | bump after editing [PDF_LINK_INSTRUCTION](../../app/services/pdf_link_selection.py#L46) |
| [`SEMANTIC_EXTRACTION_PROMPT_VERSION`](../../app/config/environment.py#L113), [`SEMANTIC_EXTRACTION_SCHEMA_VERSION`](../../app/config/environment.py#L112) | the same for extraction. The prompt text itself is hashed into the key ([prompt_fingerprint](../../app/services/semantic_extraction.py#L603)), so an edit is never served a stale answer |
| [`SEMANTIC_EXTRACTION_THINKING_BUDGET`](../../app/config/environment.py#L117), [`SEMANTIC_EXTRACTION_MAX_OUTPUT_TOKENS`](../../app/config/environment.py#L118) | part of the extraction cache key |

> **Watch out:** the code default for `semantic_extraction.fallback_model_names` is empty
> ([models.py:371](../../app/config/models.py#L371)), but the env layer's default is
> `("gemini-3.8-flash",)` ([environment.py:123](../../app/config/environment.py#L123)). Settings loaded
> through [load_settings](../../app/config/loader.py#L28) get the env layer's value. A test that builds
> `SemanticExtractionSettings()` directly gets no fallback.

---

## 2 · Gemini boundary map

### All calls on one screen

`Stage` is the label in the model-usage log ([adk_usage_callbacks](../../app/services/model_call_usage.py#L382), [observe_model_call](../../app/services/model_call_usage.py#L288)).

| # | Call | Stage | Prompt | Output schema | Fallback chain | Code that validates the answer | If the model fails |
|---|---|---|---|---|---|---|---|
| 1 | [Chat agent](#1-chat-agent-root_agent) | `adk.root` | [INSTRUCTION](../../app/agent.py#L28) | free text + tool calls | none | [ToolPolicyPlugin](../../app/plugins.py#L34), per-turn grants | the chat turn fails |
| 2 | [Request interpreter](#2-request-interpreter) | `intent.resolution` | [INTERPRETER_INSTRUCTION](../../app/services/intent_resolution.py#L98) | [RequestInterpretation](../../app/domain/interpretation.py#L103) | none; 2 attempts | [InterpretationValidator.validate](../../app/services/interpretation_validation.py#L143) | `status: unavailable`, nothing granted |
| 3 | [PDF link selection](#3-pdf-link-selection) | `discovery.pdf_link_selection` | [PDF_LINK_INSTRUCTION](../../app/services/pdf_link_selection.py#L46) | [PdfLinkBatchResponse](../../app/domain/source_discovery.py#L432) | whole selection moves to the next model | [\_classify_checked](../../app/services/pdf_link_selection.py#L258) | offering fails `source_discovery_failed` |
| 4 | [PDF transcription](#4-pdf-transcription) | `pdf.transcription` | [PDF_EXTRACTION_INSTRUCTION](../../app/services/gemini_pdf_extractor.py#L38) | [PdfModelExtractionResponse](../../app/domain/pdf_extraction.py#L205) | per PDF, next model, then OCR | [\_to_domain_response](../../app/services/gemini_pdf_extractor.py#L211), [\_covers_all_pages](../../app/services/pdf_extraction.py#L697) | OCR, or an empty document plus a warning |
| 5 | [Source discovery classifier](#5-source-discovery-classifier) | `discovery.classification` | [SOURCE_DISCOVERY_INSTRUCTION](../../app/services/discovery_classifier.py#L27) | [DiscoveryBatchResponse](../../app/domain/source_discovery.py#L360) | whole offering moves to the next model | [\_check_response](../../app/services/source_discovery.py#L956), [\_settle_temporal](../../app/services/source_discovery.py#L814) | offering fails `source_discovery_failed` |
| 6 | [Semantic extraction](#6-semantic-extraction) | `semantic.extraction` | [SEMANTIC_EXTRACTION_INSTRUCTION](../../app/services/semantic_extraction.py#L92) | [ExtractionBatchResponse](../../app/domain/semantic_extraction.py#L548) | per call, next model | [\_validate_individual_fields](../../app/services/semantic_extraction.py#L2252), [extraction_is_acceptable](../../app/services/snapshot_lifecycle.py#L189) | fields go to review, or the offering fails |
| 7 | [Embeddings](#7-embeddings) | `indexing.embedding`, `rag.query_embedding` | — | 768 floats | none | [count and non-null check](../../app/services/embedding_providers.py#L160) | lexical search only; the sweep retries later |

Every structured call (2 to 6) runs as a **tool-free** ADK `Agent` with
`output_schema`, `temperature=0` and automatic function calling disabled. Each call
creates its own `InMemoryRunner` session and keeps no conversation between calls.

### Shared plumbing (calls 3 and 5)

| What | Where |
|---|---|
| Generic strict-JSON classifier: one request model in, one response model out | [StructuredAdkClassifier](../../app/services/discovery_classifier.py#L117) |
| Temperature 0, thinking off, output token cap, one SDK attempt | [\_\_init\_\_](../../app/services/discovery_classifier.py#L125) |
| Application retry loop (backoff, jitter) on 429/5xx | [classify](../../app/services/discovery_classifier.py#L199), [is_retryable_api_error](../../app/services/discovery_classifier.py#L303), [\_RETRYABLE_STATUS_CODES](../../app/services/discovery_classifier.py#L99) |
| Single call: build the prompt, parse the JSON against the schema | [\_classify_once](../../app/services/discovery_classifier.py#L222) |
| "Answered outside the contract" error | [ModelResponseError](../../app/services/discovery_classifier.py#L307) |
| When the next model gets a turn (any `APIError` or `ModelResponseError`) | [is_model_fallback_error](../../app/services/discovery_classifier.py#L315) |
| Cost ceiling, checked at startup | [enforce_model_price_cap](../../app/services/model_pricing.py#L150) |

---

### 1 Chat agent (`root_agent`)

The only call that uses tools. It chooses and orders tool calls and writes the reply.
It never sees raw data sources, and it never decides scope or review outcomes.

| | |
|---|---|
| **Agent** | [root_agent](../../app/agent.py#L65) in [App](../../app/agent.py#L76), resumable for review pauses |
| **Model** | [MODEL](../../app/agent.py#L24) = `settings.models.generation_model`; SDK retries: [3 attempts](../../app/agent.py#L68) |
| **Prompt** | [INSTRUCTION](../../app/agent.py#L28) (language, honesty, presentation) |
| **Tools** | [TOOLS](../../app/agent.py#L55): [resolve_request](../../app/tools/resolution.py#L48), [answer_tariff_query](../../app/tools/reads.py#L56), [get_current_tariffs](../../app/tools/reads.py#L91), [get_tariff_history](../../app/tools/reads.py#L128), [run_tariff_monitoring](../../app/tools/monitoring.py#L37), [review_pending_candidates](../../app/tools/monitoring.py#L148), [get_monitoring_status](../../app/tools/monitoring.py#L185) |
| **Output** | free text; tool arguments are ignored for scope |
| **Validated by** | [ToolPolicyPlugin.before_tool_callback](../../app/plugins.py#L38): every [business tool](../../app/plugins.py#L22) needs a `resolve_request` from the same invocation, else `policy.resolve_first`. [on_tool_error_callback](../../app/plugins.py#L64) turns a tool exception into a typed envelope. Scope comes from the grants that `resolve_request` issues, checked by [issued_this_turn](../../app/tools/_state.py#L79) |
| **Fallback** | none. A provider failure ends the turn |

**What if we removed the model here?** You would need a different UI (a menu or form)
because nothing else turns free text into tool calls. None of the business logic is in
the prompt: tool order is enforced by the plugin, scope by the grants, reviews by native
`RequestInput` pauses. Only the phrasing and language of replies would be lost.

---

### 2 Request interpreter

One tool-free call per chat turn. It proposes intent, catalog scope, language and query
shape as enum-bounded JSON, and code decides what is actually granted.

| | |
|---|---|
| **Class** | [AdkRequestInterpreter](../../app/services/intent_resolution.py#L206), wired at [runtime.py:147](../../app/runtime.py#L147) |
| **Model** | `MODEL_NAME`; temperature 0, [thinking budget 0](../../app/services/intent_resolution.py#L235) |
| **Prompt** | [INTERPRETER_INSTRUCTION](../../app/services/intent_resolution.py#L98). Input: [InterpretationRequest](../../app/domain/interpretation.py#L132) (message, context, [catalog view](../../app/services/intent_resolution.py#L486), [allowed values](../../app/services/intent_resolution.py#L527)) |
| **Output schema** | [RequestInterpretation](../../app/domain/interpretation.py#L103) (intent, `replies_to`, product, `offering_ids`, [QueryShape](../../app/domain/query_shape.py#L46), clarification) |
| **Retries** | [interpret](../../app/services/intent_resolution.py#L243): [`INTENT_CLASSIFIER_MAX_ATTEMPTS`](../../app/config/environment.py#L86) = 2, on `APIError` or a parse failure; SDK 3 attempts inside |
| **Parse** | [\_interpret_once](../../app/services/intent_resolution.py#L256) → `RequestInterpretation.model_validate_json` |
| **Validated by** | [RequestResolver.resolve_turn](../../app/services/intent_resolution.py#L330) → [InterpretationValidator.validate](../../app/services/interpretation_validation.py#L143): a reply needs something pending to reply to; an accepted offer takes the **offer's** scope, not the model's; cross-family scope → clarify; [\_cross_check](../../app/services/interpretation_validation.py#L401) compares the model's offering with offerings named exactly in the message ([\_exact_offerings](../../app/services/intent_resolution.py#L447)); a single value asked of a whole family → clarify. Typed API questions: [shape_for](../../app/services/intent_resolution.py#L376) → [shape_within](../../app/services/interpretation_validation.py#L262) keeps only the shape and discards the model's scope |
| **Fallback** | none. Any failure raises [InterpretationUnavailable](../../app/services/intent_resolution.py#L88) ([resolve_turn](../../app/services/intent_resolution.py#L363)), and [resolve_request](../../app/tools/resolution.py#L88) returns `intent.interpretation_unavailable` with no grants |

**What if we removed the model here?** Everything after it still works, because
[InterpretationValidator](../../app/services/interpretation_validation.py#L115) only accepts values that
exist in the catalog. You would need a deterministic proposer that fills the same
[RequestInterpretation](../../app/domain/interpretation.py#L103): exact catalog-name matching already
exists ([\_build_targets](../../app/services/intent_resolution.py#L555), [detect_request_language](../../app/services/intent_resolution.py#L476)).
What you lose is paraphrase, follow-up resolution ("and the fee?"), yes/no to an offer, and
query shapes (ranking, comparison, history). Recorded model answers used by tests:
[recorded_interpretations.json](../../tests/fixtures/recorded_interpretations.json).

---

### 3 PDF link selection

Source discovery's first step. From **link metadata only**, before any transcription is
paid for, it decides which admitted PDFs belong to this offering.

| | |
|---|---|
| **Classes** | [AdkPdfLinkClassifier](../../app/services/pdf_link_selection.py#L84) (a [StructuredAdkClassifier](../../app/services/discovery_classifier.py#L117)); service [PdfLinkSelectionService](../../app/services/pdf_link_selection.py#L161); wired at [runtime.py:211](../../app/runtime.py#L211); called in the [`pdf_selection` stage](../../app/services/monitoring_pipeline.py#L304) |
| **Model** | source-discovery chain (`SOURCE_DISCOVERY_MODEL_NAME` + fallbacks), same retry and token settings |
| **Input (deterministic)** | [admitted_links](../../app/services/pdf_link_selection.py#L272): rules in [assess_pdf_metadata](../../app/services/pdf_admission.py#L100) drop off-topic and superseded PDFs first. Each link becomes a [PdfLinkPromptItem](../../app/domain/source_discovery.py#L406) (built by [\_prompt_item](../../app/services/pdf_link_selection.py#L297), with length caps), batched by [\_MAX_LINKS_PER_BATCH](../../app/services/pdf_link_selection.py#L44) = 40 |
| **Prompt** | [PDF_LINK_INSTRUCTION](../../app/services/pdf_link_selection.py#L46), [build_link_prompt](../../app/services/pdf_link_selection.py#L77), version [PDF_LINK_PROMPT_VERSION](../../app/services/pdf_link_selection.py#L43) |
| **Output schema** | [PdfLinkBatchResponse](../../app/domain/source_discovery.py#L432) → items of [PdfLinkModelDecision](../../app/domain/source_discovery.py#L425) (label [PdfLinkLabel](../../app/domain/pdf_extraction.py#L56), role, reason) |
| **Validated by** | [\_classify_checked](../../app/services/pdf_link_selection.py#L258): exactly one decision per link id, asked twice before [PdfLinkResponseError](../../app/services/pdf_link_selection.py#L157). The label only controls whether the PDF is transcribed: [TRANSCRIBED_LINK_LABELS](../../app/domain/pdf_extraction.py#L69) (`current_product`, `shared_terms`, `unclear`), applied in [normalization.py:245](../../app/services/normalization.py#L245). Source discovery rechecks those PDFs against their content (call 5) |
| **Cache** | key = offering, policy version, prompt version, model, [link_fingerprint](../../app/services/pdf_link_selection.py#L311) ([\_select_with](../../app/services/pdf_link_selection.py#L205)) |
| **Fallback** | [select](../../app/services/pdf_link_selection.py#L184): on [is_model_fallback_error](../../app/services/discovery_classifier.py#L315) the whole selection moves to the next model. After the last model the stage fails with `SOURCE_DISCOVERY_FAILED` |

**What if we removed the model here?** Leave `pdf_selection` as `None`, which the pipeline
already allows ([monitoring_pipeline.py:301](../../app/services/monitoring_pipeline.py#L301)). Every
PDF that passes the deterministic admission is then transcribed. Results stay correct
because call 5 still classifies each PDF by content, but transcription costs more and
takes longer.

---

### 4 PDF transcription

Bounded structure transcription: Gemini reads the PDF bytes and returns pages, blocks
and rectangular tables. It does not interpret loan semantics.

| | |
|---|---|
| **Classes** | [AdkGeminiPdfExtractor](../../app/services/gemini_pdf_extractor.py#L54) (created per model inside) [GeminiPdfExtractionService](../../app/services/pdf_extraction.py#L150); wired at [runtime.py:159](../../app/runtime.py#L159), called from [StructuralNormalizationService](../../app/services/normalization.py#L126) |
| **Model** | [`PDF_EXTRACTION_MODEL_NAME`](../../app/config/environment.py#L62) + [fallbacks](../../app/config/environment.py#L63); temperature 0, thinking off ([config](../../app/services/gemini_pdf_extractor.py#L79)) |
| **Skipped without a call** | [\_skip_reason](../../app/services/pdf_extraction.py#L445): irrelevant, or historical when [`PDF_EXTRACTION_SKIP_HISTORICAL`](../../app/config/environment.py#L70) is on. Also skipped when link selection said no ([normalization.py:245](../../app/services/normalization.py#L245)) |
| **Prompt** | [PDF_EXTRACTION_INSTRUCTION](../../app/services/gemini_pdf_extractor.py#L38) + [page-count message](../../app/services/gemini_pdf_extractor.py#L150) + PDF bytes ([Part.from_bytes](../../app/services/gemini_pdf_extractor.py#L163)) |
| **Output schema** | [PdfModelExtractionResponse](../../app/domain/pdf_extraction.py#L205) (flat [PdfModelItem](../../app/domain/pdf_extraction.py#L187) list) → domain [PdfExtractionResponse](../../app/domain/pdf_extraction.py#L243) |
| **Retries** | [extract](../../app/services/gemini_pdf_extractor.py#L118): [`PDF_EXTRACTION_MAX_ATTEMPTS`](../../app/config/environment.py#L65) on 429/5xx, with backoff |
| **Validated by** | schema parse in [\_extract_once](../../app/services/gemini_pdf_extractor.py#L182); [\_to_domain_response](../../app/services/gemini_pdf_extractor.py#L211) rejects [out-of-range pages](../../app/services/gemini_pdf_extractor.py#L231) and makes tables rectangular; a cached answer must cover every page ([\_covers_all_pages](../../app/services/pdf_extraction.py#L697)); [\_normalize](../../app/services/pdf_extraction.py#L734) turns it into a `NormalizedDocument` with locators |
| **Fallback chain** | [extract](../../app/services/pdf_extraction.py#L456): for each model, cache then call; errors in [\_MODEL_FAILURES](../../app/services/pdf_extraction.py#L62) move to the next model. After the last: [\_ocr_only](../../app/services/pdf_extraction.py#L383) (Tesseract), else [PdfTranscriptionFailed](../../app/services/pdf_extraction.py#L90). No key: OCR, else [PdfModelUnavailable](../../app/services/pdf_extraction.py#L86). Pages the model left empty on scanned input: [\_apply_ocr](../../app/services/pdf_extraction.py#L355) / [\_pages_needing_ocr](../../app/services/pdf_extraction.py#L230) |
| **On total failure** | [PdfExtractionError](../../app/services/pdf_extraction.py#L74) becomes a warning and an empty document ([normalization.py:285](../../app/services/normalization.py#L285)). The offering continues on its HTML |
| **Downstream guard** | any value cited from OCR text is sent to review: [OCR_SOURCE_ITEM_MARKER](../../app/domain/pdf_extraction.py#L158), [is_ocr_source_item](../../app/domain/pdf_extraction.py#L165) |

**What if we removed the model here?** The OCR path already exists and is what runs when
no key is configured. But Tesseract gives page text, not tables. Rows and group labels
are lost, and every OCR-backed value goes to review. PDFs with a text layer would need a
deterministic text-layer table parser instead ([probe_pdf_input](../../app/services/pdf_input_probe.py#L10) already
detects which pages have one).

---

### 5 Source discovery classifier

Classifies the normalized sections, tables and linked PDFs of one offering (whose
product, current or stale, what role). This decides which evidence extraction is
allowed to see.

| | |
|---|---|
| **Classes** | [AdkSourceDiscoveryClassifier](../../app/services/discovery_classifier.py#L266); service [SourceDiscoveryService](../../app/services/source_discovery.py#L195); chain [FallbackSourceDiscoveryService](../../app/services/source_discovery.py#L422); wired at [runtime.py:180](../../app/runtime.py#L180); called in the [`source_discovery` stage](../../app/services/monitoring_pipeline.py#L329) |
| **Model** | [`SOURCE_DISCOVERY_MODEL_NAME`](../../app/config/environment.py#L107) + [fallbacks](../../app/config/environment.py#L108); retries, backoff, [`SOURCE_DISCOVERY_CLASSIFIER_MAX_OUTPUT_TOKENS`](../../app/config/environment.py#L106) |
| **Decided without a call** | [\_rule_assessment](../../app/services/source_discovery.py#L500) (navigation, cross-sell, PDFs link selection rejected), cache hits, and members that inherit their section's label ([\_inherited_assessments](../../app/services/source_discovery.py#L995)). Candidates: [build_discovery_candidates](../../app/services/discovery_prefilter.py#L70). Batches: [\_build_batches](../../app/services/source_discovery.py#L687), limited by [`SOURCE_DISCOVERY_MAX_ITEMS_PER_BATCH`](../../app/config/environment.py#L96) / [`_MAX_CHARS_PER_BATCH`](../../app/config/environment.py#L98) |
| **Prompt** | [SOURCE_DISCOVERY_INSTRUCTION](../../app/services/discovery_classifier.py#L27), [build_classifier_prompt](../../app/services/discovery_classifier.py#L295); input [DiscoveryBatch](../../app/domain/source_discovery.py#L334) |
| **Output schema** | [DiscoveryBatchResponse](../../app/domain/source_discovery.py#L360) → [ModelSourceAssessment](../../app/domain/source_discovery.py#L345) (product association, role, relevance, authority, temporal status, periods, member exceptions, temporal evidence) |
| **Validated by** | [\_check_response](../../app/services/source_discovery.py#L956): ids match the batch exactly, member exceptions name only real members once, with a reason. Invalid → [\_classify_resilient](../../app/services/source_discovery.py#L766) asks again, then splits the batch in halves down to single items. [\_settle_temporal](../../app/services/source_discovery.py#L814): `possibly_stale`/`future` need a quote that appears in the item ([\_quoted_in](../../app/services/source_discovery.py#L939)); dated periods decide the status as of the run date, even for cached answers. Selection is plain code: [select_sources](../../app/services/source_selection.py#L58), [is_selected_assessment](../../app/services/source_selection.py#L19) |
| **Fallback** | [FallbackSourceDiscoveryService.discover](../../app/services/source_discovery.py#L437): each model has its own service and cache namespace; on [is_model_fallback_error](../../app/services/discovery_classifier.py#L315) the whole offering reruns on the next model. Batches that were checked are [saved as they finish](../../app/services/source_discovery.py#L360), so they are not paid for again |
| **On total failure** | offering fails `SOURCE_DISCOVERY_FAILED`; the error is written to the [audit archive](../../app/services/monitoring_pipeline.py#L339) |

**What if we removed the model here?** You would have to widen [\_rule_assessment](../../app/services/source_discovery.py#L500)
until it decides every candidate. The rules already cover page chrome and cross-sell
cards. Telling "this offering's table" apart from "a sibling product's table on the same
page" by rules alone is the hard part, and a wrong call there sends another product's
rate into extraction. The fallback would be to select everything and let extraction's
TARGET / OTHER PRODUCTS split and review absorb the noise.

---

### 6 Semantic extraction

Evidence-bound structured extraction: for each requested field, a value, a status and
**verbatim quotes** from supplied evidence ids. It is the only call whose output becomes
tariff data.

| | |
|---|---|
| **Classes** | [AdkSemanticExtractor](../../app/services/semantic_extraction.py#L317); service [SemanticExtractionService](../../app/services/semantic_extraction.py#L508); chain [FallbackSemanticExtractionService](../../app/services/semantic_extraction.py#L2994); wired at [runtime.py:246](../../app/runtime.py#L246); called in the [`semantic_extraction` stage](../../app/services/monitoring_pipeline.py#L354) |
| **Model** | `MODEL_NAME` + [`SEMANTIC_EXTRACTION_FALLBACK_MODEL_NAMES`](../../app/config/environment.py#L123); temperature 0, [`THINKING_BUDGET`](../../app/config/environment.py#L117), [`MAX_OUTPUT_TOKENS`](../../app/config/environment.py#L118), [`MAX_CONCURRENT_CALLS`](../../app/config/environment.py#L120) |
| **Input (deterministic)** | only evidence that source discovery selected: [build_selected_source_bundle](../../app/services/source_selection.py#L71) → [build_evidence_catalog](../../app/services/extraction_evidence.py#L29) → [build_extraction_batches](../../app/services/extraction_planner.py#L143); rendered by [build_extraction_prompt](../../app/services/semantic_extraction.py#L1174) / [render_evidence_packet](../../app/services/semantic_extraction.py#L1223) |
| **Prompt** | [SEMANTIC_EXTRACTION_INSTRUCTION](../../app/services/semantic_extraction.py#L92) |
| **Output schema** | [ExtractionBatchResponse](../../app/domain/semantic_extraction.py#L548) → [ModelFieldResult](../../app/domain/semantic_extraction.py#L502) (field, status, `value_json`, [ModelCitation](../../app/domain/semantic_extraction.py#L494) evidence id + quote) |
| **Retries** | [extract](../../app/services/semantic_extraction.py#L384): 429/5xx with backoff; an empty or cut ([MAX_TOKENS](../../app/services/semantic_extraction.py#L478)) answer is asked once more ([SemanticExtractionCallError](../../app/services/semantic_extraction.py#L259)) |
| **Validated by** | [parse_batch_response](../../app/services/semantic_extraction.py#L2647) drops only the fields that fail the schema, and keeps the rest of the call. [\_normalize_response_contract](../../app/services/semantic_extraction.py#L1291) reshapes values without changing them. [\_validate_individual_fields](../../app/services/semantic_extraction.py#L2252): one result per field, else review; [\_validate_result_evidence_boundary](../../app/services/semantic_extraction.py#L2237): cited ids were in **this** batch and every quote is a verbatim substring; [\_validate_field_result](../../app/services/semantic_extraction.py#L2379): value parses as the field's typed model ([\_field_adapter](../../app/services/semantic_extraction.py#L2440)), category matches the product family. Suspicious fields get a paid repair call, up to [`MAX_REPAIRS_PER_RUN`](../../app/config/environment.py#L119) ([\_repair_suspicious_fields](../../app/services/semantic_extraction.py#L1011)). A remembered human decision may settle a field ([\_apply_review_memory](../../app/services/semantic_extraction.py#L905)) |
| **Acceptance (after the model)** | [build_snapshot_attempt](../../app/services/snapshot_lifecycle.py#L107) → [extraction_is_acceptable](../../app/services/snapshot_lifecycle.py#L189) (every found value has official evidence, no ambiguous or conflicting field, required fields present) and [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237) (large rate change, OCR evidence, rank gap). Otherwise → HITL review |
| **Fallback** | [\_call](../../app/services/semantic_extraction.py#L797): **per call**. A call the primary cannot answer tries each fallback model (its cache first); the other calls stay on the primary. Each answer is cached under the model that gave it |
| **On total failure** | a call with no answer becomes review items; if no call answered, the stage fails ([extract](../../app/services/semantic_extraction.py#L692)). Failures a human cannot fix fail the offering: [non_reviewable_extraction_failure](../../app/services/snapshot_lifecycle.py#L223) |

**What if we removed the model here?** Deterministic candidates already exist:
[extract_scalar_candidates](../../app/services/scalar_normalizer.py#L117) finds money, percentages
and dates, and table cells keep their row and column headers. What you lose is mapping
them to typed fields and conditions ([LoanProduct](../../app/domain/semantic_extraction.py#L419)).
A rules-based extractor could fill the same [ModelFieldResult](../../app/domain/semantic_extraction.py#L502)
contract and reuse all the validation and review routing above unchanged, because those
check the output, not who produced it.

---

### 7 Embeddings

Not a generation call: vectors for the retrieval units of the structured read model.

| | |
|---|---|
| **Classes** | documents: [GeminiEmbeddingProvider.embed_documents](../../app/services/embedding_providers.py#L103) (`RETRIEVAL_DOCUMENT`, batches of [20](../../app/services/embedding_providers.py#L41)); queries: [GeminiQueryEmbeddingProvider.embed_query](../../app/services/embedding_providers.py#L192) (`RETRIEVAL_QUERY`); wrapper [StructuredUnitEmbeddingService](../../app/services/structured_unit_embeddings.py#L41); wired at [runtime.py:303](../../app/runtime.py#L303) |
| **Model** | [`EMBEDDING_MODEL_NAME`](../../app/config/environment.py#L27), [768 dimensions](../../app/domain/knowledge.py#L21) |
| **When** | documents: [worker sweep](../../app/worker.py#L234) → [embed_missing](../../app/services/structured_unit_embeddings.py#L127), not inside a run. Queries: [\_find_fields](../../app/services/structured_tariff_query.py#L397) per question |
| **Retries** | split by meaning: 429 → [`EMBEDDING_QUOTA_MAX_ATTEMPTS`](../../app/config/environment.py#L82) then [EmbeddingQuotaExhausted](../../app/services/embedding_providers.py#L30); 5xx → [`EMBEDDING_MAX_ATTEMPTS`](../../app/config/environment.py#L80); anything else fails at once |
| **Validated by** | one vector per input, none null ([documents](../../app/services/embedding_providers.py#L160), [query](../../app/services/embedding_providers.py#L209)); same model and dimensions on both sides ([check](../../app/services/structured_unit_embeddings.py#L50)); search reads only vectors from the [current model](../../app/repositories/structured_tariff_query.py#L568) |
| **Fallback** | a failed query embedding is logged and the question is answered from lexical hits alone ([structured_tariff_query.py:447](../../app/services/structured_tariff_query.py#L447)); lexical and vector hits are fused by rank, so vector search only adds recall |

**What if we removed the model here?** Answers keep working on lexical retrieval. This
path already runs whenever the embedding call fails. Paraphrased questions that share
no words with the field text would stop finding their field.

---

### Where to look when a model answer seems wrong

| Question | Look at |
|---|---|
| What did each call cost, and which model answered? | model-usage log by `stage`: [PostgresModelCallUsageRepository](../../app/services/model_call_usage.py), [pricing](../../app/services/model_pricing.py) |
| What did discovery and extraction actually see and answer? | per-run audit files: [FileSystemPipelineAuditArchive](../../app/services/pipeline_audit_archive.py), [pipeline_audit.py](../../app/services/pipeline_audit.py) (model shown per batch) |
| Why did a field go to review? | [3 Review and change detection](../codebase-map/3-review-and-change-detection.md), [debug/symptoms.md](../debug/symptoms.md) |
| How do I change a prompt safely? | [debug drill B3](../debug/drills/B3-prompt.diff), [change recipes](../change-recipes/README.md) |
