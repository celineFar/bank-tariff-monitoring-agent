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


def test_rowspan_tables_expand_without_shifting_and_preserve_cell_structure() -> None:
    html = """
    <html><body><table>
      <tr><td colspan="3">Consumer loan</td></tr>
      <tr><td rowspan="3">Loan terms</td><td>Currency</td><td>AMD</td></tr>
      <tr><td>Term</td><td>60 months</td></tr>
      <tr><td rowspan="2">Repayment method</td><td>Annuity</td></tr>
      <tr><td rowspan="2">Forms of repayment</td><td>Differentiated</td></tr>
      <tr><td>Documents</td><td><ul><li>ID</li><li>Application</li></ul></td></tr>
      <tr><td colspan="3">Footnote text</td></tr>
    </table></body></html>
    """

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url="https://ameriabank.am/loan"
    )
    table = parsed.tables[0]

    assert table.title == "Consumer loan"
    assert table.headers == ("Section", "Item", "Terms")
    assert table.headers_inferred is True
    assert table.rows == (
        ("Loan terms", "Currency", "AMD"),
        ("Loan terms", "Term", "60 months"),
        ("Loan terms", "Repayment method", "Annuity"),
        ("Forms of repayment", "Repayment method", "Differentiated"),
        ("Forms of repayment", "Documents", "• ID\n• Application"),
    )
    assert table.notes == ("Footnote text",)
    assert any(cell.rowspan == 3 for cell in table.cells)
    assert "| Loan terms | Term | 60 months |" in parsed.markdown
    assert "• ID<br>• Application" in parsed.markdown


def test_accordion_questions_answers_and_inline_links_remain_associated() -> None:
    html = """
    <html><body>
      <div class="cs-accordion__body">
        <div class="cs-accordion__title">How can I apply?</div>
        <div class="cs-accordion__panel">
          <p>Apply using <a href="/application">this link</a>.</p>
        </div>
      </div>
    </body></html>
    """

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url="https://ameriabank.am/loan"
    )
    question, answer = parsed.blocks

    assert question.type.value == "accordion"
    assert question.text == "How can I apply?"
    assert answer.parent_id == question.id
    assert answer.link_ids == (parsed.links[0].id,)
    assert str(parsed.links[0].url) == "https://ameriabank.am/application"
    assert "[this link](<https://ameriabank.am/application>)" in parsed.markdown


def test_bold_first_row_is_preserved_as_table_header() -> None:
    html = """
    <html><body><table>
      <tr><td><strong>Purpose</strong></td><td><strong>Rates and Fees</strong></td></tr>
      <tr><td>Change repayment date</td><td>AMD 10,000</td></tr>
    </table></body></html>
    """

    table = (
        HtmlArtifactParser(("ameriabank.am",))
        .parse(html, source_url="https://ameriabank.am/loan")
        .tables[0]
    )

    assert table.headers == ("Purpose", "Rates and Fees")
    assert table.rows == (("Change repayment date", "AMD 10,000"),)


def test_browser_visibility_markers_exclude_never_visible_dom() -> None:
    html = """
    <html><body>
      <p>Visible terms</p>
      <div data-acquisition-visible="false">
        <h3>No offers found matching the selected criteria</h3>
        <a href="/hidden.pdf">Hidden document</a>
        <img src="/hidden.png" alt="Hidden image">
      </div>
    </body></html>
    """

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url="https://ameriabank.am/loan"
    )

    assert parsed.visible_text == "Visible terms"
    assert parsed.links == ()
    assert parsed.images == ()


def test_nested_heading_content_is_not_emitted_twice() -> None:
    tagline = "Installment loans make shopping quick and hassle-free"
    html = f"""
    <html><body>
      <h1>Consumer finance<p>{tagline}</p></h1>
    </body></html>
    """

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url="https://ameriabank.am/loan"
    )

    assert parsed.blocks[0].text == "Consumer finance"
    assert parsed.visible_text.count(tagline) == 1


def test_superscript_reference_keeps_its_text_boundary() -> None:
    html = """
    <html><body><p>Apply in the store<sup>1</sup>just in a few minutes.</p></body></html>
    """

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url="https://ameriabank.am/loan"
    )

    assert parsed.blocks[0].text == "Apply in the store ¹ just in a few minutes."
    assert "store ¹ just" in parsed.markdown


def test_partner_cards_and_tab_table_context_are_preserved() -> None:
    html = """
    <html><body>
      <p><a href="#products" data-acquisition-tab-control="true"
         aria-controls="products">Purchasing products</a></p>
      <div class="privileges-card">
        <div class="partner-card__item">
          <div class="partner-card__item-info">
            <p>ZIGZAG</p><p>ZIGZAG LLC</p>
          </div>
        </div>
      </div>
      <div id="products" data-acquisition-context-title="Purchasing products"
           data-acquisition-visible="true" style="display: none">
        <table><tr><td>Terms</td><td>Currency</td><td>AMD</td></tr></table>
      </div>
    </body></html>
    """

    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        html, source_url="https://ameriabank.am/loan"
    )

    cards = [block for block in parsed.blocks if block.type.value == "card"]
    assert len(cards) == 1
    assert cards[0].text == "ZIGZAG\nZIGZAG LLC"
    assert parsed.tables[0].title == "Purchasing products"
    assert parsed.interactive_controls[0].aria_controls == "products"
    assert parsed.links[0].raw_href == "#products"
    assert parsed.links[0].fragment == "products"
    assert (
        "[Purchasing products](<https://ameriabank.am/loan#products>)"
        in parsed.markdown
    )
