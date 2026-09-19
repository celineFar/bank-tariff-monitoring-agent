# Indexing and retrieval projections

`IndexingPipeline.refresh()` composes the existing acquisition, structural
normalization, source discovery, and semantic extraction services. Selected normalized
documents become source-faithful `KnowledgeDocument` values; small documents remain
whole and oversized material splits only at natural block/table/page boundaries.
Stable IDs and hashes include offering, document kind, source identity, and location.

Accepted extractions also produce one deterministic `offering_summary` document. It is
a compact retrieval aid containing validated values and evidence references, never the
citation of record. Source chunks retain official wording, URL, page/section/locator,
language, checksum, extraction method, and quality.

Embedding occurs before the publication transaction. The returned source manifest
records observed/selected/indexed sources, version IDs, document/chunk counts, warnings,
failures, and stage timings. A failed refresh publishes nothing for that offering.
