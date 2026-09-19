# Semantic extraction audit

Product: **mortgage**  
Model: **gemini-3.7-flash**

Before Gemini extraction, a deterministic extraction planner groups requested fields (for example rates, fees, or eligibility), ranks accepted evidence by its source-discovery role, keywords, and authority precedence, and enforces configured item/character limits. It does not decide whether a tariff value is true and it does not use an LLM.

**NOT SENT TO SEMANTIC LLM** therefore means the evidence was accepted by source discovery but was not included in any bounded field packet after that deterministic ranking and size/count limiting. It was not rejected as false or irrelevant.

## Stage error

**FAILED — ValidationError:** 22 validation errors for tuple[ConditionalValue[Rate], ...]
0.value
  Field required [type=missing, input_value={'rate_type': 'fixed', 'r...s': ['Term: 60 months']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
0.conditions.0
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Term: 60 months', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
1.value
  Field required [type=missing, input_value={'rate_type': 'fixed', 'r...s': ['Term: 60 months']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
1.conditions.0
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Term: 60 months', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
2.value
  Field required [type=missing, input_value={'rate_type': 'fixed', 'r...s': ['Term: 60 months']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
2.conditions.0
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Term: 60 months', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
3.value
  Field required [type=missing, input_value={'rate_type': 'adjustable...g from the 37th month']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
3.conditions.0
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Term: 61-360 months', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
3.conditions.1
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Rate can be changed starting from the 37th month', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
4.value
  Field required [type=missing, input_value={'rate_type': 'adjustable...g from the 37th month']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
4.conditions.0
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Term: 61-360 months', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
4.conditions.1
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Rate can be changed starting from the 37th month', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
5.value
  Field required [type=missing, input_value={'rate_type': 'adjustable...g from the 37th month']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
5.conditions.0
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Term: 61-360 months', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
5.conditions.1
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Rate can be changed starting from the 37th month', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
6.value
  Field required [type=missing, input_value={'rate_type': 'adjustable...g from the 37th month']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
6.conditions.0
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Online refinancing', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
6.conditions.1
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Term: 61-360 months', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
6.conditions.2
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Rate can be changed starting from the 37th month', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
7.value
  Field required [type=missing, input_value={'rate_type': 'adjustable...g from the 37th month']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
7.conditions.0
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Mortgage lending campaign', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type
7.conditions.1
  Input should be a valid dictionary or instance of Condition [type=model_type, input_value='Rate can be changed starting from the 37th month', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/model_type

The evidence packets below remain available for diagnosis. Items that were sent are marked failed because no validated result was assembled.

## Source-discovered evidence

---

### Evidence 001 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0fc34c0fca496347631a72b4` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:0` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք. Երեւան, Նոր Նորք Ար. Միկոյան փող. 2/1 շենք
```

</details>

---

### Evidence 002 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_05f3cdc5609482321d2f823c` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:1` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք. Երեւան, Արաբկիր Մալխասյանց փողոց 6/1 շենք
```

</details>

---

### Evidence 003 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2833b86866222cab8fde5fa4` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:2` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք. Երեւան, Նոր-Նորք Հ. Գյուլիքեւխյան փողոց 14/2 շենք
```

</details>

---

### Evidence 004 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_af0cdc93b9d68e6f47846a93` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:3` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք. Երեւան, Ավան Աճառյան փողոց 39/25 շենք
```

</details>

---

### Evidence 005 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_444d10e456d91d729fc21e53` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:4` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք. Երեւան, Արաբկիր Օրբելի եղբայրների փողոց 67/2 շենք
```

</details>

---

### Evidence 006 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9db27e2682ae8f4d3f22e201` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:5` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք. Երեւան, Աջափնյակ Հ. Շիրազի փողոց 2/9 շենք
```

</details>

---

### Evidence 007 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8b23b7cdd100f81f35ee7568` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:6` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք. Երեւան, Քանաքեռ-Զեյթուն Պ. Սեւակի փողոց 51/2 շենք
```

</details>

---

### Evidence 008 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_df0b952a70990d79db5fec48` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:7` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք. Երեւան, Արաբկիր Մամիկոնյանց փողոց 45/1 շենք
```

</details>

---

### Evidence 009 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5746ebc18f70002aba151c49` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:8` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: ք.Երեւան, Աջափնյակ Նորաշեն թաղամաս 47/5 շենք
```

</details>

---

### Evidence 010 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0743b7cd26a99f8db0391c4f` |
| Source item | `document:0:c9465a0d1c77:page:1:table:0:row:9` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Հասցե
Row: Ք.Երեւան, Շենգավիթ, Մ. Ֆրունզեի փողոց 10/4 շենք
```

</details>

---

### Evidence 011 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2b5320decd083937cf1f8431` |
| Source item | `document:1:db6b470de92a:page:1:block:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | product_details |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
AMERIABANK CJSC
11RBD PL 72-03-98
```

</details>

---

### Evidence 012 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_061543db796edafd4439a53b` |
| Source item | `document:1:db6b470de92a:page:1:block:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents, identity, product_details |
| Section | Retail Lending Terms and Conditions<br>(Home Mortgage Loan)¹ |

<details open>
<summary><strong>Source content</strong></summary>

```text
Retail Lending Terms and Conditions
(Home Mortgage Loan)¹
```

</details>

---

### Evidence 013 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2ed59017084431d188fe77e1` |
| Source item | `document:1:db6b470de92a:page:1:block:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents, identity, product_details |
| Section | Retail Lending Terms and Conditions<br>(Home Mortgage Loan)¹ |

<details open>
<summary><strong>Source content</strong></summary>

```text
Edition 73
Effective date: August 5, 2026
```

</details>

---

### Evidence 014 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_83987852a3a18a62f60161d3` |
| Source item | `document:1:db6b470de92a:page:1:block:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents, identity, product_details |
| Section | Retail Lending Terms and Conditions<br>(Home Mortgage Loan)¹ |

<details open>
<summary><strong>Source content</strong></summary>

```text
Approved by Management Board Resolution # 08/1/01/14 as of February 4, 2014.
Current edition approved by Management Board resolutions # 01/15/26 as of May 27, 2026, and # 01/95/26 as of June 25, 2026.
```

</details>

---

### Evidence 015 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4f977ed905997b9f03886bb1` |
| Source item | `document:1:db6b470de92a:page:1:block:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents, identity, product_details |
| Section | Retail Lending Terms and Conditions<br>(Home Mortgage Loan)¹ &gt; Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Home Purchase Loan (primary market)
```

</details>

---

### Evidence 016 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2e949a3eb424e1d890afb98a` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity, product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the "Bank") | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the "Bank") | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the "Bank")
```

</details>

---

### Evidence 017 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b37cac821f9a0622fdac38b8` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, eligibility_and_documents, product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 2. Customer's personal details | 2.1. Eligible age of the customer/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
```

</details>

---

### Evidence 018 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7b7df48517f862bcff61e827` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:10` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)
```

</details>

---

### Evidence 019 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_addd63de9c69f517e134f72f` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 2. Customer's personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia
For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia
For loans in foreign currency: individuals not considered residents of Armenia | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia
For loans in foreign currency: individuals not considered residents of Armenia
```

</details>

---

### Evidence 020 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ca25afaa0326f1c02b7e40a6` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
```

</details>

---

### Evidence 021 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d506837e798dba5cb714cdcd` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 3. Loan terms | 3.2. Minimum and maximum loan limits | 3.2.1. AMD 3,000,000 - AMD 150,000,000
For online refinancing: AMD 3,000,000-100,000,000 | 3.2.2. USD 5,000 - USD 300,000
Not applicable in case of online refinancing | 3.2.3. EUR 5,000 - EUR 300,000
Not applicable in case of online refinancing
```

</details>

---

### Evidence 022 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5831c1b100cdf23ad71544bd` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 3. Loan terms | Term and interest rate | Term and interest rate | Term and interest rate | Term and interest rate
```

</details>

---

### Evidence 023 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_77176cd8457704904257448f` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 3. Loan terms | 3.3. Term (months) | 3.3.1. 60 | 3.3.1. 60 | 3.3.1. 60
```

</details>

---

### Evidence 024 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_034843b7a57c7b89f4f3fee4` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed
13.5% | 3.4.2. Fixed
11.0% | 3.4.3. Fixed
8.5%
```

</details>

---

### Evidence 025 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f40d5a4519c322614a9c7b1e` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:8` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed
14.39-15.76% | 3.5.2. Fixed
11.6-13.56% | 3.5.3. Fixed
8.86-10.71%
```

</details>

---

### Evidence 026 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6b777eb6204f18f5cd4643f8` |
| Source item | `document:1:db6b470de92a:page:1:table:0:row:9` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
Row: 3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 | 3.6.1. 61-360 | 3.6.1. 61-360
```

</details>

---

### Evidence 027 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_94de52c4c720762a17a4a6ca` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | 3.7. Nominal annual interest rate² (cont.) | Fixed component 5.5% + variable component (base rate) | Fixed component 8% + variable component (base rate) | Fixed component 7% + variable component (base rate)
```

</details>

---

### Evidence 028 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_836385c04c99372010b69350` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing | Term and interest rate in case of online refinancing
```

</details>

---

### Evidence 029 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4b1755bfe6a53a83a5df3039` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | 3.8. Term (months) | 3.8.1. 61-360 | 3.8.1. 61-360 | 3.8.1. 61-360
```

</details>

---

### Evidence 030 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_835587e2c1392ef521ef44fd` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, product_details |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | 3.9. Nominal annual interest rate | 3.9.1. Adjustable fixed (rate can be changed starting from the 37th month)
Fixed component 5.25% + variable component (base rate) | N/a | N/a
```

</details>

---

### Evidence 031 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b9e671cbf796ac354f329d1a` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 3.10.1. Adjustable fixed (rate can be changed starting from the 37th month)
14.35-15.74% | 3.10.2. Adjustable fixed (rate can be changed starting from the 37th month)
10.47-12.39% | 3.10.3. Adjustable fixed (rate can be changed starting from the 37th month)
8.3-10.12%
```

</details>

---

### Evidence 032 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d41cc0e5c98d6bfc1b4c7f30` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, fees_and_repayment |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%.
3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.
3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.
3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).
3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%.
3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.
3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.
3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).
3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%.
3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.
3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%.
3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds).
3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%.
```

</details>

---

### Evidence 033 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_205418fca7eda0431216fd57` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | 3.12. Lump sum disbursement fee | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less
```

</details>

---

### Evidence 034 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0b24723d21b383b06048fb52` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | 3.13. Minimum down payment | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral.
```

</details>

---

### Evidence 035 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9ed82894147b90951c8dbb1a` |
| Source item | `document:1:db6b470de92a:page:2:table:0:row:8` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | AMD | USD | EUR
Row: 3. Loan terms | 3.14. Manner of disbursement | 1. Lump sum
2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | 1. Lump sum
2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. | 1. Lump sum
2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower.
```

</details>

---

### Evidence 036 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c6683b9e88407a0d3aad4ab1` |
| Source item | `document:1:db6b470de92a:page:3:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 3. Loan terms | 3.15. Cashing of the loan amount by the seller from their account with the Bank after loan disbursement (where applicable) | 3.15.1.
AMD: Free
Other currency: 0.5 %
```

</details>

---

### Evidence 037 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2e5db7724016a8ec6cb2e614` |
| Source item | `document:1:db6b470de92a:page:3:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | fees_and_repayment |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)
4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) /not applicable in case of online refinancing/
4.1.3. Mixed (the customer may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) /not applicable in case of online refinancing/
```

</details>

---

### Evidence 038 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f5790033d05133ee73f3f836` |
| Source item | `document:1:db6b470de92a:page:3:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 5. Security | 5.1. Eligible collateral | 5.1.1.
1. The loan is secured by the real estate being purchased. The Bank may consider pledge of other real estate as additional security to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.
2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.
3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank.
4. In the case of online refinancing, the collateral is real estate purchased directly from the developer, which has a completion certificate and is not encumbered with any liabilities other than the refinanced loan.
```

</details>

---

### Evidence 039 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_05b84fe217d0cef484561b1c` |
| Source item | `document:1:db6b470de92a:page:3:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
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

</details>

---

### Evidence 040 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ef530ec81ab2d7d281b5f52c` |
| Source item | `document:1:db6b470de92a:page:3:table:0:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Armenia
5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020.
```

</details>

---

### Evidence 041 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b33667dfb5240c32ba6b9222` |
| Source item | `document:1:db6b470de92a:page:4:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 5. Security | 5.4. Appraisal of the collateral | 5.4.1.
1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer’s reference, unless otherwise determined by the Bank.
2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank.
```

</details>

---

### Evidence 042 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b1dc4540e94820076840585b` |
| Source item | `document:1:db6b470de92a:page:4:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security.
```

</details>

---

### Evidence 043 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2e10a78972a642feed52cb06` |
| Source item | `document:1:db6b470de92a:page:4:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases:
6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or
6.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website.
6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable).
```

</details>

---

### Evidence 044 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0dfea65594a305b823240b51` |
| Source item | `document:1:db6b470de92a:page:4:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application
• Loan application (not applicable in case of online refinancing)
• ID (original)
• Certificate of ownership/purchase right of real estate to be purchased/pledged (copy)
• Other documents upon the Bank’s request
7.1.2. Documents required after pre-approval
• Proof of employment and/or other income (not applicable in case of online refinancing)
```

</details>

---

### Evidence 045 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1a5e857534d0e83bc28e1a06` |
| Source item | `document:1:db6b470de92a:page:5:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 7. Required documents | 7.1. Required documents (cont.) | • Marriage (divorce, spouse death) certificate (original)
• Certificate of title to real estate to be pledged (original)
• Other documents upon the Bank request
7.1.3. Documents required after loan approval
• Copies of bases of title to real estate (to be submitted upon the Bank’s request)
• IDs of owners of the property to be purchased/pledged (originals)
• Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available
• Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)
• Tax clearance certificate for the real estate
• Real estate insurance policy (as required)
• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.
• Other documents upon the Bank’s request
```

</details>

---

### Evidence 046 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9ba66f8b7f932b4e275caa72` |
| Source item | `document:1:db6b470de92a:page:5:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | fees_and_repayment |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.
At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.
Where the amount of early repayment exceeds the specified limit, the following fees will be charged:
• Max 0.6% of early repayment, if made during the first year of the agreement
• Max 0.4% of early repayment, if made during the second year of the agreement
• Max 0.2% of early repayment, if made during the third year of the agreement
```

</details>

---

### Evidence 047 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b609368444dc11d2bc24e5b4` |
| Source item | `document:1:db6b470de92a:page:5:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.
Fine in the amount of 0.13 % of overdue loan and interest for each day of delay
```

</details>

---

### Evidence 048 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6a4bb999512e3ffb0a821e24` |
| Source item | `document:1:db6b470de92a:page:5:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 10. Other fees | 10.1. Other fees | 10.1.1. Fees payable by the customers for the new loans
• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and
• Appraisal fee for the real estate being pledged (as necessary)
10.1.2 Fees payable by the Bank for the loans refinanced online
• Fee for unified statement from the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
• Fees for notarization of pledge (real estate), registration of the Bank’s security interest under pledge agreement, and
• Appraisal fee for the real estate being pledged
```

</details>

---

### Evidence 049 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a8cee0737f317e40551303bd` |
| Source item | `document:1:db6b470de92a:page:6:note:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
¹These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
```

</details>

---

### Evidence 050 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_77c3d8397f7471654d054e35` |
| Source item | `document:1:db6b470de92a:page:6:note:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
²Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
```

</details>

---

### Evidence 051 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0f2c273aa9673ad170f94518` |
| Source item | `document:1:db6b470de92a:page:6:note:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | fees_and_repayment |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
³The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
- When the property insurance is obtained by the Bank at the customer’s request
- When the borrower selects differentiated or mixed form of loan repayment
- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
- If additional property is pledged as collateral
- If there are other deviations
```

</details>

---

### Evidence 052 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a0ecf342b0dc0c7cae7b3b5c` |
| Source item | `document:1:db6b470de92a:page:6:note:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
⁴ Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
```

</details>

---

### Evidence 053 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e1b4d317cd9be1e38bc8a80f` |
| Source item | `document:1:db6b470de92a:page:6:note:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
⁵ The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
```

</details>

---

### Evidence 054 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_36c66b82c00c2ac9374ce1a7` |
| Source item | `document:1:db6b470de92a:page:6:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Home Purchase Loan (primary market) - Continued |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Parameter | Details
Row: 11. Creditworthiness assessment | 11.1 Without creditworthiness assessment | -Where the loan amount is AMD 50-100 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 50% (if in Yerevan) or 60% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank
Where the loan amount is AMD 30-50 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 40% (if in Yerevan) or 50% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank.
Where the loan amount is up to AMD 30 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 30% (if in Yerevan) or 40% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank.
```

</details>

---

### Evidence 055 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_97a94853e7363636edf55612` |
| Source item | `document:2:175e5d151b3d:page:1:block:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents, identity |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
AMERIABANK CJSC
11RBD PL 72-03-98
Retail Lending Terms and Conditions (Home Mortgage Loan)¹
Edition 73
Effective date: August 5, 2026
```

</details>

---

### Evidence 056 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ccfef905417cc03fe4e52fac` |
| Source item | `document:2:175e5d151b3d:page:1:block:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Approved by Management Board Resolution # 08/1/01/14 as of February 4, 2014.
Current edition approved by Management Board resolutions # 01/15/26 as of May 27, 2026, and # 01/95/26 as of June 25, 2026.
```

</details>

---

### Evidence 057 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5fe6720d9e7e38d51faa8b90` |
| Source item | `document:2:175e5d151b3d:page:1:block:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ |

<details open>
<summary><strong>Source content</strong></summary>

```text
Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹
```

</details>

---

### Evidence 058 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_76d8ca67eeefd5519998a658` |
| Source item | `document:2:175e5d151b3d:page:1:block:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
General requirements to loan facilities
```

</details>

---

### Evidence 059 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_22e7f41bfa0747ef3aa042d9` |
| Source item | `document:2:175e5d151b3d:page:1:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Customer's personal details | 1.1. Eligible age of client/co-borrower | 1.1.1. 18-70, provided that the age of the borrower by the time of expiry of loan agreement will not have exceeded 70
```

</details>

---

### Evidence 060 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ab26af1aed03e6ce66f40a05` |
| Source item | `document:2:175e5d151b3d:page:1:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Customer's personal details | 1.2. Residency | 1.2.1. Citizens of Armenia who are resident in Armenia
```

</details>

---

### Evidence 061 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8906fc033c54352fc403f28c` |
| Source item | `document:2:175e5d151b3d:page:1:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Terms and Conditions | 2.1. Currency | 2.1.1. AMD
```

</details>

---

### Evidence 062 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e8ece253c2bd4f77d3bd6fcf` |
| Source item | `document:2:175e5d151b3d:page:1:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Terms and Conditions | 2.2. Minimum and maximum loan limit | 2.2.1. AMD 3,000,000 - AMD 100,000,000
```

</details>

---

### Evidence 063 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a5918ddf3da67015b87781c2` |
| Source item | `document:2:175e5d151b3d:page:1:table:0:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Terms and Conditions | 2.3. Cashing of the loan amount by the borrower or the seller from his account with the Bank after loan disbursement (where applicable) | 2.3.1.
AMD: free
```

</details>

---

### Evidence 064 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c7777eca7004a899488662c2` |
| Source item | `document:2:175e5d151b3d:page:1:table:0:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Terms and Conditions | 2.4. Lump sum disbursement fee | 2.4.1. N/A
```

</details>

---

### Evidence 065 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_41e84435a02efffce75a4212` |
| Source item | `document:2:175e5d151b3d:page:1:table:0:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | fees_and_repayment |
| Section | General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 3. Forms of loan repayment | 3.1. Repayment method | 3.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)
```

</details>

---

### Evidence 066 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d681043e428cccb0e9457318` |
| Source item | `document:2:175e5d151b3d:page:1:table:0:row:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial |
| Section | General requirements to loan facilities |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 5. Insurance of the collateral | 5.1. Insurance of the collateral | 5.1.1. The real estate being pledged is insured by the Bank in the following cases:
5.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or
5.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank's website.
5.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable).
```

</details>

---

### Evidence 067 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_570ee489e2a851615f4348ee` |
| Source item | `document:2:175e5d151b3d:page:2:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | fees_and_repayment |
| Section | General requirements to loan facilities (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 6. Early repayment fee | 6.1. Early repayment fee | 6.1.1.
At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.
Where the amount of early repayment exceeds the specified limit, the following fees will be charged:
• Max 0.6% of early repayment, if made during the first year of the agreement
• Max 0.4% of early repayment, if made during the second year of the agreement
• Max 0.2% of early repayment, if made during the third year of the agreement
```

</details>

---

### Evidence 068 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f33203e80c827611f8cd7c24` |
| Source item | `document:2:175e5d151b3d:page:2:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | General requirements to loan facilities (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 7. Late payment fines and penalties | 7.1. Late payment fines and penalties | 7.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.
Fine in the amount of 0.13 % of overdue loan and interest for each day of delay
```

</details>

---

### Evidence 069 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3d1c576f9befb00db8eede06` |
| Source item | `document:2:175e5d151b3d:page:2:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | General requirements to loan facilities (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 8. Other fees | 8.1. Other fees payable by the customer | 8.1.1. Fee for notarization of real estate pledged as collateral
Fee for registration of the right of ownership/purchase and the Bank rights arising out of the pledge agreements with the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
Fee for the unified reference on real estate encumbrance issued by the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
Fee for the final appraisal of the real estate (if required)
```

</details>

---

### Evidence 070 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2182ca6c7d85339f31112e2f` |
| Source item | `document:2:175e5d151b3d:page:2:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | General requirements to loan facilities (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 9. Required documents | 9.1. Required documents | 9.1.1. Required documents filed together with the loan application
ID, public services number
9.1.2. Documents required after pre-approval
• Certificate of title to real estate to be pledged (copy)
• Initial real estate appraisal report
• Other documents upon the Bank's request
9.1.3. Documents required after loan approval
Marriage certificate (if any) and ID of the spouse, public services number
Certificate of title to the real estate/right to purchase
Certificate of security interest registration
Unified reference on real estate encumbrance
• Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.
Construction permit (for construction loans)
Pro-forma invoice (for renovation and construction loans)
Other documents upon the Bank's request
```

</details>

---

### Evidence 071 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8d4b0cd40476da2af80f1138` |
| Source item | `document:2:175e5d151b3d:page:3:block:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
1. Express Home Purchase Loan (primary market)
```

</details>

---

### Evidence 072 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2eb70717053306791ac558f1` |
| Source item | `document:2:175e5d151b3d:page:3:block:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; 2. Express Home Purchase Loan (secondary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
2. Express Home Purchase Loan (secondary market)
```

</details>

---

### Evidence 073 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_45024e54be5212a38ef415d6` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes
```

</details>

---

### Evidence 074 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_53420e5b9912abe8fdbddd04` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360
```

</details>

---

### Evidence 075 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_61302abc47b62484976e684c` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
Fixed component 5.25% + variable component (base rate)
```

</details>

---

### Evidence 076 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f39c4fee1bf1de19c676d46a` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.08-15.57%
```

</details>

---

### Evidence 077 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b5435418295ca0eb3d9e88e1` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.5. Minimum down payment | 1.5.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
```

</details>

---

### Evidence 078 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_91e3496cc496219265c4e006` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

</details>

---

### Evidence 079 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2a94a4a5f8980ffbcb023bfd` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1
1.1. For loans with a term of 240 months, the loan amount is up to 90% of the sale price set by the developer³.
For loans with a term above 240 months, the loan amount is up to 80% of the sale price set by the developer⁴, unless otherwise determined by the Bank.
```

</details>

---

### Evidence 080 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_636ec00980ef0c89cebfabe1` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia
```

</details>

---

### Evidence 081 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e6f51ad51361fcacf5bcff07` |
| Source item | `document:2:175e5d151b3d:page:3:table:0:row:8` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 1. Express Home Purchase Loan (primary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. N/A
The price statement provided by the Developer⁴ is taken as the basis for the collateral value.
```

</details>

---

### Evidence 082 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_82d864cf7f9733036629c697` |
| Source item | `document:2:175e5d151b3d:page:3:table:1:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes.
```

</details>

---

### Evidence 083 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1df7f92bf05f2ec98815e33d` |
| Source item | `document:2:175e5d151b3d:page:3:table:1:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360
```

</details>

---

### Evidence 084 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_19b7452e577ed83a4a2aae8c` |
| Source item | `document:2:175e5d151b3d:page:3:table:1:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
Fixed component 5.75% + variable component (base rate)
```

</details>

---

### Evidence 085 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_17391c5bac832caa94d40975` |
| Source item | `document:2:175e5d151b3d:page:3:table:1:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.66-17.11%
```

</details>

---

### Evidence 086 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_742de24d4cea1dba3d3cbbd5` |
| Source item | `document:2:175e5d151b3d:page:3:table:1:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.5. Minimum down payment | 1.5.1. At least 5% of the purchase price of the property
```

</details>

---

### Evidence 087 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_029f41620adc9c2795d1f73b` |
| Source item | `document:2:175e5d151b3d:page:3:table:1:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

</details>

---

### Evidence 088 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3d0b7b20c43ada72562128e7` |
| Source item | `document:2:175e5d151b3d:page:3:table:1:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80% (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70% (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property
```

</details>

---

### Evidence 089 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f00928f286370cc9f4a374f4` |
| Source item | `document:2:175e5d151b3d:page:4:block:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
3. Express Home Construction Loan
```

</details>

---

### Evidence 090 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a9b8e31c195982ebd4a9a7d4` |
| Source item | `document:2:175e5d151b3d:page:4:block:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) ¹ &gt; 4. Express Home Renovation Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
4. Express Home Renovation Loan
```

</details>

---

### Evidence 091 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_39bda6f739bbc6aefc01b678` |
| Source item | `document:2:175e5d151b3d:page:4:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia
```

</details>

---

### Evidence 092 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d66c3d25a80e0c03fe5ac72f` |
| Source item | `document:2:175e5d151b3d:page:4:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 2. Express Home Purchase Loan (secondary market) (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank.
```

</details>

---

### Evidence 093 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0949bbb262a240a8c1a7209e` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.1. Purpose | 1.1. Construction of residential property
```

</details>

---

### Evidence 094 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b84964932d93032d66370aaa` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.2. Term (months) | 1.2.1. 61-360
```

</details>

---

### Evidence 095 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_237bd8513abb4f4d6f310028` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
Fixed component 5.75% + variable component (base rate)
```

</details>

---

### Evidence 096 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_713715dabbc92f3bd9324d3b` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9%
```

</details>

---

### Evidence 097 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7a65bbbd0fc7b9781fe5bb62` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being constructed. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

</details>

---

### Evidence 098 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_24bbf11898c941125521109a` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property
```

</details>

---

### Evidence 099 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a49bb5a22b34f23396fd77cb` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia
```

</details>

---

### Evidence 100 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_879e2c587be85af14bfca623` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank.
```

</details>

---

### Evidence 101 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_263458f718b12e692acf458b` |
| Source item | `document:2:175e5d151b3d:page:4:table:1:row:8` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 3. Express Home Construction Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.
For loans over AMD 50 million contractual amount at least 3 tranches must be defined.
```

</details>

---

### Evidence 102 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_dc3832d0b024b25dcecdd283` |
| Source item | `document:2:175e5d151b3d:page:4:table:2:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.1. Purpose | 1.1. Renovation of residential property
```

</details>

---

### Evidence 103 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7b759637e414b996399b864b` |
| Source item | `document:2:175e5d151b3d:page:4:table:2:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.2. Term (months) | 1.2.1. 61-240
```

</details>

---

### Evidence 104 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_df70d34c0e8b565ab5d59b06` |
| Source item | `document:2:175e5d151b3d:page:4:table:2:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
Fixed component 5.75% + variable component (base rate)
```

</details>

---

### Evidence 105 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_df500d9b55e6c52232e56b60` |
| Source item | `document:2:175e5d151b3d:page:4:table:2:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 1. Purpose | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9%
```

</details>

---

### Evidence 106 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a290b132f6212ee352bb8d2d` |
| Source item | `document:2:175e5d151b3d:page:4:table:2:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being renovated. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

</details>

---

### Evidence 107 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_975c8480d6549fae4dcb4a18` |
| Source item | `document:2:175e5d151b3d:page:5:note:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
¹Attention! The offer of the agreement is provided to the customer following which the customer may use the 7-day cooling-off period envisaged by the Armenian laws and regulations.
In case of failure to notarize the pledge agreements specified in the loan agreement and securing the borrower's obligations under the loan agreement, within 30 (thirty) business days upon execution of the loan agreement and acceptance by the Borrower, the Agreement shall cease to be valid (unless the loan has already been disbursed to the borrower by that date).
```

</details>

---

### Evidence 108 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_db1516bb8bf8523f8a7c9ca0` |
| Source item | `document:2:175e5d151b3d:page:5:note:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
² Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ± 5%.
```

</details>

---

### Evidence 109 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6ba3922ab582c512c35508ee` |
| Source item | `document:2:175e5d151b3d:page:5:note:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
³The list of developers is determined by the Bank.
```

</details>

---

### Evidence 110 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b93325354d10dcf0da78b29d` |
| Source item | `document:2:175e5d151b3d:page:5:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property
```

</details>

---

### Evidence 111 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_184239259102a52d7a965161` |
| Source item | `document:2:175e5d151b3d:page:5:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Armenia
```

</details>

---

### Evidence 112 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fd22e59c7f7d33f2fdd24c5e` |
| Source item | `document:2:175e5d151b3d:page:5:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank.
```

</details>

---

### Evidence 113 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2d581e5e9edcc79b562a56b7` |
| Source item | `document:2:175e5d151b3d:page:5:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | 4. Express Home Renovation Loan (Continued) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2 | Column 3
Row: 3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.
For loans over AMD 50 million contractual amount at least 3 tranches must be defined.
```

</details>

---

### Evidence 114 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ae53389df4381424d7f387c1` |
| Source item | `document:3:0367c52044e0:page:1:block:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer)
```

</details>

---

### Evidence 115 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_605e7a46cb0617fff7d83678` |
| Source item | `document:3:0367c52044e0:page:1:block:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC (hereinafter - the Developer) |

<details open>
<summary><strong>Source content</strong></summary>

```text
11RBD PL 72-03-104, Ed. 1
Effective date: March 25, 2025
```

</details>

---

### Evidence 116 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_aceabc6106826f2cfa6ef5ac` |
| Source item | `document:3:0367c52044e0:page:1:note:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
¹Retail Lending Terms and Conditions (Home Mortgage Loan) (11RBD PL 72-03-98), approved by the Management Board resolution # 08/1/01/14 as of February 4, 2014.
Available at https://ameriabank.am/useful-links.
```

</details>

---

### Evidence 117 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_55cb29836d9dea143aaa4253` |
| Source item | `document:3:0367c52044e0:page:1:table:0:note:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
*The rest of the terms and conditions are specified in the Terms¹.
```

</details>

---

### Evidence 118 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1bfc430503ad249416bfae9e` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | identity |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: 1. Purpose | 1.1. Increasing the mortgage loan portfolio, promoting sales
```

</details>

---

### Evidence 119 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d5b53b02134e1ede5b95ec1d` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: 2. Client/Borrower | 2.1. Individuals meeting the Terms¹ established by Ameriabank CJSC (hereinafter - the Bank)
```

</details>

---

### Evidence 120 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f8249101d7998ea67a85f8db` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: Option 1. Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice | Option 1. Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice
```

</details>

---

### Evidence 121 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8ed2ee1cfca9d77c050e4c36` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: 1. Nominal annual interest rate | 1.1. As per Terms¹
```

</details>

---

### Evidence 122 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6dd226cbf4ee47af40dfcfd3` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: 2. Annual interest rate subsidized by the Developer | 2.1. 0.5%-13.5%
```

</details>

---

### Evidence 123 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9bb357f5a0bd0f76083b58f5` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: 3. Annual percentage rate (APR) | 3.1. 13.83%-15.76%
```

</details>

---

### Evidence 124 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ce1b4f246d1657e28c36603a` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: Option 2. Partial or full payment of the down payment by the Developer | Option 2. Partial or full payment of the down payment by the Developer
```

</details>

---

### Evidence 125 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4cd1a4f1c56c604283560c61` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | fees_and_repayment |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: 1. Down payment | 1.1. Minimum 10%, paid from the funds received under the interest-free target loan agreement signed between the Developer and the Borrower. The loan amount is subject to repayment by the Borrower before the Developer receives the certificate of completion/signs the handover act for the purchased real estate, unless otherwise agreed by the parties.
```

</details>

---

### Evidence 126 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8929061da113de8886b3f2d1` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:8` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: Option 3: Partial or full payment of the down payment by the Developer and partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice | Option 3: Partial or full payment of the down payment by the Developer and partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice
```

</details>

---

### Evidence 127 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f46fcf70ace8e2d6bece98b3` |
| Source item | `document:3:0367c52044e0:page:1:table:0:row:9` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Column 1 | Column 2
Row: 1. Other terms and conditions | 1.1 The terms of Option 1 and 2 apply simultaneously.
```

</details>

---

### Evidence 128 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_35b1d80fb08a496d65fe0715` |
| Source item | `document:4:af53ff31bab9:page:1:block:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Approved by
Management Board Resolution
# 03/93/26 as of June 19, 2026
Chairman of the Management Board-
CEO
Artak Hanesyan
Effective date: July 1, 2026
```

</details>

---

### Evidence 129 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_742377baa8005dceba9e057e` |
| Source item | `document:4:af53ff31bab9:page:1:block:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | TERMS OF RESIDENTIAL AND COMMERCIAL REAL ESTATE MORTGAGE LENDING (INCLUDING REFINANCING) CAMPAIGN |

<details open>
<summary><strong>Source content</strong></summary>

```text
TERMS OF RESIDENTIAL AND COMMERCIAL REAL ESTATE MORTGAGE LENDING (INCLUDING REFINANCING) CAMPAIGN
```

</details>

---

### Evidence 130 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_bf75589a9bca69d7bdc66a48` |
| Source item | `document:4:af53ff31bab9:page:1:block:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
11RBD PL 72-03-98/03, Ed. 1
```

</details>

---

### Evidence 131 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_84e76f0ee175f0011c531d04` |
| Source item | `document:4:af53ff31bab9:page:1:note:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
¹ Lending terms and conditions are defined in the Retail Lending Terms and Conditions (Home Mortgage Loan and Commercial Mortgage Loan) (11RBD PL 72-03-98, 11RBD PL 72-03-88). Available at https://ameriabank.am/useful-links.
```

</details>

---

### Evidence 132 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_23746c55d4ba79b7a9eab91e` |
| Source item | `document:4:af53ff31bab9:page:1:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents, identity |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Purpose | Promoting sales of mortgage loans for residential and commercial real estate acquisition and moving to Ameriabank CJSC (hereinafter “the Bank”) existing mortgage loans issued by other banks and credit organizations operating in the Republic of Armenia. | Promoting sales of mortgage loans for residential and commercial real estate acquisition and moving to Ameriabank CJSC (hereinafter “the Bank”) existing mortgage loans issued by other banks and credit organizations operating in the Republic of Armenia.
```

</details>

---

### Evidence 133 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f5c7f46dabf670cbc79dee6e` |
| Source item | `document:4:af53ff31bab9:page:1:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Loan type | Loans for purchase, renovation and/or construction of residential and commercial real estate (issued online and at the Bank’s branches) | Loans for purchase, renovation and/or construction of residential and commercial real estate (issued online and at the Bank’s branches)
```

</details>

---

### Evidence 134 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5aeaf44863502c7c896677f3` |
| Source item | `document:4:af53ff31bab9:page:1:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | eligibility_and_documents |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Eligible customers | 1. For newly issued loans: individuals meeting the Bank’s standard lending termsError! Bookmark not defined.
2. For refinancing of existing loans: individuals who have existing mortgage loans with other banks/credit organization of Armenia and duly perform their credit obligations | 1. For newly issued loans: individuals meeting the Bank’s standard lending termsError! Bookmark not defined.
2. For refinancing of existing loans: individuals who have existing mortgage loans with other banks/credit organization of Armenia and duly perform their credit obligations
```

</details>

---

### Evidence 135 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6e1fde2dda199f140980bf19` |
| Source item | `document:4:af53ff31bab9:page:1:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Campaign term | 2026 From July 1, 2026 until and inclusive December 30, 2026 | 2026 From July 1, 2026 until and inclusive December 30, 2026
```

</details>

---

### Evidence 136 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e4225d3b772993e15dfe35cd` |
| Source item | `document:4:af53ff31bab9:page:1:table:0:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Loan terms | Loans are issued in accordance with the standard lending terms and conditions¹, except for the following clauses: | Loans are issued in accordance with the standard lending terms and conditions¹, except for the following clauses:
```

</details>

---

### Evidence 137 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_95f1dfc30256ac8c877d9381` |
| Source item | `document:4:af53ff31bab9:page:1:table:0:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Term | Refinancing | New loans
```

</details>

---

### Evidence 138 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_88eb78c33bca302209b908e5` |
| Source item | `document:4:af53ff31bab9:page:1:table:0:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Nominal annual interest rate | 1. For the loans for purchase/renovation/construction of residential real estate
For the loans for | 2. For the loans for purchase/renovation/construction of residential real estate
For the loans for purchase/renovation/construction of commercial real estate
```

</details>

---

### Evidence 139 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6c871c241378d3233a01a4b5` |
| Source item | `document:4:af53ff31bab9:page:2:block:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
11RBD PL 72-03-98/03, Ed. 1
```

</details>

---

### Evidence 140 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_eab63b29e549d87a616047dd` |
| Source item | `document:4:af53ff31bab9:page:2:table:0:row:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Nominal annual interest rate | purchase/renovation/construction of commercial real estate
1.1. With an incentive: 12.9% (fixed adjustable interest rate which will be modified starting from the 37th month following the loan agreement execution; fixed component 4.9% + variable component (base rate)) | 2.1. Without an incentive: 12.9% (fixed adjustable interest rate which will be modified starting from the 37th month following the loan agreement execution; fixed component 4.9% + variable component (base rate))
```

</details>

---

### Evidence 141 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0164771183a3eb2857b35a22` |
| Source item | `document:4:af53ff31bab9:page:2:table:0:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Annual percentage rate (APR) | 12.05-12.45% | 13.67-13.68%
```

</details>

---

### Evidence 142 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e1c90a1061a60f081182b3b5` |
| Source item | `document:4:af53ff31bab9:page:2:table:0:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Collateral-related costs | Collateral-related costs are covered by the Bank. | Collateral-related costs are covered by the Customer.
```

</details>

---

### Evidence 143 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ba01aa1aea3e56fe20632c4d` |
| Source item | `document:4:af53ff31bab9:page:2:table:0:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | core_financial, fees_and_repayment |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Incentive and its payment | In case of loans with a possibility of providing an incentive, the client receives an incentive payment in the amount of 1% of the loan (without the taxes stipulated by the Republic of Armenia laws and regulations). Furthermore, the incentive is paid only for the loans issued in the Bank’s branches.
The incentive is transferred to the Customer’s current account with the Bank specified by the Customer by the Credits and Card Operations and Accounting Division, upon presentation by the loan officer, within 2 (two) business days upon registration of the Bank’s security interest over the property securing the credit obligations.
In case of full repayment of the credit obligations during the first 3 (three) years of the loan term, the incentive provided to the client (including the taxes defined by the Republic of Armenia laws and regulations) will be subject to return/repayment by the client within 1 (one) month. | In case of loans with a possibility of providing an incentive, the client receives an incentive payment in the amount of 1% of the loan (without the taxes stipulated by the Republic of Armenia laws and regulations). Furthermore, the incentive is paid only for the loans issued in the Bank’s branches.
The incentive is transferred to the Customer’s current account with the Bank specified by the Customer by the Credits and Card Operations and Accounting Division, upon presentation by the loan officer, within 2 (two) business days upon registration of the Bank’s security interest over the property securing the credit obligations.
In case of full repayment of the credit obligations during the first 3 (three) years of the loan term, the incentive provided to the client (including the taxes defined by the Republic of Armenia laws and regulations) will be subject to return/repayment by the client within 1 (one) month.
```

</details>

---

### Evidence 144 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_dedd8ce722f1a26769037539` |
| Source item | `document:4:af53ff31bab9:page:2:table:0:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Property pledging procedure | The property subject to pledge can be pledged within 30 days after actual disbursement of the loan. | The property is pledged before loan disbursement.
```

</details>

---

### Evidence 145 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4420852d201a2605039f6d00` |
| Source item | `document:4:af53ff31bab9:page:2:table:0:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Term | Refinancing | New loans
Row: Required documents | Proof of income documents may not be required if the salary or equivalent payments are stated in the request to the inquiry obtained from Nork Social Services Technology and Awareness Center | According to standard lending terms.
```

</details>

---

### Evidence 146 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_57eab2f384f97db917c6c18e` |
| Source item | `document:5:7b405d165676:page:1:block:0` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

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

</details>

---

### Evidence 147 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8a65edd8bea150978e020c05` |
| Source item | `document:5:7b405d165676:page:1:block:1` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
SERVICE FEES FOR LOANS TO INDIVIDUALS
```

</details>

---

### Evidence 148 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9d1d14710ba933164fe1b1fa` |
| Source item | `document:5:7b405d165676:page:1:block:2` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | SERVICE FEES FOR LOANS TO INDIVIDUALS |

<details open>
<summary><strong>Source content</strong></summary>

```text
Approved by Management Board resolution # 01/68/18 dated May 14, 2018.
Current edition approved by resolution # .... dated ... , effective from July 14, 2026.
```

</details>

---

### Evidence 149 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_09e82f8cd8e954fb37fe0f25` |
| Source item | `document:5:7b405d165676:page:1:block:3` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | SERVICE FEES FOR LOANS TO INDIVIDUALS |

<details open>
<summary><strong>Source content</strong></summary>

```text
General Provisions
```

</details>

---

### Evidence 150 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0fe1d6f462a5f8c5982a7e9e` |
| Source item | `document:5:7b405d165676:page:1:block:4` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | SERVICE FEES FOR LOANS TO INDIVIDUALS &gt; General Provisions |

<details open>
<summary><strong>Source content</strong></summary>

```text
1. Under this document, “loan” means the loan types envisaged by the Retail Lending Terms and Conditions of the Bank.
2. The changes specified in this document are made based on the client’s application, subject to its approval in accordance with the Bank’s internal regulations.
3. These fees apply to changes initiated by the client. The changes made in order to ensure the client’s performance of the condition subsequent established by the Bank are not considered as the client’s initiative.
```

</details>

---

### Evidence 151 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7f6427e983cb0d2916de6853` |
| Source item | `document:5:7b405d165676:page:1:block:5` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
11RBD PL 72-03-29, Ed. 3
```

</details>

---

### Evidence 152 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_89a57655b0c76227e1e490f8` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:0` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 1. Term extension for mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000
```

</details>

---

### Evidence 153 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8d5bf119d84d1f221e15d973` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:1` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 2. Granting a grace period for the principal amount of mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000
```

</details>

---

### Evidence 154 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a242df3bf58e042310ea36e0` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:10` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 11. Issuing other consent not established by this document and not related to the collateral | AMD 10,000
(VAT included)
```

</details>

---

### Evidence 155 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8eaf1b0d3e8d120faec79a1d` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:11` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 12. Revision/modification of another loan term not specified in this document (including interest rate revision) | 0.1% of the outstanding loan amount, minimum AMD 10,000
```

</details>

---

### Evidence 156 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_894ea975ef1924cfcdcf1e91` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:2` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 3. Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000
```

</details>

---

### Evidence 157 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6c740697cbdf719959220034` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:3` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 4. Change of the overdraft/line of credit account/card | AMD 30,000
```

</details>

---

### Evidence 158 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6653e53f396e50e28effe608` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:4` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 5. Change of the borrower/co-borrower/guarantor | AMD 50,000
```

</details>

---

### Evidence 159 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_859c87bf12ae6d8f82178b13` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:5` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 6. Release/substitution of the collateral | AMD 50,000
```

</details>

---

### Evidence 160 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1c36da10c8dc7c8dfa7296f9` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:6` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 7. Issuing consent for change of a pledged vehicle plate number | AMD 50,000
(VAT included)
```

</details>

---

### Evidence 161 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_84609285fbbb2882063bb8e9` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:7` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 8. Collateral-related change (including change of the collateral owner) | AMD 15,000
```

</details>

---

### Evidence 162 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_352d0c410bc7f8181c710036` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:8` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | fees_and_repayment |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 9. Change of the loan repayment date | AMD 10,000
```

</details>

---

### Evidence 163 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_cc0aa610d75fb9b1d0aa3c6a` |
| Source item | `document:5:7b405d165676:page:1:table:0:row:9` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 10. Provision of loan before submitting to the Bank the document certifying state registration of the security interest | AMD 25,000 (per issue)
```

</details>

---

### Evidence 164 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e408f2078b2ed45097a1aad8` |
| Source item | `document:5:7b405d165676:page:2:block:0` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | fees_and_repayment |
| Section | SERVICE FEES FOR LOANS TO INDIVIDUALS &gt; General Provisions |

<details open>
<summary><strong>Source content</strong></summary>

```text
4. The fees specified in this document do not apply to the automatically approved consumer loans secured by deposit, bonds and metal accounts in gold.
5. Where several fees are applicable due to change of several terms of the same loan as per the application submitted by the client, only the highest of them shall be charged, once.
6. To apply a fee(s) established by this document for modification of the same term for several loans, the total outstanding amount of those loans is considered.
7. The fee amount is rounded to AMD 1,000 in favor of the client and shall be no less than the minimum amount of the respective fee (if established by this document).
8. Where a new collateral or guarantor is added due to modification of a loan term(s), no fee is charged.
9. In case of lines of credit and overdrafts, the outstanding loan amount means the bigger of the used amount of the line of credit/overdraft and the line of credit/overdraft limit currently available to the client.
```

</details>

---

### Evidence 165 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_64b35236bb136ecb7bb732b6` |
| Source item | `document:5:7b405d165676:page:2:block:1` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
11RBD PL 72-03-29, Ed. 3
```

</details>

---

### Evidence 166 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3e1941fc7b2d9d3b2e19b4b5` |
| Source item | `document:6:eca03d247e60:page:1:block:0` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION |

<details open>
<summary><strong>Source content</strong></summary>

```text
AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION
```

</details>

---

### Evidence 167 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_53401627323fdcd8b757edfa` |
| Source item | `document:6:eca03d247e60:page:1:block:1` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION |

<details open>
<summary><strong>Source content</strong></summary>

```text
This agreement (hereinafter the “Agreement”) is entered into on [date] in Yerevan under the laws and regulations of Armenia by and between Ameriabank Closed Joint Stock Company (incorporated under the resolution of the CBA Board dated September 8, 1992, registration number 50, certificate No 0154; address: 2 V. Sargsyan, Yerevan) hereinafter the “Bank”, represented by the authorized person acting on behalf of the Bank, and ................. hereinafter the “Client” or the “Borrower”. The Bank and the Client shall be hereinafter jointly referred to as the “Parties” and individually as the “Party”. This Agreement on Adjustable Interest Rate Setting and Calculation forms an integral part of Agreement # [--] (hereinafter referred to as the “Principal Agreement”).
```

</details>

---

### Evidence 168 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4175fb8fbf245b4806506fed` |
| Source item | `document:6:eca03d247e60:page:1:block:10` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS |

<details open>
<summary><strong>Source content</strong></summary>

```text
2.4. Where it is necessary to choose a Secondary Rate, in order to avoid significant fluctuations between interest rates calculated based on Primary and Secondary Rates and prevent either Party from acquiring unjustified economic gain or incurring loss at the expense of the other Party, calculation of interest rate based on Secondary Rate shall include an adjusting factor to balance possible differences between rates (hereinafter “Spread Adjustment"). Spread Adjustment shall be calculated by the Bank and presented to the Borrower with its amount indicated in the selection Offer. During calculation of the Adjustable Rate throughout the term of the Agreement after selection of the Secondary Rate, the Spread Adjustment shall remain unchanged and be included in calculation of interest
```

</details>

---

### Evidence 169 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_25e1fa0b39858104577ff2ab` |
| Source item | `document:6:eca03d247e60:page:1:block:11` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION |

<details open>
<summary><strong>Source content</strong></summary>

```text
13FOD AG 61-15, ed. 7
```

</details>

---

### Evidence 170 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f86c3509566767ba84e16519` |
| Source item | `document:6:eca03d247e60:page:1:block:2` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 1 SUBJECT OF THE AGREEMENT |

<details open>
<summary><strong>Source content</strong></summary>

```text
1 SUBJECT OF THE AGREEMENT
```

</details>

---

### Evidence 171 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9f4a23634435b2e568ac68a6` |
| Source item | `document:6:eca03d247e60:page:1:block:3` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 1 SUBJECT OF THE AGREEMENT |

<details open>
<summary><strong>Source content</strong></summary>

```text
1.1. The Parties hereby define the procedure for regular revision of the loan interest rate under the Principal Agreement in response to the changes in market interest rates to ensure that the interest rate determined by the Parties is consistent with the market rates to the highest possible degree at all times subject to the procedure established hereby.
```

</details>

---

### Evidence 172 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_053e6d6a5a1422f4709b4b4f` |
| Source item | `document:6:eca03d247e60:page:1:block:4` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 1 SUBJECT OF THE AGREEMENT |

<details open>
<summary><strong>Source content</strong></summary>

```text
1.2. The Agreement forms an integral part of the Principal Agreement.
```

</details>

---

### Evidence 173 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_458ddf7cc0ca91693fb4b004` |
| Source item | `document:6:eca03d247e60:page:1:block:5` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 1 SUBJECT OF THE AGREEMENT |

<details open>
<summary><strong>Source content</strong></summary>

```text
1.3. Hereby the Parties agree that the interest rate set by the Principal Agreement shall be considered adjustable and variable (hereinafter “Adjustable Rate”) as stipulated under this Agreement.
```

</details>

---

### Evidence 174 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_88af1a5e263c245cf51e5940` |
| Source item | `document:6:eca03d247e60:page:1:block:6` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS |

<details open>
<summary><strong>Source content</strong></summary>

```text
2 ADJUSTABLE INTEREST RATE CONSTITUENTS
```

</details>

---

### Evidence 175 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0d456ad993ead0a5c10e1b11` |
| Source item | `document:6:eca03d247e60:page:1:block:7` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS |

<details open>
<summary><strong>Source content</strong></summary>

```text
2.1. The Adjustable Rate defined by the Principal Agreement shall consist of the following constituents (components):
2.1.1. Base Rate
2.1.2. Margin (fixed component)
```

</details>

---

### Evidence 176 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_565f12e03711fd6cef13e3f4` |
| Source item | `document:6:eca03d247e60:page:1:block:8` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS |

<details open>
<summary><strong>Source content</strong></summary>

```text
2.2. The Adjustable Rate is a nominal interest rate calculated in accordance with this Agreement using the following formula: RA = RB + RM where RA is the Adjustable Rate, RB is the Base Rate and RM is the Margin (fixed component).
One primary index (hereinafter “Primary Rate” and/or “Primary Index”) and one secondary index (hereinafter “Secondary Rate” and/or “Secondary Index”) of Base Rate shall be used as basis for calculation and adjusting of the Adjustable Rate, which cannot be changed during the term of the Agreement, except in cases defined in chapter 5. The Secondary Index shall be applied if the Primary Index is inaccessible and setting of the Adjustable Rate for the next period becomes impossible.
```

</details>

---

### Evidence 177 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_82541746a2403eae49490c71` |
| Source item | `document:6:eca03d247e60:page:1:block:9` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS |

<details open>
<summary><strong>Source content</strong></summary>

```text
2.3. The Base Rate shall be determined on the basis of the following market rates, depending on the loan currency:
2.3.1. In case of Adjustable Rates for AMD-denominated loans: the primary rate underlying the Base Rate shall be the yield to maturity of Armenian 6-month Government (treasury) bills. Secondary Rate is the average yield of Armenian 6-month (or if not available, closest to 6 months) Government (treasury) bills in primary auction.
2.3.2. In case of Adjustable Rates for USD-denominated loans: the primary rate underlying the Base Rate shall be the CME Term SOFR USD 6 Month reference rate. The Secondary Rate shall be the value of 6-month US treasury bills yield curve.
2.3.3. In case of Adjustable Rates for EUR-denominated loans: the primary rate underlying the Base Rate shall be the EURIBOR 6 Month rate. The Secondary Index shall be the value of the Germany 6 Month Government EUR Bond yield curve.
```

</details>

---

### Evidence 178 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5f15a058ea6dc49b12279176` |
| Source item | `document:6:eca03d247e60:page:2:block:0` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS |

<details open>
<summary><strong>Source content</strong></summary>

```text
rate at all times, and accordingly, calculation of the Adjustable Rate based on Secondary Rate shall be performed using the following formula:
RA = RB + SA + RM
where
RA is the Adjustable Rate
RB is the Base Rate
SA is the Spread Adjustment
RM is the margin (fixed component)
However, regardless of application of the Spread Adjustment, if the Agreement provides for a maximum Adjustable Rate limit, the interest rate calculated on the basis of the Secondary Rate and Spread Adjustment shall not exceed the set maximum limit¹.
```

</details>

---

### Evidence 179 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c744bc057fe997bc80173dac` |
| Source item | `document:6:eca03d247e60:page:2:block:1` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS |

<details open>
<summary><strong>Source content</strong></summary>

```text
2.5. The margin (fixed component) shall be determined based on the terms of lending and shall be fixed in the loan agreement for each loan separately, on the basis of the respective loan decision adopted by the authorized body of the Bank.
```

</details>

---

### Evidence 180 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_adbd6496b69c6f536dde9bd1` |
| Source item | `document:6:eca03d247e60:page:2:block:10` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION |

<details open>
<summary><strong>Source content</strong></summary>

```text
13FOD AG 61-15, ed. 7
```

</details>

---

### Evidence 181 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7ae4d10c8892d4cb408daa0a` |
| Source item | `document:6:eca03d247e60:page:2:block:2` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 2 ADJUSTABLE INTEREST RATE CONSTITUENTS |

<details open>
<summary><strong>Source content</strong></summary>

```text
2.6. For the purpose of this Agreement and the Principal Agreement, the base rate of the Adjustable Rate for the Client (Borrower) at the time of execution of the Principal Agreement shall be equal to _______ percent, while the Margin (fixed component) shall be equal to _______ percent. Where the base rate of the Adjustable Rate is a negative value, the Adjustable Rate under the Principal Agreement shall be calculated based on 0 (zero).
```

</details>

---

### Evidence 182 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_abc847f08908981802602463` |
| Source item | `document:6:eca03d247e60:page:2:block:3` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE
```

</details>

---

### Evidence 183 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c3ddbcbfb2df804c0c297e23` |
| Source item | `document:6:eca03d247e60:page:2:block:4` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.1. Information on the yield to maturity of Armenian Government (treasury) bills can be obtained from the relevant publications (yield curve) on the official website of the CBA at the following link:
https://www.cba.am/am/SitePages/fmofinancialmarkets.aspx
Information on the average yield of Armenian 6-month (or if not available, closest to 6 months) Government (treasury) bills in primary auctions can be retrieved from the official website of the Armenian Securities Exchange at the following link:
https://amx.am/am/government_bond_auctions
```

</details>

---

### Evidence 184 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5318099db8baacc46cef1536` |
| Source item | `document:6:eca03d247e60:page:2:block:5` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.2. Information on the CME Term SOFR USD 6 Month reference rate can be retrieved from Bloomberg terminal under TSFR6M ticker (SR6M in Reuters).
```

</details>

---

### Evidence 185 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5da39fe9b36011d0db811d24` |
| Source item | `document:6:eca03d247e60:page:2:block:6` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.3. Information on the EURIBOR 6 Month rate can be retrieved from Bloomberg terminal under EUR006M ticker (EURIBOR6MD in Reuters).
```

</details>

---

### Evidence 186 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4627587614d653516d31c58c` |
| Source item | `document:6:eca03d247e60:page:2:block:7` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.4. Information on the yield of 6-month US treasury bills can be retrieved from Bloomberg terminal under H15T6M ticker (US6MT=RR in Reuters).
```

</details>

---

### Evidence 187 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2430c672d12515c65a644682` |
| Source item | `document:6:eca03d247e60:page:2:block:8` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.5. Information on the yield curve of Germany 6 Month Government EUR Bonds can be retrieved from Bloomberg terminal under YCGT0016 ticker (DE6MT=RR in Reuters).
```

</details>

---

### Evidence 188 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0bddf2f9b863d946cf6e24d1` |
| Source item | `document:6:eca03d247e60:page:2:block:9` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.6. In case of inaccessibility of the Bloomberg Terminal or impossibility to check the information for any other reason, the Bank shall, upon the Borrower’s request, provide the information retrieved from the system to the Borrower by e-mail or other e-channels acceptable to the Parties and/or deliver it to the Borrower within the Bank premises. Whenever Bloomberg Terminal is not accessible, the information retrieved from Thomson Reuters Eikon shall be used as an alternative.
```

</details>

---

### Evidence 189 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c27f66759e5fc1d06cfbb53e` |
| Source item | `document:6:eca03d247e60:page:2:note:0` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
¹ This clause is not applicable in case of mortgage and consumer loans.
```

</details>

---

### Evidence 190 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a7593b6f2ca4d64501f89039` |
| Source item | `document:6:eca03d247e60:page:3:block:0` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.7. Change of any link specified in clauses 3.1, 3.2., 3.3, 3.4 ,3.5 and 3.9. above shall not affect or have any implications for this Agreement and/or its validity, except for the special cases provided for in clause 5.1 below.
```

</details>

---

### Evidence 191 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2a4ea5940ae01a312ab06df6` |
| Source item | `document:6:eca03d247e60:page:3:block:1` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.8. The Base Rate shall be revised on February 1 and August 1 each year. In particular:
3.8.1.On February 1, the Base Rate shall be equal to the respective interest rate on the 30th business day preceding February 1 of that year. Where the value is negative, calculation is based on 0.
3.8.2.On August 1, the Base Rate shall be equal to the respective interest rate on the 30th business day preceding August 1. Where the value is negative, calculation is based on 0.
3.8.3.The method of calculation of the Base Rate specified in clause 3.8 herein cannot change during the term of the Agreement and the Principal Agreement.
```

</details>

---

### Evidence 192 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_751d8ef24045c2da07a77a8e` |
| Source item | `document:6:eca03d247e60:page:3:block:10` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
4.7. The maximum increase threshold of the loan rate under the Principal Agreement shall not exceed the maximum decrease threshold.³
```

</details>

---

### Evidence 193 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9ccf1ef410de68f2a5976bed` |
| Source item | `document:6:eca03d247e60:page:3:block:11` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 5 EXCEPTIONAL CIRCUMSTANCES |

<details open>
<summary><strong>Source content</strong></summary>

```text
5 EXCEPTIONAL CIRCUMSTANCES
```

</details>

---

### Evidence 194 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_de67a95fb8111a44c8c8a626` |
| Source item | `document:6:eca03d247e60:page:3:block:12` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 5 EXCEPTIONAL CIRCUMSTANCES |

<details open>
<summary><strong>Source content</strong></summary>

```text
5.1. Where the Primary and Secondary Indicators become inaccessible and impossible, the Parties agree that the Bank shall offer another similar indicator for the next period, relying solely on the standards defined by the CBA or the legislation of the Republic of Armenia. Adjustable Rate shall be considered inaccessible and impossible under the following exceptional circumstances.
5.1.1. Procedure of market interest rate calculation undergoes material changes.
```

</details>

---

### Evidence 195 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7756514d3e8ee0af1381af3e` |
| Source item | `document:6:eca03d247e60:page:3:block:13` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION |

<details open>
<summary><strong>Source content</strong></summary>

```text
13FOD AG 61-15, ed. 7
```

</details>

---

### Evidence 196 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fc022c3f85b7fb8251572197` |
| Source item | `document:6:eca03d247e60:page:3:block:2` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 3 POSTING, UPDATING AND COMMUNICATING INFORMATION ON THE BASE RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
3.9. The revised Base Rate and information about its changes shall be published on the Bank’s official website twice a year, on the first business days of February and August.
https://ameriabank.am/business/sme/financing/support/base-rate
```

</details>

---

### Evidence 197 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_70e3f54e63ff4ab78d552213` |
| Source item | `document:6:eca03d247e60:page:3:block:3` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE
```

</details>

---

### Evidence 198 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_84d8f090b7e99a786e3e0a8b` |
| Source item | `document:6:eca03d247e60:page:3:block:4` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
4.1. The first revision of the Adjustable Rate in accordance with this Agreement shall be in 3 (three)² years after execution of the Principal Agreement, except in the case defined under clause 5.1 herein, unless otherwise provided for by the imperative norms of the Republic of Armenia laws and regulations. Thereafter, the Adjustable Rate may be revised regularly every 6 (six) months. Prior to the date of the first revision, the Base Rate shall be deemed equal to the Base Rate effective on the date of execution of the Principal Agreement.
```

</details>

---

### Evidence 199 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_deeb59cc93be437b287674b7` |
| Source item | `document:6:eca03d247e60:page:3:block:5` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
4.2. The Base Rate effective on the date of revision shall be deemed the applicable rate for the time span between the given and next revisions. Loan interest payments shall be calculated and made at the revised interest rate.
```

</details>

---

### Evidence 200 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_eb386b4a37a2182819796e43` |
| Source item | `document:6:eca03d247e60:page:3:block:6` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
4.3. The date of application (calculation) of changed interest rate shall be the first payment date following the base rate change date (the first day of February and August).
```

</details>

---

### Evidence 201 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c75312ac6f7e444f2563da74` |
| Source item | `document:6:eca03d247e60:page:3:block:7` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
4.4. Calculations of the Base Rate shall be performed by rounding the rate to the nearest multiple of 0.5 (zero point five) percent. E.g., 8.23% shall be rounded to 8.0%, 8.25% shall be rounded to 8.5%, and 8.41% shall be rounded to 8.5%.
```

</details>

---

### Evidence 202 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9a3bf75b0808b598f3d8861c` |
| Source item | `document:6:eca03d247e60:page:3:block:8` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
4.5. Hereby the Parties agree that the Base Rate:
4.5.1 Shall be revised by the Bank, if the difference between the interest rate for any particular period (rounded to 0.5 p.p.) and the effective Base Rate is more than 1%. The rate can be revised not more than to the extent of such difference, however, the Bank at its own discretion can revise the rate to a smaller extent which in any case should not be lower than 0.5%. (E.g., if the effective Base Rate is 8% and the new rate is 9.5%, the Bank can revise the rate by 0.5%, 1% or 1.5%).
4.5.2 Can be revised at the Bank’s discretion, if the difference between the interest rate for any particular period (rounded to 0.5 p.p.) and the effective Base Rate does not exceed 1%.
The terms of revision of the Base Rate set out in this clause shall be applicable both to upward and downward revision of the rate.
```

</details>

---

### Evidence 203 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6816438ecfcedf90bb5e2685` |
| Source item | `document:6:eca03d247e60:page:3:block:9` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 4 THE PROCEDURE OF REGULAR REVIEW AND REVISION OF THE ADJUSTABLE INTEREST RATE |

<details open>
<summary><strong>Source content</strong></summary>

```text
4.6. The revised rate shall be applied to the outstanding loan not earlier than 7 (seven) business days after giving notice to the Borrower in the manner of notification/communication specified in the Principal Agreement.
The Parties hereby state that in any case the loan interest rate specified in the Principal Agreement shall not exceed --- percent and shall not be less than ---- percent.
```

</details>

---

### Evidence 204 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b9392725347c46c6e443b440` |
| Source item | `document:6:eca03d247e60:page:3:note:0` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
² The 3-year requirement is mandatory in case of mortgage loans only.
```

</details>

---

### Evidence 205 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_699dbd515eebe2c115d247b6` |
| Source item | `document:6:eca03d247e60:page:3:note:1` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
³ This clause is effective and applicable in case of mortgage and consumer loans only.
```

</details>

---

### Evidence 206 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_af5a9c13985c4cd017eaf831` |
| Source item | `document:6:eca03d247e60:page:4:block:0` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 5 EXCEPTIONAL CIRCUMSTANCES |

<details open>
<summary><strong>Source content</strong></summary>

```text
5.1.2. Information on the interest rate, specified in clauses 2.3.1, 2.3.2 or 2.3.3, is no longer published for respective currency.
5.1.3. In the reasonable opinion of the Bank’s authorized body the given interest rate no longer represents the actual market situation.
5.1.4. Certain amendments to the Republic of Armenia laws and regulations prohibit or make it impossible to change the interest rate in accordance with the provisions of the Principal Agreement and the Agreement.
5.1.5. There are other economically or legally reasonable and justifiable bases.
5.1.6. In other cases provided for under the laws and regulations of the Republic of Armenia.
```

</details>

---

### Evidence 207 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4443e172a1215b98f33db0e4` |
| Source item | `document:6:eca03d247e60:page:4:block:1` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 5 EXCEPTIONAL CIRCUMSTANCES |

<details open>
<summary><strong>Source content</strong></summary>

```text
5.2. Hereby the Borrower agrees that the Bank shall have the right to revise and adjust the Loan interest rate in favor of the Borrower at any time and any intervals during the term of the Agreement and/or the Principal Agreement.
```

</details>

---

### Evidence 208 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a29a4b1e6dedabde230255d4` |
| Source item | `document:6:eca03d247e60:page:4:block:2` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS |

<details open>
<summary><strong>Source content</strong></summary>

```text
6 MISCELLANEOUS
```

</details>

---

### Evidence 209 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a6e9dc7914d2db48cabed8e4` |
| Source item | `document:6:eca03d247e60:page:4:block:3` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS |

<details open>
<summary><strong>Source content</strong></summary>

```text
6.1. This Agreement shall be binding upon and inure to the benefit of the Parties’ successors and assigns.
```

</details>

---

### Evidence 210 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6a1cc97e17ce8920a8624654` |
| Source item | `document:6:eca03d247e60:page:4:block:4` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS |

<details open>
<summary><strong>Source content</strong></summary>

```text
6.2. The Agreement is made in Armenian and English in the number of counterparts equal to that of the Parties and persons providing security for obligations (if any). All counterparts are legally equal. Each Party receives one counterpart. By signing the Agreement each of the Parties confirms the receipt of their counterpart. In case of discrepancies the Armenian version shall prevail.
```

</details>

---

### Evidence 211 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_40b7dfaf6cb42add633316aa` |
| Source item | `document:6:eca03d247e60:page:4:block:5` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS |

<details open>
<summary><strong>Source content</strong></summary>

```text
6.3. Disagreements and disputes arising out of or in connection with the Agreement shall be referred to and resolved by the court of general jurisdiction of Yerevan, unless otherwise agreed between the Parties and/or stipulated by imperative legal norms of the Republic of Armenia.
```

</details>

---

### Evidence 212 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1d9fab783fa0d2a15ab186fd` |
| Source item | `document:6:eca03d247e60:page:4:block:6` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 6 MISCELLANEOUS |

<details open>
<summary><strong>Source content</strong></summary>

```text
6.4. The Agreement shall become effective upon signing by both Parties and shall remain in full force and effect until proper fulfillment of the liabilities of the Parties under the Agreement.
```

</details>

---

### Evidence 213 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_066bfdc498bb9d7d3e9bdd69` |
| Source item | `document:6:eca03d247e60:page:4:block:7` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 7 ADDRESSES AND SIGNATURES OF THE PARTIES |

<details open>
<summary><strong>Source content</strong></summary>

```text
7 ADDRESSES AND SIGNATURES OF THE PARTIES
```

</details>

---

### Evidence 214 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2225aac39ed6f3d40b240078` |
| Source item | `document:6:eca03d247e60:page:4:block:8` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION &gt; 7 ADDRESSES AND SIGNATURES OF THE PARTIES |

<details open>
<summary><strong>Source content</strong></summary>

```text
Bank
Ameriabank CJSC
Address: 2 V. Sargsyan st., Yerevan
Authorized person
________________________________
(name, surname, signature)
Seal
CLIENT/BORROWER
............................
Passport: ...................................
Address: ...................................
___________________
Signature
```

</details>

---

### Evidence 215 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_49b8e3075f83ad44c102301f` |
| Source item | `document:6:eca03d247e60:page:4:block:9` |
| Role | `legal_disclosure` |
| Authority | `official_terms` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | AGREEMENT # --- ON ADJUSTABLE INTEREST RATE SETTING AND CALCULATION |

<details open>
<summary><strong>Source content</strong></summary>

```text
13FOD AG 61-15, ed. 7
```

</details>

---

### Evidence 216 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5a44927274cf1a22e8e1759a` |
| Source item | `b100` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
INFORMATION ON FACTORS ABOUT CREDIT HISTORY AND CREDIT SCORE
```

</details>

---

### Evidence 217 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c4ce95cfff029d50bce4c3f7` |
| Source item | `b101` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
This document sets out the information required under the Republic of Armenia laws and regulations about the credit history and the credit score of customers during lending in Ameriabank CJSC (hereinafter “the Bank”) and the factors affecting them.
```

</details>

---

### Evidence 218 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_199326a6ac28d8c68e87057f` |
| Source item | `b102` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Credit History is the information on the customer’s financial obligations generated/processed by the Credit Bureau, which shows the customer’s debt, payments, payment habits or other data related to the customer’s obligations or their performance and the dynamics/history of such information.
```

</details>

---

### Evidence 219 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b97de9303e7cca0aa7d63d7d` |
| Source item | `b103` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
The credit history includes, in particular, the information required for customer identification, amount of each monetary obligation of the customer, annual interest rate, outstanding liabilities, order and terms of payments, payment delays, guarantees issued to the third parties, information about the liabilities of the parties affiliated with the customer (in depersonalized form) and the information about credit history inquiries.
```

</details>

---

### Evidence 220 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5a00374eba135bc7a1de39e4` |
| Source item | `b104` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
As a rule, financial organizations use the credit history to assess the customer’s monetary (credit) obligations, guarantees issued to the third parties, to consider the possibilities of lending at the customer’s or bank’s initiative and to submit lending offers to the customer.
```

</details>

---

### Evidence 221 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6cdb5da95106d4c3e7b4904b` |
| Source item | `b105` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Based on the customer’s consent the Bank sends an inquiry to ACRA Credit Bureau. The information about the credit history is reflected in the credit report which covers the customer’s credit history for the most recent 5 years.
```

</details>

---

### Evidence 222 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d254a0332688f2a0b71684d3` |
| Source item | `b106` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
The Customer’s credit history is available at http://www.acra.am/.
```

</details>

---

### Evidence 223 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a3afa5e2751377b763435976` |
| Source item | `b107` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Credit score is the quantified measure of the customer’s borrowing capacity and creditworthiness.
```

</details>

---

### Evidence 224 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3c07d6c1dfaf45e3df574af1` |
| Source item | `b108` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
The Bank uses its own system to assess the borrowing capacity and creditworthiness for lending to customers. The factors affecting it are as follows:
```

</details>

---

### Evidence 225 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6d13e34f72c5fc36afb85199` |
| Source item | `b109` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Credit history. The quantity and amount of existing loans, frequency of applying for loans, positive credit history (no payment delays in the credit history, high quality of loan service) can help improve the credit score and make a positive decision on lending, while a bad credit history (payment delays in the credit history, persistent nature of such delays) can serve as a basis for reducing the credit score, rejecting a new loan application or reviewing it on more stringent terms.
```

</details>

---

### Evidence 226 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c1fcbcedc94b51cf4675c8fe` |
| Source item | `b110` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Employment, income and work experience. Stable job and income can help improve the credit score and make a positive decision on lending. Unstable or non-permanent job or income can serve as a basis for reducing the credit score and rejecting a new loan application or reviewing it on more stringent terms.
```

</details>

---

### Evidence 227 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_69bbb0b35de4530dedfaf8a9` |
| Source item | `b111` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Credit burden.High credit burden and its big share in the income can serve as a basis for reducing the credit score and rejecting a new loan application or reviewing it on more stringent terms, while a low credit burden and its small share in the income can help improve the credit score and make a positive decision on lending
```

</details>

---

### Evidence 228 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_dd5739f339847001ea201712` |
| Source item | `b112` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
FICO Score. FICO Score is a scoring system that provides a numerical value of credit risk through statistic research and analysis of the customer’s credit history. It is a key used by lenders worldwide to assess creditworthiness and financial risks. Details are available at acra.am.
```

</details>

---

### Evidence 229 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4a16a7396f2cb5a6833c04b6` |
| Source item | `b113` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Other information about the Customer
```

</details>

---

### Evidence 230 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_03950273abd29ef1fd86dc0e` |
| Source item | `b114` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
The importance of credit history and credit score
```

</details>

---

### Evidence 231 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_047b1d113159395d7eaab758` |
| Source item | `b115` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Credit history and credit score are essential for making a decision on lending, enabling banks and credit organizations to assess the credit risk of the customer during lending and predict the customer’s proper fulfillment of customer’s monetary obligations and its likelihood.
```

</details>

---

### Evidence 232 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_88966c602cc189a90f04b80b` |
| Source item | `b116` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Wrong or incomplete credit history
```

</details>

---

### Evidence 233 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_65b39cda501a286d809caea5` |
| Source item | `b117` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
If there are wrong or incomplete data in the credit history, the customer can apply to ACRA Credit Reporting CJSC (credit bureau) or directly to the financial organizations having provided the information to the Credit Bureau to correct or clarify such data.
```

</details>

---

### Evidence 234 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_972c1c7b133a7a62e7484d2c` |
| Source item | `b118` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
The procedure and details on applying to ACRA Credit Reporting CJSC is available at www.acra.am
```

</details>

---

### Evidence 235 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_eddf189021e7b14434a2bbd5` |
| Source item | `b119` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Where wrong or incomplete information has been provided to the Credit Bureau by the Bank, the customer can apply to the Bank via any of the following channels:
```

</details>

---

### Evidence 236 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_43569982cb66909c63214b95` |
| Source item | `b120` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
By sending an application to the Bank’s official email address
```

</details>

---

### Evidence 237 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a6689f18b5771814c2d25721` |
| Source item | `b121` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
By calling the Bank at 010/012 561111 phone numbers
```

</details>

---

### Evidence 238 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f69e74fcc7b0bd1f736d273d` |
| Source item | `b122` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
By sending a message via the Bank’s Online/Mobile Banking system
```

</details>

---

### Evidence 239 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_557593699f4aa0de8a5a9f89` |
| Source item | `b123` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
By submitting an application at any of the Bank’s branches.
```

</details>

---

### Evidence 240 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_50e29dd35e6a30de4f3490d6` |
| Source item | `b124` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
The Bank will process the customer’s application in the manner and within the time frames defined by the Republic of Armenia laws and regulations, and/or the Bank’s internal regulations.
```

</details>

---

### Evidence 241 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f4435fa17d501abc84b0104d` |
| Source item | `b125` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
How to improve the credit history and credit score
```

</details>

---

### Evidence 242 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6b2d4ad778d91aec19f07f72` |
| Source item | `b126` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
To improve the credit history and credit score it is necessary to eliminate its root causes as soon as possible, in particular:
```

</details>

---

### Evidence 243 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3ac4e3b0d8f84359fbbfadba` |
| Source item | `b127` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Make loan payments in accordance with the defined schedule, excluding any late payments and even 1-day overdue liabilities
```

</details>

---

### Evidence 244 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_cc06743ec5b8677df6952a89` |
| Source item | `b128` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Limit the number and amount of provided guarantees, by repaying the overdue liabilities secured by guarantees, if possible
```

</details>

---

### Evidence 245 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4eef23cd4e82060875125b53` |
| Source item | `b129` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Reduce the credit burden by repaying the outstanding liabilities
```

</details>

---

### Evidence 246 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_242d89f0df629734bea04c6c` |
| Source item | `b130` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Avoid submitting new loan applications frequently since credit history inquiries (other than for loan monitoring purposes) may negatively affect the customer’s Credit Score.
```

</details>

---

### Evidence 247 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c722ad9bb924a2e037c8dff6` |
| Source item | `b131` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Detailed information about the credit history (including wrong or incomplete information) and/or Credit Score is available on the following pages:
```

</details>

---

### Evidence 248 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_05f91cc5f8d4aeed769639a4` |
| Source item | `b132` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
acra.am –Support– Frequently Asked Questions
```

</details>

---

### Evidence 249 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_58177ecc1ad3184f7f80192a` |
| Source item | `b133` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
abcfinance.am
```

</details>

---

### Evidence 250 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_993f3071f7a21eadbede6c61` |
| Source item | `b134` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
abcfinance.am
```

</details>

---

### Evidence 251 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_57d811038f5ba6ce46c3862e` |
| Source item | `b135` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of the loan for purchase of residential real estate from primary market
```

</details>

---

### Evidence 252 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3ad4b7975e093e4ce50f485e` |
| Source item | `b136` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of express Home Mortgage Loan (Purchase, Construction and Renovation)
```

</details>

---

### Evidence 253 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_64f02a2624bab61768646edb` |
| Source item | `b137` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Mortgage lending terms and conditions for purchase of residential real estate at the primary market with flexible opportunities offered by development companies cooperating with Ameriabank CJSC
```

</details>

---

### Evidence 254 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_84666af1e63420423e2676dd` |
| Source item | `b138` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of residential and commercial real estate mortgage lending (including refinancing) campaign
```

</details>

---

### Evidence 255 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f16d03bf23620d20c1695f6f` |
| Source item | `b139` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Loan service fees
```

</details>

---

### Evidence 256 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b40af59d47e12910bfaf74f8` |
| Source item | `b140` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
“Finance for All” abcfinance.am website
```

</details>

---

### Evidence 257 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f97c9a7027a512648fcc2186` |
| Source item | `b141` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Your financial database www.fininfo.am
```

</details>

---

### Evidence 258 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_362357356a643bcbe4af7271` |
| Source item | `b142` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
On the Procedure for Setting, Calculation and Revision of the Floating (Adjustable) Interest Rate
```

</details>

---

### Evidence 259 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8c6e759c40d42d4ff7c0cf35` |
| Source item | `b143` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 30.03.26 to 31.05.26)
```

</details>

---

### Evidence 260 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d6e32bd5440f2c725c31fb6a` |
| Source item | `b144` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 23.03.26 to 29.03.26)
```

</details>

---

### Evidence 261 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0fb762cbc5296f12f4635780` |
| Source item | `b145` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 04.02.26 to 23.03.26)
```

</details>

---

### Evidence 262 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_127264a82deb1abd9bf55c8f` |
| Source item | `b146` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 20.11.25 to 03.02.26)
```

</details>

---

### Evidence 263 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_496bc1ec65c4bf14e1edb668` |
| Source item | `b147` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 02.09.25 to 05.10.25)
```

</details>

---

### Evidence 264 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b479b6d6b197a4592b07d277` |
| Source item | `b148` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 04.06.25 to 01.09.25)
```

</details>

---

### Evidence 265 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1fb141909237405656ca10d2` |
| Source item | `b149` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms of the loan for purchase of residential real estate from primary market (effective from 25.11.24 to 03.06.25)
```

</details>

---

### Evidence 266 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_bdaa118eb576a74bcb51ad7f` |
| Source item | `b150` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Be informed when applying for a loan
```

</details>

---

### Evidence 267 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a802bc7b13e78e087ca4eb07` |
| Source item | `b151` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Loan Calculators
```

</details>

---

### Evidence 268 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0e3841c616d4063a52db85de` |
| Source item | `b153` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Real estate loan
for secondary market
```

</details>

---

### Evidence 269 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_02520a4899e3a559c6c2b2d5` |
| Source item | `b155` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Construction loan
```

</details>

---

### Evidence 270 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b8ee7b8778f6add32f352a45` |
| Source item | `b57` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Tariffs
```

</details>

---

### Evidence 271 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d8b38c52429091210de6785d` |
| Source item | `b58` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Express Home Mortgage Loan (Purchase, Construction and Renovation)
```

</details>

---

### Evidence 272 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ecb0075fa5a9c338a57a3cf2` |
| Source item | `b59` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Loan service fees
```

</details>

---

### Evidence 273 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e7e2ecefb96714d469b17c2b` |
| Source item | `b60` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Collateral appraisal
```

</details>

---

### Evidence 274 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8e80ca133bbba39a983511eb` |
| Source item | `b61` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Insurance of pledged property
```

</details>

---

### Evidence 275 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c3c4cacbbbe3489cf2c0d8a6` |
| Source item | `b62` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Additional payments
```

</details>

---

### Evidence 276 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d8a3821174f563b75f02c643` |
| Source item | `b63` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Required documents
```

</details>

---

### Evidence 277 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_52c26f5aedc12cffdfac92ed` |
| Source item | `b64` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Credit history and score
```

</details>

---

### Evidence 278 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0ee2db137f6a4b5fe1a3a5b6` |
| Source item | `b65` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Useful Information
```

</details>

---

### Evidence 279 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_43a1abf59a1a7fe158e6d6ee` |
| Source item | `b66` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Old Terms
```

</details>

---

### Evidence 280 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_bb1056789b61ca09a94fb740` |
| Source item | `b70` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
The real estate should be appraised by an appraisal company cooperating with the bank. The company is selected by the client from the offered list. Appraisal fee: AMD 13,000-30,000 depending on the property. On a case-by-case basis, the fee for appraisal of major items of property may be negotiable. The list of appraisal companies cooperating with the Bank may be found at the link below.
```

</details>

---

### Evidence 281 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_86acfd425b91e40f97e12bc5` |
| Source item | `b71` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Appraisal Companies Cooperating with Ameriabank
```

</details>

---

### Evidence 282 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f8b46eee4a0790f8c8326fb5` |
| Source item | `b72` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Insurance for the pledged property to be obtained on an annual basis throughout the loan term:
```

</details>

---

### Evidence 283 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_593b7601dc19acb3244bdc34` |
| Source item | `b73` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
by the bank to the extent of outstanding loan
```

</details>

---

### Evidence 284 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e5ddb48753cb4fdd8919f545` |
| Source item | `b74` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
by the client at least to the extent of outstanding loan
```

</details>

---

### Evidence 285 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_00040be4d96b0ae953b96e30` |
| Source item | `b75` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Notary fee: AMD 14,000-16,000 lump-sum (in case of vehicles)
```

</details>

---

### Evidence 286 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1730c80400307384aec1f514` |
| Source item | `b76` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Notary fee: AMD 13,000-18,000 lump-sum (in case of real estate)
```

</details>

---

### Evidence 287 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_30ec42cd3ab178225ad6e8d7` |
| Source item | `b77` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Fee for unified statement from the State Real Estate Cadaster on encumbrance of the property: AMD 10,000
```

</details>

---

### Evidence 288 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_003461d7641c98e2fb1f41ae` |
| Source item | `b78` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Fee for registration of security interest in the real estate: AMD 26,000
```

</details>

---

### Evidence 289 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8dac7b7b3e890bd660350910` |
| Source item | `b79` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Certificate of the right to purchase real estate and registration of the security interest: AMD 3,000 and AMD 50,000
```

</details>

---

### Evidence 290 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_16f1c3f9c981cdcfc8aa94d3` |
| Source item | `b80` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Certificate of acquisition of the title to the real estate and registration of the security interest: AMD 21,000 and AMD 50,000
```

</details>

---

### Evidence 291 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3d95bb180cd350fdf562cf1c` |
| Source item | `b81` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Certificate of acquisition of the title to the commercial real estate and registration of the security interest: AMD 41,000 (if the area of the premises to be purchased and pledged is above 200 sq. m) and AMD 50,000
```

</details>

---

### Evidence 292 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_37f03ca8940302dd4f4250fb` |
| Source item | `b82` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Fee of the Police of the Republic of Armenia (for lien and pledge of movable property): AMD 5,000 lump sum
```

</details>

---

### Evidence 293 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2345a546f18c53625977e164` |
| Source item | `b83` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Required documents filed together with loan application
```

</details>

---

### Evidence 294 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_84de1c76eeb87b04ac51d119` |
| Source item | `b84` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Loan application
```

</details>

---

### Evidence 295 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_32716df07c8a5179bf6adef1` |
| Source item | `b85` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
ID [original]
```

</details>

---

### Evidence 296 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c8a8dd20425f45d22d633821` |
| Source item | `b86` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Certificate of ownership of property to be purchased/pledged [copy]
```

</details>

---

### Evidence 297 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_af920f46bcb1a595b8e8e3ca` |
| Source item | `b87` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Proof of employment and/or other income
```

</details>

---

### Evidence 298 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_88540cdc68f90a1aa3f6a60e` |
| Source item | `b88` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Marriage (divorce, spouse death), birth certificate [original]
```

</details>

---

### Evidence 299 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b20c7b700a80899d7bf1a362` |
| Source item | `b89` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Certificate of title to real estate to be pledged [original]
```

</details>

---

### Evidence 300 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4b8d19354492ca809c813875` |
| Source item | `b90` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Geodetic measurement report of land plot to be pledged**
```

</details>

---

### Evidence 301 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5cd4c3365b834ce07f9c37bf` |
| Source item | `b91` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Initial real estate appraisal report
```

</details>

---

### Evidence 302 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fc1254ddd79411fe070a2d0d` |
| Source item | `b92` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Construction costs estimate
```

</details>

---

### Evidence 303 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b888799df4905abcecdd1213` |
| Source item | `b93` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Copies of bases of title to real estate (to be submitted upon request)
```

</details>

---

### Evidence 304 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_299e28d4cbf8899c869b9ba7` |
| Source item | `b94` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
IDs of owners of property to be purchased/pledged [originals]
```

</details>

---

### Evidence 305 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_70ba4ccee1c1584f06444797` |
| Source item | `b95` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Copies of marriage (divorce, spouse death) certificates of owners of property to be pledged
```

</details>

---

### Evidence 306 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_017cb55bdca845a2ff7c1296` |
| Source item | `b96` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)
```

</details>

---

### Evidence 307 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_abe2634b8fb79206b983fc9d` |
| Source item | `b97` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Real estate appraisal report (final)
```

</details>

---

### Evidence 308 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9eac0b0e2b4d98578a5ffac7` |
| Source item | `b98` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Other documents as the bank's specialist may request
```

</details>

---

### Evidence 309 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d84f91f86babb8111e6a2b30` |
| Source item | `b99` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `time_bounded` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions |

<details open>
<summary><strong>Source content</strong></summary>

```text
Depending on various circumstances, the bank may request other documents and information. Where required under the Republic of Armenia Law “On Combating Money Laundering and Terrorism Financing”, we may request you to provide additional information and documents to conduct “Know your customer” check, as well as ask further questions during verbal communication.
```

</details>

---

### Evidence 310 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c9b128cba66293753df930be` |
| Source item | `t1:note:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Home Purchase Loan (primary market)
```

</details>

---

### Evidence 311 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b5dd7b9a3f550ff31aa694c9` |
| Source item | `t1:note:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.
```

</details>

---

### Evidence 312 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b32a2eabae9a4ab26512a80d` |
| Source item | `t1:note:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Depending on the creditworthiness of the borrower, term of loan and LTV ratio, a higher or lower interest rate can be applied.
```

</details>

---

### Evidence 313 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8c983cbc9c6a3c089837d862` |
| Source item | `t1:note:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
- When the property insurance is obtained by the Bank at the customer’s request
- When the borrower selects differentiated or mixed form of loan repayment
- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
- If additional property is pledged as collateral
- If there are other deviations
```

</details>

---

### Evidence 314 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7e0a0d2d4d6dd3a712436a47` |
| Source item | `t1:note:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is ±5%.
```

</details>

---

### Evidence 315 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c0a38244b667a21c603dbee2` |
| Source item | `t1:note:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
The list of developers is determined by the Bank. If the developer is not included in the Bank's list, the terms of the loans for purchase of residential real estate from secondary market will apply.
```

</details>

---

### Evidence 316 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1c8b8fb42f065d42ca5cfd2a` |
| Source item | `t1:row:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 1. Purpose | 1.1. Purpose | 1.1.1. (i) Purchase of residential property (including parking space) for residential, lease or investment purposes, or (ii) transfer of a loan for purchase of property for residential, lease or investment purposes from another bank/credit organization to Ameriabank CJSC (the “Bank”) |  | 
```

</details>

---

### Evidence 317 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c3bb687e7954d4f7fae13221` |
| Source item | `t1:row:10` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed | 3.4.2. Fixed | 3.4.3. Fixed
```

</details>

---

### Evidence 318 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9c4df8c19749c2e6feef3831` |
| Source item | `t1:row:11` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 13.5% | 11.0% | 8.5%
```

</details>

---

### Evidence 319 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7311b0dda691db4d7e811bd1` |
| Source item | `t1:row:12` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed | 3.5.2. Fixed | 3.5.3. Fixed
```

</details>

---

### Evidence 320 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c92c7b7b447e4887abbc1a67` |
| Source item | `t1:row:13` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 14.39-15.76% | 11.6-13.56% | 8.86-10.71%
```

</details>

---

### Evidence 321 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ff63124967a52e7a7a00fe0a` |
| Source item | `t1:row:14` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.6. Term (months) | 3.6.1. 61-360 |  | 
```

</details>

---

### Evidence 322 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d1b8730baa3fb37c6b0595e1` |
| Source item | `t1:row:15` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)
```

</details>

---

### Evidence 323 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9e004b58fec964dc99a18f21` |
| Source item | `t1:row:16` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.7. Nominal annual interest rate² | Fixed component 5.5% + variable component (base rate) | Fixed component 8% + variable component (base rate) | Fixed component 7% + variable component (base rate)
```

</details>

---

### Evidence 324 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ad4254daad4a52de61687711` |
| Source item | `t1:row:17` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | Term and interest rate in case of online refinancing |  |  | 
```

</details>

---

### Evidence 325 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a1fedab75060e1ac774822e8` |
| Source item | `t1:row:18` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.8. Term (months) | 3.8.1. 61-360 |  | 
```

</details>

---

### Evidence 326 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b76b532be72047d968b4b063` |
| Source item | `t1:row:19` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.9. Nominal annual interest rate | 3.9.1. Adjustable fixed (rate can be changed starting from the 37th month) | N/a | N/a
```

</details>

---

### Evidence 327 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_000db397dddbe39ff09211b8` |
| Source item | `t1:row:20` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.9. Nominal annual interest rate | Fixed component 5.25% + variable component (base rate) | N/a | N/a
```

</details>

---

### Evidence 328 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ef4bcdf80a566b1e6a3d0377` |
| Source item | `t1:row:21` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 3.10.1. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.2. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.3. Adjustable fixed (rate can be changed starting from the 37th month)
```

</details>

---

### Evidence 329 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6018528e51f85b25d86884ad` |
| Source item | `t1:row:22` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 14.35-15.74% | 10.47-12.39% | 8.3-10.12%
```

</details>

---

### Evidence 330 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9a205193ee95e2c490b0b084` |
| Source item | `t1:row:23` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.1. If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. |  | 
```

</details>

---

### Evidence 331 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1baa4022e5d4a27e1eb79564` |
| Source item | `t1:row:24` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.2. If the collateral related ratios (loan-to-value ratio) deviate from those approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. |  | 
```

</details>

---

### Evidence 332 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_44db6ffd906f468eb1391632` |
| Source item | `t1:row:25` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.3. If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank (any or several of the declared income related criteria, OTI and OSM), the applicable interest rate is increased by 0.25%. |  | 
```

</details>

---

### Evidence 333 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6a982e0eb55140a8691edc54` |
| Source item | `t1:row:26` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.4. If the customer prefers a lending option without the early repayment fee, the applicable interest rate is increased by 0.5% (not applicable to loans secured by cash or bonds). |  | 
```

</details>

---

### Evidence 334 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ce1fd32603c8802fb77bade5` |
| Source item | `t1:row:27` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.11. Other terms related to the interest rate (not applicable in case of online refinancing) | 3.11.5. In case of other deviations, the applicable interest rate may be increased by 0.25%. |  | 
```

</details>

---

### Evidence 335 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_bba7454a12821c1129f183fc` |
| Source item | `t1:row:28` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.12. Lump sum disbursement fee | 3.12.1. N/A, except for non-resident individuals, for whom the lump sum loan disbursement fee is 1% of the loan amount or AMD 1 million, whichever is less |  | 
```

</details>

---

### Evidence 336 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d1fc86e0a6528b3266b43737` |
| Source item | `t1:row:29` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.13. Minimum down payment | 3.13.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
3.13.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children: at least 7.5 % of the appraised market price of the residential real estate to be purchased, subject to provision of additional collateral. |  | 
```

</details>

---

### Evidence 337 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1fc8583ed3bc6ffa5143cc62` |
| Source item | `t1:row:30` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.14. Manner of disbursement | 1. Lump sum
2. By tranches, in which case the amount/term of each tranche is defined in accordance with the provisions of the agreements executed between the seller company and the borrower. |  | 
```

</details>

---

### Evidence 338 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_674617b63e384938d4c3ba69` |
| Source item | `t1:row:31` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.15. Cashing of the loan amount by the seller from their account with the Bank after loan disbursement (where applicable) | 3.15.1.
AMD: Free
Other currency: 0.5 % |  | 
```

</details>

---

### Evidence 339 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f4fc11f36facb56504beb017` |
| Source item | `t1:row:32` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest) |  | 
```

</details>

---

### Evidence 340 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a5e845b331abb8deba40156f` |
| Source item | `t1:row:33` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.2. Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) /not applicable in case of online refinancing/ |  | 
```

</details>

---

### Evidence 341 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f81e20df74cf4c4e739e94de` |
| Source item | `t1:row:34` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 4. Forms of loan repayment | 4.1. Repayment method | 4.1.3. Mixed (the customer may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) /not applicable in case of online refinancing/ |  | 
```

</details>

---

### Evidence 342 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_aa7a3134f16941688bd3896c` |
| Source item | `t1:row:35` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.1. Eligible collateral | 5.1.1.
1. The loan is secured by the real estate being purchased. The Bank may consider pledge of other real estate as additional security to the reasonable satisfaction of the Bank, as well as cash in the Bank or bonds issued by the Bank.
2. If the borrower wishes to purchase property under construction without registered certificate of title, the loan will be secured by other Armenia-based real estate to the reasonable satisfaction of the Bank.
3. If the borrower wishes to purchase property abroad, the loan will be secured by Armenia-based real estate to the reasonable satisfaction of the Bank.
4. In the case of online refinancing, the collateral is real estate purchased directly from the developer, which has a completion certificate and is not encumbered with any liabilities other than the refinanced loan. |  | 
```

</details>

---

### Evidence 343 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f9dd31cc0cb25c5d7fb407b9` |
| Source item | `t1:row:36` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

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

</details>

---

### Evidence 344 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a1b6d6d9ed82083128ad39b8` |
| Source item | `t1:row:38` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.3. Location of the real estate to be pledged | 5.3.1. Armenia
5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020. |  | 
```

</details>

---

### Evidence 345 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_55afe571c1c32533b5c74529` |
| Source item | `t1:row:39` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.4. Appraisal of the collateral | 5.4.1.
1. No appraisal is required in case of acquisition of the right to purchase property from the developer. Pledge value is considered to be equal to the price specified in the developer’s reference, unless otherwise determined by the Bank.
2. In case of acquisition of the title to the real estate from the developer, appraisal is performed by appraisal companies cooperating with the Bank. |  | 
```

</details>

---

### Evidence 346 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_25fe446d1df0bba013c4aecb` |
| Source item | `t1:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | eligibility_and_documents |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 2. Customer’s personal details | 2.1. Eligible age of the customer/co-borrower/guarantor | 2.1.1. 18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70.
If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. |  | 
```

</details>

---

### Evidence 347 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1b123d5045f07fbb2a94f2cf` |
| Source item | `t1:row:40` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 5. Security | 5.5. Additional security | 5.5.1. The Bank may request guarantees of individuals and/or companies as additional security. |  | 
```

</details>

---

### Evidence 348 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_bdadf4f3d5f3c6eac03ea6b1` |
| Source item | `t1:row:41` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1. The real estate being pledged is insured by the Bank in the following cases: |  | 
```

</details>

---

### Evidence 349 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2f53a3ef5c28cf0d3b4d3b25` |
| Source item | `t1:row:42` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or |  | 
```

</details>

---

### Evidence 350 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c7b7611b0afa4021a55d371c` |
| Source item | `t1:row:43` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.1.2. if the address of the pledged real estate is included in the list of properties published on the Bank’s website. |  | 
```

</details>

---

### Evidence 351 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_910c53ba871b713b2dc0a24d` |
| Source item | `t1:row:44` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 6. Insurance of the collateral | 6.1. Insurance of the collateral | 6.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable). |  | 
```

</details>

---

### Evidence 352 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d85d21e0da36331f22d65aa1` |
| Source item | `t1:row:45` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | 7.1.1. Required documents filed together with the loan application |  | 
```

</details>

---

### Evidence 353 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ce080588c92e9b55047efa07` |
| Source item | `t1:row:46` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Loan application (not applicable in case of online refinancing) |  | 
```

</details>

---

### Evidence 354 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a8f0f219e6b824413c522d78` |
| Source item | `t1:row:47` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • ID (original) |  | 
```

</details>

---

### Evidence 355 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ba89a1f83d3ff48f887daafe` |
| Source item | `t1:row:48` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Certificate of ownership/purchase right of real estate to be purchased/pledged (copy) |  | 
```

</details>

---

### Evidence 356 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_609cb4cb372a3497c6e51862` |
| Source item | `t1:row:49` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Other documents upon the Bank’s request |  | 
```

</details>

---

### Evidence 357 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_af6c31d79ff0621eab423236` |
| Source item | `t1:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 2. Customer’s personal details | 2.2. Residency | 2.2.1. For loans in AMD: citizens and non-citizens of Armenia who are resident in Armenia
For loans in foreign currency: individuals not considered residents of Armenia |  | 
```

</details>

---

### Evidence 358 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_76886af90bb8d83a43935865` |
| Source item | `t1:row:50` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | 7.1.2. Documents required after pre-approval |  | 
```

</details>

---

### Evidence 359 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fc214713a1917e7eed1abc1d` |
| Source item | `t1:row:51` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Proof of employment and/or other income (not applicable in case of online refinancing) |  | 
```

</details>

---

### Evidence 360 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c8b3a5c3ef7570d988282b48` |
| Source item | `t1:row:52` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Marriage (divorce, spouse death) certificate (original) |  | 
```

</details>

---

### Evidence 361 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_530a5adfe92b52e822f85faa` |
| Source item | `t1:row:53` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Certificate of title to real estate to be pledged (original) |  | 
```

</details>

---

### Evidence 362 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3c79d8f78e474756a90f03aa` |
| Source item | `t1:row:54` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Other documents upon the Bank request |  | 
```

</details>

---

### Evidence 363 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_149aaf9d10f9b94730b6fd2f` |
| Source item | `t1:row:55` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | 7.1.3. Documents required after loan approval |  | 
```

</details>

---

### Evidence 364 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b37f5f1293dc49b7a3f5b5b7` |
| Source item | `t1:row:56` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Copies of bases of title to real estate (to be submitted upon the Bank’s request) |  | 
```

</details>

---

### Evidence 365 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2735e7105a189dbc6e842aea` |
| Source item | `t1:row:57` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • IDs of owners of the property to be purchased/pledged (originals) |  | 
```

</details>

---

### Evidence 366 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_860c8ca361e1ba0024069570` |
| Source item | `t1:row:58` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available |  | 
```

</details>

---

### Evidence 367 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_37a30e9f07b93d8ad2e195e4` |
| Source item | `t1:row:59` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement) |  | 
```

</details>

---

### Evidence 368 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6d9b740dec2d0a32a923b2ab` |
| Source item | `t1:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.1. Currency | 3.1.1. AMD | 3.1.2. USD | 3.1.2. EUR
```

</details>

---

### Evidence 369 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5249e71f8dd1175145c441ff` |
| Source item | `t1:row:60` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Tax clearance certificate for the real estate |  | 
```

</details>

---

### Evidence 370 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0416111c46ee33ceb181118e` |
| Source item | `t1:row:61` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Real estate insurance policy (as required) |  | 
```

</details>

---

### Evidence 371 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_44b52640646e1b7fa2134a6b` |
| Source item | `t1:row:62` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 7. Required documents | 7.1. Required documents | • Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system. |  | 
```

</details>

---

### Evidence 372 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2853919e5fbfeb09a487930f` |
| Source item | `t1:row:64` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 8. Early repayment fee | 8.1. Early repayment fee | 8.1.1.
At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.
Where the amount of early repayment exceeds the specified limit, the following fees will be charged:
• Max 0.6% of early repayment, if made during the first year of the agreement
• Max 0.4% of early repayment, if made during the second year of the agreement
• Max 0.2% of early repayment, if made during the third year of the agreement |  | 
```

</details>

---

### Evidence 373 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c96368fa0da84657a6259341` |
| Source item | `t1:row:65` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 9. Late payment fines and penalties | 9.1. Late payment fines and penalties | 9.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.
Fine in the amount of 0.13 % of overdue loan and interest for each day of delay |  | 
```

</details>

---

### Evidence 374 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d60c186ebd3168612b11989d` |
| Source item | `t1:row:66` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

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

</details>

---

### Evidence 375 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a08187966aa248b6b830c44a` |
| Source item | `t1:row:67` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 11. Creditworthiness assessment | 11.1 Without creditworthiness assessment | Where the loan amount is AMD 50-100 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 50% (if in Yerevan) or 60% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank
Where the loan amount is AMD 30-50 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 40% (if in Yerevan) or 50% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank.
Where the loan amount is up to AMD 30 million, the loan may be issued without the assessment of creditworthiness criteria if the customer (including non-resident) has made a down payment of 30% (if in Yerevan) or 40% (if in the regions of Armenia) and more and meets the requirements of the internal regulations of the Bank. |  | 
```

</details>

---

### Evidence 376 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4667a688c130caf3b9e947d6` |
| Source item | `t1:row:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

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

</details>

---

### Evidence 377 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_917ac984c878864732144d6e` |
| Source item | `t1:row:8` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | Term and interest rate |  |  | 
```

</details>

---

### Evidence 378 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5644d74f2e877b7d65c924bb` |
| Source item | `t1:row:9` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Tariffs |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms 1 | Terms 2 | Terms 3
Row: 3. Loan terms | 3.3. Term (months) | 3.3.1. 60 |  | 
```

</details>

---

### Evidence 379 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9b93cc38f00a2bdcb5dcbb9a` |
| Source item | `t2:note:0` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Express Home Mortgage Loan (Purchase, Construction and Renovation)
```

</details>

---

### Evidence 380 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_40059657a320c9a84705ee92` |
| Source item | `t2:note:1` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
General requirements to loan facilities
```

</details>

---

### Evidence 381 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_13d1e0ddec5e9edaa4f6551b` |
| Source item | `t2:note:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Express Home Purchase Loan (primary market)
```

</details>

---

### Evidence 382 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_137f2e7cecce83bde26931af` |
| Source item | `t2:note:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Express Home Purchase Loan (secondary market)
```

</details>

---

### Evidence 383 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7f3e21e6bfcdfc421e6dd175` |
| Source item | `t2:note:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Express Home Construction Loan
```

</details>

---

### Evidence 384 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_72fb3ca92300b629a3cac249` |
| Source item | `t2:note:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Express Home Renovation Loan
```

</details>

---

### Evidence 385 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_21be9b129c352b583d1c8448` |
| Source item | `t2:note:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Attention! The offer of the agreement is provided to the client following which the client may use the 7-day cooling-off period envisaged by the Armenian laws and regulations.
In case of failure to notarize the pledge agreements specified in the loan agreement and securing the borrower's obligations under the loan agreement, within 30 (thirty) business days upon execution of the loan agreement and acceptance by the Borrower, the Agreement shall cease to be valid (unless the loan has already been disbursed to the borrower by that date).
```

</details>

---

### Evidence 386 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_82c836bc1b450074e9247042` |
| Source item | `t2:note:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Attention! The adjustable nominal interest rate may be revised no more than twice a year. Furthermore, depending on the change of the adjustable nominal interest rate, the threshold above or below which the nominal rate cannot change is 5%.
```

</details>

---

### Evidence 387 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3d3bd2be2c5920e07f345f58` |
| Source item | `t2:note:8` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
The list of developers is determined by the Bank.
```

</details>

---

### Evidence 388 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f8c1b5954bf71e8152fbdcdd` |
| Source item | `t2:row:13` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 6. Early repayment fee | 6.1. Early repayment fee | 6.1.1.
At any time during a contractual year the borrower can make an early repayment to the extent of outstanding principal amount of loan for that contractual year. A contractual year is each period of 12 months following the date of execution of credit agreement.
Where the amount of early repayment exceeds the specified limit, the following fees will be charged:
• Max 0.6% of early repayment, if made during the first year of the agreement
• Max 0.4% of early repayment, if made during the second year of the agreement
• Max 0.2% of early repayment, if made during the third year of the agreement
```

</details>

---

### Evidence 389 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c0fc2b18d99e44a1fcdfea6a` |
| Source item | `t2:row:14` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 7. Late payment fines and penalties | 7.1. Late payment fines and penalties | 7.1.1. The interest rate specified in the loan agreement will continue to be applied to overdue loans.
Fine in the amount of 0.13% of overdue loan/interest for each overdue day
```

</details>

---

### Evidence 390 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4619ae854ac2627f7f535312` |
| Source item | `t2:row:15` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 8. Other fees | 8.1. Other fees payable by the client | 8.1.1. Fee for notarization of real estate pledged as collateral
Fee for registration of the right of ownership/purchase and the Bank rights arising out of the pledge agreements with the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
Fee for the unified reference on real estate encumbrance issued by the State Committee of Real Estate Cadaster of the Government of the Republic of Armenia
Fee for the final appraisal of the real estate (if required)
```

</details>

---

### Evidence 391 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e5620f47a89c6fb4c1de3aac` |
| Source item | `t2:row:16` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | eligibility_and_documents |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | 9.1.1. Required documents filed together with the loan application
```

</details>

---

### Evidence 392 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_321ef543185ccb92ed1141f2` |
| Source item | `t2:row:17` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | ID, public services number
```

</details>

---

### Evidence 393 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_245dd592afaf8185c655b54a` |
| Source item | `t2:row:18` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | 9.1.2. Documents required after pre-approval
• Certificate of title to real estate to be pledged (copy)
• Initial real estate appraisal report
• Other documents upon the Bank’s request
9.1.3. Documents required after loan approval
```

</details>

---

### Evidence 394 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8a1570c2d94d350ced9bbbfc` |
| Source item | `t2:row:2` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 1. Client’s personal details | 1.1. Eligible age of client/co-borrower | 1.1.1. 18-70, provided that the age of the borrower by the time of expiry of loan agreement will not have exceeded 70
```

</details>

---

### Evidence 395 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9f3abd475453dd3303e27e01` |
| Source item | `t2:row:23` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Marriage certificate (if any) and ID of the spouse, public services number
```

</details>

---

### Evidence 396 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ca566379a057e09b1bf5a6d1` |
| Source item | `t2:row:24` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Certificate of title to the real estate/right to purchase
```

</details>

---

### Evidence 397 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_98b1894a6fe0278786bb6ab3` |
| Source item | `t2:row:25` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Certificate of security interest registration
```

</details>

---

### Evidence 398 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2298aaff84cf174de98fa77d` |
| Source item | `t2:row:26` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Unified reference on real estate encumbrance
```

</details>

---

### Evidence 399 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_676b862a87f143f25e32e667` |
| Source item | `t2:row:27` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | • Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.
```

</details>

---

### Evidence 400 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_82ac93814c1bc23289cca94e` |
| Source item | `t2:row:28` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Construction permit (for construction loans)
```

</details>

---

### Evidence 401 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7fd98c8f7cf41add3fd4208d` |
| Source item | `t2:row:29` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Pro-forma invoice (for renovation and construction loans)
```

</details>

---

### Evidence 402 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_376af6100cac1b5b3490ca77` |
| Source item | `t2:row:3` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 1. Client’s personal details | 1.2. Residency | 1.2.1. Citizens of Armenia who are resident in Armenia
```

</details>

---

### Evidence 403 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f04efee3df2f0b7ad002fa0b` |
| Source item | `t2:row:30` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 9. Required documents | 9.1. Required documents | Other documents upon the Bank’s request
```

</details>

---

### Evidence 404 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a10345151df143f8765e16ce` |
| Source item | `t2:row:32` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes
```

</details>

---

### Evidence 405 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_10923f5b4e6b7c23a9efc225` |
| Source item | `t2:row:35` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.2. Term (months) | 1.2.1. 61-360
```

</details>

---

### Evidence 406 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_750f6ac2d4d71f5432712c44` |
| Source item | `t2:row:36` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.3. Nominal annual interest rate | 1.3.1. Adjustable fixed² (rate can be changed starting from the 37th month)
```

</details>

---

### Evidence 407 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e01a9a9c277a7ec8421ed081` |
| Source item | `t2:row:37` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.3. Nominal annual interest rate | Fixed component 5.25% + variable component (base rate)
```

</details>

---

### Evidence 408 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_01bf4cdf4c3ecd09f69225e9` |
| Source item | `t2:row:38` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.4. Annual percentage rate (APR) | 1.4.1. 14.08-15.57%
```

</details>

---

### Evidence 409 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7f502c65df4b70e54fe209df` |
| Source item | `t2:row:39` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.5. Minimum down payment | 1.5.1. At least 10% of the purchase price of the property In case of additional collateral: in the amount of 5% of the purchase price.
```

</details>

---

### Evidence 410 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5e354fc04aa52c11e7cc0c1c` |
| Source item | `t2:row:4` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Terms and Conditions | 2.1. Currency | 2.1.1. AMD
```

</details>

---

### Evidence 411 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_125188d750e0d05260f3938d` |
| Source item | `t2:row:40` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being purchased. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

</details>

---

### Evidence 412 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_600c55f9e9bbe4d3c8e4a5c6` |
| Source item | `t2:row:41` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1
1.1. For loans with a term of 240 months, the loan amount is up to 90% of the sale price set by the developer³.
For loans with a term above 240 months, the loan amount is up to 80% of the sale price set by the developer⁴, unless otherwise determined by the Bank.
```

</details>

---

### Evidence 413 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_da9188222ac7aa66b25720da` |
| Source item | `t2:row:42` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.3. Location of the real estate to be pledged | 5.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard
```

</details>

---

### Evidence 414 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2bf7d9d02686106ebe788948` |
| Source item | `t2:row:43` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. N/A
The price statement provided by the Developer⁴ is taken as the basis for the collateral value.
```

</details>

---

### Evidence 415 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_aecaaed17ae927918f31ba60` |
| Source item | `t2:row:45` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 1. Purpose | 1.1. Purpose | 1.1.1. Purchase of residential property for residential, lease or investment purposes.
```

</details>

---

### Evidence 416 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_feccb2103cd22349cc14f3e7` |
| Source item | `t2:row:5` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Terms and Conditions | 2.2. Minimum and maximum loan limit | 2.2.1. AMD 3,000,000-100,000,000
```

</details>

---

### Evidence 417 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b9a7132d23d5c26324dc3d46` |
| Source item | `t2:row:50` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.3. Nominal annual interest rate | Fixed component 5.75% + variable component (base rate)
```

</details>

---

### Evidence 418 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0c2aa14e40235dd74700c810` |
| Source item | `t2:row:51` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.4. Annual percentage rate (APR) | 1.4.1. 14.66-17.11%
```

</details>

---

### Evidence 419 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fc2e944456f6d664b1571b81` |
| Source item | `t2:row:52` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.5. Minimum down payment | 1.5.1. At least 5% of the purchase price of the property
```

</details>

---

### Evidence 420 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0289407d1afa3b345ef82d6f` |
| Source item | `t2:row:54` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80% (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70% (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
```

</details>

---

### Evidence 421 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e0eaf7a9752ff78a8bc233a6` |
| Source item | `t2:row:55` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard
```

</details>

---

### Evidence 422 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_76cd547bb5efcdc59e2c3dc4` |
| Source item | `t2:row:56` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.4. Appraisal of the collateral | 2.4.1. Pledged property to be appraised by an appraising partner of the Bank.
```

</details>

---

### Evidence 423 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_52246939a18b9f9d812cb971` |
| Source item | `t2:row:58` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 1. Purpose | 1.1. Purpose | 1.1. Construction of residential property
```

</details>

---

### Evidence 424 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_835bcb9fbfbfdf5604c3b16e` |
| Source item | `t2:row:6` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Terms and Conditions | 2.3. Cashing of the loan amount by the borrower or the seller from his account with the Bank after loan disbursement (where applicable) | 2.3.1.
AMD: free
```

</details>

---

### Evidence 425 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ae0fc0b72d9fcdeeeedc6f40` |
| Source item | `t2:row:64` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.4. Annual percentage rate (APR) | 1.4.1. 14.65-15.9%
```

</details>

---

### Evidence 426 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_09bb125a79abf0310e155166` |
| Source item | `t2:row:65` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being constructed. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

</details>

---

### Evidence 427 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_711c047754a39056347d9a6f` |
| Source item | `t2:row:66` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.2. Loan-to-value (LTV) ratio | 2.2.1.
The loan is issued:
For AMD loans with a term of 61-240 months: 80%² (if in Yerevan) and 70% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
For AMD loans with a term above 240 months: 70%² (if in Yerevan) and 60% (if in the regions of Armenia) of the lower of the two: appraised market value or purchase price of pledged property,
```

</details>

---

### Evidence 428 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_647230946c47ff3a61a651cc` |
| Source item | `t2:row:67` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.3. Location of the real estate to be pledged | 2.3.1. Yerevan, regional centers of Armenia, towns where Ameriabank has branches, as well as Jrvezh, Arinj, Dzoraghbyur, Kasakh, Tsaghkadzor, Masis and Yeghvard
5.3.1.1. In case of lending under 2024-2026 state-supported housing programs for families with children, also regional cities of Armenia not specified in clause 5.3.1 and particular rural settlements approved by the Republic of Armenia Government decree N 968-Լ as of May 14, 2020.
```

</details>

---

### Evidence 429 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9a03f02f2d8314afddd812d5` |
| Source item | `t2:row:69` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 3. Term of fulfillment of conditions of loan | 3.1. Term of fulfillment of conditions of loan | 3.1.1. Loans are disbursed in tranches. Each tranche is subject to proper use of previous tranche for the intended loan purpose by the borrower except where the amount of loan is AMD 7 million or less or the loan has been transferred from another bank, in which cases the sum is disbursed lump-sum.
For loans over AMD 50 million contractual amount at least 3 tranches must be defined.
```

</details>

---

### Evidence 430 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c8596ae1f645706e87817969` |
| Source item | `t2:row:7` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Terms and Conditions | 2.4. Lump sum disbursement fee | 2.4.1. N/A
```

</details>

---

### Evidence 431 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d86c9d629daf879b09310cef` |
| Source item | `t2:row:71` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | identity |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 1. Purpose | 1.1. Purpose | 1.1. Renovation of residential property
```

</details>

---

### Evidence 432 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b080642007b3a4c7193ae5ce` |
| Source item | `t2:row:74` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row:  | 1.2. Term (months) | 1.2.1. 61-240
```

</details>

---

### Evidence 433 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c22a02581008d5f363c67c0e` |
| Source item | `t2:row:78` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 2. Security | 2.1. Eligible collateral | 2.1.1. The loan is secured by the property being renovated. The bank may consider as additional security pledge of other real estate to the reasonable satisfaction of the bank.
```

</details>

---

### Evidence 434 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0a8f92dc947fde9df625ebbb` |
| Source item | `t2:row:8` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 3. Forms of loan repayment | 3.1. Repayment method | 3.1.1. Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)
```

</details>

---

### Evidence 435 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e1a7ded3f381e1297110652d` |
| Source item | `t2:row:9` |
| Role | `product_terms` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Express Home Mortgage Loan (Purchase, Construction and Renovation) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Section | Item | Terms
Row: 5. Insurance of the collateral | 5.1. Insurance of the collateral | 5.1.1. The real estate being pledged is insured by the Bank in the following cases:
5.1.1.1. If at the time of registration of the title to the real estate and/or at the time of reappraisal, the market value of the property is over AMD 100 million (one hundred million); or
5.1.1.2. where the address of the pledged real estate is included in the list of properties published on the Bank’s website.
5.1.2. The Bank obtains insurance each year for the amount of the outstanding principal throughout the loan term if any of the above specified conditions is in place (in this case, the calculation of the interest rate also covers all the possible costs, including those associated with the insurance, where applicable).
```

</details>

---

### Evidence 436 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_607f396b5d090c7d1d8cd6ac` |
| Source item | `t3:row:1` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 1. Term extension for mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000
```

</details>

---

### Evidence 437 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_f691f87398f296f924f687aa` |
| Source item | `t3:row:10` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 10. Provision of loan before submitting to the Bank the document certifying state registration of the security interest | AMD 25,000 (per issue)
```

</details>

---

### Evidence 438 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ad995e216c6082c013d8d7d8` |
| Source item | `t3:row:11` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 11. Issuing other consent not established by this document and not related to the collateral | AMD 10,000
(VAT included)
```

</details>

---

### Evidence 439 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fb7c0a7556ac8d6155aea58a` |
| Source item | `t3:row:12` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 12. Revision/modification of another loan term not specified in this document (including interest rate revision) | 0.1% of the outstanding loan amount, minimum AMD 10,000
```

</details>

---

### Evidence 440 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3f8ed0cb95ff89ca86e2dde0` |
| Source item | `t3:row:2` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 2. Granting a grace period for the principal amount of mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000
```

</details>

---

### Evidence 441 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_97d54d5d16c7f5b53e15877b` |
| Source item | `t3:row:3` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 3. Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000
```

</details>

---

### Evidence 442 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0f7f946a3fa8ed115a448aa0` |
| Source item | `t3:row:4` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 4. Change of the overdraft/line of credit account/card | AMD 30,000
```

</details>

---

### Evidence 443 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7f3ccf9032e54b0acd00f999` |
| Source item | `t3:row:5` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 5. Change of the borrower/co-borrower/guarantor | AMD 50,000
```

</details>

---

### Evidence 444 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_29f2a8e3b63e83f5d3c4e1f5` |
| Source item | `t3:row:6` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 6. Release/substitution of the collateral | AMD 50,000
```

</details>

---

### Evidence 445 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5b241ecbfc53ff1ba3a89864` |
| Source item | `t3:row:7` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 7. Issuing consent for change of a pledged vehicle plate number | AMD 50,000
(VAT included)
```

</details>

---

### Evidence 446 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_3a933c21161fc5bbdf0df6ee` |
| Source item | `t3:row:8` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 8. Collateral-related change (including change of the collateral owner) | AMD 15,000
```

</details>

---

### Evidence 447 of 490

> **FAILED**  
> Sent to the LLM, but the extraction run did not produce a validated result.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_1775f6b4c7ce9d935fb7c0c0` |
| Source item | `t3:row:9` |
| Role | `fees` |
| Authority | `official_terms` |
| Temporal status | `current` |
| Semantic packets | fees_and_repayment |
| Section | Loan service fees |

<details open>
<summary><strong>Source content</strong></summary>

```text
Headers: Purpose | Rates and Fees (AMD)
Row: 9. Change of the loan repayment date | AMD 10,000
```

</details>

---

### Evidence 448 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c5737502f6b7474dfbfe76d9` |
| Source item | `b152` |
| Role | `product_description` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions &gt; Loan Calculators |

<details open>
<summary><strong>Source content</strong></summary>

```text
How much can you borrow?
Calculate how much you can borrow as a mortgage based on your salary or other income and your financial situation.
```

</details>

---

### Evidence 449 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_235f7c3ad7da15229ee163ac` |
| Source item | `b154` |
| Role | `related_product` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Terms and conditions &gt; Real estate loan for secondary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
If you have already found your ideal home on the secondary market and are looking for financing options, our offer is for you. You can obtain financing directly from us or transfer your house loan from another bank or credit organization to Ameriabank.
```

</details>

---

### Evidence 450 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_43e2bd1896355c5a5c8e783d` |
| Source item | `b16` |
| Role | `product_description` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | (none) |

<details open>
<summary><strong>Source content</strong></summary>

```text
Real estate loan for primary market
```

</details>

---

### Evidence 451 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a904bd24f35ea80b8b55e8d9` |
| Source item | `b17` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
Your new home is waiting for you
```

</details>

---

### Evidence 452 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_8a6a7c74d48bb2eeeaa1163b` |
| Source item | `b18` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
AMD 3-150 million
```

</details>

---

### Evidence 453 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5a2de7db88d122d181062503` |
| Source item | `b19` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; AMD 3-150 million |

<details open>
<summary><strong>Source content</strong></summary>

```text
Loan amount
```

</details>

---

### Evidence 454 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c80eafa2a1e8d4884dffa9ab` |
| Source item | `b20` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
60-360 months
```

</details>

---

### Evidence 455 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6dfb44c740dff2d815f7aa56` |
| Source item | `b21` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; 60-360 months |

<details open>
<summary><strong>Source content</strong></summary>

```text
Term
```

</details>

---

### Evidence 456 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_d8de64865289331773262ff0` |
| Source item | `b22` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
12.9%
```

</details>

---

### Evidence 457 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_519048ee2ef4641e31948bc0` |
| Source item | `b23` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; 12.9% |

<details open>
<summary><strong>Source content</strong></summary>

```text
Nominal interest rate
```

</details>

---

### Evidence 458 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b80b01a136cf448ce992a668` |
| Source item | `b24` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
from 10%
```

</details>

---

### Evidence 459 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_06f59e0a41c5fc93785e795d` |
| Source item | `b25` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; from 10% |

<details open>
<summary><strong>Source content</strong></summary>

```text
Advance payment
```

</details>

---

### Evidence 460 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a3dfc8f1e3ac67cdf302f262` |
| Source item | `b26` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; from 10% |

<details open>
<summary><strong>Source content</strong></summary>

```text
Actual interest rate: 13.67-13.68%
```

</details>

---

### Evidence 461 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fd93317b1a830b748a61ac5a` |
| Source item | `b27` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
Real estate loan for primary market
```

</details>

---

### Evidence 462 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fcffea824b07b0425ce7f8db` |
| Source item | `b28` |
| Role | `product_description` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
Want to buy a new apartment or house? Our mortgage loan offer for the primary market will help you to buy your new home from our partner developers.
The choice is easier to make via our online platform, find your ideal option, use the calculator to find out your monthly payment, and apply online:
```

</details>

---

### Evidence 463 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2c2bafcbfaa921331994edd5` |
| Source item | `b29` |
| Role | `product_description` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
ADVANTAGES
```

</details>

---

### Evidence 464 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_425242ec00c3627d831c70af` |
| Source item | `b30` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES |

<details open>
<summary><strong>Source content</strong></summary>

```text
No property appraisal required
```

</details>

---

### Evidence 465 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_68947bac2aeebb5f31ae1be8` |
| Source item | `b31` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES |

<details open>
<summary><strong>Source content</strong></summary>

```text
Advance payment: from 10%
```

</details>

---

### Evidence 466 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_551cb887092eecf2a8372436` |
| Source item | `b32` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES |

<details open>
<summary><strong>Source content</strong></summary>

```text
Property insurance by the Bank
```

</details>

---

### Evidence 467 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fff99826322dfc70a936570e` |
| Source item | `b33` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES |

<details open>
<summary><strong>Source content</strong></summary>

```text
No loan service fees
```

</details>

---

### Evidence 468 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fac995a3ca7ccdf08b7b25c9` |
| Source item | `b34` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES |

<details open>
<summary><strong>Source content</strong></summary>

```text
Purchase of real estate for living or lease
```

</details>

---

### Evidence 469 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_e91d4e4d37afee7a3cadc3e9` |
| Source item | `b35` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES |

<details open>
<summary><strong>Source content</strong></summary>

```text
Both in Yerevan and regions
```

</details>

---

### Evidence 470 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7636f0058983d40e5c4643fa` |
| Source item | `b36` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Real estate loan for primary market &gt; ADVANTAGES |

<details open>
<summary><strong>Source content</strong></summary>

```text
Mortgage calculator
```

</details>

---

### Evidence 471 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_2a7edf4eac93d28d6c05f09d` |
| Source item | `b37` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
Mortgage calculator
```

</details>

---

### Evidence 472 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7ff24bb25c3230549b7ad6fb` |
| Source item | `b38` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
Restriction applies to entry of values as per the Bank’s terms.
```

</details>

---

### Evidence 473 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_6fce2d0194eeb0d600043476` |
| Source item | `b39` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
Annual interest rate (%)
```

</details>

---

### Evidence 474 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_796438aef1f56cf9ad72f8e5` |
| Source item | `b40` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
12.5 %14 %
```

</details>

---

### Evidence 475 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c093c28af67b938e03baaf6b` |
| Source item | `b41` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
Mortgage loan amount (AMD)
```

</details>

---

### Evidence 476 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_fa27c04c2df984ea989c03f5` |
| Source item | `b42` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
3,000,000150,000,000
```

</details>

---

### Evidence 477 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_4d57823e25ce6c2fa57fe5d2` |
| Source item | `b43` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
Mortgage loan term (months)
```

</details>

---

### Evidence 478 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_98f900c347a3d2a2ce3fb356` |
| Source item | `b44` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
60360
```

</details>

---

### Evidence 479 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_5be2f330a3862ac164cb7f45` |
| Source item | `b45` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
MONTHLY INSTALLMENT
```

</details>

---

### Evidence 480 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_b99832ab329bc25308955610` |
| Source item | `b46` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
227,228
```

</details>

---

### Evidence 481 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a69d3605aed35b2ee795c603` |
| Source item | `b47` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
Total amount payable
```

</details>

---

### Evidence 482 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a118debbc73acc81b4d8d3bd` |
| Source item | `b48` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
54,534,746
```

</details>

---

### Evidence 483 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_637356f95edfaf04a9530ab2` |
| Source item | `b49` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
AMD
```

</details>

---

### Evidence 484 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_c112ce914af31050bf925b41` |
| Source item | `b50` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
Total interest amount
```

</details>

---

### Evidence 485 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_a018b1c78c4b82f98cb6e837` |
| Source item | `b51` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
34,534,746
```

</details>

---

### Evidence 486 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_0575f7191e7f9e5421dfb105` |
| Source item | `b52` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
AMD
```

</details>

---

### Evidence 487 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_9cf6f550c1946d8278497a0f` |
| Source item | `b53` |
| Role | `pricing` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Mortgage calculator |

<details open>
<summary><strong>Source content</strong></summary>

```text
Dear Client, this calculation is for information only and might be changed
```

</details>

---

### Evidence 488 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_7cbf3960b8c3af35513ac117` |
| Source item | `b54` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
Find your new home online
```

</details>

---

### Evidence 489 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_ee188c0d5a13fd81bfa4aa22` |
| Source item | `b55` |
| Role | `eligibility` |
| Authority | `official_product_content` |
| Temporal status | `current` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market &gt; Find your new home online |

<details open>
<summary><strong>Source content</strong></summary>

```text
Choose your new apartment according to area, monthly payment amount and other criteria and submit a credit report online.
By the way, you can also apply for a loan with a co-borrower.
```

</details>

---

### Evidence 490 of 490

> **NOT SENT TO SEMANTIC LLM**  
> Deterministic planner decision: omitted from all bounded field packets after relevance ranking and configured item/character limits. The evidence remains accepted and auditable.

| Metadata | Value |
|---|---|
| Evidence ID | `ev_bccfa341928ab59ab018dabd` |
| Source item | `b56` |
| Role | `product_terms` |
| Authority | `official_product_content` |
| Temporal status | `unknown` |
| Semantic packets | (none) |
| Section | Real estate loan for primary market |

<details open>
<summary><strong>Source content</strong></summary>

```text
Terms and conditions
```

</details>
