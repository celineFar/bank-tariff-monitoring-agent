# 2 · Monitoring pipeline

[← Guide](README.md) · Deep dives: [acquisition.md](../../docs/acquisition.md), [normalization.md](../../docs/normalization.md), [source-discovery.md](../../docs/source-discovery.md), [semantic-extraction.md](../../docs/semantic-extraction.md), [failure-behavior.md](../../docs/failure-behavior.md)

Everything here is in [app/services/](../../app/services/). The contracts (Pydantic models) are in [app/domain/](../../app/domain/).

## Orchestration

| What | Where |
|---|---|
| Family run: one offering after another, siblings isolated → `partial_success` | [TariffPipeline.execute](../../app/services/monitoring_pipeline.py#L584) |
| One offering, all stages in order | [IndexingPipeline.refresh](../../app/services/monitoring_pipeline.py#L226) |
| Stage wrapper (timing, span, failure code) | [IndexingPipeline._stage](../../app/services/monitoring_pipeline.py#L541) |
| Page retried once on browser failure / incomplete content | [acquire_with_retry](../../app/services/monitoring_pipeline.py#L142) |
| Stage failure exception | [OfferingPipelineError](../../app/services/monitoring_pipeline.py#L171) |
| Stage ports (interfaces) | [AcquisitionPort … SemanticExtractionPort](../../app/services/monitoring_pipeline.py#L86) |
| Wiring (which implementation, models, caches) | [build_application_container](../../app/runtime.py#L123) |

Stage calls inside `refresh`: [acquisition](../../app/services/monitoring_pipeline.py#L271) → [pdf_selection](../../app/services/monitoring_pipeline.py#L304) → [normalization](../../app/services/monitoring_pipeline.py#L309) → [source_discovery](../../app/services/monitoring_pipeline.py#L329) → [semantic_extraction](../../app/services/monitoring_pipeline.py#L354) → [previous_snapshot](../../app/services/monitoring_pipeline.py#L400) → [build_snapshot_attempt](../../app/services/monitoring_pipeline.py#L411) → [compare_accepted_snapshots](../../app/services/monitoring_pipeline.py#L479) → [publication](../../app/services/monitoring_pipeline.py#L493)

## 1 · Acquisition (deterministic)

Three wrappers, outermost first: freshness reuse → completeness gate → the fetch itself. The wrapping is in [runtime.py](../../app/runtime.py#L278).

| What | Where |
|---|---|
| Reuse a fetch younger than `ACQUISITION_FRESHNESS_HOURS` | [FreshnessGatedAcquisitionService](../../app/services/acquisition_freshness.py#L28) |
| Fail a sharp drop compared with the last good fetch | [CompletenessGatedAcquisitionService](../../app/services/acquisition_completeness.py#L52), [compare_inventory](../../app/services/acquisition_completeness.py#L23) |
| Main fetch: HTML, browser render, linked PDFs | [AcquisitionService.acquire](../../app/services/acquisition.py#L109) |
| Minimum-content floor | [completeness_floor_failures](../../app/services/acquisition.py#L58) |
| Static HTML fetch (redirects checked hop by hop) | [HtmlRetriever.retrieve](../../app/services/html_retriever.py#L82) |
| Playwright render (blocks forms, cross-domain, downloads) | [PlaywrightBrowserRenderer](../../app/services/browser_renderer.py#L256) |
| HTML → blocks, tables, links, FAQ | [HtmlArtifactParser.parse](../../app/services/html_parser.py#L138) |
| PDF download (allowlist, size, MIME, `%PDF-` signature, retries) | [PdfDownloader.download](../../app/services/pdf_downloader.py#L121) |
| Content-addressed file storage | [FileSystemArtifactStore](../../app/services/artifact_store.py#L17) |
| Output model | [PageArtifact](../../app/domain/acquisition.py#L228) |

## 2 · PDF admission and link selection

| What | Where |
|---|---|
| Rule-based admission from link text (irrelevant / historical → skipped, no model call) | [assess_pdf_metadata](../../app/services/pdf_admission.py#L100), term lists [_RELEVANT_TERMS](../../app/services/pdf_admission.py#L17), [_HISTORICAL_TERMS](../../app/services/pdf_admission.py#L30), [_IRRELEVANT_TERMS](../../app/services/pdf_admission.py#L39) |
| Text-layer probe per page (routes scanned pages to OCR) | [probe_pdf_input](../../app/services/pdf_input_probe.py#L10) |
| Gemini: which admitted PDFs belong to this offering | [PdfLinkSelectionService.select](../../app/services/pdf_link_selection.py#L184), prompt [PDF_LINK_INSTRUCTION](../../app/services/pdf_link_selection.py#L46) |
| Labels that are transcribed | [TRANSCRIBED_LINK_LABELS](../../app/domain/pdf_extraction.py#L69) |

## 3 · Normalization (+ PDF transcription, OCR)

| What | Where |
|---|---|
| Service: artifact → `NormalizedSourceBundle` | [StructuralNormalizationService.normalize](../../app/services/normalization.py#L126) |
| HTML table reconstruction (rowspan/colspan, headers, notes) | [normalize_table_with_report](../../app/services/table_normalizer.py#L54) |
| Text blocks | [normalize_block](../../app/services/block_normalizer.py#L14) |
| Numbers, money, %, dates found in text | [extract_scalar_candidates](../../app/services/scalar_normalizer.py#L117), text helpers [normalize_money_text](../../app/domain/normalization.py#L42), [normalize_percentage](../../app/domain/normalization.py#L46) |
| Structure check against a per-page baseline | [score_page](../../app/services/normalization_baseline.py#L110), data [normalization_baseline.json](../../app/config/normalization_baseline.json) |
| Warning codes | [NormalizationWarningCode](../../app/domain/normalization.py#L77) |
| Output model | [NormalizedSourceBundle](../../app/domain/normalization.py#L238) |

**PDF path** (Gemini reads the PDF bytes; OCR is the fallback):

| What | Where |
|---|---|
| Orchestration, cache, fallback decisions | [GeminiPdfExtractionService.extract](../../app/services/pdf_extraction.py#L456) |
| Gemini transcription prompt | [PDF_EXTRACTION_INSTRUCTION](../../app/services/gemini_pdf_extractor.py#L38), agent [AdkGeminiPdfExtractor](../../app/services/gemini_pdf_extractor.py#L54) |
| Which pages need OCR (no text layer and no model output) | [_pages_needing_ocr](../../app/services/pdf_extraction.py#L230) |
| OCR fill-in / OCR-only when every model failed | [_apply_ocr](../../app/services/pdf_extraction.py#L355), [_ocr_only](../../app/services/pdf_extraction.py#L383) |
| Rasterize page → PNG | [PdfiumPageRasterizer](../../app/services/pdf_rasterizer.py#L60) |
| Tesseract (confidence floor, timeout) | [TesseractOcrTranscriber.transcribe](../../app/services/ocr_transcriber.py#L109) |
| OCR marker that later forces review | [OCR_SOURCE_ITEM_MARKER](../../app/domain/pdf_extraction.py#L158), [is_ocr_source_item](../../app/domain/pdf_extraction.py#L165) |

## 4 · Source discovery (which content belongs to this offering)

| What | Where |
|---|---|
| Service (rules → cache → Gemini on the rest) | [SourceDiscoveryService.discover](../../app/services/source_discovery.py#L313) |
| Model fallback chain | [FallbackSourceDiscoveryService](../../app/services/source_discovery.py#L422) |
| Split the bundle into classification units | [build_discovery_candidates](../../app/services/discovery_prefilter.py#L70) |
| Deterministic rules (decided with no model) | [_rule_assessment](../../app/services/source_discovery.py#L500) |
| Classifier prompt | [SOURCE_DISCOVERY_INSTRUCTION](../../app/services/discovery_classifier.py#L27) |
| Generic strict-JSON ADK classifier (retries, parsing) | [StructuredAdkClassifier](../../app/services/discovery_classifier.py#L117) |
| Offering context sent to the model | [offering_context_for](../../app/services/source_discovery.py#L66), [OfferingContext](../../app/domain/source_discovery.py#L223) |
| Labels: association, role, authority, temporal | [ProductAssociation](../../app/domain/source_discovery.py#L28), [InformationRole](../../app/domain/source_discovery.py#L38), [Authority](../../app/domain/source_discovery.py#L60), [TemporalStatus](../../app/domain/source_discovery.py#L69) |
| What counts as "selected" | [is_selected_assessment](../../app/services/source_selection.py#L19), [build_selected_source_bundle](../../app/services/source_selection.py#L71) |

## 5 · Semantic extraction (Gemini, evidence-bound; Python validates)

| What | Where |
|---|---|
| Evidence catalog (each row/block gets a stable evidence id) | [build_evidence_catalog](../../app/services/extraction_evidence.py#L29), table row rendering [render_row](../../app/services/extraction_evidence.py#L192) |
| Fields per offering category | [CATEGORY_FIELDS](../../app/services/extraction_planner.py#L115), [_PRODUCT_FIELDS](../../app/services/extraction_planner.py#L52) |
| Fields grouped into 3 calls (full mode) | [FULL_MODE_CALLS](../../app/services/extraction_planner.py#L80), [build_extraction_batches](../../app/services/extraction_planner.py#L143) |
| Keyword terms per field (used for budgeted mode and checks) | [FIELD_TERMS](../../app/domain/extraction_terms.py#L22) |
| Prompt | [SEMANTIC_EXTRACTION_INSTRUCTION](../../app/services/semantic_extraction.py#L92), [build_extraction_prompt](../../app/services/semantic_extraction.py#L1174), [render_evidence_packet](../../app/services/semantic_extraction.py#L1223) |
| The ADK call | [AdkSemanticExtractor](../../app/services/semantic_extraction.py#L317) |
| Service (plan, cache, call, validate, repair, assemble) | [SemanticExtractionService.extract](../../app/services/semantic_extraction.py#L621) |
| Cache key = exact prompt + model | [prompt_fingerprint](../../app/services/semantic_extraction.py#L603) |
| Parse the JSON reply | [parse_batch_response](../../app/services/semantic_extraction.py#L2647) |
| Reshape known serialization variants (no guessing) | [normalize_extraction_field_value](../../app/services/semantic_extraction.py#L1341) |
| **Validation**: evidence ids, quotes, numbers in quotes, conditions | [_validate_individual_fields](../../app/services/semantic_extraction.py#L2252), [_validate_field_result](../../app/services/semantic_extraction.py#L2379) |
| Quote must occur in cited evidence | [source_span](../../app/services/semantic_extraction.py#L1851) |
| Numbers must appear in the quote | [_value_numbers](../../app/services/semantic_extraction.py#L1884), [_quote_numbers](../../app/services/semantic_extraction.py#L1909) |
| Suspicious omissions | [_validate_semantic_completeness](../../app/services/semantic_extraction.py#L2049) |
| One-field bounded repair call | [_repair_batch](../../app/services/semantic_extraction.py#L1944), cap `SEMANTIC_EXTRACTION_MAX_REPAIRS_PER_RUN` |
| Pydantic type per field | [_field_adapter](../../app/services/semantic_extraction.py#L2440) |
| Build the final product from valid fields | [assemble_loan_product](../../app/services/semantic_extraction.py#L2760) |
| Invalid field → review item | [_review_item](../../app/services/semantic_extraction.py#L2500) |
| Model fallback chain | [FallbackSemanticExtractionService](../../app/services/semantic_extraction.py#L2994) |

Extraction schema ([app/domain/semantic_extraction.py](../../app/domain/semantic_extraction.py)): [ExtractionField](../../app/domain/semantic_extraction.py#L444) (field names), [LoanProduct](../../app/domain/semantic_extraction.py#L419) (the whole product), [ExtractedValue](../../app/domain/semantic_extraction.py#L361) (value + status + evidence), [ExtractionStatus](../../app/domain/semantic_extraction.py#L40) (incl. not found), value types [Rate](../../app/domain/semantic_extraction.py#L228), [MoneyRange](../../app/domain/semantic_extraction.py#L162), [TermRange](../../app/domain/semantic_extraction.py#L270), [LoanFee](../../app/domain/semantic_extraction.py#L250), [Condition](../../app/domain/semantic_extraction.py#L133), [ConditionDimension](../../app/domain/semantic_extraction.py#L81), per-category details [ConsumerLoanDetails](../../app/domain/semantic_extraction.py#L380) · [MortgageDetails](../../app/domain/semantic_extraction.py#L387) · [OverdraftDetails](../../app/domain/semantic_extraction.py#L398) · [CreditLineDetails](../../app/domain/semantic_extraction.py#L406).

## Caches (why a rerun costs $0)

| Cache | Key | Repository |
|---|---|---|
| PDF transcription | source hash, schema/prompt version, model, probe | [PostgresPdfExtractionRepository](../../app/repositories/pdf_extraction.py#L46) |
| PDF link choice | offering + link-metadata fingerprint | [PostgresPdfLinkSelectionRepository](../../app/repositories/pdf_link_selection.py#L49) |
| Source discovery | content fingerprint, policy/prompt version, model | [PostgresSourceDiscoveryRepository](../../app/repositories/source_discovery.py#L71) |
| Extraction batch | [prompt_fingerprint](../../app/services/semantic_extraction.py#L603) | [PostgresSemanticExtractionRepository](../../app/repositories/semantic_extraction.py#L54) |

The PDF and discovery caches key on a **version string**. After editing those prompts, bump `PDF_EXTRACTION_PROMPT_VERSION` or `SOURCE_DISCOVERY_PROMPT_VERSION`. Otherwise the old answers are reused. The extraction cache keys on the prompt text itself, so it invalidates on its own.

## Failures

| What | Where |
|---|---|
| Exception → stable failure code | [source_failure_code](../../app/services/failure_mapping.py#L49) |
| Human explanation per code | [_FAILURE_EXPLANATIONS](../../app/services/failure_mapping.py#L152), [explain_failure_code](../../app/services/failure_mapping.py#L234) |
| Code enums | [RunFailureCode](../../app/domain/monitoring.py#L78), [OfferingFailureCode](../../app/domain/monitoring.py#L113), [SourceFailureCode](../../app/domain/monitoring.py#L122) |
| Acquisition / download error kinds | [HtmlRetrievalFailure](../../app/services/html_retriever.py#L25), [PdfDownloadFailure](../../app/services/pdf_downloader.py#L28), [BrowserRenderingFailure](../../app/services/browser_renderer.py#L12) |

## Audit trail

Each offering run writes Markdown overlays to `artifacts/pipeline-audit/run_<run_id>/<offering_id>/`, for example `2_normalization_diff.md`, `3_source_selection_diff.md` and `4_extraction_evidence.md`.
Writer: [FileSystemPipelineAuditArchive](../../app/services/pipeline_audit_archive.py#L89). Renderers: [pipeline_audit.py](../../app/services/pipeline_audit.py#L287). Turn it off with `PIPELINE_AUDIT_ENABLED=false`.
