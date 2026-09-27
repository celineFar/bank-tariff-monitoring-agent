# Indexing and retrieval projections

`IndexingPipeline.refresh()` composes the existing acquisition, structural
normalization, source discovery, and semantic extraction services. Selected normalized
documents become source-faithful `KnowledgeDocument` values; small documents remain
whole and oversized material splits only at natural block/table/page boundaries, into
chunks of at most `CHUNK_SIZE_CHARS` (500–2,000; inside the embedding model's input).
Every piece of a split table repeats its title and header row, and a chunk that starts
mid-section opens with its heading path (`## A / B`), so no chunk loses its context.
Split pieces keep the discovery labels of the unit they came from.

Accepted extractions also produce one deterministic `offering_summary` document. It is
a compact retrieval aid containing validated values and evidence references, never the
citation of record. Its content carries no timestamp (the time is `retrieved_at` and
`metadata.as_of`), so an unchanged tariff keeps its version. Source chunks retain
official wording, URL, page/section/locator, language, checksum, extraction method, and
quality.

A version's identity is its source's raw bytes (`content_sha256`) **and** its projected
chunks (`projection_sha256`, which includes `PROJECTION_SCHEMA_VERSION`), so the same
bytes projected differently are another version, never a rewrite of the live one.

Only accepted snapshots are embedded in the pipeline. A review-required run's documents
are published as text only (no embedding call); an approval embeds them after it
commits. A provider quota refusal publishes the remaining documents as text too; the
worker's embedding sweep fills their vectors later, and lexical search serves them in
the meantime. The returned source manifest records observed/selected/indexed sources,
version IDs, document/chunk counts, warnings, failures, and stage timings. A failed
refresh publishes nothing for that offering. See `docs/knowledge-store.md` for how a
publication becomes the offering's index.
