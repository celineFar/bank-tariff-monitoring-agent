# Indexing projections

`IndexingPipeline.refresh()` composes the existing acquisition, structural
normalization, source discovery, and semantic extraction services. Selected normalized
documents become source-faithful `KnowledgeDocument` values; small documents remain
whole and oversized material splits only at natural block/table/page boundaries, into
chunks of at most `CHUNK_SIZE_CHARS` (500–2,000).
Every piece of a split table repeats its title and header row, and a chunk that starts
mid-section opens with its heading path (`## A / B`), so no chunk loses its context.
Split pieces keep the discovery labels of the unit they came from.

Source chunks retain official wording, URL, page/section/locator, language, checksum,
extraction method, and quality. They are stored as text: a snapshot's documents anchor
each fact's evidence and are what a reviewer reads; nothing embeds or searches them.

A version's identity is its source's raw bytes (`content_sha256`) **and** its projected
chunks (`projection_sha256`, which includes `PROJECTION_SCHEMA_VERSION`), so the same
bytes projected differently are another version, never a rewrite of the live one.

The returned source manifest records observed/selected/indexed sources,
version IDs, document/chunk counts, warnings, failures, and stage timings. A failed
refresh publishes nothing for that offering. See `docs/knowledge-store.md` for how a
publication becomes the offering's index.

## Projection refinements (first iteration)

- **Per-fee citations.** Each fee fact cites the fee field's citations whose quote
  contains the fee's description (up to its first colon) or, failing that, its number;
  the whole field's citations only when neither matches.
- **Collateral service fees.** When the tariff states no collateral (Credit Line,
  Overdraft), general loan-service fees about collateral, pledges, security interests
  or vehicles are not projected; a fee that says it is "not related to the collateral"
  is kept. Product-scope fees are never filtered.
- **Inferred rate currency.** A rate fact without a currency takes the currency of the
  offering's amount or credit-limit facts when they carry exactly one, and records
  `currency inferred from the offering's loan amounts` as an `other` condition.
- **Readable sections.** Each fact citation's locator carries `section`, the page or
  document section the citation's passage sits in.

