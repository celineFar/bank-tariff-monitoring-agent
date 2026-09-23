# Deliverable 9 — Normal tariff extraction, stored with source evidence

**PASS — 7/7 criteria**

## Input — the captured bank page

1. Fetched https://ameriabank.am/en/personal/loans/consumer-loans/overdraft on 2026-09-22 15:19 UTC in browser mode: 127 content blocks, 3 tables, 10 linked documents.
2. Normalized into 28 documents (1 page, 27 from PDFs) with 69571 blocks.
3. Source discovery assessed 69634 items and admitted 35 as evidence.
4. The extractor was given 120 evidence items in 6 bounded batch(es), schema 2 / prompt 2, model gemini-3.7-flash.

## Extraction — what the model returned from that text

5. interest_rate — 3 variant(s) returned
    - 21.0 rate_type=fixed basis=annual  when currency=AMD; card_type=Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Dig…
    - 20.0 rate_type=fixed basis=annual  when currency=AMD; card_type=Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital, Mastercard World/VISA Pl…
    - 15.0 to 21.0 rate_type=fixed basis=annual  when currency=AMD; application_type=scoring-based loans or loans to workers of specific industries
    - cited "AMD: 21% | | AMD: 20%" [t1:row:9] official_terms
        - from table row in Overdraft | Card loan | Apply online (#Tab2_54240 > div:nth-of-type(1) > div:nth-of-type(1) > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(5) > td:nth-of-type(1))
        - "…Signature , Visa Signature Digital | | Row: Loan terms ³ | Interest rate | AMD: 21% | | AMD: 20% | |"
        - quote matches the captured source text
    - cited "In particular, the nominal interest rate for AMD denominated loans may be 15% -21%" [t1:note:3] official_terms
        - from table note in Overdraft | Card loan | Apply online (#Tab2_54240 > div:nth-of-type(1) > div:nth-of-type(1) > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(25) > td:nth-of-type(1))
        - "Other terms can be applied for applications for scoring-based loans or loans to workers of specific industries. In particular, the nominal interest rate for AMD denominated loans may be 15% -21%, while the annual percentage rate may be 16.06-23.13% in case of loans in AMD."
        - quote matches the captured source text
6. effective_rate — 3 variant(s) returned
    - 23.13 rate_type=fixed basis=annual  when currency=AMD; card_type=Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Dig…
    - 21.92 rate_type=fixed basis=annual  when currency=AMD; card_type=Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital, Mastercard World/VISA Pl…
    - 16.06 to 23.13 rate_type=fixed basis=annual  when currency=AMD; application_type=scoring-based loans or loans to workers of specific industries
    - cited "AMD: 23.13 % | | AMD: 21.92 %" [t1:row:13] official_terms
        - from table row in Overdraft | Card loan | Apply online (#Tab2_54240 > div:nth-of-type(1) > div:nth-of-type(1) > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(5) > td:nth-of-type(1))
        - "…Signature Digital | | Row: Loan terms ³ | Annual percentage rate (APR) ⁴ | AMD: 23.13 % | | AMD: 21.92 % | |"
        - quote matches the captured source text
    - cited "while the annual percentage rate may be 16.06-23.13% in case of loans in AMD." [t1:note:3] official_terms
        - from table note in Overdraft | Card loan | Apply online (#Tab2_54240 > div:nth-of-type(1) > div:nth-of-type(1) > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(25) > td:nth-of-type(1))
        - "Other terms can be applied for applications for scoring-based loans or loans to workers of specific industries. In particular, the nominal interest rate for AMD denominated loans may be 15% -21%, while the annual percentage rate may be 16.06-23.13% in case of loans in AMD."
        - quote matches the captured source text
7. loan_amount — 3 variant(s) returned
    - 300000.0 to 10000000.0 type=absolute currency=AMD  when application_review_type=outside scoring system
    - type=salary_multiple max_multiple=4.0  when application_review_type=outside scoring system
    - None to 15000000.0 type=absolute currency=AMD  when application_review_type=scoring-based
    - cited "If the loan application is considered outside the scoring system, the minimum loan limit is AMD…" [t1:note:2] official_terms
        - from table note in Overdraft | Card loan | Apply online (#Tab2_54240 > div:nth-of-type(1) > div:nth-of-type(1) > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(24) > td:nth-of-type(1))
        - "If the loan application is considered outside the scoring system, the minimum loan limit is AMD 300,000."
        - quote matches the captured source text
    - cited "If the loan application is reviewed outside the scoring system: Maximum amount: AMD 10 million …" [t1:row:6] official_terms
        - from table row in Overdraft | Card loan | Apply online (#Tab2_54240 > div:nth-of-type(1) > div:nth-of-type(1) > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(5) > td:nth-of-type(1))
        - "… Signature , Visa Signature Digital | | Row: Loan terms ³ | Credit limit | If the loan application is reviewed outside the scoring system: Maximum amount: AMD 10 million Maximum 4 fold If the loan application is reviewed on the basis of the scoring system: Maximum amount: AMD 15 million | | | |"
        - quote matches the captured source text
8. term — 1 variant(s) returned
    - indefinite=True end_condition=on_demand  (unconditional)
    - cited "Indefinite term (until requested back): until loan cancellation by the Bank, which may occur in…" [t1:row:8] official_terms
        - from table row in Overdraft | Card loan | Apply online (#Tab2_54240 > div:nth-of-type(1) > div:nth-of-type(1) > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(5) > td:nth-of-type(1))
        - "…Signature , Visa Signature Digital | | Row: Loan terms ³ | Term (months) | Indefinite term (until requested back): until loan cancellation by the Bank, which may occur in accordance with the agreement, based on the results of the monitoring by the Bank | | | |"
        - quote matches the captured source text

## Admission and storage

9. Snapshot admission decided accepted for overdraft (snapshot b460dffb, payload sha256 471b9a0c0432): 24 validated fields, 0 review items, 0 review signals.
10. Projected the stored snapshot into typed facts, verified citations, and retrieval units (1 version published, 0 unprojectable).

## Question — asked of the stored data

11. Resolved "What is the nominal interest rate of the Overdraft?" deterministically to consumer_loan/overdraft by exact match, with no model call.
12. Issued a per-turn authorization plan: operation=single, fields=4, expires 2026-09-22T16:01:43.958931+00:00.
13. Answered from the stored typed facts: status=answered, 12 facts, as of 2026-09-22 15:19:30.285315+00:00.
    - rate.effective.maximum = 23.13 AMD  when currency=AMD; application_type=scoring-based loans or loans to workers of specific industries
        - cited to "while the annual percentage rate may be 16.06-23.13% in case of loans in AMD." [t1.r24.c0] official_terms
        - cited to "AMD: 23.13 % | | AMD: 21.92 %" [t1.r4.c0] official_terms
    - rate.effective.maximum = 23.13 AMD  when currency=AMD; card_type=Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Dig…
        - cited to "while the annual percentage rate may be 16.06-23.13% in case of loans in AMD." [t1.r24.c0] official_terms
        - cited to "AMD: 23.13 % | | AMD: 21.92 %" [t1.r4.c0] official_terms
    - rate.effective.maximum = 21.92 AMD  when currency=AMD; card_type=Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital, Mastercard World/VISA Pl…
        - cited to "while the annual percentage rate may be 16.06-23.13% in case of loans in AMD." [t1.r24.c0] official_terms
        - cited to "AMD: 23.13 % | | AMD: 21.92 %" [t1.r4.c0] official_terms
    - rate.effective.minimum = 16.06 AMD  when currency=AMD; application_type=scoring-based loans or loans to workers of specific industries
        - cited to "while the annual percentage rate may be 16.06-23.13% in case of loans in AMD." [t1.r24.c0] official_terms
        - cited to "AMD: 23.13 % | | AMD: 21.92 %" [t1.r4.c0] official_terms
    - rate.effective.minimum = 23.13 AMD  when currency=AMD; card_type=Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Dig…
        - cited to "while the annual percentage rate may be 16.06-23.13% in case of loans in AMD." [t1.r24.c0] official_terms
        - cited to "AMD: 23.13 % | | AMD: 21.92 %" [t1.r4.c0] official_terms
    - rate.effective.minimum = 21.92 AMD  when currency=AMD; card_type=Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital, Mastercard World/VISA Pl…
        - cited to "while the annual percentage rate may be 16.06-23.13% in case of loans in AMD." [t1.r24.c0] official_terms
        - cited to "AMD: 23.13 % | | AMD: 21.92 %" [t1.r4.c0] official_terms
    - rate.nominal.maximum = 21.0 AMD  when currency=AMD; application_type=scoring-based loans or loans to workers of specific industries
        - cited to "In particular, the nominal interest rate for AMD denominated loans may be 15% -21%" [t1.r24.c0] official_terms
        - cited to "AMD: 21% | | AMD: 20%" [t1.r4.c0] official_terms
    - rate.nominal.maximum = 20.0 AMD  when currency=AMD; card_type=Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital, Mastercard World/VISA Pl…
        - cited to "In particular, the nominal interest rate for AMD denominated loans may be 15% -21%" [t1.r24.c0] official_terms
        - cited to "AMD: 21% | | AMD: 20%" [t1.r4.c0] official_terms
    - rate.nominal.maximum = 21.0 AMD  when currency=AMD; card_type=Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Dig…
        - cited to "In particular, the nominal interest rate for AMD denominated loans may be 15% -21%" [t1.r24.c0] official_terms
        - cited to "AMD: 21% | | AMD: 20%" [t1.r4.c0] official_terms
    - rate.nominal.minimum = 15.0 AMD  when currency=AMD; application_type=scoring-based loans or loans to workers of specific industries
        - cited to "In particular, the nominal interest rate for AMD denominated loans may be 15% -21%" [t1.r24.c0] official_terms
        - cited to "AMD: 21% | | AMD: 20%" [t1.r4.c0] official_terms
    - rate.nominal.minimum = 20.0 AMD  when currency=AMD; card_type=Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital, Mastercard World/VISA Pl…
        - cited to "In particular, the nominal interest rate for AMD denominated loans may be 15% -21%" [t1.r24.c0] official_terms
        - cited to "AMD: 21% | | AMD: 20%" [t1.r4.c0] official_terms
    - rate.nominal.minimum = 21.0 AMD  when currency=AMD; card_type=Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Dig…
        - cited to "In particular, the nominal interest rate for AMD denominated loans may be 15% -21%" [t1.r24.c0] official_terms
        - cited to "AMD: 21% | | AMD: 20%" [t1.r4.c0] official_terms

## Notes

- Acquisition and the Gemini calls happened in run_007; this run replays their recorded output. Record a new one with `scripts/demonstrate_end_to_end.py <url>`, or replay a specific one by setting DEMONSTRATION_CAPTURE.
- The full evidence overlay for this capture, with each cited quote highlighted inside the source document, is in end-to-end/run_007/semantic-extraction/extraction.md.

## Success criteria

| | Criterion | Expected | Observed |
| --- | --- | --- | --- |
| PASS | quotes come from the captured page | every quote the model cited appears verbatim in the captured source text | all shown citations matched their captured block |
| PASS | admitted without human review | the extraction clears deterministic admission on its own | status=accepted, signals=0 |
| PASS | answered | the query is answered from accepted data, not abstained | status=answered |
| PASS | requested fields returned | both the minimum and maximum nominal rate come back | returned ['rate.effective.maximum', 'rate.effective.minimum', 'rate.nominal.maximum', 'rate.nominal.minimum'] |
| PASS | every value is cited | no returned fact lacks source evidence | 12 facts, 0 without evidence |
| PASS | evidence is verifiable | each citation carries an exact quote and a source locator | 24 citations, 0 missing quote or locator |
| PASS | freshness is reported | the answer carries the stored snapshot's as-of time | as_of=2026-09-22 15:19:30.285315+00:00 |
