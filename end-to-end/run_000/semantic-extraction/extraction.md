# Semantic extraction audit

Product: **mortgage**  
Model: **gemini-3.7-flash**

Evidence annotations distinguish content that produced a cited value, content sent to Gemini but not cited, and source-discovered content omitted by the bounded semantic planner.

## Stage error

**FAILED — ValidationError:** 7 validation errors for tuple[ConditionalValue[Rate], ...]
0.value
  Field required [type=missing, input_value={'condition': 'Fixed', 'c...5, 'rate_type': 'fixed'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
1.value
  Field required [type=missing, input_value={'condition': 'Fixed', 'c...0, 'rate_type': 'fixed'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
2.value
  Field required [type=missing, input_value={'condition': 'Fixed', 'c...5, 'rate_type': 'fixed'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
3.value
  Field required [type=missing, input_value={'condition': 'Adjustable...'rate_type': 'floating'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
4.value
  Field required [type=missing, input_value={'condition': 'Adjustable...'rate_type': 'floating'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
5.value
  Field required [type=missing, input_value={'condition': 'Adjustable...'rate_type': 'floating'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
6.value
  Field required [type=missing, input_value={'condition': 'Online ref...'rate_type': 'floating'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing

The evidence packets below remain available for diagnosis. Items that were sent are marked failed because no validated result was assembled.

## Source-discovered evidence

### SKIPPED BY PLANNER — `ev_0fc34c0fca496347631a72b4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:0`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք. Երեւան, Նոր Նորք Ար. Միկոյան փող. 2/1 շենք
```

### SKIPPED BY PLANNER — `ev_05f3cdc5609482321d2f823c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:1`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք. Երեւան, Արաբկիր Մալխասյանց փողոց 6/1 շենք
```

### SKIPPED BY PLANNER — `ev_2833b86866222cab8fde5fa4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:2`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք. Երեւան, Նոր-Նորք Հ. Գյուլիքեւխյան փողոց 14/2 շենք
```

### SKIPPED BY PLANNER — `ev_af0cdc93b9d68e6f47846a93`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:3`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք. Երեւան, Ավան Աճառյան փողոց 39/25 շենք
```

### SKIPPED BY PLANNER — `ev_444d10e456d91d729fc21e53`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:4`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք. Երեւան, Արաբկիր Օրբելի եղբայրների փողոց 67/2 շենք
```

### SKIPPED BY PLANNER — `ev_9db27e2682ae8f4d3f22e201`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:5`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք. Երեւան, Աջափնյակ Հ. Շիրազի փողոց 2/9 շենք
```

### SKIPPED BY PLANNER — `ev_8b23b7cdd100f81f35ee7568`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:6`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք. Երեւան, Քանաքեռ-Զեյթուն Պ. Սեւակի փողոց 51/2 շենք
```

### SKIPPED BY PLANNER — `ev_df0b952a70990d79db5fec48`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:7`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք. Երեւան, Արաբկիր Մամիկոնյանց փողոց 45/1 շենք
```

### SKIPPED BY PLANNER — `ev_5746ebc18f70002aba151c49`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:8`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: ք.Երեւան, Աջափնյակ Նորաշեն թաղամաս 47/5 շենք
```

### SKIPPED BY PLANNER — `ev_0743b7cd26a99f8db0391c4f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:0:c9465a0d1c77:page:1:table:0:row:9`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Հասցե
Row: Ք.Երեւան, Շենգավիթ, Մ. Ֆրունզեի փողոց 10/4 շենք
```

### FAILED — `ev_a25eecd6e093f88df11dfdfa`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:block:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Retail Lending Terms and Conditions (Home Mortgage Loan)¹ &gt; Home Purchase Loan (primary market)

```text
AMERIABANK CJSC
11RBD PL 72-03-98
Retail Lending Terms and Conditions (Home Mortgage Loan)¹
Edition 73
Effective date: August 5, 2026
Approved by Management Board Resolution # 08/1/01/14 as of February 4, 2014.
Current edition approved by Management Board resolutions # 01/15/26 as of May 27, 2026, and # 01/95/26 as of June 25, 2026.
Home Purchase Loan (primary market)
```

### FAILED — `ev_8dba1a6bbf6a5bb55d7a44a4`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”)
```

### FAILED — `ev_89f04ad5efa82b7970cfd683`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 2. Customer’s personal details | 2.1. Eligible age of the customer/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
```

### FAILED — `ev_1833e80e22f3aeff89a8173a`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:10`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 14.39-15.76% | 11.6-13.56% | 8.86-10.71%
```

### FAILED — `ev_ae1ee32f0175757f0198388c`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:11`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 | 3.6.1. 61-360 | 3.6.1. 61-360
```

### FAILED — `ev_683fac14010eb66fee095570`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:12`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)
```

### FAILED — `ev_ae5db4a8a78e5ad4befc25ac`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 2. Customer’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia
For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia
For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia
For loans in foreign currency: individuals not considered residents of Armenia
```

### FAILED — `ev_386f78b9ef99c87950fbe7c3`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
```

### FAILED — `ev_ef44ec0ac575285bdac7e175`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1.
AMD 3,000,000 - AMD 150,000,000
For online refinancing: AMD 3,000,000-100,000,000 | 3.2.2.
USD 5,000 - USD 300,000
Not applicable in case of online refinancing | 3.2.3.
EUR 5,000 - EUR 300,000
Not applicable in case of online refinancing
```

### FAILED — `ev_3bf7662e4c21976f9f9e4e08`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | Term and interest rate | Term and interest rate | Term and interest rate | Term and interest rate
```

### FAILED — `ev_f173f0c1b978d2829daf70cf`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.3. Term (months) | 3.3.1. 60 | 3.3.1. 60 | 3.3.1. 60
```

### FAILED — `ev_0d2f2535ad7550cc981e39dc`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed | 3.4.2. Fixed | 3.4.3. Fixed
```

### FAILED — `ev_6eedd264158e128a00cb0b47`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:8`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 13.5% | 11.0% | 8.5%
```

### FAILED — `ev_54bb0175baea1a59ad19edcb`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:1:table:0:row:9`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed | 3.5.2. Fixed | 3.5.3. Fixed
```

### FAILED — `ev_220360efba75fa605fc45b78`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.7. Nominal annual interest rate² | Fixed component 5.5% + variable component (base rate) | Fixed component 8% + variable component (base rate) | Fixed component 7% + variable component (base rate)
```

### FAILED — `ev_8779988e22406bea94359f1c`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing
```

### FAILED — `ev_37b3d1e7925caf933fc1dd8f`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:10`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).
```

### FAILED — `ev_de4df11b9236e24b6ea3893b`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:11`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%.
```

### FAILED — `ev_e3ea99923046a161209f9bf7`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:12`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.12. Lump sum disbursement fee | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less
```

### FAILED — `ev_b7f15a0466e7bd9b63e9c6f9`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:13`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.13. Minimum down payment | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral.
```

### SKIPPED BY PLANNER — `ev_c708079e1dea8a3bdef0904d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:14`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.14. Manner of disbursement | 1. Lump sum
2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | 1. Lump sum
2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | 1. Lump sum
2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower.
```

### SKIPPED BY PLANNER — `ev_5d108ad9f1e8c15353aaca88`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.8. Term (months) | 3.8.1. 61-360 | 3.8.1. 61-360 | 3.8.1. 61-360
```

### FAILED — `ev_f105645fd121f8f14bb78d94`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.9. Nominal annual interest rate | 3.9.1. Adjustable fixed (rate can be changed starting from the 37th month) | N/a | N/a
```

### FAILED — `ev_ee0181a07d7cb2868f36c95f`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.9. Nominal annual interest rate | Fixed component 5.25% + variable component (base rate) | N/a | N/a
```

### FAILED — `ev_23270fda34542aff2246546f`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 3.10.1. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.2. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.3. Adjustable fixed (rate can be changed starting from the 37th month)
```

### FAILED — `ev_d0831ca8a7468018e237c41b`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 14.35-15.74% | 10.47-12.39% | 8.3-10.12%
```

### FAILED — `ev_874f5008493b841daf90d67a`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%.
```

### FAILED — `ev_b5c6607f973e3c64b399a487`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:8`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.
```

### FAILED — `ev_552d1dc78cff7621b1ddfc29`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:2:table:0:row:9`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | AMD | USD | EUR
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.
```

### SKIPPED BY PLANNER — `ev_9e859222ff3a1223e2765d92`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:3:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 3. Loan terms | 3.15. Cashing of the loan amount by the seller from their account with the Bank after loan disbursement (where applicable) | 3.15.1.
AMD: Free
Other currency: 0.5 %
```

### FAILED — `ev_62ec6ff85940bc1d8e9e7787`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:3:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)
```

### FAILED — `ev_62d90b60c110c24dcf8d6f07`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:3:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) /not applicable in case of online refinancing/
```

### FAILED — `ev_f0c2a5c7f05e25a2eb3adf7e`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:3:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (the customer may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) /not applicable in case of online refinancing/
```

### SKIPPED BY PLANNER — `ev_6e572c225c6514e6f901fe22`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:3:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 5. Security | 5.1. Eligible collateral | 5.1.1.
1. The loan is secured by the real estate being purchased. The Bank may consider pledge of other real estate as additional security to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.
2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.
3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank.
4. In the case of online refinancing, the collateral is real estate purchased directly from the developer, which has a completion certificate and is not encumbered with any liabilities other than the refinanced loan.
```

### FAILED — `ev_c8522c2d0fc2de47ba799d23`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:3:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 5. Security | 5.2. Loan-to-value (LTV) ratio | 5.2.1. The loan is issued:
1. For AMD loans with a term of 61-240 months: up to 90%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,
For AMD loans with a term above 240 months: up to 80%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁶ reference provided to the client, unless otherwise determined by the Bank,
2. For foreign currency loans with a term of 61-240 months: up to 70%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,
For foreign currency loans with a term above 240 months: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client, unless otherwise determined by the Bank,
3. up to 100% of the value of cash in the Bank or bonds issued by the Bank.
4. For up to AMD 30 million loans without creditworthiness assessment: up to 70% (if in Yerevan) and up to 60% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).
For AMD 30-50 million loans without creditworthiness assessment: up to 60% (if in Yerevan) and up to 50% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).
For AMD 50-100 million loans without creditworthiness assessment: up to 50% (if in Yerevan) and up to 40% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).
```

### SKIPPED BY PLANNER — `ev_f83c15bfe189c585373772aa`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:3:table:0:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Armenia
5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020.
```

### SKIPPED BY PLANNER — `ev_88645468485a4350589a095d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:4:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 5. Security | 5.4. Appraisal of the collateral | 5.4.1.
1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer’s reference, unless otherwise determined by the Bank.
2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank.
```

### SKIPPED BY PLANNER — `ev_49967824611f330ce0289b96`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:4:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security.
```

### SKIPPED BY PLANNER — `ev_3c1d77da46942d54d126d645`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:4:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases:
```

### SKIPPED BY PLANNER — `ev_2a4d7abd1eda8f33c09ca28e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:4:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or
```

### SKIPPED BY PLANNER — `ev_497a6fd76fb35665c5b10844`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:4:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website.
```

### SKIPPED BY PLANNER — `ev_0e3dac62b34f0eca7392ec2c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:4:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable).
```

### FAILED — `ev_656cbdf1ee50e5d0b12929ae`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:4:table:0:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application
• Loan application (not applicable in case of online refinancing)
• ID (original)
• Certificate of ownership/purchase right of real estate to be purchased/pledged (copy)
• Other documents upon the Bank’s request
```

### SKIPPED BY PLANNER — `ev_02dfafb2b2a6431704290838`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:4:table:0:row:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 7. Required documents | 7.1. Required documents | 7.1.2. Documents required after pre-approval
• Proof of employment and/or other income (not applicable in case of online refinancing)
```

### FAILED — `ev_0a8c4fc9114ab2f5e6e1f6fb`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:5:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original)
```

### SKIPPED BY PLANNER — `ev_db26ec04c74afb9be93c2102`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:5:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 7. Required documents | 7.1. Required documents | • Certificate of title to real estate to be pledged (original)
```

### SKIPPED BY PLANNER — `ev_23e8cb03cca32e94988b1830`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:5:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 7. Required documents | 7.1. Required documents | • Other documents upon the Bank request
```

### FAILED — `ev_47a5bc1036cd2e3a1a111ba5`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:5:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 7. Required documents | 7.1. Required documents | 7.1.3. Documents required after loan approval
• Copies of bases of title to real estate (to be submitted upon the Bank’s request)
• IDs of owners of the property to be purchased/pledged (originals)
• Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available
• Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)
• Tax clearance certificate for the real estate
• Real estate insurance policy (as required)
• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.
• Other documents upon the Bank’s request
```

### FAILED — `ev_a15d731701f412b4f6afad9a`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:5:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.
At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.
Where the amount of early repayment exceeds the specified limit, the following fees will be charged:
• Max 0.6% of early repayment, if made during the first year of the agreement
• Max 0.4% of early repayment, if made during the second year of the agreement
• Max 0.2% of early repayment, if made during the third year of the agreement
```

### SKIPPED BY PLANNER — `ev_3aa409b333521d3cbaf1d04c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:5:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.
Fine in the amount of 0.13 % of overdue loan and interest for each day of delay
```

### SKIPPED BY PLANNER — `ev_4bbecef63d2efe25b51a6be6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:5:table:0:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 10. Other fees | 10.1. Other fees | 10.1.1. Fees payable by the customers for the new loans
• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and
• Appraisal fee for the real estate being pledged (as necessary)
10.1.2 Fees payable by the Bank for the loans refinanced online
• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and
• Appraisal fee for the real estate being pledged
```

### SKIPPED BY PLANNER — `ev_a8cee0737f317e40551303bd`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:6:note:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
¹These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
```

### SKIPPED BY PLANNER — `ev_77c3d8397f7471654d054e35`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:6:note:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
²Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
```

### FAILED — `ev_0f2c273aa9673ad170f94518`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:1:db6b470de92a:page:6:note:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
³The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
- When the property insurance is obtained by the Bank at the customer’s request
- When the borrower selects differentiated or mixed form of loan repayment
- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
- If additional property is pledged as collateral
- If there are other deviations
```

### SKIPPED BY PLANNER — `ev_a0ecf342b0dc0c7cae7b3b5c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:6:note:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
⁴ Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
```

### SKIPPED BY PLANNER — `ev_e1b4d317cd9be1e38bc8a80f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:6:note:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
⁵ The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
```

### SKIPPED BY PLANNER — `ev_8587172eeac8dc16f0cfeb4b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:1:db6b470de92a:page:6:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Home Purchase Loan (primary market) (Continued)

```text
Headers: Section | Clause | Details
Row: 11. Creditworthiness assessment | 11.1 Without creditworthiness assessment | -Where the loan amount is AMD 50-100 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 50% (if in Yerevan) or 60% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank
Where the loan amount is AMD 30-50 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 40% (if in Yerevan) or 50% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank.
Where the loan amount is up to AMD 30 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 30% (if in Yerevan) or 40% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank.
```

### SKIPPED BY PLANNER — `ev_a5b7642c2031215b5c95e195`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:block:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Approved by Management Board Resolution # 08/1/01/14 as of February 4, 2014.
Current edition approved by Management Board resolutions # 01/15/26 as of May 27, 2026, and # 01/95/26 as of June 25, 2026.
```

### FAILED — `ev_dd868bea593ea7db990894dd`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:1:block:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹

```text
Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹
```

### FAILED — `ev_11f6c647a9297d9ac01dbd7e`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:1:block:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; General requirements to loan facilities

```text
General requirements to loan facilities
```

### SKIPPED BY PLANNER — `ev_b1cbcccc6973506d091a19ac`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Header Information

```text
Headers: Column 1 | Column 2
Row: AMERIABANK CJSC | 11RBD PL 72-03-98
```

### FAILED — `ev_8e35420291c4b8fa1e0fcbd5`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:1:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Header Information

```text
Headers: Column 1 | Column 2
Row: Retail Lending Terms and Conditions
(Home Mortgage Loan)¹ | Edition 73
```

### FAILED — `ev_cdb2161ca9be2aff34ec361c`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:1:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Header Information

```text
Headers: Column 1 | Column 2
Row: Retail Lending Terms and Conditions
(Home Mortgage Loan)¹ | Effective date: August 5, 2026
```

### SKIPPED BY PLANNER — `ev_1134ad180f17be5f257d828a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:table:1:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Customer’s personal details | 1.1. Eligible age of client/co-borrower | 1.1.1. 18-70, provided that the age of the borrower by the time of expiry of loan agreement will not have exceeded 70
```

### SKIPPED BY PLANNER — `ev_a6de9f71c80206fceccd291e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:table:1:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Customer’s personal details | 1.2. Residency | 1.2.1. Citizens of Armenia who are resident in Armenia
```

### SKIPPED BY PLANNER — `ev_9c84a5b5d0201b59d9cb6634`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:table:1:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Terms and Conditions | 2.1. Currency | 2.1.1. AMD
```

### SKIPPED BY PLANNER — `ev_ef8f3eda81e53f7a89890813`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:table:1:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Terms and Conditions | 2.2. Minimum and maximum loan limit | 2.2.1. AMD 3,000,000 - AMD 100,000,000
```

### SKIPPED BY PLANNER — `ev_162808a6405bbdc3ac6af1b8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:table:1:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Terms and Conditions | 2.3. Cashing of the loan amount by the borrower or the seller from his account with the Bank after loan disbursement (where applicable) | 2.3.1.
AMD: free
```

### SKIPPED BY PLANNER — `ev_e89c79f611ab03753120f752`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:table:1:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Terms and Conditions | 2.4. Lump sum disbursement fee | 2.4.1. N/A
```

### FAILED — `ev_864c7129ed418567b2710831`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:1:table:1:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities

```text
Headers: Column 1 | Column 2 | Column 3
Row: 3. Forms of loan repayment | 3.1. Repayment method | 3.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)
```

### SKIPPED BY PLANNER — `ev_1126add00a52d45edc9ab23a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:1:table:1:row:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities

```text
Headers: Column 1 | Column 2 | Column 3
Row: 5. Insurance of the collateral | 5.1. Insurance of the collateral | 5.1.1. The real estate being pledged is insured by the Bank in the following cases:
5.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or
5.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website.
5.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable).
```

### FAILED — `ev_570ee489e2a851615f4348ee`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:2:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 6. Early repayment fee | 6.1. Early repayment fee | 6.1.1.
At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.
Where the amount of early repayment exceeds the specified limit, the following fees will be charged:
• Max 0.6% of early repayment, if made during the first year of the agreement
• Max 0.4% of early repayment, if made during the second year of the agreement
• Max 0.2% of early repayment, if made during the third year of the agreement
```

### SKIPPED BY PLANNER — `ev_f33203e80c827611f8cd7c24`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:2:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 7. Late payment fines and penalties | 7.1. Late payment fines and penalties | 7.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.
Fine in the amount of 0.13 % of overdue loan and interest for each day of delay
```

### SKIPPED BY PLANNER — `ev_3d1c576f9befb00db8eede06`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:2:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 8. Other fees | 8.1. Other fees payable by the customer | 8.1.1. Fee for notarization of real estate pledged as collateral
Fee for registration of the right of ownership/purchase and the Bank rights arising out of the pledge agreements with the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
Fee for the unified reference on real estate encumbrance issued by the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
Fee for the final appraisal of the real estate (if required)
```

### FAILED — `ev_27840889daa901e1ba71fd84`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:2:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: General requirements to loan facilities (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 9. Required documents | 9.1. Required documents | 9.1.1. Required documents filed together with the loan application
ID, public services number
9.1.2. Documents required after pre-approval
• Certificate of title to real estate to be pledged (copy)
• Initial real estate appraisal report
• Other documents upon the Bank’s request
9.1.3. Documents required after loan approval
Marriage certificate (if any) and ID of the spouse, public services number
Certificate of title to the real estate/right to purchase
Certificate of security interest registration
Unified reference on real estate encumbrance
• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.
Construction permit (for construction loans)
Pro-forma invoice (for renovation and construction loans)
Other documents upon the Bank’s request
```

### FAILED — `ev_8d4b0cd40476da2af80f1138`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:3:block:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; 1. Express Home Purchase Loan (primary market)

```text
1. Express Home Purchase Loan (primary market)
```

### FAILED — `ev_2eb70717053306791ac558f1`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:3:block:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; 2. Express Home Purchase Loan (secondary market)

```text
2. Express Home Purchase Loan (secondary market)
```

### FAILED — `ev_45024e54be5212a38ef415d6`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes
```

### FAILED — `ev_53420e5b9912abe8fdbddd04`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360
```

### FAILED — `ev_61302abc47b62484976e684c`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
Fixed component 5.25% + variable component (base rate)
```

### FAILED — `ev_f39c4fee1bf1de19c676d46a`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.08-15.57%
```

### SKIPPED BY PLANNER — `ev_b5435418295ca0eb3d9e88e1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.5. Minimum down payment | 1.5.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
```

### SKIPPED BY PLANNER — `ev_91e3496cc496219265c4e006`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

### SKIPPED BY PLANNER — `ev_2a94a4a5f8980ffbcb023bfd`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1
1.1. For loans with a term of 240 months, the loan amount is up to 90% of the sale price set by the developer³.
For loans with a term above 240 months, the loan amount is up to 80% of the sale price set by the developer⁴, unless otherwise determined by the Bank.
```

### SKIPPED BY PLANNER — `ev_636ec00980ef0c89cebfabe1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia
```

### SKIPPED BY PLANNER — `ev_e6f51ad51361fcacf5bcff07`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:0:row:8`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 1. Express Home Purchase Loan (primary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. N/A
The price statement provided by the Developer⁴ is taken as the basis for the collateral value.
```

### SKIPPED BY PLANNER — `ev_82d864cf7f9733036629c697`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:1:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes.
```

### SKIPPED BY PLANNER — `ev_1df7f92bf05f2ec98815e33d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:1:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360
```

### SKIPPED BY PLANNER — `ev_19b7452e577ed83a4a2aae8c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:1:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
Fixed component 5.75% + variable component (base rate)
```

### SKIPPED BY PLANNER — `ev_17391c5bac832caa94d40975`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:1:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.66-17.11%
```

### SKIPPED BY PLANNER — `ev_742de24d4cea1dba3d3cbbd5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:1:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.5. Minimum down payment | 1.5.1. At least 5% of the purchase price of the property
```

### SKIPPED BY PLANNER — `ev_029f41620adc9c2795d1f73b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:1:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

### SKIPPED BY PLANNER — `ev_3d0b7b20c43ada72562128e7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:3:table:1:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80% (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70% (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property
```

### SKIPPED BY PLANNER — `ev_f00928f286370cc9f4a374f4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:block:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; 3. Express Home Construction Loan

```text
3. Express Home Construction Loan
```

### SKIPPED BY PLANNER — `ev_a9b8e31c195982ebd4a9a7d4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:block:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; 4. Express Home Renovation Loan

```text
4. Express Home Renovation Loan
```

### SKIPPED BY PLANNER — `ev_39bda6f739bbc6aefc01b678`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market) (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia
```

### SKIPPED BY PLANNER — `ev_d66c3d25a80e0c03fe5ac72f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 2. Express Home Purchase Loan (secondary market) (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank.
```

### SKIPPED BY PLANNER — `ev_0949bbb262a240a8c1a7209e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.1. Purpose | 1.1. Construction of residential property
```

### SKIPPED BY PLANNER — `ev_b84964932d93032d66370aaa`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360
```

### SKIPPED BY PLANNER — `ev_237bd8513abb4f4d6f310028`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
Fixed component 5.75% + variable component (base rate)
```

### SKIPPED BY PLANNER — `ev_713715dabbc92f3bd9324d3b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9%
```

### SKIPPED BY PLANNER — `ev_7a65bbbd0fc7b9781fe5bb62`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being constructed. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

### SKIPPED BY PLANNER — `ev_24bbf11898c941125521109a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property
```

### SKIPPED BY PLANNER — `ev_a49bb5a22b34f23396fd77cb`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia
```

### SKIPPED BY PLANNER — `ev_879e2c587be85af14bfca623`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank.
```

### SKIPPED BY PLANNER — `ev_263458f718b12e692acf458b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:1:row:8`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 3. Express Home Construction Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.
For loans over AMD 50 million contractual amount at least 3 tranches must be defined.
```

### SKIPPED BY PLANNER — `ev_dc3832d0b024b25dcecdd283`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:2:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.1. Purpose | 1.1. Renovation of residential property
```

### SKIPPED BY PLANNER — `ev_7b759637e414b996399b864b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:2:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.2. Term (months) | 1.2.1. 61-240
```

### SKIPPED BY PLANNER — `ev_df70d34c0e8b565ab5d59b06`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:2:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
Fixed component 5.75% + variable component (base rate)
```

### SKIPPED BY PLANNER — `ev_df500d9b55e6c52232e56b60`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:2:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9%
```

### SKIPPED BY PLANNER — `ev_a290b132f6212ee352bb8d2d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:4:table:2:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being renovated. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

### SKIPPED BY PLANNER — `ev_975c8480d6549fae4dcb4a18`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:5:note:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
¹Attention! The offer of the agreement is provided to the customer following which the customer may use the 7-day cooling-off period envisaged by the Armenian laws and regulations.
In case of failure to notarize the pledge agreements specified in the loan agreement and securing the borrower's obligations under the loan agreement, within 30 (thirty) business days upon execution of the loan agreement and acceptance by the Borrower, the Agreement shall cease to be valid (unless the loan has already been disbursed to the borrower by that date).
```

### SKIPPED BY PLANNER — `ev_db1516bb8bf8523f8a7c9ca0`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:5:note:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
² Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ± 5%.
```

### SKIPPED BY PLANNER — `ev_6ba3922ab582c512c35508ee`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:5:note:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
³The list of developers is determined by the Bank.
```

### SKIPPED BY PLANNER — `ev_b93325354d10dcf0da78b29d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:5:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property
```

### SKIPPED BY PLANNER — `ev_184239259102a52d7a965161`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:5:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia
```

### SKIPPED BY PLANNER — `ev_fd22e59c7f7d33f2fdd24c5e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:5:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank.
```

### SKIPPED BY PLANNER — `ev_2d581e5e9edcc79b562a56b7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:2:175e5d151b3d:page:5:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: 4. Express Home Renovation Loan (Continued)

```text
Headers: Column 1 | Column 2 | Column 3
Row: 3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.
For loans over AMD 50 million contractual amount at least 3 tranches must be defined.
```

### FAILED — `ev_ae53389df4381424d7f387c1`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:block:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)
```

### SKIPPED BY PLANNER — `ev_605e7a46cb0617fff7d83678`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:3:0367c52044e0:page:1:block:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
11RBD PL 72-03-104, Ed. 1
Effective date: March 25, 2025
```

### SKIPPED BY PLANNER — `ev_aceabc6106826f2cfa6ef5ac`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:3:0367c52044e0:page:1:note:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
¹Retail Lending Terms and Conditions (Home Mortgage Loan) (11RBD PL 72-03-98), approved by the Management Board resolution # 08/1/01/14 as of February 4, 2014.
Available at https://ameriabank.am/useful-links.
```

### FAILED — `ev_55cb29836d9dea143aaa4253`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:table:0:note:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)

```text
*The rest of the terms and conditions are specified in the Terms¹.
```

### FAILED — `ev_2312c0b8598980d4cf382b53`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)

```text
Headers: Category / Option | Details
Row: 1. Purpose | 1.1. Increasing the mortgage loan portfolio, promoting sales
```

### FAILED — `ev_0be00fab69d8979f85eda252`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)

```text
Headers: Category / Option | Details
Row: 2. Client/Borrower | 2.1. Individuals meeting the Terms¹ established by Ameriabank CJSC (hereinafter - the Bank)
```

### FAILED — `ev_d555a2b9dbb26f22dda71c60`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)

```text
Headers: Category / Option | Details
Row: Option 1. Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice / 1. Nominal annual interest rate | 1.1. As per Terms¹
```

### FAILED — `ev_5513737836d95273f6ed0d9b`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)

```text
Headers: Category / Option | Details
Row: Option 1. Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice / 2. Annual interest rate subsidized by the Developer | 2.1. 0.5%-13.5%
```

### FAILED — `ev_d91167e8c7d934c4b367835b`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)

```text
Headers: Category / Option | Details
Row: Option 1. Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice / 3. Annual percentage rate (APR) | 3.1. 13.83%-15.76%
```

### FAILED — `ev_b1f845613883bbb24dfef135`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)

```text
Headers: Category / Option | Details
Row: Option 2. Partial or full payment of the down payment by the Developer / 1. Down payment | 1.1. Minimum 10%, paid from the funds received under the interest-free target loan agreement signed between the Developer and the Borrower. The loan amount is subject to repayment by the Borrower before the Developer receives the certificate of completion/signs the handover act for the purchased real estate, unless otherwise agreed by the parties.
```

### FAILED — `ev_12a1a6841437551239163ca2`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:3:0367c52044e0:page:1:table:0:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)

```text
Headers: Category / Option | Details
Row: Option 3: Partial or full payment of the down payment by the Developer and partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice / 1. Other terms and conditions | 1.1 The terms of Option 1 and 2 apply simultaneously.
```

### SKIPPED BY PLANNER — `ev_32e4f72e4e494d25e1730390`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:block:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Approved by
Management Board Resolution
# 03/93/26 as of June 19, 2026
Chairman of the Management Board-CEO
Artak Hanesyan
Effective date: July 1, 2026
```

### SKIPPED BY PLANNER — `ev_742377baa8005dceba9e057e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:block:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
TERMS OF RESIDENTIAL AND COMMERCIAL REAL ESTATE MORTGAGE LENDING (INCLUDING REFINANCING) CAMPAIGN
```

### SKIPPED BY PLANNER — `ev_bf75589a9bca69d7bdc66a48`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:block:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
11RBD PL 72-03-98/03, Ed. 1
```

### SKIPPED BY PLANNER — `ev_8e2a1d738da504ed69f18372`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:note:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
1 Lending terms and conditions are defined in the Retail Lending Terms and Conditions (Home Mortgage Loan and Commercial Mortgage Loan) (11RBD PL 72-03-98, 11RBD PL 72-03-88). Available at https://ameriabank.am/useful-links.
```

### FAILED — `ev_23746c55d4ba79b7a9eab91e`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:4:af53ff31bab9:page:1:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Purpose | Promoting sales of mortgage loans for residential and commercial real estate acquisition and moving to Ameriabank CJSC (hereinafter “the Bank”) existing mortgage loans issued by other banks and credit organizations operating in the Republic of Armenia. | Promoting sales of mortgage loans for residential and commercial real estate acquisition and moving to Ameriabank CJSC (hereinafter “the Bank”) existing mortgage loans issued by other banks and credit organizations operating in the Republic of Armenia.
```

### SKIPPED BY PLANNER — `ev_f5c7f46dabf670cbc79dee6e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Loan type | Loans for purchase, renovation and/or construction of residential and commercial real estate (issued online and at the Bank’s branches) | Loans for purchase, renovation and/or construction of residential and commercial real estate (issued online and at the Bank’s branches)
```

### SKIPPED BY PLANNER — `ev_5aeaf44863502c7c896677f3`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Eligible customers | 1. For newly issued loans: individuals meeting the Bank’s standard lending termsError! Bookmark not defined.
2. For refinancing of existing loans: individuals who have existing mortgage loans with other banks/credit organization of Armenia and duly perform their credit obligations | 1. For newly issued loans: individuals meeting the Bank’s standard lending termsError! Bookmark not defined.
2. For refinancing of existing loans: individuals who have existing mortgage loans with other banks/credit organization of Armenia and duly perform their credit obligations
```

### SKIPPED BY PLANNER — `ev_6e1fde2dda199f140980bf19`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Campaign term | 2026 From July 1, 2026 until and inclusive December 30, 2026 | 2026 From July 1, 2026 until and inclusive December 30, 2026
```

### SKIPPED BY PLANNER — `ev_48f11e7edfeaafde36546f6a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Loan terms | Loans are issued in accordance with the standard lending terms and conditions1, except for the following clauses: | Loans are issued in accordance with the standard lending terms and conditions1, except for the following clauses:
```

### SKIPPED BY PLANNER — `ev_256afdb2d57d2dfbaf7bfebb`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:1:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Nominal annual interest rate | 1. For the loans for purchase/renovation/construction of residential real estate
For the loans for | 2. For the loans for purchase/renovation/construction of residential real estate
For the loans for purchase/renovation/construction of commercial real estate
```

### SKIPPED BY PLANNER — `ev_6c871c241378d3233a01a4b5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:2:block:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
11RBD PL 72-03-98/03, Ed. 1
```

### SKIPPED BY PLANNER — `ev_eab63b29e549d87a616047dd`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:2:table:0:row:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Nominal annual interest rate | purchase/renovation/construction of commercial real estate
1.1. With an incentive: 12.9% (fixed adjustable interest rate which will be modified starting from the 37th month following the loan agreement execution; fixed component 4.9% + variable component (base rate)) | 2.1. Without an incentive: 12.9% (fixed adjustable interest rate which will be modified starting from the 37th month following the loan agreement execution; fixed component 4.9% + variable component (base rate))
```

### SKIPPED BY PLANNER — `ev_0164771183a3eb2857b35a22`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:2:table:0:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Annual percentage rate (APR) | 12.05-12.45% | 13.67-13.68%
```

### SKIPPED BY PLANNER — `ev_e1c90a1061a60f081182b3b5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:2:table:0:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Collateral-related costs | Collateral-related costs are covered by the Bank. | Collateral-related costs are covered by the Customer.
```

### FAILED — `ev_ba01aa1aea3e56fe20632c4d`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:4:af53ff31bab9:page:2:table:0:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Incentive and its payment | In case of loans with a possibility of providing an incentive, the client receives an incentive payment in the amount of 1% of the loan (without the taxes stipulated by the Republic of Armenia laws and regulations). Furthermore, the incentive is paid only for the loans issued in the Bank’s branches.
The incentive is transferred to the Customer’s current account with the Bank specified by the Customer by the Credits and Card Operations and Accounting Division, upon presentation by the loan officer, within 2 (two) business days upon registration of the Bank’s security interest over the property securing the credit obligations.
In case of full repayment of the credit obligations during the first 3 (three) years of the loan term, the incentive provided to the client (including the taxes defined by the Republic of Armenia laws and regulations) will be subject to return/repayment by the client within 1 (one) month. | In case of loans with a possibility of providing an incentive, the client receives an incentive payment in the amount of 1% of the loan (without the taxes stipulated by the Republic of Armenia laws and regulations). Furthermore, the incentive is paid only for the loans issued in the Bank’s branches.
The incentive is transferred to the Customer’s current account with the Bank specified by the Customer by the Credits and Card Operations and Accounting Division, upon presentation by the loan officer, within 2 (two) business days upon registration of the Bank’s security interest over the property securing the credit obligations.
In case of full repayment of the credit obligations during the first 3 (three) years of the loan term, the incentive provided to the client (including the taxes defined by the Republic of Armenia laws and regulations) will be subject to return/repayment by the client within 1 (one) month.
```

### SKIPPED BY PLANNER — `ev_dedd8ce722f1a26769037539`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:2:table:0:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Property pledging procedure | The property subject to pledge can be pledged within 30 days after actual disbursement of the loan. | The property is pledged before loan disbursement.
```

### SKIPPED BY PLANNER — `ev_4420852d201a2605039f6d00`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:4:af53ff31bab9:page:2:table:0:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Term | Refinancing | New loans
Row: Required documents | Proof of income documents may not be required if the salary or equivalent payments are stated in the request to the inquiry obtained from Nork Social Services Technology and Awareness Center | According to standard lending terms.
```

### SKIPPED BY PLANNER — `ev_57eab2f384f97db917c6c18e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:block:0`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Approved by
Management Board resolution
# ---- as of ...
Chairman of the Management Board -
CEO
Artak Hanesyan
Ameriabank CJSC
+(37410) 561111, +(37412) 561111 office@ameriabank.am
```

### SKIPPED BY PLANNER — `ev_8a65edd8bea150978e020c05`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:block:1`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: SERVICE FEES FOR LOANS TO INDIVIDUALS

```text
SERVICE FEES FOR LOANS TO INDIVIDUALS
```

### SKIPPED BY PLANNER — `ev_9d1d14710ba933164fe1b1fa`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:block:2`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: SERVICE FEES FOR LOANS TO INDIVIDUALS

```text
Approved by Management Board resolution # 01/68/18 dated May 14, 2018.
Current edition approved by resolution # .... dated ... , effective from July 14, 2026.
```

### SKIPPED BY PLANNER — `ev_09e82f8cd8e954fb37fe0f25`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:block:3`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: SERVICE FEES FOR LOANS TO INDIVIDUALS &gt; General Provisions

```text
General Provisions
```

### SKIPPED BY PLANNER — `ev_0fe1d6f462a5f8c5982a7e9e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:block:4`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: SERVICE FEES FOR LOANS TO INDIVIDUALS &gt; General Provisions

```text
1. Under this document, “loan” means the loan types envisaged by the Retail Lending Terms and Conditions of the Bank.
2. The changes specified in this document are made based on the client’s application, subject to its approval in accordance with the Bank’s internal regulations.
3. These fees apply to changes initiated by the client. The changes made in order to ensure the client’s performance of the condition subsequent established by the Bank are not considered as the client’s initiative.
```

### SKIPPED BY PLANNER — `ev_7f6427e983cb0d2916de6853`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:block:5`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: SERVICE FEES FOR LOANS TO INDIVIDUALS

```text
11RBD PL 72-03-29, Ed. 3
```

### SKIPPED BY PLANNER — `ev_89a57655b0c76227e1e490f8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:0`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 1. Term extension for mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000
```

### SKIPPED BY PLANNER — `ev_8d5bf119d84d1f221e15d973`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:1`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 2. Granting a grace period for the principal amount of mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000
```

### SKIPPED BY PLANNER — `ev_a242df3bf58e042310ea36e0`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:10`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 11. Issuing other consent not established by this document and not related to the collateral | AMD 10,000
(VAT included)
```

### SKIPPED BY PLANNER — `ev_8eaf1b0d3e8d120faec79a1d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:11`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 12. Revision/modification of another loan term not specified in this document (including interest rate revision) | 0.1% of the outstanding loan amount, minimum AMD 10,000
```

### SKIPPED BY PLANNER — `ev_894ea975ef1924cfcdcf1e91`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:2`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 3. Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000
```

### SKIPPED BY PLANNER — `ev_6c740697cbdf719959220034`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:3`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 4. Change of the overdraft/line of credit account/card | AMD 30,000
```

### SKIPPED BY PLANNER — `ev_6653e53f396e50e28effe608`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:4`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 5. Change of the borrower/co-borrower/guarantor | AMD 50,000
```

### SKIPPED BY PLANNER — `ev_859c87bf12ae6d8f82178b13`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:5`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 6. Release/substitution of the collateral | AMD 50,000
```

### SKIPPED BY PLANNER — `ev_1c36da10c8dc7c8dfa7296f9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:6`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 7. Issuing consent for change of a pledged vehicle plate number | AMD 50,000
(VAT included)
```

### SKIPPED BY PLANNER — `ev_84609285fbbb2882063bb8e9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:7`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 8. Collateral-related change (including change of the collateral owner) | AMD 15,000
```

### FAILED — `ev_352d0c410bc7f8181c710036`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:5:7b405d165676:page:1:table:0:row:8`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 9. Change of the loan repayment date | AMD 10,000
```

### SKIPPED BY PLANNER — `ev_cc0aa610d75fb9b1d0aa3c6a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:1:table:0:row:9`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 10. Provision of loan before submitting to the Bank the document certifying state registration of the security interest | AMD 25,000 (per issue)
```

### FAILED — `ev_e408f2078b2ed45097a1aad8`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `document:5:7b405d165676:page:2:block:0`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: SERVICE FEES FOR LOANS TO INDIVIDUALS &gt; General Provisions

```text
4. The fees specified in this document do not apply to the automatically approved consumer loans secured by deposit, bonds and metal accounts in gold.
5. Where several fees are applicable due to change of several terms of the same loan as per the application submitted by the client, only the highest of them shall be charged, once.
6. To apply a fee(s) established by this document for modification of the same term for several loans, the total outstanding amount of those loans is considered.
7. The fee amount is rounded to AMD 1,000 in favor of the client and shall be no less than the minimum amount of the respective fee (if established by this document).
8. Where a new collateral or guarantor is added due to modification of a loan term(s), no fee is charged.
9. In case of lines of credit and overdrafts, the outstanding loan amount means the bigger of the used amount of the line of credit/overdraft and the line of credit/overdraft limit currently available to the client.
```

### SKIPPED BY PLANNER — `ev_64b35236bb136ecb7bb732b6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:5:7b405d165676:page:2:block:1`  
Role / authority: `fees` / `official_terms`  
Temporal status: `unknown`  
Section: SERVICE FEES FOR LOANS TO INDIVIDUALS

```text
11RBD PL 72-03-29, Ed. 3
```

### SKIPPED BY PLANNER — `ev_3e1941fc7b2d9d3b2e19b4b5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:0`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION

```text
AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION
```

### SKIPPED BY PLANNER — `ev_53401627323fdcd8b757edfa`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:1`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION

```text
This agreement (hereinafter the “Agreement”) is entered into on [date] in Yerevan under the laws and regulations of Armenia by and between Ameriabank Closed Joint Stock Company (incorporated under the resolution of the CBA Board dated September 8, 1992, registration number 50, certificate No 0154; address: 2 V. Sargsyan, Yerevan) hereinafter the “Bank”, represented by the authorized person acting on behalf of the Bank, and ................. hereinafter the “Client” or the “Borrower”. The Bank and the Client shall be hereinafter jointly referred to as the “Parties” and individually as the “Party”. This Agreement on Adjustable Interest Rate Setting and Calculation forms an integral part of Agreement # [--] (hereinafter referred to as the “Principal Agreement”).
```

### SKIPPED BY PLANNER — `ev_4175fb8fbf245b4806506fed`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:10`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS

```text
2.4. Where it is necessary to choose a Secondary Rate, in order to avoid significant fluctuations between interest rates calculated based on Primary and Secondary Rates and prevent either Party from acquiring unjustified economic gain or incurring loss at the expense of the other Party, calculation of interest rate based on Secondary Rate shall include an adjusting factor to balance possible differences between rates (hereinafter “Spread Adjustment"). Spread Adjustment shall be calculated by the Bank and presented to the Borrower with its amount indicated in the selection Offer. During calculation of the Adjustable Rate throughout the term of the Agreement after selection of the Secondary Rate, the Spread Adjustment shall remain unchanged and be included in calculation of interest
```

### SKIPPED BY PLANNER — `ev_f86c3509566767ba84e16519`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:2`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 1 SUBJECT OF THE AGREEMENT

```text
1 SUBJECT OF THE AGREEMENT
```

### SKIPPED BY PLANNER — `ev_9f4a23634435b2e568ac68a6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:3`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 1 SUBJECT OF THE AGREEMENT

```text
1.1. The Parties hereby define the procedure for regular revision of the loan interest rate under the Principal Agreement in response to the changes in market interest rates to ensure that the interest rate determined by the Parties is consistent with the market rates to the highest possible degree at all times subject to the procedure established hereby.
```

### SKIPPED BY PLANNER — `ev_053e6d6a5a1422f4709b4b4f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:4`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 1 SUBJECT OF THE AGREEMENT

```text
1.2. The Agreement forms an integral part of the Principal Agreement.
```

### SKIPPED BY PLANNER — `ev_458ddf7cc0ca91693fb4b004`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:5`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 1 SUBJECT OF THE AGREEMENT

```text
1.3. Hereby the Parties agree that the interest rate set by the Principal Agreement shall be considered adjustable and variable (hereinafter “Adjustable Rate”) as stipulated under this Agreement.
```

### SKIPPED BY PLANNER — `ev_88af1a5e263c245cf51e5940`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:6`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS

```text
2 ADJUSTABLE INTEREST RATE CONSTITUENTS
```

### SKIPPED BY PLANNER — `ev_0d456ad993ead0a5c10e1b11`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:7`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS

```text
2.1. The Adjustable Rate defined by the Principal Agreement shall consist of the following constituents (components):
2.1.1. Base Rate
2.1.2. Margin (fixed component)
```

### SKIPPED BY PLANNER — `ev_565f12e03711fd6cef13e3f4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:8`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS

```text
2.2. The Adjustable Rate is a nominal interest rate calculated in accordance with this Agreement using the following formula: RA = RB + RM where RA is the Adjustable Rate, RB is the Base Rate and RM is the Margin (fixed component).
One primary index (hereinafter “Primary Rate” and/or “Primary Index”) and one secondary index (hereinafter “Secondary Rate” and/or “Secondary Index”) of Base Rate shall be used as basis for calculation and adjusting of the Adjustable Rate, which cannot be changed during the term of the Agreement, except in cases defined in chapter 5. The Secondary Index shall be applied if the Primary Index is inaccessible and setting of the Adjustable Rate for the next period becomes impossible.
```

### SKIPPED BY PLANNER — `ev_82541746a2403eae49490c71`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:1:block:9`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS

```text
2.3. The Base Rate shall be determined on the basis of the following market rates, depending on the loan currency:
2.3.1. In case of Adjustable Rates for AMD-denominated loans: the primary rate underlying the Base Rate shall be the yield to maturity of Armenian 6-month Government (treasury) bills. Secondary Rate is the average yield of Armenian 6-month (or if not available, closest to 6 months) Government (treasury) bills in primary auction.
2.3.2. In case of Adjustable Rates for USD-denominated loans: the primary rate underlying the Base Rate shall be the CME Term SOFR USD 6 Month reference rate. The Secondary Rate shall be the value of 6-month US treasury bills yield curve.
2.3.3. In case of Adjustable Rates for EUR-denominated loans: the primary rate underlying the Base Rate shall be the EURIBOR 6 Month rate. The Secondary Index shall be the value of the Germany 6 Month Government EUR Bond yield curve.
```

### SKIPPED BY PLANNER — `ev_1893abe705c42b7241723c96`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:0`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS

```text
rate at all times, and accordingly, calculation of the Adjustable Rate based on Secondary Rate shall be performed using the following formula:
RA = RB + SA + RM
where
RA is the Adjustable Rate
RB is the Base Rate
SA is the Spread Adjustment
RM is the margin (fixed component)
However, regardless of application of the Spread Adjustment, if the Agreement provides for a maximum Adjustable Rate limit, the interest rate calculated on the basis of the Secondary Rate and Spread Adjustment shall not exceed the set maximum limit1.
```

### SKIPPED BY PLANNER — `ev_c744bc057fe997bc80173dac`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:1`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS

```text
2.5. The margin (fixed component) shall be determined based on the terms of lending and shall be fixed in the loan agreement for each loan separately, on the basis of the respective loan decision adopted by the authorized body of the Bank.
```

### SKIPPED BY PLANNER — `ev_7ae4d10c8892d4cb408daa0a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:2`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS

```text
2.6. For the purpose of this Agreement and the Principal Agreement, the base rate of the Adjustable Rate for the Client (Borrower) at the time of execution of the Principal Agreement shall be equal to _______ percent, while the Margin (fixed component) shall be equal to _______ percent. Where the base rate of the Adjustable Rate is a negative value, the Adjustable Rate under the Principal Agreement shall be calculated based on 0 (zero).
```

### SKIPPED BY PLANNER — `ev_abc847f08908981802602463`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:3`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE
```

### SKIPPED BY PLANNER — `ev_c3ddbcbfb2df804c0c297e23`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:4`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.1. Information on the yield to maturity of Armenian Government (treasury) bills can be obtained from the relevant publications (yield curve) on the official website of the CBA at the following link:
https://www.cba.am/am/SitePages/fmofinancialmarkets.aspx
Information on the average yield of Armenian 6-month (or if not available, closest to 6 months) Government (treasury) bills in primary auctions can be retrieved from the official website of the Armenian Securities Exchange at the following link:
https://amx.am/am/government_bond_auctions
```

### SKIPPED BY PLANNER — `ev_5318099db8baacc46cef1536`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:5`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.2. Information on the CME Term SOFR USD 6 Month reference rate can be retrieved from Bloomberg terminal under TSFR6M ticker (SR6M in Reuters).
```

### SKIPPED BY PLANNER — `ev_5da39fe9b36011d0db811d24`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:6`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.3. Information on the EURIBOR 6 Month rate can be retrieved from Bloomberg terminal under EUR006M ticker (EURIBOR6MD in Reuters).
```

### SKIPPED BY PLANNER — `ev_4627587614d653516d31c58c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:7`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.4. Information on the yield of 6-month US treasury bills can be retrieved from Bloomberg terminal under H15T6M ticker (US6MT=RR in Reuters).
```

### SKIPPED BY PLANNER — `ev_2430c672d12515c65a644682`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:8`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.5. Information on the yield curve of Germany 6 Month Government EUR Bonds can be retrieved from Bloomberg terminal under YCGT0016 ticker (DE6MT=RR in Reuters).
```

### SKIPPED BY PLANNER — `ev_0bddf2f9b863d946cf6e24d1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:block:9`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.6. In case of inaccessibility of the Bloomberg Terminal or impossibility to check the information for any other reason, the Bank shall, upon the Borrower’s request, provide the information retrieved from the system to the Borrower by e-mail or other e-channels acceptable to the Parties and/or deliver it to the Borrower within the Bank premises. Whenever Bloomberg Terminal is not accessible, the information retrieved from Thomson Reuters Eikon shall be used as an alternative.
```

### SKIPPED BY PLANNER — `ev_b5e3fb82cf442a8921ab46b9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:2:note:0`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
1 This clause is not applicable in case of mortgage and consumer loans.
```

### SKIPPED BY PLANNER — `ev_a7593b6f2ca4d64501f89039`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:0`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.7. Change of any link specified in clauses 3.1, 3.2., 3.3, 3.4 ,3.5 and 3.9. above shall not affect or have any implications for this Agreement and/or its validity, except for the special cases provided for in clause 5.1 below.
```

### SKIPPED BY PLANNER — `ev_2a4ea5940ae01a312ab06df6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:1`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.8. The Base Rate shall be revised on February 1 and August 1 each year. In particular:
3.8.1.On February 1, the Base Rate shall be equal to the respective interest rate on the 30th business day preceding February 1 of that year. Where the value is negative, calculation is based on 0.
3.8.2.On August 1, the Base Rate shall be equal to the respective interest rate on the 30th business day preceding August 1. Where the value is negative, calculation is based on 0.
3.8.3.The method of calculation of the Base Rate specified in clause 3.8 herein cannot change during the term of the Agreement and the Principal Agreement.
```

### SKIPPED BY PLANNER — `ev_19156011bd542ca21eb988e0`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:10`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE

```text
4.7. The maximum increase threshold of the loan rate under the Principal Agreement shall not exceed the maximum decrease threshold.3
```

### SKIPPED BY PLANNER — `ev_fc022c3f85b7fb8251572197`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:2`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE

```text
3.9. The revised Base Rate and information about its changes shall be published on the Bank’s official website twice a year, on the first business days of February and August.
https://ameriabank.am/business/sme/financing/support/base-rate
```

### SKIPPED BY PLANNER — `ev_70e3f54e63ff4ab78d552213`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:3`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE

```text
4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE
```

### SKIPPED BY PLANNER — `ev_65bd736ca38b26cb5820a898`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:4`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE

```text
4.1. The first revision of the Adjustable Rate in accordance with this Agreement shall be in 3 (three)2 years after execution of the Principal Agreement, except in the case defined under clause 5.1 herein, unless otherwise provided for by the imperative norms of the Republic of Armenia laws and regulations. Thereafter, the Adjustable Rate may be revised regularly every 6 (six) months. Prior to the date of the first revision, the Base Rate shall be deemed equal to the Base Rate effective on the date of execution of the Principal Agreement.
```

### SKIPPED BY PLANNER — `ev_deeb59cc93be437b287674b7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:5`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE

```text
4.2. The Base Rate effective on the date of revision shall be deemed the applicable rate for the time span between the given and next revisions. Loan interest payments shall be calculated and made at the revised interest rate.
```

### SKIPPED BY PLANNER — `ev_eb386b4a37a2182819796e43`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:6`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE

```text
4.3. The date of application (calculation) of changed interest rate shall be the first payment date following the base rate change date (the first day of February and August).
```

### SKIPPED BY PLANNER — `ev_c75312ac6f7e444f2563da74`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:7`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE

```text
4.4. Calculations of the Base Rate shall be performed by rounding the rate to the nearest multiple of 0.5 (zero point five) percent. E.g., 8.23% shall be rounded to 8.0%, 8.25% shall be rounded to 8.5%, and 8.41% shall be rounded to 8.5%.
```

### SKIPPED BY PLANNER — `ev_9a3bf75b0808b598f3d8861c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:8`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE

```text
4.5. Hereby the Parties agree that the Base Rate:
4.5.1 Shall be revised by the Bank, if the difference between the interest rate for any particular period (rounded to 0.5 p.p.) and the effective Base Rate is more than 1%. The rate can be revised not more than to the extent of such difference, however, the Bank at its own discretion can revise the rate to a smaller extent which in any case should not be lower than 0.5%. (E.g., if the effective Base Rate is 8% and the new rate is 9.5%, the Bank can revise the rate by 0.5%, 1% or 1.5%).
4.5.2 Can be revised at the Bank’s discretion, if the difference between the interest rate for any particular period (rounded to 0.5 p.p.) and the effective Base Rate does not exceed 1%.
The terms of revision of the Base Rate set out in this clause shall be applicable both to upward and downward revision of the rate.
```

### SKIPPED BY PLANNER — `ev_6816438ecfcedf90bb5e2685`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:block:9`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE

```text
4.6. The revised rate shall be applied to the outstanding loan not earlier than 7 (seven) business days after giving notice to the Borrower in the manner of notification/communication specified in the Principal Agreement.
The Parties hereby state that in any case the loan interest rate specified in the Principal Agreement shall not exceed --- percent and shall not be less than ---- percent.
```

### SKIPPED BY PLANNER — `ev_5565c7dcc11a3a9d871e26ed`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:3:note:0`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
2 The 3-year requirement is mandatory in case of mortgage loans only.
3This clause is effective and applicable in case of mortgage and consumer loans only.
```

### SKIPPED BY PLANNER — `ev_f1d818b0fe918d0ab3971016`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:0`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 5 EXCEPTIONAL CIRCUMSTANCES

```text
5 EXCEPTIONAL CIRCUMSTANCES
```

### SKIPPED BY PLANNER — `ev_250199f56b8792b0ba4c13a9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:1`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 5 EXCEPTIONAL CIRCUMSTANCES

```text
5.1. Where the Primary and Secondary Indicators become inaccessible and impossible, the Parties agree that the Bank shall offer another similar indicator for the next period, relying solely on the standards defined by the CBA or the legislation of the Republic of Armenia. Adjustable Rate shall be considered inaccessible and impossible under the following exceptional circumstances.
5.1.1. Procedure of market interest rate calculation undergoes material changes.
5.1.2. Information on the interest rate, specified in clauses 2.3.1, 2.3.2 or 2.3.3, is no longer published for respective currency.
5.1.3. In the reasonable opinion of the Bank’s authorized body the given interest rate no longer represents the actual market situation.
5.1.4. Certain amendments to the Republic of Armenia laws and regulations prohibit or make it impossible to change the interest rate in accordance with the provisions of the Principal Agreement and the Agreement.
5.1.5. There are other economically or legally reasonable and justifiable bases.
5.1.6. In other cases provided for under the laws and regulations of the Republic of Armenia.
```

### SKIPPED BY PLANNER — `ev_f15d212a005f85936a7aa137`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:2`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 5 EXCEPTIONAL CIRCUMSTANCES

```text
5.2. Hereby the Borrower agrees that the Bank shall have the right to revise and adjust the Loan interest rate in favor of the Borrower at any time and any intervals during the term of the Agreement and/or the Principal Agreement.
```

### SKIPPED BY PLANNER — `ev_8c488fb698c6ac3ea1e7a7a6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:3`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS

```text
6 MISCELLANEOUS
```

### SKIPPED BY PLANNER — `ev_ce5e4474abf8acdac0a6d5b0`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:4`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS

```text
6.1. This Agreement shall be binding upon and inure to the benefit of the Parties’ successors and assigns.
```

### SKIPPED BY PLANNER — `ev_ca66b49da72c4260ba45513b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:5`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS

```text
6.2. The Agreement is made in Armenian and English in the number of counterparts equal to that of the Parties and persons providing security for obligations (if any). All counterparts are legally equal. Each Party receives one counterpart. By signing the Agreement each of the Parties confirms the receipt of their counterpart. In case of discrepancies the Armenian version shall prevail.
```

### SKIPPED BY PLANNER — `ev_7625bc4019326467cb2c59fa`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:6`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS

```text
6.3. Disagreements and disputes arising out of or in connection with the Agreement shall be referred to and resolved by the court of general jurisdiction of Yerevan, unless otherwise agreed between the Parties and/or stipulated by imperative legal norms of the Republic of Armenia.
```

### SKIPPED BY PLANNER — `ev_8bf2d14fb47e72268b8b7956`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:7`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS

```text
6.4. The Agreement shall become effective upon signing by both Parties and shall remain in full force and effect until proper fulfillment of the liabilities of the Parties under the Agreement.
```

### SKIPPED BY PLANNER — `ev_345a240878b7264a9676b3cc`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:block:8`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 7 ADDRESSES AND SIGNATURES OF THE PARTIES

```text
7 ADDRESSES AND SIGNATURES OF THE PARTIES
```

### SKIPPED BY PLANNER — `ev_532a83a8cd172d863b81ff60`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `document:6:eca03d247e60:page:4:table:0:row:0`  
Role / authority: `legal_disclosure` / `official_terms`  
Temporal status: `unknown`  
Section: (none)

```text
Headers: Bank | CLIENT/BORROWER
Row: Ameriabank CJSC
Address: 2 V. Sargsyan st., Yerevan
Authorized person
________________________________
(name, surname, signature)
Seal | ............................
Passport: ...................................
Address: ...................................
___________________
Signature
```

### SKIPPED BY PLANNER — `ev_eb1e5edea484b2bd337379e5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b100`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
INFORMATION ON FACTORS ABOUT CREDIT HISTORY AND CREDIT SCORE
```

### SKIPPED BY PLANNER — `ev_ffb33f9ef74fbcc86ab3e587`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b101`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
This document sets out the information required under the Republic of Armenia laws and regulations about the credit history and the credit score of customers during lending in Ameriabank CJSC (hereinafter “the Bank”) and the factors affecting them.
```

### SKIPPED BY PLANNER — `ev_5f51fae1d916f0716b577134`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b102`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Credit History is the information on the customer’s financial obligations generated/processed by the Credit Bureau, which shows the customer’s debt, payments, payment habits or other data related to the customer’s obligations or their performance and the dynamics/history of such information.
```

### SKIPPED BY PLANNER — `ev_f37b558f80500642e1cc4428`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b103`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
The credit history includes, in particular, the information required for customer identification, amount of each monetary obligation of the customer, annual interest rate, outstanding liabilities, order and terms of payments, payment delays, guarantees issued to the third parties, information about the liabilities of the parties affiliated with the customer (in depersonalized form) and the information about credit history inquiries.
```

### SKIPPED BY PLANNER — `ev_c13ef642dc017b410ede0c43`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b104`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
As a rule, financial organizations use the credit history to assess the customer’s monetary (credit) obligations, guarantees issued to the third parties, to consider the possibilities of lending at the customer’s or bank’s initiative and to submit lending offers to the customer.
```

### SKIPPED BY PLANNER — `ev_df3d60bc4bed5908380e7abc`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b105`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Based on the customer’s consent the Bank sends an inquiry to ACRA Credit Bureau. The information about the credit history is reflected in the credit report which covers the customer’s credit history for the most recent 5 years.
```

### SKIPPED BY PLANNER — `ev_db1cc12c60e32fbe93520592`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b106`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
The Customer’s credit history is available at http://www.acra.am/.
```

### SKIPPED BY PLANNER — `ev_acfe808c3f0417b27752f261`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b107`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Credit score is the quantified measure of the customer’s borrowing capacity and creditworthiness.
```

### SKIPPED BY PLANNER — `ev_f07c5fac7b4b3550cf1cf2f1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b108`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
The Bank uses its own system to assess the borrowing capacity and creditworthiness for lending to customers. The factors affecting it are as follows:
```

### SKIPPED BY PLANNER — `ev_b20747de488d3a8e4ec28f15`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b109`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Credit history. The quantity and amount of existing loans, frequency of applying for loans, positive credit history (no payment delays in the credit history, high quality of loan service) can help improve the credit score and make a positive decision on lending, while a bad credit history (payment delays in the credit history, persistent nature of such delays) can serve as a basis for reducing the credit score, rejecting a new loan application or reviewing it on more stringent terms.
```

### SKIPPED BY PLANNER — `ev_78b112286055986140ca8d2a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b110`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Employment, income and work experience. Stable job and income can help improve the credit score and make a positive decision on lending. Unstable or non-permanent job or income can serve as a basis for reducing the credit score and rejecting a new loan application or reviewing it on more stringent terms.
```

### SKIPPED BY PLANNER — `ev_90dcb30558fab4c566f56248`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b111`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Credit burden.High credit burden and its big share in the income can serve as a basis for reducing the credit score and rejecting a new loan application or reviewing it on more stringent terms, while a low credit burden and its small share in the income can help improve the credit score and make a positive decision on lending
```

### SKIPPED BY PLANNER — `ev_72fe3683c126f115b07bcce3`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b112`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
FICO Score. FICO Score is a scoring system that provides a numerical value of credit risk through statistic research and analysis of the customer’s credit history. It is a key used by lenders worldwide to assess creditworthiness and financial risks. Details are available at acra.am.
```

### SKIPPED BY PLANNER — `ev_197d8c32709bb8da6c5afadd`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b113`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Other information about the Customer
```

### SKIPPED BY PLANNER — `ev_c933b39e9b300d87de42d1bb`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b114`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
The importance of credit history and credit score
```

### SKIPPED BY PLANNER — `ev_365ffdd665df5a47a9995d0e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b115`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Credit history and credit score are essential for making a decision on lending, enabling banks and credit organizations to assess the credit risk of the customer during lending and predict the customer’s proper fulfillment of customer’s monetary obligations and its likelihood.
```

### SKIPPED BY PLANNER — `ev_8ea52356a2b649cfe6cbb061`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b116`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Wrong or incomplete credit history
```

### SKIPPED BY PLANNER — `ev_e6215b1f6ce7dd53041ff94d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b117`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
If there are wrong or incomplete data in the credit history, the customer can apply to ACRA Credit Reporting CJSC (credit bureau) or directly to the financial organizations having provided the information to the Credit Bureau to correct or clarify such data.
```

### SKIPPED BY PLANNER — `ev_b212d63c2eaf35cf7e20f02d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b118`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
The procedure and details on applying to ACRA Credit Reporting CJSC is available at www.acra.am
```

### SKIPPED BY PLANNER — `ev_d2869a24025e32b6b9c7adf2`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b119`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Where wrong or incomplete information has been provided to the Credit Bureau by the Bank, the customer can apply to the Bank via any of the following channels:
```

### SKIPPED BY PLANNER — `ev_047806b761051e68e4a4a3fc`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b120`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
By sending an application to the Bank’s official email address
```

### SKIPPED BY PLANNER — `ev_9de1d8694a9b4d1835ef902a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b121`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
By calling the Bank at 010/012 561111 phone numbers
```

### SKIPPED BY PLANNER — `ev_5f01992fcd10e9c99bfbe387`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b122`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
By sending a message via the Bank’s Online/Mobile Banking system
```

### SKIPPED BY PLANNER — `ev_7cd95fdde3134fa675f609ec`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b123`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
By submitting an application at any of the Bank’s branches.
```

### SKIPPED BY PLANNER — `ev_23c506b37c8e02898e84d752`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b124`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
The Bank will process the customer’s application in the manner and within the time frames defined by the Republic of Armenia laws and regulations, and/or the Bank’s internal regulations.
```

### SKIPPED BY PLANNER — `ev_6caf332f0a7d8ec1ba55c129`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b125`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
How to improve the credit history and credit score
```

### SKIPPED BY PLANNER — `ev_f02e171e34ffb2a48bba6025`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b126`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
To improve the credit history and credit score it is necessary to eliminate its root causes as soon as possible, in particular:
```

### SKIPPED BY PLANNER — `ev_4c12bfbe1bf7962da6b49861`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b127`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Make loan payments in accordance with the defined schedule, excluding any late payments and even 1-day overdue liabilities
```

### SKIPPED BY PLANNER — `ev_f05ac22c74b7009208298b5f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b128`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Limit the number and amount of provided guarantees, by repaying the overdue liabilities secured by guarantees, if possible
```

### SKIPPED BY PLANNER — `ev_3a71c32b4501dab7031a2b7e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b129`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Reduce the credit burden by repaying the outstanding liabilities
```

### SKIPPED BY PLANNER — `ev_0ddb4f3740d4c3fe1d31a2a4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b130`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Avoid submitting new loan applications frequently since credit history inquiries (other than for loan monitoring purposes) may negatively affect the customer’s Credit Score.
```

### SKIPPED BY PLANNER — `ev_a8aa864b536fa22c25e768ae`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b131`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Detailed information about the credit history (including wrong or incomplete information) and/or Credit Score is available on the following pages:
```

### SKIPPED BY PLANNER — `ev_6b9dbb62f0e54bfea4fdd876`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b132`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
acra.am –Support– Frequently Asked Questions
```

### SKIPPED BY PLANNER — `ev_afbdcbdbefe88b21b22a06bf`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b133`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
abcfinance.am
```

### SKIPPED BY PLANNER — `ev_a10a603aeb2fa4ecb5348f3b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b134`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
abcfinance.am
```

### SKIPPED BY PLANNER — `ev_27a99293d4360167121042eb`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b135`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of the loan for purchase of residential real estate from primary market
```

### SKIPPED BY PLANNER — `ev_5b94f605ae24d89f826b551a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b136`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of express Home Mortgage Loan (Purchase, Construction and Renovation)
```

### FAILED — `ev_54c091d4bf1e3eaaa76fc9bb`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `b137`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC
```

### FAILED — `ev_6f6d1b69eb83b6314e778c82`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `b138`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of residential and commercial real estate mortgage lending (including refinancing) campaign
```

### SKIPPED BY PLANNER — `ev_0eef31a454cb3cd06611f735`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b139`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Loan service fees
```

### SKIPPED BY PLANNER — `ev_87fe9f294f2b9108312fbcde`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b140`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
“Finance for All” abcfinance.am website
```

### SKIPPED BY PLANNER — `ev_4f543861c7f0618e19d50188`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b141`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Your financial database www.fininfo.am
```

### SKIPPED BY PLANNER — `ev_dd83614ff390d79e055571cc`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b142`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
On the Procedure for Setting, Calculation and Revision of the Floating (Adjustable) Interest Rate
```

### SKIPPED BY PLANNER — `ev_d756a834a74282d627ff73de`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b143`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 30.03.26 to 31.05.26)
```

### SKIPPED BY PLANNER — `ev_7245dce5576a10b92ef14a47`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b144`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 23.03.26 to 29.03.26)
```

### SKIPPED BY PLANNER — `ev_4470031566f485a77d033f7c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b145`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 04.02.26 to 23.03.26)
```

### SKIPPED BY PLANNER — `ev_8bcfc55c58c7b59ead584d9c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b146`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 20.11.25 to 03.02.26)
```

### SKIPPED BY PLANNER — `ev_16af46445a398926e233a627`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b147`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 02.09.25 to 05.10.25)
```

### SKIPPED BY PLANNER — `ev_8402e156a23b613c679614df`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b148`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 04.06.25 to 01.09.25)
```

### SKIPPED BY PLANNER — `ev_cf5ac8dd07da1167e5833d68`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b149`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 25.11.24 to 03.06.25)
```

### SKIPPED BY PLANNER — `ev_d245c4350454f79b6a9fb380`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b150`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Be informed when applying for a loan
```

### SKIPPED BY PLANNER — `ev_5b885b2f9ed665e62681041b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b151`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Loan Calculators
```

### SKIPPED BY PLANNER — `ev_b30cd2a172cc5074a46bd364`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b153`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Real estate loan
for secondary market
```

### SKIPPED BY PLANNER — `ev_0bf0f1230cdb8618c9b19b4e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b155`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Construction loan
```

### SKIPPED BY PLANNER — `ev_a1b4c22f3b54cbbb4fb71513`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b57`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Tariffs
```

### SKIPPED BY PLANNER — `ev_41b2d2f1fb317ca357ced519`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b58`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Express Home Mortgage Loan (Purchase, Construction and Renovation)
```

### SKIPPED BY PLANNER — `ev_f357eb428c08f79a2309b73a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b59`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Loan service fees
```

### SKIPPED BY PLANNER — `ev_14faa334f00871aeecc849a5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b60`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Collateral appraisal
```

### SKIPPED BY PLANNER — `ev_fe4894e49c27fc7fb893d91a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b61`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Insurance of pledged property
```

### SKIPPED BY PLANNER — `ev_091d9b5ea42ea8d5c5037d61`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b62`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Additional payments
```

### SKIPPED BY PLANNER — `ev_04a55fd7532060c70469ecfb`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b63`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Required documents
```

### SKIPPED BY PLANNER — `ev_fb264413158c8bd5f8807c9a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b64`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Credit history and score
```

### SKIPPED BY PLANNER — `ev_282d5170feb5b100d1e9f9f9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b65`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Useful Information
```

### SKIPPED BY PLANNER — `ev_91985c64d5567296b0337bc7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b66`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Old Terms
```

### SKIPPED BY PLANNER — `ev_7ec319656f9be6419ef68545`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b70`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
The real estate should be appraised by an appraisal company cooperating with the bank. The company is selected by the client from the offered list. Appraisal fee: AMD 13,000-30,000 depending on the property. On a case-by-case basis, the fee for appraisal of major items of property may be negotiable. The list of appraisal companies cooperating with the Bank may be found at the link below.
```

### SKIPPED BY PLANNER — `ev_32fa775abf6e467af7e2e773`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b71`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Appraisal Companies Cooperating with Ameriabank
```

### SKIPPED BY PLANNER — `ev_453545c3e18a3ee83876fd70`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b72`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Insurance for the pledged property to be obtained on an annual basis throughout the loan term:
```

### SKIPPED BY PLANNER — `ev_0056f91888092b4f8e675e5c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b73`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
by the bank to the extent of outstanding loan
```

### SKIPPED BY PLANNER — `ev_a093182d17e0f5b617192fe2`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b74`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
by the client at least to the extent of outstanding loan
```

### SKIPPED BY PLANNER — `ev_23411eefb24b4c17dfb6a0f6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b75`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Notary fee: AMD 14,000-16,000 lump-sum (in case of vehicles)
```

### SKIPPED BY PLANNER — `ev_05decb26b7d080b1ac2bfd69`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b76`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Notary fee: AMD 13,000-18,000 lump-sum (in case of real estate)
```

### SKIPPED BY PLANNER — `ev_ab336c2ad7e7fcede7f59890`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b77`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Fee for unified statement from the State Real Estate Cadaster on encumbrance of the property: AMD 10,000
```

### SKIPPED BY PLANNER — `ev_93b16a497bed918f5581e927`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b78`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Fee for registration of security interest in the real estate: AMD 26,000
```

### SKIPPED BY PLANNER — `ev_0579750bbce868a473612f07`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b79`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Certificate of the right to purchase real estate and registration of the security interest: AMD 3,000 and AMD 50,000
```

### SKIPPED BY PLANNER — `ev_f65aaf1222f8660927d03c26`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b80`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Certificate of acquisition of the title to the real estate and registration of the security interest: AMD 21,000 and AMD 50,000
```

### SKIPPED BY PLANNER — `ev_90f9fc919f5845e77f07de97`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b81`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Certificate of acquisition of the title to the commercial real estate and registration of the security interest: AMD 41,000 (if the area of the premises to be purchased and pledged is above 200 sq. m) and AMD 50,000
```

### SKIPPED BY PLANNER — `ev_eb3c269d7cd571960e577f8f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b82`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Fee of the Police of the Republic of Armenia (for lien and pledge of movable property): AMD 5,000 lump sum
```

### FAILED — `ev_fd8e294a788d4e1597492132`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `b83`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Required documents filed together with loan application
```

### SKIPPED BY PLANNER — `ev_6edeaf0399367094b41b905e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b84`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Loan application
```

### SKIPPED BY PLANNER — `ev_d0f345ac18292de294774515`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b85`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
ID [original]
```

### SKIPPED BY PLANNER — `ev_4366dc6086a8452378d30226`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b86`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Certificate of ownership of property to be purchased/pledged [copy]
```

### SKIPPED BY PLANNER — `ev_7c07e7654dd4638f48e58247`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b87`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Proof of employment and/or other income
```

### SKIPPED BY PLANNER — `ev_e3e873d962e35294f1e4c712`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b88`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Marriage (divorce, spouse death), birth certificate [original]
```

### SKIPPED BY PLANNER — `ev_52770e8ed1f57460232d3bee`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b89`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Certificate of title to real estate to be pledged [original]
```

### SKIPPED BY PLANNER — `ev_f5ab27a41d37524d01a77cef`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b90`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Geodetic measurement report of land plot to be pledged**
```

### SKIPPED BY PLANNER — `ev_8456b57d49315e449ad7a972`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b91`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Initial real estate appraisal report
```

### SKIPPED BY PLANNER — `ev_b52509e3d0027da62a5a8e42`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b92`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Construction costs estimate
```

### SKIPPED BY PLANNER — `ev_6dc9a42162c3ffb556ecca5b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b93`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Copies of bases of title to real estate (to be submitted upon request)
```

### SKIPPED BY PLANNER — `ev_a7987f5c3501d99f23eeaf84`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b94`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
IDs of owners of property to be purchased/pledged [originals]
```

### SKIPPED BY PLANNER — `ev_713d3260f1fd262de32aa8d3`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b95`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Copies of marriage (divorce, spouse death) certificates of owners of property to be pledged
```

### SKIPPED BY PLANNER — `ev_cd1747974678ead7fd81a28c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b96`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)
```

### SKIPPED BY PLANNER — `ev_919ffde6c458b79e40f78935`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b97`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Real estate appraisal report (final)
```

### SKIPPED BY PLANNER — `ev_9448c14e9dec71a1cd4d7eeb`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b98`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Other documents as the bank's specialist may request
```

### SKIPPED BY PLANNER — `ev_730ea0008c450145ca8c0bc7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b99`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `time_bounded`  
Section: Real estate loan for primary market &gt; Terms and conditions

```text
Depending on various circumstances, the bank may request other documents and information. Where required under the Republic of Armenia Law “On Combating Money Laundering and Terrorism Financing”, we may request you to provide additional information and documents to conduct “Know your customer” check, as well as ask further questions during verbal communication.
```

### SKIPPED BY PLANNER — `ev_8e2a06ad2f752b28ccca97c5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:note:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Home Purchase Loan (primary market)
```

### SKIPPED BY PLANNER — `ev_1db803a0bf19edf604948d46`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:note:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
```

### SKIPPED BY PLANNER — `ev_d8259361f1cfd3e0f7ad8e8a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:note:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
```

### FAILED — `ev_ba8346dc509d48bc2cf09ad3`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t1:note:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
- When the property insurance is obtained by the Bank at the customer’s request
- When the borrower selects differentiated or mixed form of loan repayment
- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
- If additional property is pledged as collateral
- If there are other deviations
```

### SKIPPED BY PLANNER — `ev_b44727986c641b82611ded34`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:note:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
```

### SKIPPED BY PLANNER — `ev_30bfdc19fafb4fa5ac143839`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:note:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
```

### SKIPPED BY PLANNER — `ev_f0b5f4f96d0471f2ea7ec0ba`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) |  | 
```

### SKIPPED BY PLANNER — `ev_b0e40a07d98558e1148362e9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:10`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed | 3.4.2. Fixed | 3.4.3. Fixed
```

### SKIPPED BY PLANNER — `ev_df89a1ef322034ce92e74833`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:11`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 13.5% | 11.0% | 8.5%
```

### SKIPPED BY PLANNER — `ev_ee6c39b9f4bde6e269612fc9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:12`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed | 3.5.2. Fixed | 3.5.3. Fixed
```

### SKIPPED BY PLANNER — `ev_ea1abf83e46c050da2daf19d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:13`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 14.39-15.76% | 11.6-13.56% | 8.86-10.71%
```

### SKIPPED BY PLANNER — `ev_d7c5a2142de724755f7bb6bd`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:14`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 |  | 
```

### SKIPPED BY PLANNER — `ev_86f3b35f814e70938d945f30`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:15`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)
```

### SKIPPED BY PLANNER — `ev_18cf9831f366bbbafaf41039`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:16`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.7. Nominal annual interest rate² | Fixed component 5.5% + variable component (base rate) | Fixed component 8% + variable component (base rate) | Fixed component 7% + variable component (base rate)
```

### SKIPPED BY PLANNER — `ev_0c7d2668ee9689841596eba8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:17`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | Term and interest rate in case of online refinancing |  |  | 
```

### SKIPPED BY PLANNER — `ev_d3cff7c14f8df334b255cba5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:18`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.8. Term (months) | 3.8.1. 61-360 |  | 
```

### SKIPPED BY PLANNER — `ev_c6be4aed2b52670b4033fb0d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:19`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.9. Nominal annual interest rate | 3.9.1. Adjustable fixed (rate can be changed starting from the 37th month) | N/a | N/a
```

### SKIPPED BY PLANNER — `ev_c1e1a5f6f11f558cfbd798d8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:20`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.9. Nominal annual interest rate | Fixed component 5.25% + variable component (base rate) | N/a | N/a
```

### SKIPPED BY PLANNER — `ev_b229a4c55bb8dfba1c341aaa`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:21`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 3.10.1. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.2. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.3. Adjustable fixed (rate can be changed starting from the 37th month)
```

### SKIPPED BY PLANNER — `ev_13cd7e3ffab8b366aad97fb8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:22`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 14.35-15.74% | 10.47-12.39% | 8.3-10.12%
```

### SKIPPED BY PLANNER — `ev_fa091226691cace4a4343d57`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:23`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. |  | 
```

### SKIPPED BY PLANNER — `ev_b34e296e848310a4fbd055e8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:24`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. |  | 
```

### SKIPPED BY PLANNER — `ev_7b5a5e5104bc09ae4d77b347`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:25`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. |  | 
```

### FAILED — `ev_4d45f092060a46ddcc1c6186`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t1:row:26`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). |  | 
```

### SKIPPED BY PLANNER — `ev_3bf3884e6c09a877aa0cdaf5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:27`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. |  | 
```

### SKIPPED BY PLANNER — `ev_e33824994f6db4c99d1f8b01`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:28`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.12. Lump sum disbursement fee | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less |  | 
```

### SKIPPED BY PLANNER — `ev_4bec5acde71a29030384a023`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:29`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.13. Minimum down payment | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. |  | 
```

### SKIPPED BY PLANNER — `ev_d43ca1a9ca61e6696f8c4118`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:30`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.14. Manner of disbursement | 1. Lump sum
2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. |  | 
```

### SKIPPED BY PLANNER — `ev_0a701836f57afc946e32817b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:31`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.15. Cashing of the loan amount by the seller from their account with the Bank after loan disbursement (where applicable) | 3.15.1.
AMD: Free
Other currency: 0.5 % |  | 
```

### FAILED — `ev_9f3c7404986efef1100e728a`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t1:row:32`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) |  | 
```

### SKIPPED BY PLANNER — `ev_48c0f4049f81795b762b0947`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:33`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) /not applicable in case of online refinancing/ |  | 
```

### SKIPPED BY PLANNER — `ev_80791ca1dd3190c728ac45d7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:34`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (the customer may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) /not applicable in case of online refinancing/ |  | 
```

### SKIPPED BY PLANNER — `ev_197834f4f70905ac648a92be`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:35`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.1. Eligible collateral | 5.1.1.
1. The loan is secured by the real estate being purchased. The Bank may consider pledge of other real estate as additional security to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.
2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.
3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank.
4. In the case of online refinancing, the collateral is real estate purchased directly from the developer, which has a completion certificate and is not encumbered with any liabilities other than the refinanced loan. |  | 
```

### SKIPPED BY PLANNER — `ev_014fec966fdc495c0f920cfa`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:36`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.2. Loan-to-value (LTV) ratio | 5.2.1. The loan is issued:
1. For AMD loans with a term of 61-240 months: up to 90%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,
For AMD loans with a term above 240 months: up to 80%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁶ reference provided to the client, unless otherwise determined by the Bank,
2. For foreign currency loans with a term of 61-240 months: up to 70%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client,
For foreign currency loans with a term above 240 months: up to 60%² of the (i) lesser of the two: appraised market value of the property and purchase price, or (ii) value specified in the developer’s⁵ reference provided to the client, unless otherwise determined by the Bank,
3. up to 100% of the value of cash in the Bank or bonds issued by the Bank.
4. For up to AMD 30 million loans without creditworthiness assessment: up to 70% (if in Yerevan) and up to 60% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).
For AMD 30-50 million loans without creditworthiness assessment: up to 60% (if in Yerevan) and up to 50% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization).
For AMD 50-100 million loans without creditworthiness assessment: up to 50% (if in Yerevan) and up to 40% (if in the regions of Armenia) of the price specified in the developer reference⁵ or the lower of the two: appraised market value or purchase price of pledged property (this clause does not refer to the loans issued with a purpose of transfer of existing loans from another bank/credit organization). |  | 
```

### SKIPPED BY PLANNER — `ev_8dd0d1a8a8f04bfeae37412b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:38`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Armenia
5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020. |  | 
```

### SKIPPED BY PLANNER — `ev_b34f3f640c48ef5a30e619d6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:39`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.4. Appraisal of the collateral | 5.4.1.
1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer’s reference, unless otherwise determined by the Bank.
2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank. |  | 
```

### FAILED — `ev_dfdf83ed8abc0d3b01f04804`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t1:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 2. Customer’s personal details | 2.1. Eligible age of the customer/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. |  | 
```

### SKIPPED BY PLANNER — `ev_a5a00953a456a6f9d75782c8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:40`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security. |  | 
```

### SKIPPED BY PLANNER — `ev_7cf94307a77632deb3272486`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:41`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases: |  | 
```

### SKIPPED BY PLANNER — `ev_e631138d08d32618784ef636`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:42`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or |  | 
```

### SKIPPED BY PLANNER — `ev_7f7d020428f808a3fef4a48b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:43`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website. |  | 
```

### SKIPPED BY PLANNER — `ev_320e4fefc64ed1cdcc7d6982`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:44`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |  | 
```

### SKIPPED BY PLANNER — `ev_0d39c775b544f6d277bf9c7a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:45`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application |  | 
```

### SKIPPED BY PLANNER — `ev_d06c31b9f697b87c401e2337`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:46`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Loan application (not applicable in case of online refinancing) |  | 
```

### SKIPPED BY PLANNER — `ev_beb9d12f2fafc0e560b8667b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:47`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • ID (original) |  | 
```

### SKIPPED BY PLANNER — `ev_975f86b6844114e42c62d02c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:48`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Certificate of ownership/purchase right of real estate to be purchased/pledged (copy) |  | 
```

### SKIPPED BY PLANNER — `ev_94708de03c1c4cf7ab92adda`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:49`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Other documents upon the Bank’s request |  | 
```

### SKIPPED BY PLANNER — `ev_7a04879078fb654fe3177a61`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 2. Customer’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia
For loans in foreign currency: individuals not considered residents of Armenia |  | 
```

### SKIPPED BY PLANNER — `ev_f1f564a137f613289d7d259d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:50`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | 7.1.2. Documents required after pre-approval |  | 
```

### SKIPPED BY PLANNER — `ev_56e82fd82b67a3e09600adc6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:51`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Proof of employment and/or other income (not applicable in case of online refinancing) |  | 
```

### SKIPPED BY PLANNER — `ev_e068a74defd12921fe093ebf`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:52`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original) |  | 
```

### SKIPPED BY PLANNER — `ev_8bf4a3d210c9a9b1b26cca3c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:53`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Certificate of title to real estate to be pledged (original) |  | 
```

### SKIPPED BY PLANNER — `ev_2a4359e8953fa7736b0feb7e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:54`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Other documents upon the Bank request |  | 
```

### SKIPPED BY PLANNER — `ev_644651ea0b8e1606b0bc4bcd`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:55`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | 7.1.3. Documents required after loan approval |  | 
```

### SKIPPED BY PLANNER — `ev_71aba60f9656b872bfffee06`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:56`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Copies of bases of title to real estate (to be submitted upon the Bank’s request) |  | 
```

### SKIPPED BY PLANNER — `ev_a7228304b7e61f24447317c4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:57`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • IDs of owners of the property to be purchased/pledged (originals) |  | 
```

### SKIPPED BY PLANNER — `ev_53ea453b6c397c54ee9619f1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:58`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available |  | 
```

### SKIPPED BY PLANNER — `ev_05610098532209f82fe0a3b3`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:59`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement) |  | 
```

### SKIPPED BY PLANNER — `ev_899d289e8f1e34228d2ff987`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
```

### SKIPPED BY PLANNER — `ev_7eca0d390b8870604983eab1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:60`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Tax clearance certificate for the real estate |  | 
```

### SKIPPED BY PLANNER — `ev_95f7554f6030b9a48d38dfae`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:61`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Real estate insurance policy (as required) |  | 
```

### SKIPPED BY PLANNER — `ev_88d4ed89699dee967ba0efae`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:62`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system. |  | 
```

### FAILED — `ev_f62609d84453068ab3c593cd`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t1:row:64`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.
At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.
Where the amount of early repayment exceeds the specified limit, the following fees will be charged:
• Max 0.6% of early repayment, if made during the first year of the agreement
• Max 0.4% of early repayment, if made during the second year of the agreement
• Max 0.2% of early repayment, if made during the third year of the agreement |  | 
```

### SKIPPED BY PLANNER — `ev_0ddcb8c0ef242468b4560e8e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:65`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.
Fine in the amount of 0.13 % of overdue loan and interest for each day of delay |  | 
```

### SKIPPED BY PLANNER — `ev_d1b10ad1bf6b8041b94cd6ce`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:66`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 10. Other fees | 10.1. Other fees | 10.1.1. Fees payable by the customers for the new loans
• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and
• Appraisal fee for the real estate being pledged (as necessary)
10.1.2 Fees payable by the Bank for the loans refinanced online
• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and
• Appraisal fee for the real estate being pledged |  | 
```

### SKIPPED BY PLANNER — `ev_91bc95c7958b40c18b05323b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:67`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 11. Creditworthiness assessment | 11.1 Without creditworthiness assessment | Where the loan amount is AMD 50-100 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 50% (if in Yerevan) or 60% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank
Where the loan amount is AMD 30-50 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 40% (if in Yerevan) or 50% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank.
Where the loan amount is up to AMD 30 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 30% (if in Yerevan) or 40% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank. |  | 
```

### SKIPPED BY PLANNER — `ev_c080eef1024ee578c69428c1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1.
AMD 3,000,000 - AMD 150,000,000
For online refinancing: AMD 3,000,000-100,000,000 | 3.2.2.
USD 5,000 - USD 300,000
Not applicable in case of online refinancing | 3.2.3.
EUR 5,000 - EUR 300,000
Not applicable in case of online refinancing
```

### SKIPPED BY PLANNER — `ev_b6f871c6dbda7bbf7cc5bebe`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:8`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | Term and interest rate |  |  | 
```

### SKIPPED BY PLANNER — `ev_4f87ca9824010b7e1e34438c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t1:row:9`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Tariffs

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.3. Term (months) | 3.3.1. 60 |  | 
```

### SKIPPED BY PLANNER — `ev_8ee42a3cbc103456ef95a5f3`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:0`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Express Home Mortgage Loan (Purchase, Construction and Renovation)
```

### SKIPPED BY PLANNER — `ev_29e3245628bd7773ce626813`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:1`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
General requirements to loan facilities
```

### SKIPPED BY PLANNER — `ev_157bf7c3138e9ca8c8f28470`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Express Home Purchase Loan (primary market)
```

### SKIPPED BY PLANNER — `ev_b0162e961f750b416e469b73`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Express Home Purchase Loan (secondary market)
```

### SKIPPED BY PLANNER — `ev_576b8a681d2a783e74d03b9b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Express Home Construction Loan
```

### SKIPPED BY PLANNER — `ev_adf4b92ae9f6eb5602349968`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Express Home Renovation Loan
```

### SKIPPED BY PLANNER — `ev_30cd2e9ae41b050ccc28cc11`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Attention! The offer of the agreement is provided to the client following which the client may use the 7-day cooling-off period envisaged by the Armenian laws and regulations.
In case of failure to notarize the pledge agreements specified in the loan agreement and securing the borrower's obligations under the loan agreement, within 30 (thirty) business days upon execution of the loan agreement and acceptance by the Borrower, the Agreement shall cease to be valid (unless the loan has already been disbursed to the borrower by that date).
```

### SKIPPED BY PLANNER — `ev_ae7f536b3329b6baf9c157af`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is 5%.
```

### SKIPPED BY PLANNER — `ev_a4c1234de42665cf20d91c2f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:note:8`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
The list of developers is determined by the Bank.
```

### FAILED — `ev_501c5f6565b582c21cb14bab`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t2:row:13`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 6. Early repayment fee | 6.1. Early repayment fee | 6.1.1.
At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.
Where the amount of early repayment exceeds the specified limit, the following fees will be charged:
• Max 0.6% of early repayment, if made during the first year of the agreement
• Max 0.4% of early repayment, if made during the second year of the agreement
• Max 0.2% of early repayment, if made during the third year of the agreement
```

### SKIPPED BY PLANNER — `ev_6b6f793a5cf454c76ce3b3c0`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:14`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 7. Late payment fines and penalties | 7.1. Late payment fines and penalties | 7.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.
Fine in the amount of 0.13% of overdue loan/interest for each overdue day
```

### SKIPPED BY PLANNER — `ev_ef4a22ec8060cf4287f9ce05`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:15`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 8. Other fees | 8.1. Other fees payable by the client | 8.1.1. Fee for notarization of real estate pledged as collateral
Fee for registration of the right of ownership/purchase and the Bank rights arising out of the pledge agreements with the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
Fee for the unified reference on real estate encumbrance issued by the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
Fee for the final appraisal of the real estate (if required)
```

### FAILED — `ev_e333f6cba6280e621d911747`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t2:row:16`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | 9.1.1. Required documents filed together with the loan application
```

### SKIPPED BY PLANNER — `ev_1f8b062eb498e785336168c9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:17`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | ID, public services number
```

### SKIPPED BY PLANNER — `ev_244e5a5135a02a2ce38a5003`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:18`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | 9.1.2. Documents required after pre-approval
• Certificate of title to real estate to be pledged (copy)
• Initial real estate appraisal report
• Other documents upon the Bank’s request
9.1.3. Documents required after loan approval
```

### SKIPPED BY PLANNER — `ev_1c79fda3cf6518cdc55fb073`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:2`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 1. Client’s personal details | 1.1. Eligible age of client/co-borrower | 1.1.1. 18-70, provided that the age of the borrower by the time of expiry of loan agreement will not have exceeded 70
```

### SKIPPED BY PLANNER — `ev_0bae9dcc8cdd1175efcde574`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:23`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Marriage certificate (if any) and ID of the spouse, public services number
```

### SKIPPED BY PLANNER — `ev_88d9409b336781120b35be59`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:24`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Certificate of title to the real estate/right to purchase
```

### SKIPPED BY PLANNER — `ev_c3ecbdf11aeb060bd52ef7c7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:25`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Certificate of security interest registration
```

### SKIPPED BY PLANNER — `ev_3ae1d28579581f24e773dae4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:26`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Unified reference on real estate encumbrance
```

### SKIPPED BY PLANNER — `ev_c909f5f5bc84bdee524be070`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:27`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | • Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.
```

### SKIPPED BY PLANNER — `ev_78066417f12bb442a1a51b8c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:28`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Construction permit (for construction loans)
```

### SKIPPED BY PLANNER — `ev_4548fd909545c455981ab21e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:29`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Pro-forma invoice (for renovation and construction loans)
```

### SKIPPED BY PLANNER — `ev_e68ce1cbf90519af7b7be856`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:3`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 1. Client’s personal details | 1.2. Residency | 1.2.1. Citizens of Armenia who are resident in Armenia
```

### SKIPPED BY PLANNER — `ev_d0f0049ba93df6f8853cd1cf`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:30`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Other documents upon the Bank’s request
```

### FAILED — `ev_2dc5f658213dca6f7c88b994`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t2:row:32`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes
```

### SKIPPED BY PLANNER — `ev_113655d7a7a65b08b510e98c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:35`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.2. Term (months) | 1.2.1. 61-360
```

### SKIPPED BY PLANNER — `ev_e2db0799032c969ff1027076`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:36`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
```

### SKIPPED BY PLANNER — `ev_698ecf3b7e4f7b8d02d1a1a7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:37`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.3. Nominal annual interest rate | Fixed component 5.25% + variable component (base rate)
```

### SKIPPED BY PLANNER — `ev_07b19939201a1f2938f1dd43`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:38`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.4. Annual percentage rate (APR) | 1.4.1. 14.08-15.57%
```

### SKIPPED BY PLANNER — `ev_80ae049c1151bf19e114fb05`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:39`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.5. Minimum down payment | 1.5.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
```

### SKIPPED BY PLANNER — `ev_2975cf9456c0f7f574b30e07`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:4`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Terms and Conditions | 2.1. Currency | 2.1.1. AMD
```

### SKIPPED BY PLANNER — `ev_e461de59707aa47177eee8dc`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:40`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

### SKIPPED BY PLANNER — `ev_a55a10f2aa7b8727efeeb63b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:41`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1
1.1. For loans with a term of 240 months, the loan amount is up to 90% of the sale price set by the developer³.
For loans with a term above 240 months, the loan amount is up to 80% of the sale price set by the developer⁴, unless otherwise determined by the Bank.
```

### SKIPPED BY PLANNER — `ev_5ee44355ae2bb1cb4233752a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:42`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.3. Location of the real estate to be pledged | 5.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard
```

### SKIPPED BY PLANNER — `ev_6e7e4d87c7c968fd5cebd3fb`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:43`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. N/A
The price statement provided by the Developer⁴ is taken as the basis for the collateral value.
```

### FAILED — `ev_14c473dbbc98f1fbf6acbebe`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t2:row:45`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes.
```

### SKIPPED BY PLANNER — `ev_ba6947e4f4bed47b2e514e40`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:5`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Terms and Conditions | 2.2. Minimum and maximum loan limit | 2.2.1. AMD 3,000,000-100,000,000
```

### SKIPPED BY PLANNER — `ev_7c893329c0fc3042b6535d4d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:50`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.3. Nominal annual interest rate | Fixed component 5.75% + variable component (base rate)
```

### SKIPPED BY PLANNER — `ev_33ce15c934a8bc8076fcf8c1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:51`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.4. Annual percentage rate (APR) | 1.4.1. 14.66-17.11%
```

### SKIPPED BY PLANNER — `ev_50db911cdd8882419a35a7c3`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:52`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.5. Minimum down payment | 1.5.1. At least 5% of the purchase price of the property
```

### SKIPPED BY PLANNER — `ev_a1859556de0cf973f3235b7e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:54`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80% (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70% (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
```

### SKIPPED BY PLANNER — `ev_f91187afb5dfd8edfef9fe82`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:55`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard
```

### SKIPPED BY PLANNER — `ev_861c2615858581b3745c8218`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:56`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank.
```

### FAILED — `ev_7fe5d12bd4e60d5e8bdf1715`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t2:row:58`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 1. Purpose | 1.1. Purpose | 1.1. Construction of residential property
```

### SKIPPED BY PLANNER — `ev_d9ac482a51a32d0aae0e79bb`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:6`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Terms and Conditions | 2.3. Cashing of the loan amount by the borrower or the seller from his account with the Bank after loan disbursement (where applicable) | 2.3.1.
AMD: free
```

### SKIPPED BY PLANNER — `ev_5ab71c3be58c6c347c52cfd2`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:64`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9%
```

### SKIPPED BY PLANNER — `ev_2375c9f33ab4d225a98e00dd`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:65`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being constructed. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

### SKIPPED BY PLANNER — `ev_95c703a68f11347d33d07897`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:66`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
```

### SKIPPED BY PLANNER — `ev_3bc369cd3e391fa518699321`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:67`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard
5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020.
```

### FAILED — `ev_4624927f2cc8426f656f1b53`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t2:row:69`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.
For loans over AMD 50 million contractual amount at least 3 tranches must be defined.
```

### SKIPPED BY PLANNER — `ev_5adc40fae9090e3b8eea5bc2`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:7`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Terms and Conditions | 2.4. Lump sum disbursement fee | 2.4.1. N/A
```

### FAILED — `ev_1b16519fa16b80044e428990`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t2:row:71`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 1. Purpose | 1.1. Purpose | 1.1. Renovation of residential property
```

### SKIPPED BY PLANNER — `ev_2d5336ad3e21843d04d49577`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:74`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row:  | 1.2. Term (months) | 1.2.1. 61-240
```

### SKIPPED BY PLANNER — `ev_f706c67095e27b7452718de5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:78`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being renovated. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

### FAILED — `ev_033878c6a2803988370af7a6`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t2:row:8`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 3. Forms of loan repayment | 3.1. Repayment method | 3.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)
```

### SKIPPED BY PLANNER — `ev_bbd2a66647d9e27c31cb05ad`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t2:row:9`  
Role / authority: `product_terms` / `official_terms`  
Temporal status: `current`  
Section: Express Home Mortgage Loan (Purchase, Construction and Renovation)

```text
Headers: Section | Item | Terms
Row: 5. Insurance of the collateral | 5.1. Insurance of the collateral | 5.1.1. The real estate being pledged is insured by the Bank in the following cases:
5.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or
5.1.1.2. where the address of the pledged real estate is included in the list of properties published on the Bank’s website.
5.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable).
```

### SKIPPED BY PLANNER — `ev_47df8d13a0adc963e522377f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:1`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 1. Term extension for mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000
```

### SKIPPED BY PLANNER — `ev_42e32106dd74a5ba1480f867`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:10`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 10. Provision of loan before submitting to the Bank the document certifying state registration of the security interest | AMD 25,000 (per issue)
```

### SKIPPED BY PLANNER — `ev_208e52bdd80bcad27137b4ab`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:11`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 11. Issuing other consent not established by this document and not related to the collateral | AMD 10,000
(VAT included)
```

### SKIPPED BY PLANNER — `ev_e2fac17ad904b379a685a8f1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:12`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 12. Revision/modification of another loan term not specified in this document (including interest rate revision) | 0.1% of the outstanding loan amount, minimum AMD 10,000
```

### SKIPPED BY PLANNER — `ev_582e2353e6d514647abe55f9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:2`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 2. Granting a grace period for the principal amount of mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000
```

### SKIPPED BY PLANNER — `ev_b6a8f1d1cb71bc288efc3e04`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:3`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 3. Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000
```

### SKIPPED BY PLANNER — `ev_2ab6f04896a7f4d7c5002106`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:4`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 4. Change of the overdraft/line of credit account/card | AMD 30,000
```

### SKIPPED BY PLANNER — `ev_b6bfc42927a7f0ef14f9e0c8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:5`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 5. Change of the borrower/co-borrower/guarantor | AMD 50,000
```

### SKIPPED BY PLANNER — `ev_dd65eef40c866c68a620bc5b`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:6`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 6. Release/substitution of the collateral | AMD 50,000
```

### SKIPPED BY PLANNER — `ev_46eabe3fe7eacaa7f8dfa30c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:7`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 7. Issuing consent for change of a pledged vehicle plate number | AMD 50,000
(VAT included)
```

### SKIPPED BY PLANNER — `ev_4259a3d29d33db929be585b7`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `t3:row:8`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 8. Collateral-related change (including change of the collateral owner) | AMD 15,000
```

### FAILED — `ev_c905c54fc15d7c050e161390`

Sent to the LLM, but the extraction run did not produce a validated result.  
Source item: `t3:row:9`  
Role / authority: `fees` / `official_terms`  
Temporal status: `current`  
Section: Loan service fees

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 9. Change of the loan repayment date | AMD 10,000
```

### SKIPPED BY PLANNER — `ev_027eb3b714ea0e857cdda674`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b152`  
Role / authority: `product_description` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Terms and conditions &gt; Loan Calculators

```text
How much can you borrow?
Calculate how much you can borrow as a mortgage based on your salary or other income and your financial situation.
```

### SKIPPED BY PLANNER — `ev_3c700e1104e8402cd68289bf`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b154`  
Role / authority: `related_product` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Terms and conditions &gt; Real estate loan for secondary market

```text
If you have already found your ideal home on the secondary market and are looking for financing options, our offer is for you. You can obtain financing directly from us or transfer your house loan from another bank or credit organization to Ameriabank.
```

### SKIPPED BY PLANNER — `ev_21079901faf0a561b9b6244d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b16`  
Role / authority: `product_description` / `official_product_content`  
Temporal status: `unknown`  
Section: (none)

```text
Real estate loan for primary market
```

### SKIPPED BY PLANNER — `ev_7ec48ce56a184291d9f1af6f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b17`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
Your new home is waiting for you
```

### SKIPPED BY PLANNER — `ev_a046933eb5bf73cf3c7a61ab`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b18`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
AMD 3-150 million
```

### SKIPPED BY PLANNER — `ev_3b5f6812e01948e06f4a84fd`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b19`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; AMD 3-150 million

```text
Loan amount
```

### SKIPPED BY PLANNER — `ev_f8ea6bdb581eb9bd2292f7a5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b20`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
60-360 months
```

### SKIPPED BY PLANNER — `ev_4412665ad45e5eb9d396d47e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b21`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; 60-360 months

```text
Term
```

### SKIPPED BY PLANNER — `ev_4ddf67de07299c46f5bf630d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b22`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
12.9%
```

### SKIPPED BY PLANNER — `ev_07016bd49e57a7e82edf01c5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b23`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; 12.9%

```text
Nominal interest rate
```

### SKIPPED BY PLANNER — `ev_3c1c98bcefa254a9a5f8502d`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b24`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
from 10%
```

### SKIPPED BY PLANNER — `ev_d44812b1d3340083c3312863`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b25`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; from 10%

```text
Advance payment
```

### SKIPPED BY PLANNER — `ev_b58dcae3d3e6f59e9da30f92`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b26`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; from 10%

```text
Actual interest rate: 13.67-13.68%
```

### SKIPPED BY PLANNER — `ev_90232d0744e99446f240b6a0`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b27`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
Real estate loan for primary market
```

### SKIPPED BY PLANNER — `ev_e78af03cd7acdfce078143ed`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b30`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES

```text
No property appraisal required
```

### SKIPPED BY PLANNER — `ev_28ccdb06f521d1eaed7198f4`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b31`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES

```text
Advance payment: from 10%
```

### SKIPPED BY PLANNER — `ev_66156bdc79f938a6f1f8d60a`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b32`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES

```text
Property insurance by the Bank
```

### SKIPPED BY PLANNER — `ev_775b10b7802368a323c1e7a3`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b33`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES

```text
No loan service fees
```

### SKIPPED BY PLANNER — `ev_c10ddb48ce2bea5f956d10a0`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b34`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES

```text
Purchase of real estate for living or lease
```

### SKIPPED BY PLANNER — `ev_9102da48bec0331556d99b71`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b35`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES

```text
Both in Yerevan and regions
```

### SKIPPED BY PLANNER — `ev_ed8aad4a5420ecd6f6aea760`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b36`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES

```text
Mortgage calculator
```

### SKIPPED BY PLANNER — `ev_c006990058d4efec43a32622`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b37`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
Mortgage calculator
```

### SKIPPED BY PLANNER — `ev_5098d84e5ac87056ae5aa858`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b38`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
Restriction applies to entry of values as per the Bank’s terms.
```

### SKIPPED BY PLANNER — `ev_45fddda57fb695932e488fa8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b39`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
Annual interest rate (%)
```

### SKIPPED BY PLANNER — `ev_603705bd9610e9e9f2d14df6`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b40`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
12.5 %14 %
```

### SKIPPED BY PLANNER — `ev_612fe2d9b72743ccbb52c0a0`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b41`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
Mortgage loan amount (AMD)
```

### SKIPPED BY PLANNER — `ev_c1d10e80d5d16064cb566db9`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b42`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
3,000,000150,000,000
```

### SKIPPED BY PLANNER — `ev_aeb7975035d0aae91c0716f8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b43`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
Mortgage loan term (months)
```

### SKIPPED BY PLANNER — `ev_bd4a1725166645a5a33f8372`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b44`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
60360
```

### SKIPPED BY PLANNER — `ev_68ea68f487903aa73a22f22f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b45`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
MONTHLY INSTALLMENT
```

### SKIPPED BY PLANNER — `ev_d9a7d8e39f88ca3679d74f75`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b46`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
227,228
```

### SKIPPED BY PLANNER — `ev_c1aa712eac3b273d90e339c5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b47`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
Total amount payable
```

### SKIPPED BY PLANNER — `ev_9798b6c15aadb3b65458b63f`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b48`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
54,534,746
```

### SKIPPED BY PLANNER — `ev_d18b8af2354abbb292544762`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b49`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
AMD
```

### SKIPPED BY PLANNER — `ev_2d16e8f370f040e284bb03b8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b50`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
Total interest amount
```

### SKIPPED BY PLANNER — `ev_face1f9a4b39a5abd7d4eeb1`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b51`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
34,534,746
```

### SKIPPED BY PLANNER — `ev_762d64c66976d39ecd257c4c`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b52`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
AMD
```

### SKIPPED BY PLANNER — `ev_cac39e7fdc0f3976258b0650`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b53`  
Role / authority: `pricing` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Mortgage calculator

```text
Dear Client, this calculation is for information only and might be changed
```

### SKIPPED BY PLANNER — `ev_f6b542f2defc3d922c53caa5`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b54`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
Find your new home online
```

### SKIPPED BY PLANNER — `ev_4fd5b9dc01616f6f8d033d2e`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b55`  
Role / authority: `product_description` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Find your new home online

```text
Choose your new apartment according to area, monthly payment amount and other criteria and submit a credit report online.
By the way, you can also apply for a loan with a co-borrower.
```

### SKIPPED BY PLANNER — `ev_7e36b5564ca96b03c59c7dec`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b56`  
Role / authority: `product_terms` / `official_product_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market

```text
Terms and conditions
```

### SKIPPED BY PLANNER — `ev_7577e60ac7c2e683a6595af8`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b28`  
Role / authority: `product_description` / `marketing_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market

```text
Want to buy a new apartment or house? Our mortgage loan offer for the primary market will help you to buy your new home from our partner developers.
The choice is easier to make via our online platform, find your ideal option, use the calculator to find out your monthly payment, and apply online:
```

### SKIPPED BY PLANNER — `ev_9c3e8a2831ca0322fe77e129`

Accepted by source discovery but not selected for any bounded field packet.  
Source item: `b29`  
Role / authority: `product_description` / `marketing_content`  
Temporal status: `unknown`  
Section: Real estate loan for primary market &gt; Real estate loan for primary market

```text
ADVANTAGES
```
