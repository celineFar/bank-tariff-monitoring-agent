# Seed catalog

`app/config/seed_catalog.yaml` is the checked-in runtime catalog for every supported
Ameria consumer-loan and mortgage family/offering. Version 2 separates stable business
identifiers from the language users employ to refer to them.

## Structure

The `families` collection contains exactly one entry for each `ProductType`. The
`offerings` collection binds each stable `OfferingId` to its family and HTTPS acquisition
seed. Every family and offering has exactly two localized term sets:

- `en`: English primary name, aliases, synonyms, and optional transliterations;
- `hy`: Armenian primary name, aliases, synonyms, and optional Latin
  transliterations.

Each offering may declare a `category` -- `consumer_loan`, `overdraft`, `credit_line` or
`mortgage` -- which must belong to its family (`mortgage` for the mortgage family, one
of the first three for consumer loans). Without one it is the family's own category.
Semantic extraction asks exactly that category's fields (an overdraft's credit limit
and grace period, a mortgage's down payment), and a model answer naming another
category goes to review. `overdraft` and `credit_line` declare theirs.

The existing offering `display_name` and `language` fields remain available to the
monitoring/indexing pipeline. `display_name` must match the primary English localized
name after normalization. URLs remain acquisition inputs, not product identifiers.

## Validation

`load_seed_catalog()` validates the complete file before any runtime service receives it.
It rejects:

- missing or duplicate product-family definitions;
- duplicate offering IDs or enabled seed URLs;
- family/offering mismatches;
- missing English or Armenian names;
- whitespace-only, repeated, or normalized-empty resolution terms;
- normalized term collisions between different families or between different offerings;
- a legacy display name that disagrees with the English primary name;
- non-HTTPS URLs; and
- hosts outside `ALLOWED_SOURCE_HOSTS`.

A family term may intentionally equal a child offering term—for example, “Consumer
Loans”—because the approved intent-sensitive rules distinguish a family-wide request from
a request requiring one tariff value. Collisions between two offerings or two families
are rejected because deterministic exact matching could not safely choose between them.

Normalization applies Unicode NFKC, case folding, punctuation/separator collapse,
trimming, and whitespace collapse. The resolver's exact catalog matcher (the V5
cross-check against the interpreter, see `docs/intent-resolution.md`) reuses this
single function for user input, IDs, names, aliases, synonyms, and transliterations.
The request interpreter receives every name, alias, synonym and transliteration of the
catalog in each call.

## Name review

The Armenian names were checked against Ameriabank's current public navigation and product
labels on 2026-09-20, including the official [consumer-loan and mortgage product
list](https://ameriabank.am/personal/loans/consumer-loans/credit-line). The checked-in unit
fixture asserts all thirteen Armenian primary labels so an incidental catalog edit is
visible in review.

Both API and worker composition load the same catalog. Adding or changing an offering
therefore requires a reviewed catalog change and catalog tests. A failed, review-held, or
otherwise unpublished run leaves the offering's active sources as they are, so a seed that
temporarily fails retires nothing. An accepted publication (`activate_snapshot_set`,
`app/repositories/knowledge_publication.py`) makes the snapshot's document set the
offering's whole active set: it retires every active document of the offering outside
that set, such as a changed page's old version or a PDF no longer linked. An accepted
publication with no documents leaves the previous set in place.
