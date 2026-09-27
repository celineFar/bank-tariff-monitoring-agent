# RRS05: ranking with conditional variants

**What.** `family_rank` over fixtures with conditional variants (card type), mixed
currencies, and identical offerings.

**How.** `uv run pytest tests/unit/test_structured_tariff_query.py -k rank`.

**Pass bar.** Answered per group; the winner's conditions are reported; an
`incomparable` reason names the actual difference.
