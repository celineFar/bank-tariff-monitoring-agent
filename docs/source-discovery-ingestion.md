# Official source discovery and local ingestion

Component 6 builds on the exact-product crawler rather than replacing its safety
checks. It returns two deliberately different classes of candidate:

- validated product pages, supporting pages, and documents already retrieved by the
  restricted crawler;
- relevant same-domain URLs proposed by bounded public-sitemap inspection, marked
  `not_retrieved` until a later validation/ranking decision retrieves them.

Candidates retain their product, source type, origin, normalized and original URL,
discovery path, match signals, retrieval status, status code, MIME type, and checksum
where content was retrieved. Candidate status is not an authority decision.

## Persisted artifacts

`SourceIngestionService` stores only bytes that the crawler or document downloader
already validated. The default `LocalArtifactStore` uses keys such as:

```text
data/artifacts/
  raw/ab/abcdef...0123.pdf
  raw/f1/f12345...9876.html
  manifests/<ingestion-run-id>.json
```

The filename is derived from SHA-256 and a trusted MIME-to-extension mapping, never
from an untrusted URL. Repeated bytes reuse the same immutable artifact. Manifests
contain metadata and artifact keys, not raw document bodies, so subsequent parsers
can load exact versioned input with `ArtifactStore.read(storage_key)`.

The artifact root is ignored by Git. Docker Compose mounts one `source_artifacts`
volume into both API and worker containers. This local backend is intentionally
behind the `ArtifactStore` protocol so a future backend does not change discovery,
parsing, or chunking contracts.

## Run discovery and ingestion

All registered products:

```powershell
uv run python scripts\discover_and_ingest_sources.py --pretty
```

One product:

```powershell
uv run python scripts\discover_and_ingest_sources.py `
  --product-id consumer.finance `
  --pretty
```

The command prints the artifact root and manifest key. The manifest is the handoff
contract for PDF/Office extraction, HTML cleaning, OCR routing, and chunking.
