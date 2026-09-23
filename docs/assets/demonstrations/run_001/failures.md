# Deliverable 13 — Controlled failure scenarios with safe, typed outcomes

**PASS — 8/8 criteria**

## Steps

1. 1) Requested a document from a host outside the allowlist: rejected before any request with DisallowedSourceUrl: Source host is not allowlisted: evil.example.com.
2. 2) Requested a page that returns 404: raised HtmlRetrievalError mapped to source.not_found after 1 attempt(s); a client error is not retried.
3. 3) Simulated a connect timeout: raised HtmlRetrievalError mapped to source.timeout after exactly 2 bounded attempt(s), then gave up.
4. 4) Served an unexpected content type: rejected as source.mime_rejected instead of being parsed.
5. 5) Asked about an offering with no accepted snapshot: status=missing, reason='no accepted offering projection', 0 facts returned.

## Notes

- Transport failures are scripted through httpx.MockTransport so the demonstration is reproducible offline, but the retriever, allowlist, retry policy, and failure mapping are the production code paths.

## Success criteria

| | Criterion | Expected | Observed |
| --- | --- | --- | --- |
| PASS | off-domain source rejected | a URL outside the approved bank domain is refused before any request | DisallowedSourceUrl |
| PASS | missing document handled | a 404 maps to the specific source.not_found code, not a generic error | HtmlRetrievalError -> source.not_found |
| PASS | client errors are not retried | a 404 is attempted once rather than burning the retry budget | 1 attempt(s) |
| PASS | timeout maps to a typed code | a connect timeout becomes source.timeout | source.timeout |
| PASS | retries are bounded | a transient failure retries at most max_attempts times | 2 attempt(s), limit 2 |
| PASS | unexpected content type rejected | a non-HTML payload is refused instead of parsed | source.mime_rejected |
| PASS | missing snapshot abstains | a question with no accepted data returns a stated absence | status=missing |
| PASS | no fabricated business data | every failure path returns zero tariff values | 0 facts, answer=None |
