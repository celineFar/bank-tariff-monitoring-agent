import pytest

from app.domain.crawl import CrawlLinkType, ProductCategory, ProductSeed
from app.domain.product_registry import PRODUCT_REGISTRY
from app.security.urls import DisallowedSourceUrl
from app.services.source_discovery import (
    classify_discovered_link,
    discover_armenian_candidates,
    extract_discovered_links,
    normalize_crawl_url,
)

ALLOWED = ("ameriabank.am", "www.ameriabank.am")
PAGE_URL = "https://ameriabank.am/en/personal/loans/consumer-loans/credit-line"
PRODUCT = ProductSeed(
    product_id="consumer.credit_line",
    category=ProductCategory.CONSUMER,
    name="Credit line",
    url_en=PAGE_URL,
)


HTML = b"""<!doctype html>
<html lang="en"><head>
  <link rel="alternate" hreflang="hy" href="/personal/loans/consumer-loans/credit-line">
  <link rel="stylesheet" href="/assets/site.css">
</head><body><form id="Form">
  <div id="topbar"><a href="/personal/loans/consumer-loans/credit-line">hy</a></div>
  <div id="wsc_main_content">
    <h1>Credit line</h1>
    <a href="/files/terms.pdf?utm_source=test#rates">Terms and conditions</a>
    <iframe src="/files/summary.pdf"></iframe>
    <object data="/files/rates.docx"></object>
    <source src="/files/table.xlsx">
    <div data-download="/files/guide.pdf">Information guide</div>
    <button onclick="window.open('/files/click.pdf')">Download</button>
    <script>const documentUrl = "/Portals/0/files/script.pdf";</script>
    <a href="/en/special-offers/credit-line">Special offer</a>
    <a href="/en/personal/loans/consumer-loans/overdraft">Overdraft</a>
    <a href="/en/personal/loan-calculator">Loan calculator</a>
    <a href="/en/apply">Apply now</a>
    <a href="https://partner.example/offer">Partner offer</a>
  </div>
</form></body></html>"""


def test_normalization_is_conservative_and_removes_tracking() -> None:
    assert (
        normalize_crawl_url(
            "/Files/Terms.PDF?utm_source=x&lang=en#fees",
            base_url=PAGE_URL,
            allowed_hosts=ALLOWED,
        )
        == "https://ameriabank.am/Files/Terms.PDF?lang=en"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://ameriabank.am/file.pdf",
        "https://127.0.0.1/file.pdf",
        "https://user:secret@ameriabank.am/file.pdf",
        "https://ameriabank.am:8443/file.pdf",
    ],
)
def test_normalization_rejects_unsafe_discovered_urls(url: str) -> None:
    with pytest.raises(DisallowedSourceUrl):
        normalize_crawl_url(url, base_url=PAGE_URL)


def test_language_discovery_prefers_explicit_switcher_candidates() -> None:
    candidates = discover_armenian_candidates(
        HTML, page_url=PAGE_URL, allowed_hosts=ALLOWED
    )

    assert candidates[0] == (
        "https://ameriabank.am/personal/loans/consumer-loans/credit-line"
    )
    assert len(candidates) == 1


def test_extracts_all_required_dom_and_literal_script_sources() -> None:
    links = extract_discovered_links(HTML, page_url=PAGE_URL, allowed_hosts=ALLOWED)
    by_url = {link.normalized_url: link for link in links}

    expected_documents = {
        "https://ameriabank.am/files/terms.pdf",
        "https://ameriabank.am/files/summary.pdf",
        "https://ameriabank.am/files/rates.docx",
        "https://ameriabank.am/files/table.xlsx",
        "https://ameriabank.am/files/guide.pdf",
        "https://ameriabank.am/files/click.pdf",
        "https://ameriabank.am/Portals/0/files/script.pdf",
    }
    assert expected_documents <= set(by_url)
    assert by_url["https://ameriabank.am/files/guide.pdf"].attribute == "data-download"
    assert by_url["https://ameriabank.am/files/click.pdf"].attribute == "onclick"
    assert by_url["https://ameriabank.am/Portals/0/files/script.pdf"].attribute == (
        "script"
    )


def test_classification_filters_siblings_and_actions_without_losing_sources() -> None:
    links = extract_discovered_links(HTML, page_url=PAGE_URL, allowed_hosts=ALLOWED)
    classified = {
        link.normalized_url: classify_discovered_link(
            link,
            product=PRODUCT,
            registry=PRODUCT_REGISTRY,
            language_variant_urls=frozenset(
                {"https://ameriabank.am/personal/loans/consumer-loans/credit-line"}
            ),
            allowed_hosts=ALLOWED,
        )
        for link in links
    }

    assert classified["https://ameriabank.am/files/terms.pdf"].classification is (
        CrawlLinkType.DOCUMENT
    )
    assert (
        classified["https://ameriabank.am/en/special-offers/credit-line"].classification
        is CrawlLinkType.SUPPORTING_PAGE
    )
    assert (
        classified[
            "https://ameriabank.am/en/personal/loans/consumer-loans/overdraft"
        ].classification_reason
        == "registered_sibling_product"
    )
    assert (
        classified[
            "https://ameriabank.am/en/personal/loan-calculator"
        ].classification_reason
        == "calculator_reference"
    )
    assert classified["https://ameriabank.am/en/apply"].classification is (
        CrawlLinkType.IGNORE
    )
    assert classified["https://partner.example/offer"].classification is (
        CrawlLinkType.EXTERNAL
    )
