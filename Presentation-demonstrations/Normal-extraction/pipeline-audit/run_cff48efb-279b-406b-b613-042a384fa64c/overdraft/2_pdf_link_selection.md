# PDF link selection

Source discovery's first step: for each PDF that deterministic admission let through, whether it belongs to this offering, judged from its link before transcription. Only `current_product`, `shared_terms` and `unclear` PDFs are transcribed.

| Document | Decision | Role | By | Transcribed | Reason |
|---|---|---|---|---|---|
| Informational summary of unsecured overdraft | current_product | product_terms | llm (gemini-3.1-flash-lite) | yes | The document is an informational summary specifically for the unsecured overdraft, which is a core component of the overdraft offering described on the page. |
| Lending terms for individuals / Card overdrafts | current_product | product_terms | llm (gemini-3.1-flash-lite) | yes | The document title explicitly mentions card overdrafts, which matches the offering's name and description. |
| Loan service fees | shared_terms | fees | llm (gemini-3.1-flash-lite) | yes | This document covers general loan service fees, which typically apply to multiple loan products including the overdraft. |
| Informational summary of unsecured overdraft | not asked (admission skipped it) | — | — | no | — |
| Informational summary of unsecured overdraft | not asked (admission skipped it) | — | — | no | — |
| Informational summary of unsecured overdraft | not asked (admission skipped it) | — | — | no | — |
| Informational summary of unsecured overdraft | not asked (admission skipped it) | — | — | no | — |
| Lending terms for individuals without collateral / Card overdrafts | not asked (admission skipped it) | — | — | no | — |
| Lending terms for individuals without collateral / Card overdrafts | not asked (admission skipped it) | — | — | no | — |
| Lending terms for individuals without collateral / Card overdrafts | not asked (admission skipped it) | — | — | no | — |
