# Phase-1 product source crawler

`ProductCrawler` implements the deterministic workflow in
`Project Documents/Scraper Specification - Phase 1.md`. It is an application service,
not an ADK model tool. Gemini receives neither its HTTP client nor raw source bytes.

## Registry and crawl scope

`app.domain.product_registry.PRODUCT_REGISTRY` is the only hard-coded product
knowledge. It contains five consumer-loan and nine mortgage seeds, including the
singular `consumer-loan/online-consumer-finance` path and the Diaspora campaign path.
Document URLs are never generated or stored in the registry.

For each seed the crawler:

1. validates and retrieves the configured English page;
2. inspects the real language switcher, then tries verified `/en/` removal only as a
   fallback;
3. scans English and Armenian raw HTML independently;
4. classifies and deduplicates discovered links;
5. retrieves directly relevant supporting pages at depth one;
6. downloads and validates discovered documents; and
7. returns `SUCCESS`, `PARTIAL`, or `FAILED` in a `ProductSourceInventory`.

One product failure does not discard other product inventories.

Static HTML is always attempted first. Some Ameriabank DNN modules expose only empty
containers until their public content loader runs. The crawler renders both pages
with no usable static content and otherwise-usable pages containing unresolved,
non-boilerplate DNN content modules. It passes the stable `Container<module-id>`
identifiers to `PlaywrightHtmlRenderer`, which waits for every required module rather
than accepting an already-loaded banner. Empty header/footer/navigation/sidebar
modules are excluded. If a required module does not populate before the bounded
timeout, the known-incomplete static shell is rejected rather than ingested.

The fallback does not click, submit forms, accept downloads, bypass
access controls, or interact with calculators. HTTP and WebSocket requests are
restricted to configured HTTPS/WSS hosts; images, media, fonts, stylesheets, service
workers, and off-domain traffic are blocked. Each isolated browser context is bounded
by `CRAWL_RENDER_TIMEOUT_SECONDS` and `MAX_HTML_BYTES`.

Use `ProductCrawler` as an async context manager so a lazily started browser is closed
after the run. The Docker image installs Chromium and runs the application as a
non-root user.

Run every registered product, or select individual products, with:

```powershell
uv run python scripts/crawl_product_sources.py --pretty
uv run python scripts/crawl_product_sources.py --product-id consumer.overdraft --pretty
uv run python scripts/crawl_product_sources.py --summary
uv run python scripts/crawl_product_sources.py --product-id consumer.finance --summary --document-urls --pretty
```

The command prints inventory metadata as JSON and deliberately excludes downloaded
document bytes. Application code receives those bytes in each `DocumentResource` for
the later parsing and artifact-storage stages.

## Static discovery

`source_discovery` reads `a[href]`, `link[href]`, `iframe[src]`, `embed[src]`,
`object[data]`, `source[src]`, the configured `data-*` URL attributes, `onclick`, and
literal URL strings in inline scripts. It never executes JavaScript. Relative URLs are
resolved, fragments and known tracking parameters are removed, path case is retained,
and only safe HTTPS URLs are kept.

Classification uses document extensions/paths, English and Armenian tariff terms,
same-product paths, campaign/special-offer paths, content location, and explicit
exclusions. Registered sibling products, global navigation, application/login/contact
links, and unrelated pages are not crawled. Calculator and external references are
recorded without interaction.

## Bounds and deduplication

The following settings control traffic:

- `CRAWL_MAX_CONCURRENT_REQUESTS` (default `4`);
- `CRAWL_REQUESTS_PER_SECOND` (default `2`); and
- `CRAWL_MAX_SUPPORTING_DEPTH` (`0` or `1`, default `1`); and
- `CRAWL_MAX_CONCURRENT_RENDERS` (default `2`).

Each run caches HTML and document requests by conservatively normalized URL. Product
and supporting pages are deduplicated by final/canonical URL. Documents with different
URLs but identical SHA-256 bytes become one resource retaining all discovered URLs,
their original URL spellings, referrers, and language hints.

PDF and Office attachments must have an enabled MIME type and a matching PDF, OLE, or
ZIP/OOXML signature. Redirects, response sizes, retries, and host allowlisting remain
owned by `RestrictedHttpTransport`.

## Testing

The default suite uses mocked HTTP and static fixtures:

```powershell
uv run pytest tests/unit/test_product_registry.py tests/unit/test_source_discovery.py
uv run pytest tests/integration/test_product_crawler.py
uv run pytest tests/integration/test_document_downloader.py
```

These tests cover all registry entries, multilingual discovery, DOM/data/script URLs,
sibling and depth exclusion, request caching, URL and content deduplication, attachment
validation, and per-product failure isolation without depending on the live website.

The heavier live crawl is explicit because it loads all official product pages,
supporting pages, and discovered documents:

```powershell
$env:RUN_LIVE_CRAWLER = "1"
uv run pytest tests/live/test_product_crawler_live.py -v
Remove-Item Env:RUN_LIVE_CRAWLER
```
