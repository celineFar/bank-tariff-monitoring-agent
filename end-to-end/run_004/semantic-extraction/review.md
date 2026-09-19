# Semantic extraction human-review queue

Open review items: **2**

Each item preserves the original model value, validation path, evidence IDs, batch, and model.

---

## interest_rate

Review ID: `review_2291cc26f802ddb9abe77824`  
Batch: `extract_001`  
Model: `gemini-3.7-flash`  
Evidence: `ev_0d2f2535ad7550cc981e39dc`, `ev_6eedd264158e128a00cb0b47`, `ev_683fac14010eb66fee095570`, `ev_220360efba75fa605fc45b78`, `ev_f105645fd121f8f14bb78d94`, `ev_ee0181a07d7cb2868f36c95f`

### Validation problems

- `interest_rate.0.value`: Field required (`missing`)
- `interest_rate.0.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `interest_rate.1.value`: Field required (`missing`)
- `interest_rate.1.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `interest_rate.2.value`: Field required (`missing`)
- `interest_rate.2.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `interest_rate.3.value`: Field required (`missing`)
- `interest_rate.3.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `interest_rate.4.value`: Field required (`missing`)
- `interest_rate.4.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `interest_rate.5.value`: Field required (`missing`)
- `interest_rate.5.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `interest_rate.6.value`: Field required (`missing`)
- `interest_rate.6.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `interest_rate.6.conditions.1`: Input should be a valid dictionary or instance of Condition (`model_type`)

### Raw field output

```json
{
  "field": "interest_rate",
  "status": "found",
  "value_json": "[{\"currency\":\"AMD\",\"rate_type\":\"fixed\",\"rate_pct\":13.5,\"conditions\":[\"Fixed rate\"]},{\"currency\":\"USD\",\"rate_type\":\"fixed\",\"rate_pct\":11.0,\"conditions\":[\"Fixed rate\"]},{\"currency\":\"EUR\",\"rate_type\":\"fixed\",\"rate_pct\":8.5,\"conditions\":[\"Fixed rate\"]},{\"currency\":\"AMD\",\"rate_type\":\"floating\",\"formula\":\"Fixed component 5.5% + variable component (base rate)\",\"conditions\":[\"Adjustable fixed (rate can be changed starting from the 37th month)\"]},{\"currency\":\"USD\",\"rate_type\":\"floating\",\"formula\":\"Fixed component 8% + variable component (base rate)\",\"conditions\":[\"Adjustable fixed (rate can be changed starting from the 37th month)\"]},{\"currency\":\"EUR\",\"rate_type\":\"floating\",\"formula\":\"Fixed component 7% + variable component (base rate)\",\"conditions\":[\"Adjustable fixed (rate can be changed starting from the 37th month)\"]},{\"currency\":\"AMD\",\"rate_type\":\"floating\",\"formula\":\"Fixed component 5.25% + variable component (base rate)\",\"conditions\":[\"Online refinancing\",\"Adjustable fixed (rate can be changed starting from the 37th month)\"]}]",
  "evidence": [
    {
      "evidence_id": "ev_0d2f2535ad7550cc981e39dc",
      "quote": "Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 3.4.1. Fixed | 3.4.2. Fixed | 3.4.3. Fixed"
    },
    {
      "evidence_id": "ev_6eedd264158e128a00cb0b47",
      "quote": "Row: 3. Loan terms | 3.4. Nominal annual interest rate² | 13.5% | 11.0% | 8.5%"
    },
    {
      "evidence_id": "ev_683fac14010eb66fee095570",
      "quote": "Row: 3. Loan terms | 3.7. Nominal annual interest rate² | 3.7.1. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.2. Adjustable fixed⁴ (rate can be changed starting from the 37th month) | 3.7.3. Adjustable fixed⁴ (rate can be changed starting from the 37th month)"
    },
    {
      "evidence_id": "ev_220360efba75fa605fc45b78",
      "quote": "Row: 3. Loan terms | 3.7. Nominal annual interest rate² | Fixed component 5.5% + variable component (base rate) | Fixed component 8% + variable component (base rate) | Fixed component 7% + variable component (base rate)"
    },
    {
      "evidence_id": "ev_f105645fd121f8f14bb78d94",
      "quote": "Row: 3. Loan terms | 3.9. Nominal annual interest rate | 3.9.1. Adjustable fixed (rate can be changed starting from the 37th month) | N/a | N/a"
    },
    {
      "evidence_id": "ev_ee0181a07d7cb2868f36c95f",
      "quote": "Row: 3. Loan terms | 3.9. Nominal annual interest rate | Fixed component 5.25% + variable component (base rate) | N/a | N/a"
    }
  ],
  "explanation": null
}
```

---

## effective_rate

Review ID: `review_38fae092354697b91aab68cb`  
Batch: `extract_001`  
Model: `gemini-3.7-flash`  
Evidence: `ev_54bb0175baea1a59ad19edcb`, `ev_1833e80e22f3aeff89a8173a`, `ev_23270fda34542aff2246546f`, `ev_d0831ca8a7468018e237c41b`

### Validation problems

- `effective_rate.0.value`: Field required (`missing`)
- `effective_rate.0.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `effective_rate.1.value`: Field required (`missing`)
- `effective_rate.1.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `effective_rate.2.value`: Field required (`missing`)
- `effective_rate.2.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `effective_rate.3.value`: Field required (`missing`)
- `effective_rate.3.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `effective_rate.4.value`: Field required (`missing`)
- `effective_rate.4.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)
- `effective_rate.5.value`: Field required (`missing`)
- `effective_rate.5.conditions.0`: Input should be a valid dictionary or instance of Condition (`model_type`)

### Raw field output

```json
{
  "field": "effective_rate",
  "status": "found",
  "value_json": "[{\"currency\":\"AMD\",\"min_rate_pct\":14.39,\"max_rate_pct\":15.76,\"conditions\":[\"Fixed rate\"]},{\"currency\":\"USD\",\"min_rate_pct\":11.6,\"max_rate_pct\":13.56,\"conditions\":[\"Fixed rate\"]},{\"currency\":\"EUR\",\"min_rate_pct\":8.86,\"max_rate_pct\":10.71,\"conditions\":[\"Fixed rate\"]},{\"currency\":\"AMD\",\"min_rate_pct\":14.35,\"max_rate_pct\":15.74,\"conditions\":[\"Adjustable fixed (rate can be changed starting from the 37th month)\"]},{\"currency\":\"USD\",\"min_rate_pct\":10.47,\"max_rate_pct\":12.39,\"conditions\":[\"Adjustable fixed (rate can be changed starting from the 37th month)\"]},{\"currency\":\"EUR\",\"min_rate_pct\":8.3,\"max_rate_pct\":10.12,\"conditions\":[\"Adjustable fixed (rate can be changed starting from the 37th month)\"]}]",
  "evidence": [
    {
      "evidence_id": "ev_54bb0175baea1a59ad19edcb",
      "quote": "Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 3.5.1. Fixed | 3.5.2. Fixed | 3.5.3. Fixed"
    },
    {
      "evidence_id": "ev_1833e80e22f3aeff89a8173a",
      "quote": "Row: 3. Loan terms | 3.5. Annual percentage rate (APR)³ | 14.39-15.76% | 11.6-13.56% | 8.86-10.71%"
    },
    {
      "evidence_id": "ev_23270fda34542aff2246546f",
      "quote": "Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 3.10.1. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.2. Adjustable fixed (rate can be changed starting from the 37th month) | 3.10.3. Adjustable fixed (rate can be changed starting from the 37th month)"
    },
    {
      "evidence_id": "ev_d0831ca8a7468018e237c41b",
      "quote": "Row: 3. Loan terms | 3.10. Annual percentage rate (APR)³ | 14.35-15.74% | 10.47-12.39% | 8.3-10.12%"
    }
  ],
  "explanation": null
}
```
