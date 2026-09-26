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
3. When the browser is enabled (the default), every page is rendered by
   `PlaywrightBrowserRenderer`. The bank's tariff tables, PDF links and data payloads
   exist only in the rendered page: static HTML carried none of them on any of the 13
   seeds (survey of 2026-09-26). There is **no static fallback**: a render that fails
   fails the acquisition with `source.browser_failed` or `source.browser_unavailable`.
   Static HTML is used only when `ACQUISITION_BROWSER_ENABLED=false`, and must then
   pass the same completeness floor.
4. The renderer waits for the page's content to be shown before reading it. The bank
   fades its whole ASP.NET form in from opacity 0, so the wait watches the element
   holding the page's text (and the `<h1>` when there is one), and opacity is never
   treated as hiding: only `display`, `visibility`, `hidden` and zero size are.
5. Browser requests are restricted to allowlisted GET/HEAD URLs. Images, media, fonts,
   service workers, form submissions, and cross-domain requests are blocked. After the
   page has loaded, a main-frame navigation (a clicked button that changes
   `location`) is answered with an empty 204, which keeps the current document; the
   page URL is checked again after the interactions. Every hop of the main document's
   redirect chain is validated against the allowlist. Redirects of page *resources*
   are followed by the browser without a per-hop check (Playwright routes only the
   first URL of a chain); their final responses are still host-checked before capture.
6. The renderer opens bounded accordions/tabs/content-revealing controls and captures
   same-domain textual XHR/fetch responses within a byte budget. The payload count cap
   is applied after the captures are deduplicated and sorted, so the kept set never
   depends on arrival order. Reaching the interaction or payload cap is a typed
   warning.
7. **Completeness floor.** Every acquisition must carry at least
   `ACQUISITION_MIN_MAIN_CONTENT_CHARS` of *main* text -- text outside the site's
   `header`/`nav`/`footer` and ARIA banner/navigation/contentinfo regions, which alone
   run to ~9k characters on every bank page -- **and** at least one table, same-host
   PDF link or captured payload. Otherwise it fails with `source.incomplete_content`
   and its reasons (for example `main_chars 368 < 1500; no tables, PDF links or
   payloads`). The counts are kept on the artifact as `PageArtifact.inventory`.
8. Same-domain PDF links are downloaded through the existing `PdfDownloader` security
   boundary, up to `ACQUISITION_MAX_LINKED_DOCUMENTS` (40). A failed linked PDF, a
   dead link, or links beyond the cap are recorded as typed warnings
   (`acquisition.linked_document_failed`, `acquisition.linked_document_missing` for
   HTTP 404, `acquisition.linked_document_cap_reached`) and cannot create a partial
   document artifact. A failed download makes the acquisition partial, so it is not
   stored for reuse; a dead link does not, because it is the same on every fetch. Acquisition warnings reach the run's
   source manifest and audit metadata.
9. Raw HTML, rendered HTML, Markdown, network payloads, and PDFs are written atomically
   to content-addressed storage.

## Identity

`page_content_hash` names the page document downstream (`page:<hash>`), and so every
evidence id and extraction-cache key quoted from it. It is built from the **parsed**
page only -- canonical URL, blocks, tables, links, images and controls -- never from
the raw or rendered HTML bytes. The bank's pages carry `__VIEWSTATE`,
`__EVENTVALIDATION` and `__RequestVerificationToken` values that change on every
request; hashing the bytes gave an unchanged page a new id on every fetch and missed
every extraction cache. `content_hash` adds the linked documents and payloads; it is a
consistency tag checked between normalization, discovery and extraction, not the input
to change detection, which compares accepted field values.

Raw and rendered HTML come from two separate fetches (the static request and the
browser's own navigation) and can differ in such per-request fields; raw HTML is kept
for audit only.

## Completeness baseline

`CompletenessGatedAcquisitionService` (wired between the freshness gate and
acquisition) compares each fresh acquisition's inventory with the last one of the same
URL that passed, stored in `acquisition_baselines`. A table, PDF-link or payload count
that falls to zero fails; so does a relative drop of PDF links or main content beyond
`ACQUISITION_BASELINE_MAX_PDF_LINK_DROP` / `ACQUISITION_BASELINE_MAX_MAIN_CONTENT_DROP`.
Only a passing acquisition moves the baseline, so a degraded one never becomes the
reference. A drop keeps failing (`source.incomplete_content`) until an operator, having
checked that the bank really redesigned the page, runs:

```bash
uv run python -m scripts.reset_acquisition_baseline <offering_id>
```

The reset clears the inventory, stamps `reset_by`/`reset_at`, and writes an
`acquisition.baseline_reset` audit event; the next passing run records a new baseline.
It is an operator tool only and is never exposed to the model.

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

The `ACQUISITION_*` environment variables control browser use, the completeness floor
(`ACQUISITION_MIN_MAIN_CONTENT_CHARS`), the baseline drop thresholds, browser
timeout/settling, interaction count, network payload count/size, the linked-document
budget and the freshness window. General HTTP host, retry, redirect, and byte limits
remain in the shared HTTP settings.

`scripts/survey_acquisition.py` acquires every enabled seed once (no PDF downloads,
nothing written to the database) and prints each seed's mode, inventory, page id and
warnings, to compare before and after an acquisition change.

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

This file is absent only when the browser is disabled.

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
