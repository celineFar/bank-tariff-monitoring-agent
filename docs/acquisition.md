# Acquisition

`AcquisitionService` retrieves and preserves official source material without assigning
loan semantics. It is a deterministic application service and is not exposed directly
to the ADK model.

## Flow

1. `HtmlRetriever` validates the initial HTTPS URL and every redirect against the exact
   source-host allowlist. It applies bounded retries, redirect limits, MIME checks, and
   streamed byte limits before returning decoded HTML and its SHA-256 checksum.
2. `HtmlArtifactParser` preserves title, language, canonical URL, visible structural
   blocks, heading paths, rowspan/colspan-aware tables, FAQ/accordion relationships,
   inline links, images, and interactive controls with CSS/XPath locators. Both the
   physical table cells and a deterministic logical grid are retained.
3. Static content is used when it is sufficient. Interactive markup, an application
   shell, or insufficient text triggers `PlaywrightBrowserRenderer` when enabled.
4. Browser requests are restricted to allowlisted GET/HEAD URLs. Images, media, fonts,
   service workers, form submissions, and cross-domain requests are blocked. The
   renderer opens bounded accordions/tabs/content-revealing controls and captures a
   bounded set of same-domain textual XHR/fetch responses.
5. Same-domain PDF links are downloaded through the existing `PdfDownloader` security
   boundary. A failed linked PDF is recorded as a warning and cannot create a partial
   document artifact.
6. Raw HTML, rendered HTML, Markdown, network payloads, and PDFs are written atomically
   to content-addressed storage. `PageArtifact.content_hash` excludes timestamps and
   storage paths, so identical source material hashes identically across runs.

## Ownership and lifecycle

The caller owns the shared `httpx.AsyncClient`. `build_acquisition_service` composes the
retriever, parser, browser renderer, downloader, and filesystem artifact store from the
validated application settings. Playwright launches a fresh isolated Chromium context
for an acquisition and closes it before returning.

The stored relative paths are generated exclusively from SHA-256 values. Source URLs,
link labels, and model output can never select filesystem paths. Raw artifacts remain
untrusted evidence and are not instructions for the agent.

## Current document scope

The first implementation downloads PDF linked documents, matching the current Ameria
loan-source scope and the existing hardened downloader. Other downloadable formats are
retained as links but are not fetched until a format-specific validator is implemented.

## Configuration

The `ACQUISITION_*` environment variables control browser use, minimum useful static
text, browser timeout/settling, interaction count, network payload count/size, and the
linked-document budget. General HTTP host, retry, redirect, and byte limits remain in
the shared HTTP settings.

## Manual demonstration

Run acquisition for one allowlisted URL with:

```bash
uv run python scripts/demonstrate_acquisition.py "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
```

The script writes the requested URL to `.temp/acuisition_test/source_url.txt` and
places the inspection files under `.temp/acuisition_test/output/`. The output includes
the complete `PageArtifact`, summary, raw and rendered HTML, Markdown, structural
blocks, tables, links, images, interactive controls, documents, network payloads, and
content-addressed raw artifacts.


---

# Output Content Explanation

Each run produces one self-contained investigation case:

```text
case_000/
├── source_url.txt
└── output/
    ├── summary.txt
    ├── page_artifact.json
    ├── raw.html
    ├── rendered.html
    ├── page.md
    ├── blocks.json
    ├── tables.json
    ├── links.json
    ├── documents.json
    ├── network_payloads.json
    └── artifacts/
```

### `source_url.txt`

The exact URL you supplied to the script.

Use it to identify the starting point of the acquisition. It may differ from the final or canonical URL after redirects.

### `summary.txt`

A quick overview of the run:

- Requested, final, and canonical URLs
- Whether acquisition used static HTTP or Playwright
- Retrieval timestamp
- Content hash
- Number of blocks, tables, links, documents, and network payloads
- Warnings encountered

This is the best file to open first.

### `raw.html`

The HTML returned by the original HTTP request, before JavaScript execution or interaction.

Use it to answer:

- What did the server initially return?
- Was useful content present without JavaScript?
- Was the page merely an application shell?
- Were accordions and tabs already represented in the HTML?

### `rendered.html`

The final DOM after Playwright:

- executed page JavaScript;
- opened accordions;
- inspected tabs;
- clicked bounded content-revealing controls;
- waited for page content to settle.

Compare this with `raw.html` to see what JavaScript or interaction added.

This file is absent when the static HTML was sufficient.

### `page.md`

A readable Markdown representation constructed from the selected DOM.

It contains headings, paragraphs, lists, accordions, and tables in a more convenient format than HTML. This is intended for human inspection and later processing, but it is not semantic loan extraction yet.

### `blocks.json`

The page divided into structural content units.

A typical block looks like:

```json
{
  "id": "b24",
  "type": "paragraph",
  "text": "Loan term: up to 60 months",
  "heading_path": [
    "Consumer Loan",
    "Terms"
  ],
  "parent_id": null,
  "locator": {
    "source_url": "https://ameriabank.am/...",
    "source_type": "page",
    "block_id": "b24",
    "css_selector": "body > div:nth-of-type(2) > p:nth-of-type(1)",
    "xpath": "/html[1]/body[1]/div[2]/p[1]"
  },
  "visible": true
}
```

Important fields:

- `id`: stable reference within this acquired page.
- `type`: heading, paragraph, list, table, accordion, etc.
- `text`: faithfully collected text.
- `heading_path`: headings that provide context for the block.
- `parent_id`: containing structural block, when applicable.
- `locator`: information for finding the content again.
- `visible`: whether acquisition considered it visible.

Later source discovery and extraction should refer to these block IDs.

### `tables.json`

Tables represented as rows and columns rather than flattened text.

Example:

```json
{
  "id": "t1",
  "caption": "Loan terms",
  "headers": ["Currency", "Amount", "Interest rate"],
  "rows": [
    ["AMD", "Up to 10,000,000", "13%"]
  ],
  "locator": {
    "source_url": "https://ameriabank.am/...",
    "css_selector": "...",
    "xpath": "..."
  }
}
```

This allows later stages to understand row/column relationships without reparsing HTML.

The acquisition stage does not yet decide that a particular cell represents the official loan amount or rate.

### `links.json`

Every collected HTTP/HTTPS link.

Important fields:

- `url`: resolved, defragmented absolute URL used for retrieval and deduplication.
- `raw_href`: exact `href` value supplied by the source DOM.
- `fragment`: same-page or document fragment target, without the leading `#`.
- `text`: visible link text.
- `title`: HTML title attribute.
- `rel`: values such as `canonical`, `noopener`, or `nofollow`.
- `declared_mime_type`: MIME type declared by the page, if any.
- `same_allowlisted_source`: whether it is on an approved Ameriabank host.
- `downloadable`: whether it appears to be a downloadable document.
- `locator`: where the link appeared.

This file will be an input to source discovery. Many links will be navigation or unrelated products; acquisition intentionally does not make that semantic decision.

### `documents.json`

Metadata for linked PDFs that were successfully downloaded.

Typical information includes:

- original link URL;
- final URL after redirects;
- document name;
- MIME type;
- byte size;
- SHA-256 checksum;
- retrieval timestamp;
- path to the saved PDF inside `artifacts/`.

Only successfully validated PDFs appear here. A linked document must pass URL, redirect, size, MIME, and PDF-signature checks.

### `network_payloads.json`

Textual API responses captured from browser `XHR` and `fetch` requests.

These sometimes contain structured product information not directly present in the raw HTML.

Important fields:

- request URL and method;
- HTTP status;
- MIME type;
- response body;
- size and SHA-256 hash;
- retrieval time;
- JSON locator;
- stored artifact path.

Not every payload is useful. Some may contain menus, site configuration, localization, or unrelated page data. Source discovery will classify them later.

### `page_artifact.json`

The complete acquisition result in one file.

It combines:

- page metadata;
- raw and rendered HTML;
- Markdown;
- blocks;
- tables;
- links;
- documents;
- network payloads;
- stored artifact references;
- warnings;
- timestamps;
- content hash.

This is the machine-readable primary output. The other JSON and text files are convenient views of parts of this object.

### `artifacts/`

The original stored material, organized by SHA-256 checksum:

```text
artifacts/
└── ab/
    └── abcdef...1234.pdf
```

The first two checksum characters form the directory name.

Possible extensions include:

- `.html`: raw or rendered HTML
- `.md`: generated Markdown
- `.pdf`: downloaded official documents
- `.json`: captured JSON responses
- `.txt`: other captured textual responses

These filenames are intentionally hash-based:

- the same bytes produce the same path;
- source-controlled filenames cannot escape the storage directory;
- duplicate content is stored only once;
- content corruption can be detected by recomputing the hash.

The `stored_artifacts` section of `page_artifact.json` maps roles such as `raw_html`, `rendered_html`, or `linked_document_1` to these files.

### The three URLs

You will commonly see three URL fields:

- `url`: the URL you requested.
- `final_url`: the URL reached after redirects and browser navigation.
- `canonical_url`: the page’s declared preferred identity.

They are often identical but should not be assumed to be.

### `content_hash`

This is the fingerprint of the meaningful acquisition result. It includes structural content and the hashes of captured documents and network payloads, but excludes timestamps and local storage paths.

Therefore:

- identical source material should produce the same hash;
- a different hash means some acquired material changed;
- a changed hash does not yet mean a tariff changed—that determination happens much later.
