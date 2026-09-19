# Pre-validation semantic extraction audit

This preserves what Gemini produced before canonical field validation. Green passed validation, red failed and entered human review, and orange is valid but semantically ambiguous or conflicting.

---

## extract_004: product_details

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>property_market — VALIDATED</strong></div>

```json
"primary"
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>down_payment_pct — VALIDATED</strong></div>

```json
[
  {
    "condition": null,
    "value": 10.0
  },
  {
    "condition": "In case of additional collateral",
    "value": 5.0
  },
  {
    "condition": "In case of lending under 2024-2026 state-supported housing programs for families with children, subject to provision of additional collateral",
    "value": 7.5
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>ltv_pct — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>collateral — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>income_verification_required — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>property_requirements — VALIDATED</strong></div>

```json
null
```

---

## extract_000: identity

<div style="border-left:5px solid #f79009;background:#fff4e5;padding:0.55em 0.8em;margin-top:1em;"><strong>product_name — AMBIGUOUS</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>category — VALIDATED</strong></div>

```json
"mortgage"
```

<div style="border-left:5px solid #f79009;background:#fff4e5;padding:0.55em 0.8em;margin-top:1em;"><strong>purpose — AMBIGUOUS</strong></div>

```json
null
```

---

## extract_001: core_financial

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>loan_amount — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #d92d20;background:#fee4e2;padding:0.55em 0.8em;margin-top:1em;"><strong>interest_rate — INVALID — HUMAN REVIEW</strong></div>

```json
[
  {
    "currency": "AMD",
    "rate_type": "fixed",
    "rate_pct": 13.5,
    "conditions": [
      "Fixed rate"
    ]
  },
  {
    "currency": "USD",
    "rate_type": "fixed",
    "rate_pct": 11.0,
    "conditions": [
      "Fixed rate"
    ]
  },
  {
    "currency": "EUR",
    "rate_type": "fixed",
    "rate_pct": 8.5,
    "conditions": [
      "Fixed rate"
    ]
  },
  {
    "currency": "AMD",
    "rate_type": "floating",
    "formula": "Fixed component 5.5% + variable component (base rate)",
    "conditions": [
      "Adjustable fixed (rate can be changed starting from the 37th month)"
    ]
  },
  {
    "currency": "USD",
    "rate_type": "floating",
    "formula": "Fixed component 8% + variable component (base rate)",
    "conditions": [
      "Adjustable fixed (rate can be changed starting from the 37th month)"
    ]
  },
  {
    "currency": "EUR",
    "rate_type": "floating",
    "formula": "Fixed component 7% + variable component (base rate)",
    "conditions": [
      "Adjustable fixed (rate can be changed starting from the 37th month)"
    ]
  },
  {
    "currency": "AMD",
    "rate_type": "floating",
    "formula": "Fixed component 5.25% + variable component (base rate)",
    "conditions": [
      "Online refinancing",
      "Adjustable fixed (rate can be changed starting from the 37th month)"
    ]
  }
]
```

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

<div style="border-left:5px solid #d92d20;background:#fee4e2;padding:0.55em 0.8em;margin-top:1em;"><strong>effective_rate — INVALID — HUMAN REVIEW</strong></div>

```json
[
  {
    "currency": "AMD",
    "min_rate_pct": 14.39,
    "max_rate_pct": 15.76,
    "conditions": [
      "Fixed rate"
    ]
  },
  {
    "currency": "USD",
    "min_rate_pct": 11.6,
    "max_rate_pct": 13.56,
    "conditions": [
      "Fixed rate"
    ]
  },
  {
    "currency": "EUR",
    "min_rate_pct": 8.86,
    "max_rate_pct": 10.71,
    "conditions": [
      "Fixed rate"
    ]
  },
  {
    "currency": "AMD",
    "min_rate_pct": 14.35,
    "max_rate_pct": 15.74,
    "conditions": [
      "Adjustable fixed (rate can be changed starting from the 37th month)"
    ]
  },
  {
    "currency": "USD",
    "min_rate_pct": 10.47,
    "max_rate_pct": 12.39,
    "conditions": [
      "Adjustable fixed (rate can be changed starting from the 37th month)"
    ]
  },
  {
    "currency": "EUR",
    "min_rate_pct": 8.3,
    "max_rate_pct": 10.12,
    "conditions": [
      "Adjustable fixed (rate can be changed starting from the 37th month)"
    ]
  }
]
```

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

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>term — VALIDATED</strong></div>

```json
null
```

---

## extract_002: fees_and_repayment

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>fees — VALIDATED</strong></div>

```json
[
  "Early repayment fee (if exceeding contractual year limit): Max 0.6% of early repayment if made during first year, Max 0.4% if made during second year, Max 0.2% if made during third year",
  "Change of the loan repayment date: AMD 10,000"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>repayment — VALIDATED</strong></div>

```json
[
  "Annuity (equal monthly installments consisting of a portion of loan and a portion of interest)",
  "Differentiated (monthly repayment of equal portions of principal amount while interest accrues to outstanding loan and decreases each month) /not applicable in case of online refinancing/",
  "Mixed (the customer may choose an individual repayment schedule based on seasonality of cash flows, provided that at least 5% of contractual loan amount is repaid each year; interest payable on monthly basis) /not applicable in case of online refinancing/"
]
```

---

## extract_003: eligibility_and_documents

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>eligibility — VALIDATED</strong></div>

```json
[
  "Individuals meeting the Terms established by Ameriabank CJSC"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>residency_requirements — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>age_requirements — VALIDATED</strong></div>

```json
"18-70 years old, provided that the borrower's age at the time of expiry of loan agreement will not have exceeded 70, otherwise a co-borrower or guarantor is required. The eligible age of co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age of the co-borrower or guarantor is 18-70 provided that at the time of expiry of agreement it will not have exceeded 70."
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>application_channel — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>required_documents — VALIDATED</strong></div>

```json
[
  "Loan application (not applicable in case of online refinancing)",
  "ID (original)",
  "Certificate of ownership/purchase right of real estate to be purchased/pledged (copy)",
  "Marriage (divorce, spouse death) certificate (original)",
  "Copies of bases of title to real estate (to be submitted upon the Bank’s request)",
  "IDs of owners of the property to be purchased/pledged (originals)",
  "Copies of marriage (divorce, spouse death) certificates of owners of the property to be pledged, to be presented if available",
  "Statement from the State Committee of Real Estate Cadaster on encumbrance of real estate (unified statement)",
  "Tax clearance certificate for the real estate",
  "Real estate insurance policy (as required)",
  "Documentary proof that the down payment was made in a non-cash manner (e.g.: original receipt, or, if paid electronically, a document showing that the electronic payment was confirmed). Such proof is not required if the payment was made from the accounts held with the Bank and the Bank specialist has exported the payment document from the system.",
  "Other documents upon the Bank’s request"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>special_conditions — VALIDATED</strong></div>

```json
[
  "Option 1: Partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act for the real estate specified by the Developer, or for a longer period, at the Developer's choice",
  "Option 2: Partial or full payment of the down payment by the Developer (Minimum 10%, paid from the funds received under the interest-free target loan agreement signed between the Developer and the Borrower, subject to repayment before completion certificate/handover act)",
  "Option 3: Partial or full payment of the down payment by the Developer and partial or full subsidy of the interest rate by the Developer until receipt of the certificate of completion/signing of the handover act"
]
```
