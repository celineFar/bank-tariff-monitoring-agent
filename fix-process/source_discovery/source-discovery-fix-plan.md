# Source discovery: problem report and fix plan

Date: 2026-09-26 · Branch: `fix/source-discovery` (from `integration/process-fixes` at `f5c4e44`) ·
Status: **in progress** (see the phase notes). Decisions Q1–Q6 are made. The hand labels wait
for the user's confirmation.

## Scope

Source discovery decides which parts of a normalized bundle are about the offering being
monitored, and in what role. It runs between normalization and semantic extraction:

- candidates and their context ([discovery_prefilter.py](../../app/services/discovery_prefilter.py));
- rules, cache, batching, inheritance and the extraction context
  ([source_discovery.py](../../app/services/source_discovery.py));
- the Gemini classifier ([discovery_classifier.py](../../app/services/discovery_classifier.py));
- the assessment cache ([repositories/source_discovery.py](../../app/repositories/source_discovery.py));
- how the result is used: extraction's selection
  ([source_selection.py](../../app/services/source_selection.py)) and the RAG projection
  ([knowledge_projection.py](../../app/services/knowledge_projection.py)).

PDF *admission* (the keyword and date check before transcription,
[pdf_admission.py](../../app/services/pdf_admission.py)) belongs to normalization. It is in this
plan only where discovery trusts its result (SD2, SD4).

**Out of scope** (Q3): merging duplicate evidence before extraction, and removing duplicate
chunks across documents in the RAG index. They get their own plan.

## How this was checked

- **Code.** Read on `integration/process-fixes` at `f5c4e44`, after the normalization fix.
- **Probe.** [survey/probe_discovery.py](survey/probe_discovery.py) runs today's candidate
  builder, rules and batcher on the 13 captured seed pages
  (`fix-process/normalization/.cache-live-2`, the normalization fix's last live capture), replays PDF admission against the 91 hand-labelled PDFs
  (`fix-process/normalization/data/seed-pdf-labels.json`), and compares % values between each
  current PDF and its page. No Gemini call. Output before any fix:
  [data/probe-output-before.txt](data/probe-output-before.txt). Run it with
  `uv run python fix-process/source_discovery/survey/probe_discovery.py`.
- **Gemini baseline.** Phase 0 ran today's discovery with `gemini-3.1-flash-lite` on the 13
  seeds and scored it against hand labels ([data/discovery-check-before.json](data/discovery-check-before.json));
  that run found SD18.

"Confirmed" means the probe shows it on the seed data. "Code" means it was reasoned from the
code and not reproduced.

---

## Summary

| ID | Problem | Severity | Evidence | Status |
|---|---|---|---|---|
| SD1 | Gemini is never told which offering it is classifying; the cache is shared across offerings | **critical** | code + confirmed | proposed |
| SD2 | PDFs are chosen by keyword, not Gemini, and all become the offering's top-precedence terms | **critical** | confirmed | decided (Q1) |
| SD3 | Section members inherit a label from text Gemini never saw | **high** | confirmed | decided (Q5, Q6) |
| SD4 | Skipped and failed PDFs are sent to Gemini as empty documents | **high** | code | proposed |
| SD5 | Cached date judgements never expire | **high** | code | proposed |
| SD6 | One bad batch fails the offering and throws away the good batches | **high** | code | proposed |
| SD7 | Extraction and the RAG index select sources differently | **high** | code | decided (Q3) |
| SD8 | No fallback model is configured | medium | config | decided (Q2) |
| SD9 | Site header and footer are recognised by English words; footer blocks join the last content section | medium | confirmed | proposed |
| SD10 | Inserting one block changes every section's fingerprint | medium | code | proposed |
| SD11 | The "prior assessment" hint can come from a different section | medium | confirmed | proposed |
| SD12 | A PDF's tables are cut off before Gemini sees them | medium | code | proposed |
| SD13 | Retries stack: up to 9 calls per batch | low | code | proposed |
| SD14 | Temperature 0 is skipped for two hard-coded model names | low | code | proposed |
| SD15 | The HTML-template and API-payload rules are dead code | low | code | proposed |
| SD16 | Candidates are built twice per run | low | code | proposed |
| SD17 | The 12,000-character context cap | low | confirmed | proposed |
| SD18 | Gemini marks undated content `possibly_stale`, which drops the page's own tariff table | **critical** | confirmed (Phase 0) | proposed |

---

## SD1. Gemini is never told which offering it is classifying

**Where.** [source_discovery.py:471-515](../../app/services/source_discovery.py#L471-L515)
(`_build_batches`), [domain/source_discovery.py:377](../../app/domain/source_discovery.py#L377)
(`DiscoveryBatch`), [repositories/source_discovery.py:140](../../app/repositories/source_discovery.py#L140)
(cache key), [monitoring_pipeline.py:245](../../app/services/monitoring_pipeline.py#L245).

**What happens.**
- `DiscoveryBatch` holds `id`, `product` (consumer loan or mortgage) and the items. No offering
  name, no page URL, no page title.
- The classifier must still choose between `current_product` and `related_product`. That label
  matters downstream: extraction rejects a value supported only by related-product evidence
  ([semantic_extraction.py:1373](../../app/services/semantic_extraction.py#L1373)) and the
  planner weights related evidence −14 ([extraction_planner.py:409](../../app/services/extraction_planner.py#L409)).
- The cache key is product type + versions + model + content fingerprint. So an answer given
  for one mortgage offering is reused for every other mortgage offering that shows the same
  content (a shared PDF, for example).

**Confirmed on the seeds.** The mortgage_primary, construction, renovation and secondary-market
pages each carry a 12,000-character "Express Home Mortgage Loan (Purchase, Construction and
Renovation)" table. Several pages carry cross-sell sections titled "Construction loan",
"Renovation loan" or "Mortgage from secondary market". Knowing only "mortgage", the classifier
cannot tell these belong to other offerings.

**Fix.**
- Add an `OfferingContext` to the batch: `offering_id`, `display_name`, the catalog's localized
  names, `seed_url`, and the page's title. The catalog entry is already in the pipeline
  (`offering`); `discover()` takes it instead of the bare product type.
- Rewrite the instruction around it: `current_product` means *this* offering;
  `related_product` means another Ameria product or a variant this offering does not cover;
  shared material (a fee schedule for all loans) is `generic_bank_information` or
  `current_product` with a condition, as the item says.
- Add `offering_id` to both cache lookups (exact and structural). Migration `019` adds the
  column and replaces the unique constraint and the structural index.
- Bump `policy_version` and `prompt_version` to `2`, so no old answer is reused.

## SD2. PDFs are chosen by keyword, not Gemini

**Where.** [pdf_admission.py:132](../../app/services/pdf_admission.py#L132),
[source_discovery.py:342-384](../../app/services/source_discovery.py#L342-L384).

**What happens.**
- Admission marks a PDF `relevant` if its name, link text, heading, nearby text or URL contains
  any of `loan`, `mortgage`, `credit`, `fee`, `tariff`, `վարկ`, …. On a loan page, almost every
  PDF does.
- Discovery then turns every `relevant` admission into an assessment by rule, without looking at
  content: `current_product`, authority `official_terms`, precedence 1. That outranks the page's
  own tariff tables.

**Confirmed.** Of the 55 non-historical PDF links on the 13 seeds, **52 are decided by this
rule and 3 reach Gemini**. The rule's 52 include:
- `web-info-eng.pdf` (the website's profile terms; hand-labelled irrelevant), twice;
- `insured-properties.pdf` (a list of property addresses), on 6 mortgage pages;
- `mortgage_personal_express_eng.pdf` (Express mortgage terms) on the primary, construction,
  renovation and secondary-market pages.

Whether the campaign and flexible-mortgage terms belong to the offerings that link them is for
the Phase 0 labels to settle.

**How much of a PDF repeats the page** (% values only; fees in amounts were not compared):

| Seed | PDF | % values in PDF | also on page | only in PDF |
|---|---|---|---|---|
| consumer_standard | Terms of consumer loans | 11 | 11 | 0 |
| consumer_standard | Information leaflet | 15 | 12 | 3 |
| mortgage_primary | Terms, primary market | 31 | 30 | 1 |
| mortgage_primary | Express mortgage terms (sibling) | 15 | 15 | 0 |
| overdraft | Lending terms | 10 | 10 | 0 |
| overdraft | Informational summary | 14 | 11 | 3 |

So the product's own terms PDF mostly repeats the page; the information leaflet adds a few
values; the sibling's terms repeat the sibling's table that the page also shows. Roughly 2–3
PDFs per offering matter, not one and not all.

**Fix (Q1: by title first).**
- Keep deterministic admission as it is: date-based skipping of old editions (the 114-case gate
  from the normalization fix) and the off-topic skip.
- New Gemini step, **PDF link selection**, part of source discovery, run *before*
  transcription. One call per offering, with the `OfferingContext` (SD1) and, for each admitted
  link: document name, link text, link title, heading path, nearby text, file name, and the
  admission's dates. Answer per link:
  `current_product` · `shared_terms` (applies to this offering among others: the loan fee
  schedule, the floating-rate procedure) · `related_product` · `generic_bank_information` ·
  `unclear`, with a role and a reason.
- Normalization transcribes only `current_product`, `shared_terms` and `unclear`. The others
  become empty documents with a new warning `PDF_SKIPPED_NOT_SELECTED`, so the run report
  shows them.
- Discovery turns the selection into the PDF's assessment by rule (new
  `DecisionSource.LINK_SELECTION`). An `unclear` PDF is transcribed and classified on its
  content (SD12 context).
- Normalization stays deterministic: it receives the selection as input. The pipeline order
  becomes acquisition → PDF link selection → normalization → discovery → extraction.
- Cache the selection by `offering_id` + link-metadata fingerprint + versions + model.
- Update AGENTS.md (the "PDF admission deterministic" line gains: "Gemini selects which
  admitted PDFs belong to the offering, from link metadata, before transcription"),
  `docs/architecture.md` and `docs/source-discovery.md`.

## SD3. Section members inherit a label from text Gemini never saw

**Where.** [source_discovery.py:533-565](../../app/services/source_discovery.py#L533-L565)
(`_inherited_assessments`), [source_discovery.py:481](../../app/services/source_discovery.py#L481)
(cut to `max_chars_per_item`), [discovery_prefilter.py:299-316](../../app/services/discovery_prefilter.py#L299-L316).

**What happens.**
- A page section (blocks under one heading and parent) gets one assessment. Every member block
  copies it (`decision_source=inherited`).
- The section's text is ranked by tariff words, capped at 12,000 characters, then cut to 3,000
  for the prompt. Members past the cut are labelled without Gemini seeing them.
- Tables are one item; their text is cut the same way, so the classifier sees the header and
  the first rows only.

**Confirmed.** On every seed, 1–5 Gemini items are cut. Examples: "Terms and conditions" on
consumer_standard (11,770 chars → 3,000), five 12,000-char tariff tables on
mortgage_construction and mortgage_renovation.

**Fix (Q5: one call per group, with exceptions; Q6: PDFs inherit).**
- A section item lists every member: `{member_id, text}`. The response gains
  `member_exceptions: [{member_id, relevance, product_association, role, reason}]` for members
  that differ from the section (a cross-sell card under "Terms", for example).
- A section too long for one item is **split** into consecutive parts, never cut. Each part is
  its own item with the same heading and "part i of n". Every member is labelled by the item
  that showed its text.
- A table item shows the title, headers, the first cell of **every** row, then as many full rows
  as fit.
- Members without an exception keep `decision_source=inherited`, now with the guarantee that
  their text was in the prompt. Exceptions are recorded as `llm`.
- Validation: every exception's `member_id` must belong to the item, else the response is
  invalid (SD6).
- PDF blocks and tables inherit the PDF-level decision (from SD2 or the content check). A PDF
  covering several variants is left to extraction's variant-scope check.
- Expected cost: about +30% items per page (the split parts). At `gemini-3.1-flash-lite`
  prices this is under $0.01 per page.

## SD4. Skipped and failed PDFs are sent to Gemini as empty documents

**Where.** [pdf_extraction.py:473-478](../../app/services/pdf_extraction.py#L473-L478),
[pdf_extraction.py:875](../../app/services/pdf_extraction.py#L875),
[discovery_prefilter.py:205-206](../../app/services/discovery_prefilter.py#L205-L206),
[source_selection.py:46-51](../../app/services/source_selection.py#L46-L51).

**What happens.**
- A PDF skipped before transcription, or one whose transcription failed, becomes a document with
  no blocks.
- Discovery has a rule only for `relevant` admissions and for all-hidden members. An
  `irrelevant` or `ambiguous` PDF with no content goes to Gemini as
  "Document has no extracted text. URL: …".
- If Gemini answers `possibly_relevant`, the empty document is kept for extraction.

**Fix.** A rule for every PDF document with no content, no Gemini call:
- skipped as historical → `historical_version`, `possibly_stale`;
- skipped as irrelevant → `irrelevant`;
- not selected (SD2) → the selection's labels;
- transcription failed → `irrelevant` with the failure as reason. The normalization warning
  already reports it.

## SD5. Cached date judgements never expire

**Where.** [source_discovery.py:166-189](../../app/services/source_discovery.py#L166-L189),
[pdf_admission.py:195-215](../../app/services/pdf_admission.py#L195-L215).

**What happens.**
- The exact-cache key is the content fingerprint. Gemini's `temporal_status` was judged on the
  day it ran.
- A campaign section saying "valid until 31.10.2026" stays `current` on 1 November, because its
  text has not changed.
- PDFs are not affected: admission is recomputed every run with `as_of`, and it is part of the
  PDF fingerprint.

**Fix.**
- Move `_temporal_status` out of `pdf_admission.py` into a shared function
  `temporal_status_at(periods, as_of)`.
- Apply it to every Gemini assessment, fresh or cached, whose effective periods have dates. The
  model's own status stands only when there are no dated periods.
- `as_of` is the artifact's `retrieved_at` date, passed to `discover()`.

## SD6. One bad batch fails the offering and throws away the good batches

**Where.** [source_discovery.py:240-270](../../app/services/source_discovery.py#L240-L270),
[discovery_classifier.py:107-127](../../app/services/discovery_classifier.py#L107-L127),
[discovery_classifier.py:197-204](../../app/services/discovery_classifier.py#L197-L204).

**What happens.**
- A response that is not valid JSON, fails validation, or has the wrong IDs raises a
  `ValueError` or `ValidationError`. Only `APIError` is retried or passed to a fallback model, so
  one bad answer fails the offering.
- Answers are saved only after every batch succeeds. When batch 4 of 4 fails, batches 1–3 are
  paid for again on the next run.
- Batches run one after another.

**The batch limits themselves are fine.** 14–32 Gemini items per page make 2–4 batches. The
18,000-character batch limit binds before the 8-item limit. No change to the limits.

**Fix.**
- Save each valid batch as soon as it is checked.
- On an invalid response: retry the batch once; then split it in halves, down to single items.
  A single item that is invalid twice raises `DiscoveryResponseError`, which counts as a
  fallback error, so the next model gets a turn.
- Run batches concurrently, `max_concurrent_batches` (new setting, default 3). Results are
  put back in batch order, so the output does not depend on timing.
- Count retries and splits in the classifier usage, for the run report.

## SD7. Extraction and the RAG index select sources differently

**Where.** [source_selection.py:18-77](../../app/services/source_selection.py#L18-L77),
[source_discovery.py:582-633](../../app/services/source_discovery.py#L582-L633),
[monitoring_pipeline.py:312-321](../../app/services/monitoring_pipeline.py#L312-L321),
[knowledge_projection.py:44-73](../../app/services/knowledge_projection.py#L44-L73),
[rag_retrieval.py:213](../../app/services/rag_retrieval.py#L213).

**What happens.**
- Extraction selects per block and table, from direct and inherited assessments
  (`build_selected_source_bundle`).
- The RAG projection selects whole documents, from `extraction_context` (direct assessments
  only), then indexes **every** block of each selected document from the full bundle. The
  product page is always selected, so its menu, cross-sell cards and sibling-product tables are
  indexed under the offering.
- Chunks carry no discovery labels, so retrieval cannot rank related or old content lower.
- The precedence function is copied in both files. `ExtractionContextItem.text` (up to 12,000
  characters per item) is built and never read; only `document_id` is used.

The default answer path (`structured`) reads only snapshot facts and is not affected. The
source-chunk index feeds the `legacy` path and is re-embedded every run.

**Fix (Q3: the selection bug and chunk labels only).**
- One selection function, `select_sources(discovery) → SourceSelection` (document IDs, and item
  IDs per document). Extraction and projection both use it.
- The projection indexes the **selected** bundle, not the full one.
- Each chunk's metadata gains the best assessment of its source items: product association,
  temporal status, authority, precedence.
- The legacy retriever leaves out chunks labelled related product, navigation, historical or
  future.
- Keep one precedence function. Replace `ExtractionContext` with `SourceSelection`; drop the
  12,000-character text copy.

## SD8. No fallback model is configured

**Where.** [config/models.py:346](../../app/config/models.py#L346),
[.env.example:81](../../.env.example#L81), [runtime.py:161-195](../../app/runtime.py#L161-L195).

**What happens.** `fallback_model_names = ()`. A persistent 429 or a retired model fails the
offering after the retries.

**Fix (Q2).** Default `fallback_model_names = ("gemini-2.5-flash-lite",)` in
`SourceDiscoverySettings` and in `.env.example`. It is $0.10 in / $0.40 out, inside the $1.50
cap, and has its own quota. A startup test checks that the chain passes the price cap.
PDF extraction and semantic extraction also have no fallback; that is noted, not changed here.

## SD9. Site header and footer are recognised by English words

**Where.** [discovery_prefilter.py:88-98](../../app/services/discovery_prefilter.py#L88-L98),
[source_discovery.py:453-468](../../app/services/source_discovery.py#L453-L468),
[html_parser.py:283](../../app/services/html_parser.py#L283).

**What happens.**
- All unheaded list blocks on a page form one group, `<root-navigation-lists>`. The group is
  navigation if its text contains at least 4 of 9 English words ("personal", "loans", …).
- An unheaded list of product terms anywhere on the page would join the menu group and be
  dropped with it.
- The parser already knows which blocks are site chrome (inside `nav`, `header`, `footer`, or a
  navigation role), but that fact is not passed on to normalized blocks.

**Confirmed.**
- On all 13 seeds, the group is the 15 header-menu blocks, none has a number, and the rule
  fires. So nothing is lost today.
- Every seed sends **4 Gemini items that contain site-chrome blocks** (52 across the seeds, on
  the current capture): single unheaded header paragraphs, and footer blocks such as
  "HEAD OFFICE".
- **Footer blocks join a content section.** They inherit a heading path, so they share that
  section's group. On the current capture the whole footer (about 30 blocks from "Dear User,"
  onward) sits under the page's top heading and is classified with the page's opening section.
  In the Phase 0 Gemini baseline those ~30 blocks per page came back `current` (386 blocks in
  all). On the older capture the footer sat under the last cross-sell card instead (on
  mortgage_primary, 13 content blocks and 12 footer blocks as one "Construction loan" item).
- Some unheaded header blocks (language switch, "IR", "About Bank", phone, "Branches") are
  outside the semantic chrome elements. They sit before the page's first main heading.

**Fix.**
- Carry the parser's chrome flag: `ContentBlock.site_chrome` → `NormalizedBlock.site_chrome`
  (default `False`, so stored artifacts still load).
- Site-chrome blocks never share a group with content blocks: `site_chrome` is part of the
  grouping key.
- Rule: a group whose members are all site chrome is `global_navigation`, `irrelevant`. No
  Gemini call.
- Rule: unheaded blocks before the first main-content heading form one "page header" group,
  decided the same way.
- Every other unheaded block, lists included, is its own item and goes to Gemini.
- Remove the English word list.
- Check in Phase 1 that the new field does not change the acquisition content hash or page
  identity (acquisition reuse depends on them).

## SD10. Inserting one block changes every section's fingerprint

**Where.** [discovery_prefilter.py:141-151](../../app/services/discovery_prefilter.py#L141-L151),
[discovery_prefilter.py:97](../../app/services/discovery_prefilter.py#L97),
[html_parser.py:278](../../app/services/html_parser.py#L278).

**What happens.** A section's content fingerprint includes its block IDs, and page block IDs are
positional (`b1`, `b2`, …). One new block near the top renumbers every later block, so every
section misses the cache and is classified again. Unheaded root groups are keyed by block ID
too. Normalization made PDF document IDs content-addressed for this same reason.

**Fix.** Fingerprint sections by content only: text, markdown, fields, visibility, and link
URLs (not link IDs). Key unheaded root groups by a hash of their text. Two identical unheaded
paragraphs then share one group, which is correct.

## SD11. The "prior assessment" hint can come from a different section

**Where.** [discovery_prefilter.py:268-275](../../app/services/discovery_prefilter.py#L268-L275),
[repositories/source_discovery.py:198-234](../../app/repositories/source_discovery.py#L198-L234).

**What happens.** The structural fingerprint is URL + heading path + title + scope + type. It
leaves out the parent, which is part of the grouping key. Different sections then share one
fingerprint, and the prior for one comes from whichever was saved last.

**Confirmed.** consumer_standard has 12 "Terms and conditions" sections with one fingerprint;
overdraft 12; credit_line 11; mortgage_diaspora 8 "Frequently asked questions". On every seed
the menu group and one unheaded block share "Unheaded page content", so a real paragraph can be
sent the menu's "navigation, irrelevant" as its prior.

**Fix.** Add the parent's text (the accordion or card title) to the structural fingerprint. If
two candidates on the same page still share one, send neither a prior.

## SD12. A PDF's tables are cut off before Gemini sees them

**Where.** [discovery_prefilter.py:189-206](../../app/services/discovery_prefilter.py#L189-L206).

**What happens.** A PDF document's context is its blocks (ranked, up to 12,000 characters) with
its tables added after, then cut to 12,000, then to 3,000 for the prompt. A long PDF's tables,
where tariffs usually are, never reach the classifier. After SD2, this context is used for
`unclear` PDFs.

**Fix.** Build PDF context in document order: the title and first page's text, then each table
as title + headers + row labels (as in SD3), within the item budget.

## SD13. Retries stack: up to 9 calls per batch

**Where.** [discovery_classifier.py:76](../../app/services/discovery_classifier.py#L76),
[discovery_classifier.py:107-127](../../app/services/discovery_classifier.py#L107-L127).

**What happens.** The SDK retries 3 times inside each of the classifier's 3 attempts. A 429 can
cost 9 calls per batch before the fallback model is tried.

**Fix.** SDK `HttpRetryOptions(attempts=1)` for this classifier. The application loop keeps
its backoff, jitter and logging. At most 3 calls per batch per model.

## SD14. Temperature 0 is skipped for two hard-coded model names

**Where.** [discovery_classifier.py:80-95](../../app/services/discovery_classifier.py#L80-L95).

**What happens.** `gemini-3.8-flash` and `gemini-3.5-flash-lite` run without `temperature=0`;
every other model runs with it. The reason is not recorded (the line came in `f837030`, a
price-cap commit). With Q2's chain (3.1-flash-lite, then 2.5-flash-lite) both models run at 0,
so behaviour does not change today.

**Fix.** Move the list to the model registry in
[model_pricing.py](../../app/services/model_pricing.py) as a per-model flag with a comment, so
a new model states it once. Log the temperature used in the classifier usage.

## SD15. The HTML-template and API-payload rules are dead code

**Where.** [source_discovery.py:406-416](../../app/services/source_discovery.py#L406-L416),
[source_discovery.py:446-450](../../app/services/source_discovery.py#L446-L450),
[discovery_prefilter.py:190-194](../../app/services/discovery_prefilter.py#L190-L194).

**What happens.** Normalization builds one page document plus PDFs; it never builds a
`SourceType.API` document (network payloads were removed everywhere in normalization Q1). The
`/contentthemes/` rule and the `API_PAYLOAD` branches cannot run, so whether the rule is too
permissive does not matter.

**Fix.** Delete the rule and the branches. Keep the `API_PAYLOAD` enum value, so old cache rows
still load.

## SD16. Candidates are built twice per run

**Where.** [source_discovery.py:157](../../app/services/source_discovery.py#L157),
[source_discovery.py:277](../../app/services/source_discovery.py#L277).

**Fix.** `plan()` returns all candidates; `discover()` uses them.

## SD17. The 12,000-character context cap

**Where.** [discovery_prefilter.py:19](../../app/services/discovery_prefilter.py#L19).

**What the data shows.** Several tariff tables hit exactly 12,000 characters. But the prompt
only ever gets 3,000 per item, and the 12,000-character copy in `ExtractionContext` is not read.
The value itself is not the problem; the silent truncation is.

**Fix.** Covered by SD3 (split instead of cut), SD12 (PDF context) and SD7 (drop the copy).
Keep 12,000 only as a hard upper bound on a single member's text.

## SD18. Gemini marks undated content `possibly_stale`

*Found in the Phase 0 Gemini baseline.*

**Where.** [discovery_classifier.py:23-37](../../app/services/discovery_classifier.py#L23-L37)
(instruction), [source_selection.py:18-22](../../app/services/source_selection.py#L18-L22)
(`possibly_stale` is not selected).

**What happens.** The instruction says "Do not infer currentness merely from an official host",
and gives no rule for content with no date. `gemini-3.1-flash-lite` then marks undated tables
`possibly_stale`. Selection drops everything `possibly_stale`.

**Confirmed, but not on every capture.** On the older capture
(`fix-process/normalization/.cache`, before the normalization fix), all three mortgage_primary
tables came back `possibly_stale` with the reason "no explicit effective date is provided", in
two separate runs ([superseded/discovery-check-before-stale-capture.json](data/superseded/discovery-check-before-stale-capture.json),
[superseded/discovery-check-before-primary-rerun-stale-capture.json](data/superseded/discovery-check-before-primary-rerun-stale-capture.json)).
That excluded **"Tariffs — Home Purchase Loan (primary market)"**, the offering's own tariff
table, and the fee table. On the current capture (`.cache-live-2`) the same tables came back
`current`. So the outcome depends on small differences in the table text: nothing in the
instruction or the code prevents it.

**Fix.**
- Instruction: content on the live product page with no date is `unknown`, not
  `possibly_stale`. `possibly_stale` needs evidence in the item: a past end date, or wording
  such as "previous terms", "archive" or "valid until" a past date.
- Response: `stale_evidence`, a short quote from the item that shows it is out of date.
- Deterministic check: a `possibly_stale` answer whose `stale_evidence` is missing or not found
  in the item's text becomes `unknown`. SD5's date rule then applies to dated periods.

---

## Checked, no change needed

- **The batch limits** (8 items, 3,000 characters per item, 18,000 per batch). See SD6.
- **The navigation group on today's pages.** It holds only menu blocks on all 13 seeds. SD9
  replaces the mechanism anyway.
- **An official terms PDF outranks the page's tables.** Once SD2 selects only the offering's
  own PDFs and shared schedules, precedence 1 for them is right: they are the legal documents.
- **Related-product evidence reaches extraction.** That is by design: extraction rejects a
  value supported only by related evidence and uses it to tell variants apart. SD1 makes the
  label correct.
- **Date-based skipping of old PDF editions** stays deterministic, as the normalization fix
  validated (114 cases, no current PDF skipped).

---

## Decisions

| # | Question | Answer | Status | Affects |
|---|---|---|---|---|
| Q1 | Where should Gemini decide which PDFs belong to the offering? | **By title first**: Gemini selects from link metadata before transcription; unclear PDFs are transcribed and classified on content. AGENTS.md gains a line. | decided | SD2, SD4, SD12 |
| Q2 | Which fallback model for discovery? | **`gemini-2.5-flash-lite`**, within the current $1.50 cap. | decided | SD8 |
| Q3 | Include the RAG and evidence-merging work? | **Only the selection bug and chunk labels.** Evidence merging and cross-document chunk de-duplication get their own plan. | decided | SD7 |
| Q4 | How to validate? | **Small Gemini budget**: offline tests with a fake classifier, plus up to three real discovery passes over the 13 seeds (before, after, cache re-run), about $1 in total, checked against hand labels. | decided | Phase 0, Phase 7 |
| Q5 | How do section members go through classification? | **One call per section with exceptions**; long sections are split, never cut. | decided | SD3 |
| Q6 | Do a PDF's blocks inherit the PDF-level decision? | **Yes.** Multi-variant PDFs are left to extraction's variant-scope check. | decided | SD3 |

**One-time effects on the first production run after deploy.**
- `policy_version`/`prompt_version` go to `2` and the cache gains `offering_id`: every page is
  classified once more (about $0.25 for the 13 seeds).
- The PDF link selection is new: one call per offering, then cached.
- Fewer PDFs are transcribed (siblings and the website-profile PDF are no longer selected).
- The selected sources change, so evidence changes and every offering is extracted again.
- Values that came from sibling products before will disappear or change. That shows up as
  tariff changes and may open reviews, although the bank changed nothing.
- The source-chunk index is rebuilt from the selected bundle and re-embedded.

---

## Implementation phases

Order: labels and failing tests first; then the deterministic fixes that need no prompt change;
then the offering identity, which every Gemini change depends on; then member classification;
then PDF selection; then reliability; then the single selection path; then validation. Each
phase ends green on `uv run pytest tests/unit tests/integration`.

### Phase 0: Preparation

- [x] Create branch `fix/source-discovery` from `integration/process-fixes` (`f5c4e44`).
- [x] Write [survey/probe_discovery.py](survey/probe_discovery.py) and save
      [data/probe-output-before.txt](data/probe-output-before.txt).
- [x] Run `uv run pytest tests/unit tests/integration` and record the baseline (count, known
      failures).
- [x] **Hand labels.** For each of the 13 seeds, record in `data/seed-discovery-labels.json`:
  - [x] every page section and table: `current_product`, `related_product` (which offering),
        `generic_bank_information` or `navigation`, with a reason;
  - [x] every admitted PDF link: `current_product`, `shared_terms`, `related_product`,
        `generic_bank_information` or `irrelevant`, extending `seed-pdf-labels.json`.
- [ ] **Confirm the labels with the user.** They are the pass criteria for Phases 2–4 and 7.
- [x] Write `survey/check_discovery_labels.py`: runs discovery with a given classifier and
      compares every assessment with the labels (per seed: agree, wrong association, wrong
      relevance; PDFs selected vs labelled).
- [x] **Gemini baseline (Q4).** Run today's discovery on the 13 seeds with
      `gemini-3.1-flash-lite`, a spend guard of $0.40, and a scratch cache. Save
      `data/discovery-check-before.json`. *Spends Gemini budget.*
- [x] Add regression tests, `xfail(strict=True)`, one per confirmed or code-level bug, each
      asserting the correct behaviour:
  - [x] SD4: an empty skipped PDF gets a rule assessment, no classifier call;
  - [x] SD5: a cached assessment with period ending before `as_of` is `possibly_stale`;
  - [x] SD6: a batch with a bad response is split, and the good batches are saved;
  - [x] SD9: a group of site-chrome blocks is decided by rule; an unheaded product list is its
        own item; footer blocks under the last heading are not grouped with its content;
  - [x] SD10: inserting a block at the top leaves other sections' fingerprints unchanged;
  - [x] SD11: two sections with the same heading and different parents get different
        structural fingerprints;
  - [x] SD7: projection leaves out a block that discovery marked irrelevant;
  - [x] SD1: the batch sent to the classifier carries the offering's name and URL.
  - [x] SD18 (found in the baseline): undated content is not `possibly_stale` without evidence.

#### Phase 0 notes (2026-09-26)

**State: done, except the user's confirmation of the hand labels.** That confirmation does not
block Phase 1 (deterministic fixes); it blocks judging the Gemini results of Phases 2–4 and 7.

**Test baseline** (`uv run pytest tests/unit tests/integration`, before any fix): **914 passed,
42 skipped, 1 failed, 3 errors.** The failure and errors need a Gemini key and fail the same way
on the parent branch (`test_agent.py::test_agent_stream`; the three `test_server_e2e.py` tests).
The 42 skips are the Postgres tests, which need `TEST_DATABASE_URL` (the scratch database
`tariff_acquisition_test` on the dev container, as in the normalization fix).

**Hand labels** ([data/seed-discovery-labels.json](data/seed-discovery-labels.json)). Drafted by
Claude from the rendered pages and the existing PDF labels; **the user has not reviewed them
yet.** Choices worth checking:
- Labels are rules on heading paths, not per block. Cross-sell cards under "Terms and
  conditions" (e.g. "Construction loan" on the primary page) are `related`; calculators and
  teaser cards are `any` (not scored).
- Everything from the first "Last updated on" / "Dear User," block onward is the site footer
  (`navigation`), even where the parser did not mark it as chrome.
- On the four mortgage pages that show it, the Express table is `related`. The construction and
  renovation pages' commercial-property tables are `current`: those offerings cover both.
- PDFs: `terms_flexible_mortgage_eng.pdf` on the primary page is `related_product` (a separate
  developer programme); the refinancing campaign terms are `shared_terms`;
  `insured-properties.pdf` and `Payment_terminals_arm.pdf` are `generic_bank_information`
  (not scored).

**Label checker** ([survey/check_discovery_labels.py](survey/check_discovery_labels.py)). Scores
each page block and table: `lost` (a current item excluded or called another product), `leak`
(a related item called current or unknown, which extraction treats as the offering's own), and
`noise` (navigation kept as current). PDFs: `lost` if a current or shared PDF is not selected,
`leak` if a related or irrelevant one is. It estimates the Gemini cost before the first call and
refuses to start over the guard. It works with both the old `discover(bundle, product)` and the
new `discover(bundle, offering, as_of=…)` signature.

**Capture used.** The first baseline ran on `fix-process/normalization/.cache`, which was
captured *before* the normalization fix: its stored blocks differ from what this branch's parser
produces, so its chrome and footer labels were misaligned. It is kept in
[data/superseded/](data/superseded/) and not used. Every result below, and every later run, uses
`fix-process/normalization/.cache-live-2`, the normalization fix's last live capture, whose
stored blocks, tables and links match the parser exactly. The survey scripts re-parse each
capture's rendered HTML, so they also see `site_chrome` (Phase 1). The labels were then
re-fitted to that capture's heading paths (the normalization fix moved the cross-sell cards out
of "Terms and conditions").

**Gemini baseline** ([data/discovery-check-before.json](data/discovery-check-before.json)):
the Phase 0 code (`51fc659`, run from a separate worktree) on `.cache-live-2`,
`gemini-3.1-flash-lite`, 41 calls, 105,398 input + 40,188 output tokens, **$0.087** (estimated
$0.095). The report stores every assessment, so it can be re-scored after label changes with
`--rescore` at no cost. The Gemini key came from the sibling project's `.env`, read into the
process environment only; this repository has no `.env`.

| | Count | What it is |
|---|---|---|
| Scored page blocks and tables | 1,845 | |
| `leak` | 20 | The Express table as current on the construction, renovation, primary and secondary-market pages; sibling cross-sell cards ("Credit line", "Overdraft", "Online mortgage", "Construction loan") as current (SD1) |
| `lost` | 0 | |
| `noise` | 386 | The site footer, merged into the page's opening section and called current (SD9) |
| PDF `leak` | 8 | Express terms on 4 pages, the website-profile PDF on 3, flexible-mortgage terms on the primary page (SD2) |
| PDF `lost` | 0 | |

SD18 came from the superseded run: see its entry for the evidence and why it did not reproduce
on `.cache-live-2`.

**Regression tests.** [tests/unit/test_source_discovery_fixes.py](../../tests/unit/test_source_discovery_fixes.py)
has 10 `xfail(strict=True)` tests (SD1 ×2, SD4, SD5, SD6 ×2, SD9, SD10, SD11, SD18), and
[tests/unit/test_monitoring_pipeline.py](../../tests/unit/test_monitoring_pipeline.py) has one for
SD7. Each asserts the target behaviour and API (`OfferingContext`,
`discover(bundle, offering, as_of=…)`, `NormalizedBlock.site_chrome`, `DiscoveryResponseError`).
All 11 were checked with `--runxfail` to fail today.

**Spend so far: $0.26** of the ~$1 budget: $0.090 on the superseded capture (baseline and
the primary re-run), and two $0.087 baseline runs on `.cache-live-2` (the first did not yet store
its assessments for re-scoring).

### Phase 1: Deterministic groundwork (SD9, SD10, SD11, SD15, SD16, SD4 rules, SD12)

- [x] SD15: delete the template rule and the `API_PAYLOAD` branches; keep the enum value.
- [x] SD16: build candidates once; `plan()` carries them to `discover()`.
- [x] SD9: add `site_chrome` to `ContentBlock` and `NormalizedBlock`, set by the parser.
- [x] SD9: check that stored artifacts load and that the acquisition content hash and page
      identity are unchanged on the 13 captures.
- [x] SD9: `site_chrome` in the grouping key; rules for all-chrome groups and the page-header
      group; remove `<root-navigation-lists>` and the English word list.
- [x] SD10: content-only section fingerprints; root groups keyed by text hash.
- [x] SD11: parent text in the structural fingerprint; no prior when a fingerprint repeats on
      the page.
- [x] SD4: rules for PDF documents with no content (skipped historical, skipped irrelevant,
      failed).
- [x] SD12: PDF context in document order with compact tables.
- [x] Remove the matching `xfail` markers. Re-run the probe: 0 Gemini items with any
      site-chrome member, no shared structural fingerprints within a page.

#### Phase 1 notes (2026-09-26)

**State: done.** Commit: *Source discovery Phase 1: deterministic groundwork*.

**What changed.**
- **SD9, site chrome.** `ContentBlock.site_chrome` (set by the HTML parser from its existing
  nav/header/footer detection) is carried to `NormalizedBlock.site_chrome`. The candidate
  builder ([discovery_prefilter.py](../../app/services/discovery_prefilter.py)) now puts every
  chrome block in one "Site navigation, header and footer" group, and unheaded blocks above the
  page's first heading in one "Page header" group. Both are decided by rule
  (`global_navigation`, `irrelevant`) via the new `DiscoveryCandidate.layout`
  (`CandidateLayout`). Every other unheaded block, lists included, is its own item. The
  `<root-navigation-lists>` group and the English word rule are gone.
- **Page identity is unchanged.** `site_chrome` is left out of the page-content hash (chrome
  blocks were already excluded from it). Checked on the 13 captures: the re-parsed page hash is
  identical before and after the change, so no page id, evidence id or extraction cache key
  moves.
- **SD10.** Section fingerprints use block content (text, markdown, fields, visibility, link
  URLs), not block or link ids. Unheaded root groups are keyed by a text hash. Tables are
  fingerprinted by title, headers, row texts, sections and notes, not their positional ids
  (the plan only named sections; tables had the same problem).
- **SD11.** The parent block's text (the accordion or card title) is part of a section's
  structural fingerprint. `plan()` drops the prior for any structural fingerprint that occurs
  more than once on the page.
- **SD4.** A linked document with no blocks and no tables is decided by rule before anything
  else, with no Gemini call: superseded edition → `historical_version`/`possibly_stale`,
  off-topic admission → `irrelevant`, anything else (failed transcription) → `irrelevant` with
  the extraction method in the reason. This also stops a *relevant*-admission PDF whose
  transcription failed from being passed to extraction as an empty official document.
- **SD12.** A PDF's context is its text page by page, each page's tables shown as title,
  headers and the first cell of every row. The PDF content fingerprint now includes the
  extraction method, so an assessment of a failed transcription is never reused for a later
  successful one.
- **SD15.** The HTML-template rule and the `API_PAYLOAD` scope branch are deleted; the enum
  value stays for old cache rows. **SD16.** `discover()` reuses the candidates `plan()` built.

**Measured** ([data/probe-output-phase1.txt](data/probe-output-phase1.txt) against
[data/probe-output-before.txt](data/probe-output-before.txt), both on `.cache-live-2`):
- Gemini items with any site-chrome member: **4 per page → 0** on all 13 seeds.
- Structural fingerprints shared within a page: **1 → 0** on all 13 seeds.
- Gemini items per page: 15–33 → 12–30 (3 fewer on every seed).

**Tests.** SD10 and SD11 regression tests pass; markers removed. New direct tests for SD9
(chrome and page-header groups, footer kept apart, an unheaded product list as its own item),
SD4 (all four no-content cases) and SD12. **The SD4 and SD9 regression tests are still
`xfail`**: they call the Phase 2 signature (`discover(bundle, offering)`) and are cleared in
Phase 2. Full suite: 919 passed, 42 skipped, 9 xfailed, plus the 4 known key-dependent
failures. `ruff check` and `ruff format --check` clean.

**Remaining issues.**
- Artifacts stored before this change have `site_chrome=False` on every block. Until a page is
  acquired again, only the page-header rule applies to it, and footer blocks go to Gemini as
  before. Acquisition reuses a stored artifact only within its freshness window, so this ends
  on the next fetch of each page.
- The existing discovery tests still use an `api` document in their fixture; it is now
  assessed as a plain linked document, which is what the code does with it.

### Phase 2: Offering identity and cache scope (SD1)

- [x] Add `OfferingContext` to the domain and to `DiscoveryBatch`.
- [x] Change the discovery port to `discover(bundle, offering, *, as_of)`. Update
      `monitoring_pipeline.py`, the monitoring node path, `FallbackSourceDiscoveryService`, and
      the test doubles.
- [x] Rewrite `SOURCE_DISCOVERY_INSTRUCTION` around the offering: definitions of
      `current_product`, `related_product` and shared material, with one example of a sibling
      table.
- [x] Migration `019_source_discovery_offering_scope.sql`: add `offering_id`, replace the
      unique constraint and the structural index. Update the Postgres, file and in-memory
      repositories.
- [x] Bump `policy_version` and `prompt_version` to `2` in settings and `.env.example`.
- [x] Unit tests: the prompt carries the offering; the same content for two offerings is two
      cache entries.

#### Phase 2 notes (2026-09-26)

**State: done.** Commit: *Source discovery Phase 2: offering identity and cache scope*.

**What changed.**
- **`OfferingContext`** ([domain/source_discovery.py](../../app/domain/source_discovery.py)):
  offering id, product, display name, seed URL, page title, and up to 20 catalog names and
  aliases (English and Armenian). `OfferingContext.from_catalog_entry()` builds it from the
  catalog entry the pipeline already runs. Every `DiscoveryBatch` carries it, so the prompt
  (the batch's JSON) names the offering.
- **Signature.** `SourceDiscoveryService.plan(bundle, offering)` and
  `discover(bundle, offering, *, as_of=None)`; the same for `FallbackSourceDiscoveryService`
  and the pipeline port. The pipeline passes the page title and `artifact.retrieved_at` as
  `as_of` (used from Phase 5 on). `SourceDiscoveryPlan` and `SourceDiscoveryResult` record the
  `offering_id`.
- **Instruction** rewritten around the offering: definitions of `current_product` (including
  terms that apply to it among other loans, such as the loan fee schedule),
  `related_product` (with the Express-table example), `generic_bank_information`,
  `global_navigation`, historical/future versions and `unknown`.
- **Cache scope.** `offering_id` is part of the exact and structural cache keys in the
  Postgres, file and in-memory repositories and in the repository contract. Migration
  [019_source_discovery_offering_scope.sql](../../migrations/019_source_discovery_offering_scope.sql)
  adds the column (old rows get `''` and never match), replaces the unique constraint and the
  structural index, and is safe to apply twice.
- **Versions.** `policy_version` and `prompt_version` default to `2` (settings and
  `.env.example`). Phase 5 changes the prompt again (SD18); nothing is deployed between the
  phases, so it stays `2`.
- **Tools and demos.** `offering_context_for(bundle, product)` finds the catalog offering whose
  seed URL is the bundle's page, or names an unlisted page after itself. The two demonstration
  scripts use it.
- **Docs.** [docs/source-discovery.md](../../docs/source-discovery.md) and
  [docs/architecture.md](../../docs/architecture.md) describe the offering in the cache key and
  in every batch, and the Phase 1 rules (site chrome, page header, no-content documents,
  content-only fingerprints); the API-payload section is gone.

**Tests.** The SD1 (×2), SD4 and SD9 regression tests pass; markers removed. The old discovery,
PDF and file-cache tests now pass an offering. New Postgres test
[test_source_discovery_postgres.py](../../tests/integration/test_source_discovery_postgres.py):
the same content saved for two offerings is two entries with different associations, a third
offering sees neither, and migration 019 applies twice. Postgres tests run against the scratch
`tariff_acquisition_test` database: 37 + 1 passed. Full suite: 923 passed, 43 skipped,
5 xfailed, plus the 4 known key-dependent failures. `ruff` clean.

**Not measured yet.** No Gemini run with the offering in the prompt; Phase 7 measures it
against the labels (the baseline has 20 `leak`s, mostly sibling tables and cross-sell cards).

**Found while documenting (affects Q2).** [docs/source-discovery.md](../../docs/source-discovery.md)
records that `gemini-2.5-flash-lite` "held this slot until the provider stopped serving it to
new users on 2026-09-22". That is the fallback chosen in Q2. Phase 5 checks with one minimal
call whether this project's key can still use it; if not, the choice goes back to the user.

### Phase 3: Member classification (SD3, SD17)

- [x] Add `members` to `DiscoveryPromptItem` and `member_exceptions` to
      `ModelSourceAssessment`.
- [x] Split long sections into parts instead of cutting them; compact tables to headers + all
      row labels + full rows that fit.
- [x] Validate exceptions (member belongs to the item); apply them in
      `_inherited_assessments`.
- [x] Keep 12,000 characters only as the upper bound on one member's text (SD17).
- [x] Unit tests: every member of a 12,000-character section appears in some prompt item; an
      exception overrides inheritance; a foreign `member_id` is rejected.

#### Phase 3 notes (2026-09-26)

**State: done.** Commit: *Source discovery Phase 3: members are classified, not inherited blind*.

**What changed.**
- **Members in the prompt.** A section candidate carries `members` (member id and full text,
  12,000 characters at most per member) and `member_context` (its links). Its prompt item
  lists the members as `m1`, `m2`, … with their text; the item's `content` is then only the
  links. The instruction explains members and `member_exceptions`.
- **Split, never cut.** `build_discovery_candidates(bundle, item_chars=…)` (the service passes
  `max_chars_per_item`) splits a section whose members do not fit one item into consecutive
  parts, `…::section::<id>::part::<n>`, titled "Terms and conditions (part 2 of 5)". The part
  label is in the title, so it is in the structural fingerprint. A single member longer than
  the item budget is sent alone and whole, up to 12,000 characters (SD17). Rule-decided groups
  (site chrome, page header) are never split: they are never sent.
- **Exceptions.** `ModelSourceAssessment` and `SourceAssessment` carry `member_exceptions`
  (member id, association, role, relevance, reason). `_check_response` rejects an exception
  that names a member the item did not show, or names one twice. `_inherited_assessments`
  gives an excepted member the exception's values with `decision_source=llm` (`cache` on a
  cache hit) and keeps `inherited_from` pointing at its section. Because exceptions are stored
  with the section's assessment, a cache hit reproduces them.
- **Tables** show the headers, then `Row labels:` with the first cell of every row, then as many
  full rows (with their in-table section) as fit, then the notes if all rows fit.
- **Selection fix found on the way.** `selected_assessments_by_source_item` used every selected
  assessment's `source_refs`, and a section's refs name up to 20 of its members. A member the
  classifier excluded by exception would still have been selected through its section. An
  item's own (block or table) assessment now decides it; container refs count only for items
  with none. Phase 6 builds on this.

**Measured** ([data/probe-output-phase3.txt](data/probe-output-phase3.txt), all 13 seeds;
Phase 0 measured with the same probe from the Phase 0 worktree):

| | Phase 0 | Phase 3 |
|---|---|---|
| Gemini items | 293 | 279 (chrome removed in Phase 1; parts added here) |
| Items the classifier sees only in part | 1–5 per page | **0** |
| Content characters sent | 186,128 | 246,802 (+33%) |

The +33% is the text that used to be cut; at `gemini-3.1-flash-lite` prices the whole 13-seed
pass stays around $0.10.

**Tests.** New: every member of a 20-paragraph section reaches exactly one part, in order, and
no part exceeds the budget; an exception overrides inheritance *and* selection, and survives a
cache hit; an exception naming `m9` is rejected; a 40-row table shows its last row's label.
The SD6 and SD9 regression tests now read member text too (they looked only at `content`, so
SD6 briefly passed without being fixed). Full suite: 927 passed, 43 skipped, 5 xfailed, plus
the 4 known key-dependent failures. `ruff` clean.

**Remaining.** A bad exception still fails the whole batch; Phase 5 (SD6) turns that into a
retry and split.

### Phase 4: PDF link selection (SD2, SD4 not-selected)

- [x] Domain: `PdfLinkSelection` (per link: label, role, reason) and
      `DecisionSource.LINK_SELECTION`.
- [x] Service: a tool-free ADK classifier with structured output, one call per offering, with
      the `OfferingContext`; cached by offering + link-metadata fingerprint + versions + model;
      uses the same fallback chain (SD8).
- [x] Pipeline: new stage between acquisition and normalization, with its own audit record and
      failure code.
- [x] Normalization: takes the selection; transcribes only `current_product`, `shared_terms`
      and `unclear`; others become empty documents with `PDF_SKIPPED_NOT_SELECTED`.
- [x] Discovery: rule assessment from the selection; `unclear` PDFs go to content
      classification.
- [x] Remove the `relevant`-admission shortcut in `_rule_assessment`.
- [x] Update AGENTS.md, `docs/architecture.md` and `docs/source-discovery.md` (new stage,
      pipeline order, Gemini's role).
- [x] Unit tests with a fake selector: sibling terms are not transcribed; the fee schedule is;
      an unclear PDF is transcribed and classified on content.
- [x] Offline check against the PDF labels with a replayed selector: no `current_product` or
      `shared_terms` PDF skipped.

#### Phase 4 notes (2026-09-26)

**State: done, except the real-Gemini check**, which is Phase 7's first pass (the replayed-label
check below covers the plumbing). Commit: *Source discovery Phase 4: Gemini picks the
offering's PDFs from their links*.

**What changed.**
- **Stage.** A new pipeline stage, `pdf_selection`, runs between acquisition and normalization
  when the page links PDFs (progress label "Choosing the offering's documents"; failures map to
  `offering.source_discovery_failed` / `source.model_failed`). `NormalizationPort.normalize`
  takes `pdf_selection=`; `IndexingPipeline` takes an optional `pdf_selection` port (omitted,
  the stage is skipped and discovery classifies PDFs on content).
- **Service** ([pdf_link_selection.py](../../app/services/pdf_link_selection.py)).
  `admitted_links()` applies the extractor's own skip rule (off-topic; historical when
  `skip_historical`), so the selector is never asked about a PDF that would not be transcribed.
  One batch per offering (up to 40 links), the `OfferingContext`, and per link: file name,
  document name, link text and title, heading path, nearby text (600 chars), effective
  periods. Labels `current_product`, `shared_terms`, `related_product`,
  `generic_bank_information`, `unclear`, plus a role and reason. An answer that does not name
  every link once is asked again once, then raises `PdfLinkResponseError`. A provider error
  moves to the next discovery model. Prompt version `1`, policy version = discovery's.
- **Cache.** `pdf_link_selections` ([migration 020](../../migrations/020_pdf_link_selections.sql),
  [repository](../../app/repositories/pdf_link_selection.py)), keyed by offering, versions,
  model, and a fingerprint of the link metadata (not the PDF bytes: the decision is made from
  the link). A separate table instead of `source_discovery_assessments`, whose rows are
  `SourceAssessment`s and would have needed a label smuggled into another field.
- **Classifier.** `discovery_classifier.py` now has a generic `StructuredAdkClassifier`
  (instruction, schema, prompt builder, usage stage, retries); `AdkSourceDiscoveryClassifier`
  and `AdkPdfLinkClassifier` configure it.
- **Normalization.** A PDF the selection did not keep is not read or transcribed: it becomes
  an empty `pdf_not_selected` document with its `pdf_selection` and a
  `PDF_SKIPPED_NOT_SELECTED` warning. Every other PDF document, transcribed or failed, carries
  its choice in `NormalizedDocument.pdf_selection`.
- **Discovery rules.** Order: no content (the selection's labels for unselected PDFs; SD4
  otherwise) → explicit historical/future dates → link selection (`current_product` and
  `shared_terms` become `link_selection` document decisions with authority `official_terms`
  and the admission's temporal status; shared terms carry the condition "Applies to other
  loans as well as this offering.") → `unclear`, or no selection at all, goes to content
  classification. The keyword shortcut (`relevant` admission → official terms) is gone. The
  selection's label and role are part of the PDF's content fingerprint.
- **Audit.** `2_pdf_link_selection.md` lists each linked PDF, its decision, who made it,
  whether it was transcribed, and why.
- **Docs.** AGENTS.md now lists source discovery, including the link selection before
  transcription, among Gemini's roles. `docs/architecture.md` (pipeline diagram, PDF flow,
  source-discovery boundary, migrations 019/020) and `docs/source-discovery.md` (new section)
  describe the stage.

**Checked.** With the hand labels replayed through the selector
([data/discovery-check-phase4-pdf-labels-replayed.json](data/discovery-check-phase4-pdf-labels-replayed.json)):
all 55 labelled links on the 13 seeds reach the selector (admission drops none of the 40
current or shared ones), and 0 lost / 0 leaked. Kept: 20 `current_product` + 20
`shared_terms`; dropped: 5 `related_product`, 7 `generic_bank_information`, 3 irrelevant.
**15 fewer transcriptions per full run** (55 → 40), on top of the 62 old editions admission
already skips.

**Tests.** New [test_pdf_link_selection.py](../../tests/unit/test_pdf_link_selection.py): only
admitted links are asked, in one call, and the second run is all cache; the cache is per
offering; a wrong answer is asked again, then rejected; a 404 moves to the next model;
normalization never reads an unselected PDF; discovery decides selected (own, shared) and
unselected PDFs by rule with no Gemini call. Pipeline test: `pdf_selection` runs before
normalization and passes its result. Postgres test for `pdf_link_selections`. Full suite:
934 passed, 44 skipped, 5 xfailed, plus the 4 known key-dependent failures; 39 Postgres tests
pass on the scratch database. `ruff` clean.

**Remaining.**
- The real selector's accuracy on the 55 links is measured in Phase 7 (`--pdf-selector gemini`).
- An `unclear` PDF is transcribed and classified whole; per Q6 its members inherit that one
  decision.

### Phase 5: Reliability (SD5, SD18, SD6, SD8, SD13, SD14)

- [ ] SD5: shared `temporal_status_at(periods, as_of)`; `pdf_admission.py` uses it; applied to
      fresh and cached Gemini assessments with dated periods.
- [ ] SD18: instruction rule for undated content; `stale_evidence` in the response;
      `possibly_stale` without evidence found in the item becomes `unknown`.
- [ ] SD6: save per batch; retry once, then split down to single items;
      `DiscoveryResponseError` counts as a fallback error.
- [ ] SD6: `max_concurrent_batches` setting (default 3), results in batch order; retries and
      splits counted in usage.
- [ ] SD8: default fallback `gemini-2.5-flash-lite` in settings and `.env.example`; startup
      test that the chain passes the price cap.
- [ ] SD13: SDK retry attempts 1 for the discovery classifier and the PDF link selector.
- [ ] SD14: temperature flag per model in the model registry; used by the classifier; logged.
- [ ] Remove the matching `xfail` markers.

### Phase 6: One selection path (SD7)

- [ ] `select_sources(discovery) → SourceSelection` in `source_selection.py`, one precedence
      function; remove `_precedence` from `source_discovery.py`.
- [ ] `build_selected_source_bundle` uses it; the pipeline projects the selected bundle, not
      the full one.
- [ ] Replace `ExtractionContext` with `SourceSelection`; update the pipeline audit record.
- [ ] Add product association, temporal status, authority and precedence to chunk metadata.
- [ ] Legacy retriever: leave out related-product, navigation, historical and future chunks.
- [ ] Remove the `xfail` marker; integration test on Postgres: the menu and a sibling table are
      not in `knowledge_chunks` for the offering.

### Phase 7: Validation

- [ ] `uv run pytest tests/unit tests/integration`: all green, no `xfail` left from Phase 0.
- [ ] `agents-cli lint`: no new findings in changed files.
- [ ] Re-run [survey/probe_discovery.py](survey/probe_discovery.py); save
      `data/probe-output-after.txt` and compare with the before output.
- [ ] **Gemini pass after the fix (Q4).** Run discovery (PDF link selection + classification)
      on the 13 seeds with a $0.40 spend guard. Save `data/discovery-check-after.json`.
      *Spends Gemini budget.*
  - [ ] Every sibling-product table and section labelled `related_product`.
  - [ ] Every PDF labelled `current_product` or `shared_terms` selected; no sibling or
        website-profile PDF selected.
  - [ ] Agreement with the hand labels recorded per seed; every disagreement listed with its
        reason.
- [ ] **Cache re-run.** Run the same pass again immediately: every discovery and link-selection
      call is a cache hit (0 Gemini calls). *Spends no budget if it passes.*
- [ ] Write scenarios in `scenarios/` with a `run_scenarios.py`, as in the acquisition and
      normalization fixes:
  - [ ] S01 offline test suite;
  - [ ] S02 confirmed bugs fixed (the probe);
  - [ ] S03 offering identity: sibling tables labelled related on the four mortgage pages;
  - [ ] S04 PDF selection against the labels;
  - [ ] S05 cache: re-run is all hits; inserting a block reclassifies only its section;
  - [ ] S06 dated campaign expires without a new Gemini call;
  - [ ] S07 bad response: batch split, good batches saved, fallback model used;
  - [ ] S08 projection: no navigation or sibling chunks indexed.
- [ ] Record the total Gemini spend for Phases 0 and 7 (budget about $1).
- [ ] Update this document: the status of every item, and the before/after results.
