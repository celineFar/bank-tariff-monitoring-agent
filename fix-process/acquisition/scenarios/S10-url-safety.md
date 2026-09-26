# S10: Unsafe URLs are refused before any request

**What it checks.** Plain HTTP, other hosts, look-alike hosts, IP literals, credentials and non-443 ports are rejected by validation, without a request to anyone.

**Plan items.** A15 (port), existing allowlist rules.

**Steps.** Try to acquire six unsafe URLs.

**Pass criteria.** 6/6 fail with `source.url_rejected`; 0 HTTP requests and 0 browser renders.

**Gemini.** None. Acquisition makes no model calls; the harness runs with no API key and
makes any attempt to create a Gemini client fail loudly.

## Result: **PASS**

Run 2026-09-26, branch `integration/process-fixes`. Raw result: [results/S10.json](results/S10.json).

All 6 unsafe URLs were rejected with `source.url_rejected`: plain HTTP, another host, a
look-alike host (`ameriabank.am.example.com`), an IP literal, embedded credentials, and port
8443. **0 HTTP requests and 0 browser renders.** Validation happens before any network
activity.

### Cost

| Gemini calls | Gemini cost | Bank HTTP requests | Browser renders | Data captured | Wall time |
|---|---|---|---|---|---|
| 0 | $0.00 | 0 | 0 | 0.0 MB | 0.1 s |
