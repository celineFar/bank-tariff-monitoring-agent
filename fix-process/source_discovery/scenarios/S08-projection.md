# S08: The RAG index holds only the offering's selected content

**What it checks.** Projecting the real primary-mortgage and consumer-loan pages with the
recorded Phase 7 assessments: no site-chrome text, no Express table, and no chunk labelled
`related_product` (SD7).

**Plan items.** SD7, Q3.

**Steps.** Build a `SourceDiscoveryResult` from the recorded block and table assessments,
then `build_selected_source_bundle` and `project_sources(labels=…)`, as the pipeline does.

**Pass criteria.** No site-chrome block text in any chunk; the Express table absent; no
`related_product` in chunk metadata.

**Gemini.** None.

## Result: **PASS**

Raw result: [results/S08.json](results/S08.json). Primary mortgage: 7 chunks, consumer loan:
4 chunks, all labelled `current_product`; no chrome text and no Express table.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 1.6 s |
