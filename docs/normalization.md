# Structural normalization

Structural normalization is the uniform-schema boundary between source-specific
acquisition artifacts and the later chunking, retrieval, and evidence-bound tariff
extraction stages. It does not decide that a value is an interest rate, loan limit,
or another business field. Instead, it makes source structure uniform and retains a
verifiable pointer to the acquired source for every accepted block, table cell, and
note.

## Input and output

`StructuralNormalizationService` accepts one immutable `PageArtifact`. Its output is
a `NormalizedSourceBundle` containing:

- one normalized page document;
- one page-addressable document for each downloaded PDF;
- one JSON-path-addressable document for each captured textual API payload;
- normalized content blocks and rectangular tables;
- normalized links with original `href` text and fragment targets;
- syntax-level scalar candidates (number, range, date, operator, and unit); and
- typed warnings for unavailable artifacts, model-required/model-failed PDFs, and
  invalid JSON.

Every `NormalizedBlock`, `NormalizedTableCell`, and `NormalizedNote` carries one or
more `SourceReference` values. A reference combines the stable acquisition item ID
with its original `SourceLocator` (URL plus block, DOM, PDF-page, or JSON-path
coordinates). Raw text is retained beside normalized text.

## Transformations and the PDF model boundary

HTML blocks retain their type, visibility, parent, heading path, link IDs, Markdown,
and locator. Links retain their resolved URL, raw `href`, and fragment. Whitespace
and Unicode compatibility forms are canonicalized. Cards and key/value blocks also
receive explicit fields where their acquired structure supports it.

Tables are rebuilt from physical cell coordinates and span metadata. The normalizer:

- determines width from populated cells, excluding trailing phantom DOM columns;
- expands rowspans by repeating the source cell into each logical record;
- keeps colspan continuations empty rather than shifting later values;
- removes empty carry-only and exact duplicate rows;
- merges list-item continuation rows that share row-spanned section/item cells;
- uses source headers when present and otherwise emits explicit inferred headers;
- retains cell lists inside the cell; and
- separates full-width footnotes from data rows while preserving their markers.

Downloaded PDFs use a deliberately narrow model-backed substep. Python first records
link/title/heading context, checks effective-date and archive markers, and probes each
page as `machine_readable`, `image_only`, `mixed`, or `unknown`. The probe discards
its extracted text; it exists for routing, logging, and audit only.

A deterministic admission gate then decides whether the document is worth
transcribing at all, because transcription is the most output-heavy model call in
the system. `assess_pdf_metadata` in `app/services/pdf_admission.py` reads only
link metadata — document name, link text and title, origin heading path, nearby
text, and the URL path — and returns a relevance, a role, and a temporal status:

- any product-relevant term (`loan`, `mortgage`, `credit`, `tariff`, `fee`,
  `վարկ`, `հիփոթեք`, …) makes the document `relevant`, so a tariff sheet that
  happens to mention a branch or a contact line stays admissible;
- a document with no relevant term at all that matches an off-topic marker
  (privacy policy, annual report, vacancy, sitemap, ATM, …) becomes
  `irrelevant` and is never sent to the model;
- anything else stays `ambiguous` and is transcribed, because its content still
  has to reach source discovery to be judged.

Independently, an explicit effective-date range in the link context, or an
archive/`previous terms` marker, resolves the document as `current`,
`historical`, `future`, `time_bounded`, or `unknown`. Unless
`PDF_EXTRACTION_SKIP_HISTORICAL` is disabled, a `historical` document is skipped
as well, so superseded tariff sheets are not paid for. A skipped document
becomes an empty `pdf_skipped` normalized document that keeps its locator and
admission reason, so the decision stays auditable.

The original PDF bytes of an admitted document are then supplied to a tool-free
Gemini ADK agent with a strict response schema and thinking disabled. The
response must contain every page exactly once and rectangular tables; Python
rejects invalid output and converts accepted blocks, tables, notes, and footnotes
to the same page-addressable normalized structures used downstream.

This stage has its own model rather than the global `MODEL_NAME`:
`PDF_EXTRACTION_MODEL_NAME` defaults to `gemini-3.1-flash-lite`, with
`PDF_EXTRACTION_FALLBACK_MODEL_NAMES` empty, and
`PDF_EXTRACTION_MAX_PRICE_PER_MILLION_TOKENS_USD` (default `1.50`) rejects any
configured model whose input or output rate exceeds the ceiling before a live
call. `gemini-2.5-flash-lite` held this slot until the provider stopped serving
it to new users on 2026-09-22; its successor `gemini-3.5-flash-lite` prices
output at `2.50`, so naming it here also means raising that ceiling. Transient failures receive bounded retries before the next model is tried.
Exact results are reusable by PDF SHA-256, schema version, prompt version, model,
and admission/probe fingerprint.
The demonstration stores this exact cache under `pdf_extraction/cache` and writes a
checkpoint JSON file immediately after each completed PDF. Restarting after a later
failure therefore reuses completed model responses instead of charging for them again.

JSON payloads are flattened only to scalar leaves. Each leaf becomes a key/value
block with its exact JSON path. Invalid JSON remains available as a raw text block and
produces a warning.

Scalar parsing is deliberately semantic-free. For example, `13%-15%`,
`AMD 3,000,000 - AMD 150,000,000`, and `up to 60 months` become typed candidates,
but the later evidence-bound extraction component decides which tariff field—if
any—each candidate represents.

## Inspection

Normalize an existing acquisition case with:

```bash
uv run python scripts/demonstrate_normalization.py .temp/acuisition_test/case_008
```

The command writes `normalization/` inside that case with the complete bundle,
flattened block/table/scalar views, rendered Markdown, and a warning/count summary.
The files are inspection views; `normalized_bundle.json` is the canonical contract.

Inspect PDF routing and estimated cost without a model call, then optionally execute
the extraction in a separate numbered directory:

```bash
uv run python scripts/demonstrate_pdf_extraction.py .temp/acuisition_test/case_008
uv run python scripts/demonstrate_pdf_extraction.py .temp/acuisition_test/case_008 --execute-llm
```

Preflight writes `pdf_extraction/preflight/`; live runs write
`pdf_extraction/llm_run_000/`, `llm_run_001/`, and so on, so one mode never overwrites
the other.

---


# Normalization Content Explanation

Each acquisition case can contain one self-contained normalization result:

```text
case_008/
├── source_url.txt
├── output/
│   └── ...
└── normalization/
    ├── summary.txt
    ├── normalized_bundle.json
    ├── normalized.md
    ├── normalized_blocks.json
    ├── normalized_tables.json
    ├── normalized_links.json
    └── normalized_scalars.json
```

### `summary.txt`

A quick overview of the normalization result:

- Canonical source URL
- Acquisition content hash
- Number of normalized documents
- Number of blocks
- Number of tables and logical table rows
- Number of links
- Number of scalar candidates
- Normalization warnings

For `case_008`, it reports:

```text
Documents: 29
Blocks: 30944
Tables: 3
Links: 109
Table rows: 123
Scalar candidates: 1217
Warnings: 0
```

This is the best file to open first.

The 29 documents consist of:

- 1 normalized web page;
- 9 downloaded PDFs;
- 19 captured API responses.

Here, “document” means an independently addressable source artifact. It does not necessarily mean a downloadable file.

### `normalized.md`

A readable Markdown rendering of the normalized material.

It contains:

- normalized headings and paragraphs;
- cards and lists;
- reconstructed tables;
- repeated rowspan values;
- cell-internal lists;
- separated table footnotes;
- preserved links;
- properly escaped Markdown table delimiters.

Unlike acquisition’s `page.md`, this file renders tables after structural repairs have been applied.

For example, a source table with merged cells can be represented as:

```markdown
| Section | Item | Terms |
| --- | --- | --- |
| Loan terms² | Currency | AMD |
| Loan terms² | Minimum and maximum loan limits | AMD 50,000–6,000,000 |
| Loan terms² | Term | Up to 60 months |
```

Use this file for manual visual inspection.

It is not the canonical machine-readable result because Markdown cannot fully represent:

- source locators;
- visibility;
- table-cell evidence;
- JSON paths;
- PDF page numbers;
- extraction methods;
- typed scalar values;
- normalization warnings.

### `normalized_blocks.json`

All normalized content blocks from the page, PDFs, and API payloads in one flattened list.

A typical normalized HTML block looks like:

```json
{
  "id": "b24",
  "type": "paragraph",
  "raw_text": "Loan term:  up to 60 months",
  "text": "Loan term: up to 60 months",
  "markdown": null,
  "heading_path": [
    "Consumer Loan",
    "Terms"
  ],
  "parent_id": null,
  "link_ids": [],
  "visible": true,
  "table_id": null,
  "fields": {},
  "scalar_candidates": [
    {
      "raw": "up to 60 months",
      "kind": "number",
      "operator": "<=",
      "value": "60",
      "unit": "month"
    }
  ],
  "source_refs": [
    {
      "source_item_id": "b24",
      "locator": {
        "source_url": "https://ameriabank.am/...",
        "source_type": "page",
        "block_id": "b24",
        "css_selector": "...",
        "xpath": "..."
      }
    }
  ],
  "extraction_method": "browser"
}
```

Important fields:

- `id`: stable block identifier inherited from acquisition or generated for PDF/API content.
- `type`: heading, paragraph, list, key/value pair, table, accordion, card, link, or other.
- `raw_text`: text before normalization.
- `text`: normalized Unicode and whitespace representation.
- `markdown`: source Markdown where meaningful formatting or links exist.
- `heading_path`: headings providing context for the block.
- `parent_id`: containing accordion, card, or other structural block.
- `link_ids`: links occurring inside the block.
- `visible`: browser visibility recorded during acquisition.
- `table_id`: corresponding normalized table for a table block.
- `fields`: explicit structure extracted without semantic inference.
- `scalar_candidates`: numbers, ranges, units, and dates recognized in the block.
- `source_refs`: evidence pointing back to the acquired source.
- `extraction_method`: `browser`, `static`, `gemini_pdf:<model>`, `json`, or `text`.

Examples of `fields` include:

```json
{
  "title": "Special offer",
  "body": "Apply until September 30, 2026"
}
```

or:

```json
{
  "key": "Currency",
  "value": "AMD"
}
```

These fields describe obvious source structure. They do not assign financial meaning.

For API responses, each scalar JSON leaf becomes a block with fields such as:

```json
{
  "path": "$['rates'][0]['value']",
  "value": "13%"
}
```

The large number of blocks in `case_008` is primarily caused by flattening the captured JSON payloads into individually addressable JSON leaves.

### `normalized_tables.json`

Tables after deterministic structural repair.

A typical normalized table looks like:

```json
{
  "id": "t1",
  "title": "Consumer loan not secured by property",
  "headers": [
    "Section",
    "Item",
    "Terms"
  ],
  "headers_inferred": true,
  "rows": [
    {
      "id": "t1:row:1",
      "cells": [
        {
          "raw_text": "Loan terms²",
          "text": "Loan terms²",
          "markdown": "Loan terms<sup>2</sup>",
          "list_items": [],
          "scalar_candidates": [],
          "source_refs": []
        },
        {
          "raw_text": "Currency",
          "text": "Currency",
          "markdown": "Currency",
          "list_items": [],
          "scalar_candidates": [],
          "source_refs": []
        },
        {
          "raw_text": "AMD",
          "text": "AMD",
          "markdown": "AMD",
          "list_items": [],
          "scalar_candidates": [],
          "source_refs": []
        }
      ]
    }
  ],
  "notes": [],
  "source_refs": []
}
```

Important fields:

- `id`: stable table identifier.
- `title`: caption, tab title, panel title, or nearby table heading.
- `headers`: final logical column names.
- `headers_inferred`: whether normalization had to construct headers.
- `rows`: rectangular logical records.
- `notes`: table footnotes separated from ordinary records.
- `source_refs`: evidence pointing to the original acquired table.

Each row contains:

- `id`: stable logical row identifier.
- `cells`: cells in the same order as the table headers.

Each cell contains:

- `raw_text`: original acquired cell content.
- `text`: normalized cell text.
- `markdown`: links and meaningful formatting preserved inside the cell.
- `list_items`: bullets or numbered items belonging to the cell.
- `scalar_candidates`: numbers, ranges, dates, and units found in the cell.
- `source_refs`: one or more original table cells that produced the normalized cell.

Multiple source references can occur when several physical rows are consolidated into one logical list cell.

The normalizer repairs the table structure by:

- determining the actual width from populated cells;
- removing trailing phantom DOM columns;
- expanding rowspans;
- preventing colspan values from shifting into incorrect columns;
- repeating section labels on every logical row;
- removing empty carry-only rows;
- removing exact duplicate rows;
- merging list continuation rows under shared rowspan labels;
- retaining lists inside cells;
- separating full-width footnotes from data rows;
- preserving raw cell-level evidence.

For `case_008`, the three tables are:

```text
Tariffs
    Section | Item | Terms 1 | Terms 2 | Terms 3
    63 logical rows
    6 notes

Express Home Mortgage Loan
    Section | Item | Terms
    48 logical rows
    9 notes

Loan service fees
    Purpose | Rates and Fees (AMD)
    12 logical rows
```

Repeated section values are intentional. A normalized row should remain understandable even if retrieved without the rows surrounding it.

### `normalized_links.json`

All normalized links from the HTML page.

A typical link looks like:

```json
{
  "id": "l17",
  "url": "https://ameriabank.am/en/personal/loans/mortgage/primary#terms",
  "raw_href": "#terms",
  "fragment": "terms",
  "text": "Terms and conditions",
  "title": null,
  "source_refs": [
    {
      "source_item_id": "l17",
      "locator": {
        "source_url": "https://ameriabank.am/...",
        "source_type": "page",
        "block_id": "b42",
        "css_selector": "...",
        "xpath": "..."
      }
    }
  ]
}
```

Important fields:

- `id`: identifier used by block `link_ids`.
- `url`: resolved absolute URL.
- `raw_href`: exact `href` supplied by the source DOM.
- `fragment`: fragment target without the leading `#`.
- `text`: visible link text.
- `title`: HTML title attribute, when present.
- `source_refs`: where the link appeared.

Preserving both `url` and `raw_href` is important.

For example:

```text
raw_href: #terms
url: https://ameriabank.am/en/personal/loans/mortgage/primary#terms
fragment: terms
```

This shows that the link points to a section of the current page rather than to a separate source.

This file is an input to source discovery. Normalization does not decide whether a link represents:

- official terms;
- a related product;
- global navigation;
- an old tariff;
- an inline source document;
- an irrelevant external destination.

### `normalized_scalars.json`

A flattened index of numeric and date expressions found throughout the normalized documents.

A range candidate can look like:

```json
{
  "document_id": "page:a522f3b80371822d",
  "container_id": "t1:row:7",
  "column_index": 2,
  "raw": "AMD 3,000,000 - AMD 150,000,000",
  "kind": "range",
  "operator": null,
  "value": null,
  "min_value": "3000000",
  "max_value": "150000000",
  "unit": "AMD",
  "normalized_date": null
}
```

A bounded number can look like:

```json
{
  "document_id": "page:a522f3b80371822d",
  "container_id": "b24",
  "raw": "up to 240 months",
  "kind": "number",
  "operator": "<=",
  "value": "240",
  "min_value": null,
  "max_value": null,
  "unit": "month",
  "normalized_date": null
}
```

Important fields:

- `document_id`: normalized document containing the expression.
- `container_id`: block or table row containing it.
- `column_index`: table column, when the expression came from a table.
- `raw`: exact matched source expression.
- `kind`: `number`, `range`, or `date`.
- `operator`: `<=`, `>=`, `<`, or `>`, when applicable.
- `value`: single numeric value.
- `min_value`: lower range boundary.
- `max_value`: upper range boundary.
- `unit`: normalized unit.
- `normalized_date`: parsed calendar date.

Recognized units include:

- `AMD`
- `USD`
- `EUR`
- `percent`
- `month`
- `year`
- `day`

Currency names and symbols are converted into canonical codes where possible.

Examples:

```text
֏ 1,000,000        → value=1000000, unit=AMD
13%-15%            → min_value=13, max_value=15, unit=percent
up to 240 months   → operator=<=, value=240, unit=month
September 4, 2015  → normalized_date=2015-09-04
```

These are syntactic candidates, not semantic loan fields.

For example, normalization can determine that:

```text
13%
```

is a percentage, but it does not determine whether it is:

- a nominal interest rate;
- an APR;
- a penalty;
- a down payment;
- an LTV value;
- a service fee.

That decision belongs to semantic extraction.

### `normalized_bundle.json`

The complete normalization result in one file.

It combines:

- canonical source identity;
- acquisition hash;
- normalized HTML page;
- normalized PDFs;
- normalized API payloads;
- blocks;
- tables;
- links;
- scalar candidates;
- extraction methods;
- quality scores;
- source evidence;
- normalization warnings.

This is the machine-readable primary output.

The other files are convenient flattened or rendered views of parts of this object.

Its top-level structure is approximately:

```json
{
  "canonical_url": "https://ameriabank.am/en/personal/loans/mortgage/primary",
  "acquisition_content_hash": "a522f3b8...",
  "documents": [],
  "warnings": []
}
```

Each document contains:

```json
{
  "id": "document:1:db6b470de92a",
  "name": "Terms of the loan for purchase of residential real estate",
  "source_url": "https://ameriabank.am/...pdf",
  "source_type": "pdf",
  "mime_type": "application/pdf",
  "content_sha256": "...",
  "extraction_method": "gemini_pdf:gemini-2.5-flash-lite",
  "quality_score": 1.0,
  "blocks": [],
  "tables": [],
  "links": []
}
```

The document types in `case_008` are:

```text
page: 1
pdf:  9
api: 19
```

### `source_refs`

Source references appear throughout the normalized bundle.

A source reference looks like:

```json
{
  "source_item_id": "c42",
  "locator": {
    "source_url": "https://ameriabank.am/...",
    "source_type": "page",
    "block_id": "b17",
    "css_selector": "...",
    "xpath": "...",
    "pdf_page": null,
    "json_path": null
  }
}
```

Depending on the source, a locator may identify:

- an HTML block;
- a CSS selector;
- an XPath;
- a PDF page;
- a JSON path.

Examples:

```json
{
  "source_type": "pdf",
  "pdf_page": 4
}
```

```json
{
  "source_type": "api",
  "json_path": "$['rates'][0]['value']"
}
```

These references are the bridge between normalized content and verifiable evidence.

Later components should preserve them when producing:

- retrieval chunks;
- extracted tariff values;
- atomic claims;
- verification results;
- change reports.

### `raw_text` and `text`

Most normalized structures retain two text representations:

- `raw_text`: original acquired representation.
- `text`: deterministic normalized representation.

Normalization can change:

- repeated whitespace;
- non-breaking spaces;
- Unicode compatibility characters;
- line endings;
- numeric formatting.

It does not intentionally discard the original value.

For example:

```json
{
  "raw_text": "up to  240\u00a0months",
  "text": "up to 240 months"
}
```

`raw_text` supports auditing and exact source comparison.  
`text` supports searching, chunking, scalar recognition, and extraction.

### `extraction_method`

This records how normalized text was obtained.

Possible values include:

- `static`: block came from statically retrieved HTML.
- `browser`: block came from the rendered browser DOM.
- `gemini_pdf:<model>`: page structure was transcribed from the native PDF by the
  named Gemini model and passed deterministic schema/page-coverage validation.
- `json`: block came from a successfully parsed JSON payload.
- `text`: payload was retained as ordinary text.

The extraction method helps later verification assess evidence quality.

### `quality_score`

PDF documents contain a quality score between `0` and `1`. It is the fraction of
pages for which the accepted model response supplied at least one block or table.

Examples:

```text
1.0   every PDF page produced at least one accepted block or table
0.5   half of the PDF pages produced at least one accepted block or table
0.0   no PDF page produced an accepted block or table
```

This is an extraction-quality signal. It is not a relevance or source-authority score.

Source discovery will determine relevance and authority later.

### `warnings`

Normalization warnings are structured conditions that require attention.

Possible warning codes include:

- `ARTIFACT_UNAVAILABLE`: stored source bytes could not be read or verified.
- `PDF_MODEL_REQUIRED`: PDF bytes were available but no Gemini PDF extractor was configured.
- `PDF_MODEL_FAILED`: all bounded Gemini extraction attempts failed or returned invalid output.
- `INVALID_JSON`: a captured JSON response could not be decoded.
- `AMBIGUOUS_TABLE`: table structure could not be resolved reliably.

A warning does not necessarily invalidate the whole bundle. It identifies a specific source or operation that may be incomplete.

`case_008` has:

```text
Warnings: 0
```

This means all acquired artifacts needed by normalization were readable and structurally processed without a reported failure.

It does not mean that:

- all 29 documents are relevant;
- every scalar candidate is a tariff;
- all sources have equal authority;
- there are no conflicting loan terms;
- semantic extraction is complete.

Those decisions belong to the following subsystem stages.

### `acquisition_content_hash`

This is copied from the acquisition result.

It ties the normalized bundle to the exact acquired source state:

```text
a522f3b80371822da7d497a3c0c66ca64af41270fc3533a4cd09ebbea1219816
```

Therefore:

- normalization can be reproduced from the corresponding acquisition artifact;
- later stages can identify which acquisition version produced their inputs;
- a changed hash means the acquired material changed;
- a changed hash does not necessarily mean a tariff changed.

Tariff-change detection happens only after semantic extraction, verification, and snapshot comparison.
