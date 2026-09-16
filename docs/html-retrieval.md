# Website scraper / HTML retriever

`HtmlRetriever` is a deterministic ingestion service for public official product
pages. It accepts one discovery-approved `HtmlCandidate`; it is not a generic browser,
crawler, form client, or ADK model tool.

## Network boundary

HTML and PDF retrieval share `RestrictedHttpTransport`. The transport:

- permits only HTTPS URLs on exact configured hosts;
- validates the initial URL and every redirect target;
- disables automatic redirects and detects loops and redirect-limit exhaustion;
- retries only timeouts, transport errors, HTTP 429, and HTTP 5xx;
- applies capped exponential backoff, jitter, and bounded `Retry-After`;
- accepts only the MIME types requested by the caller and allowed by configuration;
- checks declared and streamed byte counts; and
- returns bytes only after a complete successful response, with checksum and bounded
  safe provenance headers.

HTML pages use the separate `MAX_HTML_BYTES` limit and require `text/html`. HTTP 4xx,
non-HTML content, oversized responses, disallowed redirects, empty pages, and likely
access-denied/CAPTCHA pages produce typed controlled failures. The retriever never
executes JavaScript, submits forms, accepts cookies, or attempts to bypass access
controls.

## Extraction contract

Beautiful Soup parses the untrusted bytes without a browser runtime. Before content is
returned, scripts, styles, frames, form controls, semantic navigation/footer
containers, cookie UI, chat widgets, and common repeated boilerplate are removed.
Form containers are unwrapped rather than executed or submitted, preserving content
from ASP.NET/DNN sites that wrap the entire public page in a form.

`RetrievedHtmlPage` contains:

- source, final, and validated same-allowlist canonical URLs;
- title, ordered headings, deduplicated main text, structured table rows, and a
  deterministic language hint;
- deduplicated allowlisted links with anchor text, bounded context, and an HTML/PDF/
  other classification; and
- MIME type, encoding hint, byte size, SHA-256, retrieval timestamps, safe headers,
  and the original untrusted bytes for controlled artifact storage.

Relative links are resolved against the final URL. Off-domain, non-HTTPS, credentialed,
and IP-literal links are excluded. This component collects evidence faithfully; source
discovery and ranking decide relevance and authority in later components, and tariff
extraction must consume cleaned/indexed evidence rather than raw HTML.

## Initial product coverage

Fixtures model the supplied Ameriabank consumer-loan and secondary-market mortgage
pages in Armenian and English. They verify preservation of Armenian text, tables,
mortgage fee/insurance statements, and official PDF links while excluding scripts,
cookie UI, navigation, and off-domain links.
