"""Reproduce the confirmed normalization problems on small HTML fixtures.

    uv run python fix-process/normalization/data/probe_normalization.py

Output before any fix: probe-output-before.txt.
"""

from app.services.block_normalizer import normalize_block
from app.services.html_parser import HtmlArtifactParser
from app.services.table_normalizer import normalize_table

P = HtmlArtifactParser(("ameriabank.am",))
URL = "https://ameriabank.am/x"


def run(name, html):
    p = P.parse(f"<html><body>{html}</body></html>", source_url=URL)
    print(f"\n=== {name}")
    for b in p.blocks:
        nb = normalize_block(b)
        print(
            f"  block {b.id} {b.type.value} path={b.heading_path} text={b.text!r} fields={nb.fields} scalars={[(s.raw, str(s.value), s.unit) for s in nb.scalar_candidates]}"
        )
    for t in p.tables:
        nt = normalize_table(t)
        print(
            f"  table {t.id} title={nt.title!r} headers={nt.headers} inferred={nt.headers_inferred}"
        )
        for r in nt.rows:
            print(
                "    row",
                r.id,
                [c.text for c in r.cells],
                [c.list_items for c in r.cells if c.list_items],
            )
        for n in nt.notes:
            print("    note marker=", n.marker, "text=", repr(n.text))


run(
    "minified table block text",
    "<h2>Rates</h2><table><tr><th>Term</th><th>Amount</th></tr><tr><td>12</td><td>500 000 AMD</td></tr></table>",
)
run(
    "card h3+p",
    '<div class="card"><h3>Consumer loan</h3><p>Up to 5 000 000 AMD</p></div>',
)
run(
    "row header table",
    '<table><tr><th scope="row">Interest rate</th><td>12%</td></tr><tr><th scope="row">Term</th><td>60 months</td></tr></table>',
)
run(
    "title row + numeric note",
    '<table><tr><td colspan="2">Consumer loan tariffs</td></tr><tr><th>Item</th><th>Value</th></tr><tr><td>Rate</td><td>12%¹</td></tr><tr><td colspan="2">5 000 000 AMD is the maximum amount for unsecured loans</td></tr><tr><td colspan="2">¹ Fixed for the first year</td></tr></table>',
)
run(
    "single column",
    "<table><tr><td>Loan conditions</td></tr><tr><td>Rate 12%</td></tr><tr><td>Term up to 60 months</td></tr></table>",
)
run(
    "list items decimals",
    "<table><tr><th>Item</th><th>Value</th></tr><tr><td>Rate</td><td>12.5% annual</td></tr><tr><td>Effective</td><td>01.03.2025</td></tr></table>",
)
run(
    "nested table",
    "<table><tr><th>Product</th><th>Terms</th></tr><tr><td>Loan</td><td><table><tr><td>AMD</td><td>12%</td></tr><tr><td>USD</td><td>8%</td></tr></table></td></tr></table>",
)
run(
    "nested li",
    "<ul><li>Documents<ul><li>Passport</li><li>Income 12%</li></ul></li></ul>",
)
run(
    "section rows in table",
    '<table><tr><th>Item</th><th>Value</th></tr><tr><td colspan="2">AMD loans</td></tr><tr><td>Fee</td><td>0%</td></tr><tr><td colspan="2">USD loans</td></tr><tr><td>Fee</td><td>0%</td></tr><tr><td>Rate</td><td>9%</td></tr></table>',
)
run(
    "heading leak across accordions",
    '<div class="accordion-item"><button class="accordion-header">Mortgage</button><div class="accordion-panel"><h4>Mortgage rates</h4><p>Rate 10%</p></div></div><div class="accordion-item"><button class="accordion-header">Consumer</button><div class="accordion-panel"><p>Rate 18%</p></div></div>',
)
run(
    "text-only div panel",
    '<div class="accordion-item"><div class="accordion-title">Fees</div><div class="accordion-content">Service fee 1% of loan amount</div></div>',
)
run("dt/dd", "<dl><dt>Interest rate</dt><dd>12%</dd></dl>")
run("p inside dd", "<dl><dt>Rate</dt><dd><p>12%</p></dd></dl>")
run(
    "two header rows",
    '<table><tr><th rowspan="2">Term</th><th colspan="2">Rate</th></tr><tr><th>AMD</th><th>USD</th></tr><tr><td>12 months</td><td>12%</td><td>8%</td></tr></table>',
)
run(
    "bold first data row",
    "<table><tr><td><strong>Rate</strong></td><td><strong>12%</strong></td></tr><tr><td>Term</td><td>60 months</td></tr></table>",
)
