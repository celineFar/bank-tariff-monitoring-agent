# Pre-validation semantic extraction audit

This preserves what Gemini produced before canonical field validation. Green passed validation, red failed and entered human review, and orange is valid but semantically ambiguous or conflicting.

---

## extract_000: identity

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>product_name — VALIDATED</strong></div>

```json
"Installment financing for product purchase and service provision"
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>category — VALIDATED</strong></div>

```json
"consumer_loan"
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>purpose — VALIDATED</strong></div>

```json
[
  "Purchasing products",
  "Service provision",
  "Acquisition of solar systems"
]
```

---

## extract_001: core_financial

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>loan_amount — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 6000000.0,
        "min": 50000.0
      },
      "type": "absolute"
    }
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>interest_rate — VALIDATED</strong></div>

```json
[
  {
    "conditions": [],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21.5,
      "min": 0.0,
      "rate_type": "fixed"
    }
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>effective_rate — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "purchase of goods and services"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 24.0,
      "min": 0.0,
      "rate_type": "unknown"
    }
  },
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "purchase of solar panels and water heaters"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 17.0,
      "min": 0.0,
      "rate_type": "unknown"
    }
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>term — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "application_channel",
        "value": "seller's premises"
      },
      {
        "dimension": "purpose",
        "value": "purchasing products"
      }
    ],
    "value": {
      "max_months": 60,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "application_channel",
        "value": "online remote consumer finance system"
      },
      {
        "dimension": "purpose",
        "value": "purchasing products"
      }
    ],
    "value": {
      "max_months": 36,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "service provision"
      }
    ],
    "value": {
      "max_months": 24,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "acquisition of solar systems"
      }
    ],
    "value": {
      "max_months": 120,
      "min_months": 6
    }
  }
]
```

---

## extract_002: fees_and_repayment

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>fees — VALIDATED</strong></div>

```json
[
  {
    "description": "Monthly account service fee: As specified in the Cooperation Agreement between the Company and the Bank",
    "scope": "product",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": []
  },
  {
    "description": "Disbursement fee (lump-sum)/down payment: As specified in the Cooperation Agreement between the Company and the Bank",
    "scope": "product",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": []
  },
  {
    "description": "Fee for the service, payment of interest and other charges: in case of payment via the Bank’s remote banking system (no fee charged)",
    "scope": "product",
    "amount": 0.0,
    "currency": null,
    "rate_pct": null,
    "conditions": [
      {
        "dimension": "payment_channel",
        "operator": "eq",
        "value": "Bank's remote banking system"
      }
    ]
  },
  {
    "description": "Fee for the service, payment of interest and other charges: if paid via payment terminals and ATMs owned by the Bank (according to the Terms and Conditions of Transactions through Payment Terminals 11RBD/12CIB PL 72-16)",
    "scope": "general_loan_service",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": [
      {
        "dimension": "payment_channel",
        "operator": "eq",
        "value": "Payment terminals and ATMs owned by the Bank"
      }
    ]
  },
  {
    "description": "Fee for the service, payment of interest and other charges: if paid via payment terminals owned by other companies (according to the tariffs of the respective company)",
    "scope": "general_loan_service",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": [
      {
        "dimension": "payment_channel",
        "operator": "eq",
        "value": "Payment terminals owned by other companies"
      }
    ]
  },
  {
    "description": "Fee for the service, payment of interest and other charges: if paid at the Bank’s branches (according to Ameriabank CJSC Tariffs for Individuals 11RBD PL 72-01-01)",
    "scope": "general_loan_service",
    "amount": null,
    "currency": null,
    "rate_pct": null,
    "conditions": [
      {
        "dimension": "payment_channel",
        "operator": "eq",
        "value": "Bank branches"
      }
    ]
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>repayment — VALIDATED</strong></div>

```json
[
  "Annuity (equal monthly installments consisting of a portion of debt and a portion of interest) where interest rate is applied",
  "Equal monthly installments schedule (equal monthly installments consisting of a portion of debt and a portion of fee) where a fee is applied"
]
```

---

## extract_003: eligibility_and_documents

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>eligibility — VALIDATED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia",
  "Eligible age: From 20 to 66 years inclusive"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>residency_requirements — VALIDATED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia",
  "Actually resident in the Republic of Armenia for 183 and more days during the tax year (Tax Code, Article 25)"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>age_requirements — VALIDATED</strong></div>

```json
"From 20 to 66 years inclusive"
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>application_channel — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>special_conditions — VALIDATED</strong></div>

```json
null
```

---

## extract_004: required_documents

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>required_documents — VALIDATED</strong></div>

```json
[
  "Identity document",
  "Public services number (social card)",
  "Ownership certificate of the property (for solar panels/systems, upon request)",
  "Electricity and gas bills for the most recent 6 months (for solar panels/systems, upon request)"
]
```

---

## extract_005: product_details

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>collateral — VALIDATED</strong></div>

```json
[
  "The purchased item serves as a collateral."
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>income_verification_required — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>creditworthiness_assessment_required — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>credit_limit — VALIDATED</strong></div>

```json
[
  {
    "type": "absolute",
    "range": {
      "min": 200000,
      "max": 6000000,
      "currency": "AMD"
    }
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>grace_period_days — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>revolving — VALIDATED</strong></div>

```json
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>linked_account_or_card — VALIDATED</strong></div>

```json
null
```

---

## extract_001__repair_loan_amount: core_financial_repair

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>loan_amount — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 6000000.0,
        "min": 50000.0
      },
      "type": "absolute"
    }
  }
]
```

---

## extract_001__repair_term: core_financial_repair

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>term — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "application_channel",
        "value": "seller's premises"
      },
      {
        "dimension": "purpose",
        "value": "purchasing products"
      }
    ],
    "value": {
      "max_months": 60,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "application_channel",
        "value": "online remote consumer finance system"
      },
      {
        "dimension": "purpose",
        "value": "purchasing products"
      }
    ],
    "value": {
      "max_months": 36,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "service provision"
      }
    ],
    "value": {
      "max_months": 24,
      "min_months": 6
    }
  },
  {
    "conditions": [
      {
        "dimension": "purpose",
        "value": "acquisition of solar systems"
      }
    ],
    "value": {
      "max_months": 120,
      "min_months": 6
    }
  }
]
```
