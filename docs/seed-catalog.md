# Seed catalog

`app/config/seed_catalog.yaml` is the checked-in runtime catalog for all approved
Ameria consumer-loan and mortgage entry points. Each enabled item binds a stable
`offering_id` to one `ProductType`, display name, HTTPS seed URL, language, and optional
metadata. URLs are acquisition inputs, not business identifiers.

`load_seed_catalog()` validates the complete file before use. It rejects duplicate
offering IDs, duplicate enabled URLs, family/offering mismatches, non-HTTPS URLs, and
hosts outside `ALLOWED_SOURCE_HOSTS`. Both API and worker composition load this
same catalog; adding or changing an offering therefore requires a reviewed catalog
change and catalog tests.

Sources are never retired because an enabled seed temporarily fails or a linked source
is not rediscovered. Only a successfully published version with the same stable
document key supersedes its previous active version.
