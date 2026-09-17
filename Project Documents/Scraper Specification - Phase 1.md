# Phase 1 — deterministic crawling/scraping implementation specification

## 1. Objective

Implement a crawler that uses a **known product registry** as its starting point.

For every known subproduct, the crawler must:

1. fetch the configured English product page;
2. locate/fetch the Armenian version;
3. extract all links from the page;
4. identify links likely to be:
    - PDFs;
    - tariff documents;
    - lending terms;
    - information guides;
    - information summaries;
    - terms and conditions;
    - special offers;
    - campaign pages;
    - other downloadable attachments relevant to the same product;
5. optionally crawl those directly linked supporting pages one additional level to discover documents;
6. validate every URL;
7. follow redirects safely;
8. deduplicate sources;
9. return a structured source inventory for that exact subproduct.

The initial product-page URLs may be hard-coded.

**PDF/document URLs must not be hard-coded.**

---

# 2. Known Consumer Loan registry

Start with these direct Consumer Loan products.

```
CONSUMER_PRODUCTS = {
    "consumer.unsecured": {
        "name": "Consumer loan",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "consumer-loans/consumer-loans"
        ),
    },

    "consumer.overdraft": {
        "name": "Overdraft",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "consumer-loans/overdraft"
        ),
    },

    "consumer.credit_line": {
        "name": "Credit line",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "consumer-loans/credit-line"
        ),
    },

    "consumer.finance": {
        "name": "Consumer finance",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "consumer-loans/consumer-finance"
        ),
    },

    "consumer.finance.online": {
        "name": "Online consumer finance",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "consumer-loan/online-consumer-finance"
        ),
    },
}
```

Those five direct entries are currently exposed under Ameriabank's Consumer Loans navigation.

Note the inconsistent path:

```
consumer-loans/...
consumer-loan/online-consumer-finance
```

Do not derive URLs from naming rules.

The current online consumer-finance page confirms this singular path.

---

# 3. Known Mortgage registry

Use these as Phase-1 Mortgage seeds:

```
MORTGAGE_PRODUCTS = {
    "mortgage.online.primary_secondary": {
        "name": "Online mortgage - primary and secondary market",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "mortgage/online"
        ),
    },

    "mortgage.purchase.primary": {
        "name": "Mortgage loan for primary market",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "mortgage/primary"
        ),
    },

    "mortgage.diaspora": {
        "name": "Mortgage loan for Diaspora",
        "url_en": (
            "https://ameriabank.am/en/campaigns/"
            "mortgage-loan-for-diaspora"
        ),
    },

    "mortgage.purchase.secondary": {
        "name": "Real estate loan for secondary market",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "mortgage/secondary-market"
        ),
    },

    "mortgage.commercial_real_estate": {
        "name": "Commercial real estate loan",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "mortgage/commercial-mortgage"
        ),
    },

    "mortgage.quick": {
        "name": "Quick mortgage loan",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "mortgage/express-loan"
        ),
    },

    "mortgage.no_income_verification": {
        "name": "Mortgage without income verification",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "mortgage/no-income-verification"
        ),
    },

    "mortgage.renovation": {
        "name": "Renovation loan",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "mortgage/renovation-mortgage"
        ),
    },

    "mortgage.construction": {
        "name": "Construction loan",
        "url_en": (
            "https://ameriabank.am/en/personal/loans/"
            "mortgage/construction-mortgage"
        ),
    },
}
```

Ameriabank's current Mortgage navigation exposes these product variants.

The current pages for online mortgage, primary market, secondary market, commercial, renovation, and construction resolve under these paths.

Do not make assumptions such as:

```
assert "/mortgage/" in product_url
```

because the Diaspora mortgage is under `/campaigns/`.

---

# 4. Registry structure

Prefer a model rather than loose dictionaries:

```
from pydantic import BaseModel, HttpUrl


class ProductSeed(BaseModel):
    product_id: str
    category: str
    name: str
    url_en: str
```

Example:

```
ProductSeed(
    product_id="mortgage.purchase.secondary",
    category="mortgage",
    name="Real estate loan for secondary market",
    url_en="https://ameriabank.am/en/personal/loans/mortgage/secondary-market",
)
```

The registry is the only hard-coded product knowledge in Phase 1.

---

# 5. Crawl flow per product

For every `ProductSeed` run this exact sequence:

```
configured EN product URL
        ↓
validate URL
        ↓
HTTP GET
        ↓
follow safe redirects
        ↓
parse HTML
        ↓
extract page metadata
        ↓
discover HY page
        ↓
extract all links
        ↓
classify candidate links
        ↓
fetch relevant supporting pages
        ↓
extract documents from supporting pages
        ↓
validate discovered documents
        ↓
deduplicate
        ↓
return ProductSourceInventory
```

---


# 12. Extract links from more than `<a href>`

At minimum inspect:

```
a[href]
link[href]
iframe[src]
embed[src]
object[data]
source[src]
```

Also inspect likely custom attributes:

```
data-href
data-url
data-src
data-file
data-download
```

Normalize every discovered relative URL using:

```
urllib.parse.urljoin
```

---

# 13. Detect URL strings inside inline JavaScript conservatively

Ameriabank may bind downloads through scripts/UI components.

Inspect:

```
onclick
inline <script>
JSON blobs
```

for literal URLs only.

Do not execute arbitrary JavaScript during static parsing.

Useful patterns include:

```
.pdf
/Portals/0/files/
download
document
```

Extract literal candidate URLs and validate them normally.

---

# 14. Armenian page discovery

Do not simply assume:

```
/en/foo → /foo
```

even though this often works.

First inspect the actual language switcher.

Look for links whose:

```
hreflang == "hy"
lang == "hy"
anchor text == "hy"
```

or whose surrounding UI clearly represents Armenian.

Store the discovered URL.

Only use the `/en/` removal pattern as a **fallback candidate**, and verify it before accepting.

Example logic:

```
def discover_armenian_variant(page) -> str | None:
    # 1. explicit hreflang
    # 2. language-switch navigation
    # 3. verified path fallback
```

Verify that:

```
HTTP 200
page title/H1 is not an error
host is Ameriabank
```

---

# 15. Fetch both EN and HY product pages

Once Armenian URL is discovered:

```
fetch EN
fetch HY
```

Run document/link discovery independently on both.

Do not assume EN and HY contain identical links.

This is important because one language version can expose a document the other does not.

---

# 16. Candidate link classification

For every discovered link, classify into one of:

```
class CrawlLinkType(str, Enum):
    DOCUMENT = "document"
    SUPPORTING_PAGE = "supporting_page"
    LANGUAGE_VARIANT = "language_variant"
    EXTERNAL = "external"
    IGNORE = "ignore"
```

This is deterministic Phase-1 classification.

No LLM required.

---

# 17. Recognize document candidates

Treat as strong document candidates when URL or link context contains:

```
.pdf
.doc
.docx
.xls
.xlsx
```

with PDF being the main case.

Also consider paths such as:

```
/Portals/0/files/
/userfiles/file/
```

as document candidates.

But validate content after download.

---

# 18. Recognize relevant document link text

Inspect anchor text and nearby text.

English keywords:

```
terms
terms and conditions
tariff
tariffs
rates
fees
commission
lending terms
loan terms
information guide
information summary
download
details
```

Armenian:

```
պայմաններ
սակագներ
պայմաններ և սակագներ
տեղեկատվական ամփոփագիր
ամփոփաթերթիկ
վարկավորման պայմաններ
տոկոսադրույք
միջնորդավճար
վճար
ներբեռնել
```

Don't require the filename itself to be meaningful.

---

# 19. Supporting-page classification

Follow a non-document link one extra level when the link is likely relevant to the same product.

Examples:

```
Terms and conditions
Special offer
Information
Details
Campaign
Fees
Tariffs
Learn more
```

And product-specific paths such as:

```
/special-offers/
/campaigns/
```

But do **not** follow:

```
Apply now
contact
branch finder
news unrelated to product
login
MyAmeria
social media
footer links
privacy
terms of use
```

---

# 20. Maximum supporting crawl depth

Phase 1 should remain bounded.

Recommended:

```
Product page = depth 0
Direct supporting page = depth 1
Documents linked from it = retrieve
STOP
```

Do not recurse supporting-page → supporting-page → supporting-page indefinitely.

Use:

```
MAX_SUPPORTING_PAGE_DEPTH = 1
```

---

# 21. Same-product relevance guard

Before crawling a supporting HTML page, require at least one deterministic relevance signal:

```
link originated in main product content
OR
anchor contains tariff/terms/special-offer wording
OR
URL is under same product path
OR
page is a campaign directly linked from product page
```

Avoid crawling generic navigation items just because they're in the page DOM.

---

# 22. Exclude global navigation noise

Ameriabank pages include global navigation links to many other loan products.

If you simply collect every `<a>`, each product crawl will discover the entire bank catalog.

Phase 1 must distinguish:

```
main page content links
```

from:

```
global menu/footer links
```

Preferred approaches:

1. identify the main content container;
2. ignore `header`, `nav`, `footer`;
3. alternatively blacklist links repeated identically across many product pages.

Do not treat sibling product navigation links as documents/supporting sources of the current product.

For example, the Credit Line page also shows links to Overdraft, Consumer Loan and Consumer Finance. Those are siblings, not Credit Line supporting sources.

---

# 26. PDF/document download

For every document candidate:

```
validate URL
→ HEAD optionally
→ GET
→ validate final redirect
→ validate content type
→ validate bytes
```

Do not rely only on a `HEAD`; servers sometimes handle it differently.

GET is authoritative.

---
# 30. Document metadata for crawl inventory

implement in a way that matches the rest of the system

---

# 31. URL deduplication

Deduplicate URLs conservatively.

Safe normalization:

```
lowercase scheme
lowercase hostname
remove #fragment
remove known tracking parameters
normalize default port
resolve relative URLs
```

Do not alter path spelling or case aggressively.

Preserve both:

```
original_url
normalized_url
```

---

# 32. Content-level deduplication

Two different Ameriabank URLs may point to identical document bytes.

Use:

```
SHA-256
```

to identify this.

Structure:

```
DocumentResource(
    sha256="...",
    urls=[
        "...eng.pdf",
        "...another-path..."
    ],
)
```

Do not download/process the same bytes repeatedly.

---

# 33. Page deduplication

Deduplicate product/supporting HTML pages by:

1. final URL;
2. optionally canonical `<link rel="canonical">`.

Don't deduplicate EN and HY merely because their layout is the same.

Language variants are separate sources.

---

# 34. Do not generate PDF URLs

Never do:

```
pdf_url = product_name.replace(" ", "_") + ".pdf"
```

Ameriabank filenames can contain historical naming inconsistencies.

Only accept document URLs actually discovered from:

```
page DOM
rendered DOM
directly linked supporting page
```

in Phase 1.

---

# 35. Do not crawl sibling products during a product crawl

Example:

While crawling:

```
consumer.credit_line
```

Ameriabank navigation may show:

```
Overdraft
Consumer loan
Consumer finance
```

These are not relevant supporting links.

They already have separate registry entries.

Ignore them during this product's source collection.

The Credit Line page currently exposes those sibling links.

---

# 36. Special-offer pages

If a known product page directly links to a special offer:

```
follow it
```

provided:

```
same Ameriabank domain
clearly product-related
depth <= 1
```

Record it as:

```
source_type="supporting_page"
```

Then scan that special-offer page for documents.

Ameriabank has, for example, a current Consumer Finance special-offer page with explicit rates and terms, so such linked pages can be meaningful sources.

---

# 37. Campaign page handling

Known product seeds themselves may live under `/campaigns/`, as with Diaspora mortgage.

Therefore:

```
/campaigns/
```

must not automatically mean irrelevant.

Rule:

```
if page is a configured product seed:
    treat as PRODUCT_PAGE
elif directly linked from configured product:
    treat as SUPPORTING_PAGE
```

No semantic agent needed in Phase 1.

---

# 38. Calculators

For Phase 1:

```
record but don't recursively interact with calculators
```

If product content links to a calculator:

```
source_type = "calculator_reference"
```

Do not click/type values.

Dynamic calculator extraction belongs outside this crawling phase unless later explicitly required.

---

# 39. External links

If the page links to:

```
myhome.am
mycar.am
government sites
partner stores
social networks
```

record optionally:

```
ExternalReference(
    url=...,
    referrer=...,
)
```

but do not crawl.

---

# 40. Crawl output model

implement this in a way that suits the rest of the system.

---


# 41. Example expected result

```
{
  "product_id": "mortgage.purchase.secondary",
  "product_name": "Real estate loan for secondary market",

  "product_page_en": {
    "final_url": "https://ameriabank.am/en/personal/loans/mortgage/secondary-market",
    "language": "en",
    "status_code": 200
  },

  "product_page_hy": {
    "final_url": "https://ameriabank.am/personal/loans/mortgage/secondary-market",
    "language": "hy",
    "status_code": 200
  },

  "supporting_pages": [],

  "documents": [
    {
      "source_url": "...pdf",
      "referrer_url": "...secondary-market",
      "content_type": "application/pdf",
      "sha256": "...",
      "language_hint": "en"
    }
  ],

  "warnings": [],
  "errors": []
}
```

---


---

# 43. Parallelism

Products may be fetched concurrently, but limit concurrency.

For example:

```
MAX_CONCURRENT_REQUESTS = 4
```

Use a semaphore.

Do not hammer the site.

---

# 44. Per-host rate limiting

Add a small delay or rate limiter.

Example conceptual maximum:

```
2 requests/second
```

This is an engineering choice, not an Ameriabank-published limit.

Make it configurable.

---

# 45. Cache repeated requests inside one run

If many product pages contain the same common resource:

```
url_cache: dict[str, FetchResult]
```

Avoid fetching it repeatedly.

Especially useful if EN/HY pages link to the same PDF.

---

# 46. Structured failure handling

Do not throw away the entire crawl when one product fails.

Possible product result:

```
{
  "product_id": "consumer.overdraft",
  "status": "PARTIAL",
  "errors": [
    {
      "type": "HTTP_TIMEOUT",
      "url": "...",
      "attempts": 3
    }
  ]
}
```

Continue crawling other products.

---

# 47. Phase-1 statuses

Use something simple:

```
class CrawlStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
```

`PARTIAL` if:

```
EN page succeeded
HY page failed
```

or:

```
product page succeeded
one linked document failed
```

---

# 48. Logging

For every HTTP operation log:

```
product_id
requested_url
final_url
status_code
duration_ms
content_type
bytes
retry_count
```

For discovered links log:

```
product_id
referrer
candidate_url
classification
reason
```

Do not log entire PDF contents.

