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

Normalization currently applies Unicode NFKC, case folding, trimming, and whitespace
collapse. Phase C reuses this single function and adds the deterministic exact/fuzzy
resolution cascade around it.

## Name review

The Armenian names were checked against Ameriabank's current public navigation and product
labels on 2026-09-20, including the official [consumer-loan and mortgage product
list](https://ameriabank.am/personal/loans/consumer-loans/credit-line). The checked-in unit
fixture asserts all thirteen Armenian primary labels so an incidental catalog edit is
visible in review.

Both API and worker composition load the same catalog. Adding or changing an offering
therefore requires a reviewed catalog change and catalog tests. Sources are never retired
because an enabled seed temporarily fails or a linked source is not rediscovered. Only a
successfully published version with the same stable document key supersedes its previous
active version.
