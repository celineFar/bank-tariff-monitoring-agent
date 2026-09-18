# ruff: noqa: RUF001

from app.services.html_parser import HtmlArtifactParser


def test_parser_preserves_unicode_tables_links_and_locators() -> None:
    html = """
    <html lang="hy">
      <head>
        <title>Վարկ</title>
        <link rel="canonical" href="/hy/loan">
      </head>
      <body>
        <h1>Սպառողական վարկ</h1>
        <p>Գումար՝ մինչև 10 000 000 AMD</p>
        <table>
          <caption>Պայմաններ</caption>
          <tr><th>Ժամկետ</th><th>Տոկոս</th></tr>
          <tr><td>60 ամիս</td><td>13%</td></tr>
        </table>
        <a href="/files/terms.pdf" type="application/pdf">Պայմաններ</a>
        <a href="https://example.com/other.pdf">External</a>
      </body>
    </html>
    """

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url="https://ameriabank.am/products/loan"
    )

    assert parsed.canonical_url == "https://ameriabank.am/hy/loan"
    assert parsed.title == "Վարկ"
    assert parsed.language == "hy"
    assert "10 000 000 AMD" in parsed.visible_text
    assert parsed.tables[0].headers == ("Ժամկետ", "Տոկոս")
    assert parsed.tables[0].rows == (("60 ամիս", "13%"),)
    assert parsed.links[0].downloadable is True
    assert parsed.links[0].same_allowlisted_source is True
    assert parsed.links[1].same_allowlisted_source is False
    assert parsed.blocks[0].locator.css_selector
    assert parsed.blocks[0].locator.xpath
    assert "| Ժամկետ | Տոկոս |" in parsed.markdown


def test_parser_rejects_off_domain_canonical_and_ignores_hidden_content() -> None:
    html = """
    <html><head><link rel="canonical" href="https://evil.example/loan"></head>
    <body>
      <p>Visible official content</p>
      <div hidden><p>Hidden unrelated value 99%</p></div>
      <script>document.write('not evidence')</script>
    </body></html>
    """

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url="https://ameriabank.am/loan"
    )

    assert parsed.canonical_url == "https://ameriabank.am/loan"
    assert "99%" not in parsed.visible_text
    assert "document.write" not in parsed.visible_text
