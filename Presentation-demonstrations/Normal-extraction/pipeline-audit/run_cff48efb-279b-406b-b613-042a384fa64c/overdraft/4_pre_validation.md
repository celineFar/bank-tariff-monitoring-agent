# Pre-validation semantic extraction audit

This preserves what Gemini produced before canonical field validation. Green passed validation, red failed and entered human review, and orange is valid but semantically ambiguous or conflicting.

---

## overdraft:identity_and_core: identity_and_core

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>product_name — VALIDATED</strong></div>

```json
"Overdraft"
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>formal_terms_names — VALIDATED</strong></div>

```json
[
  "Retail Lending Terms and Conditions (Overdrafts via Cards not secured with property (unsecured))",
  "Information Guide Overdrafts via Cards not secured with property (unsecured)",
  "SERVICE FEES FOR LOANS TO INDIVIDUALS"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>variants — VALIDATED</strong></div>

```json
[]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>category — VALIDATED</strong></div>

```json
"overdraft"
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>purpose — VALIDATED</strong></div>

```json
[
  "Payments",
  "Cash withdrawal"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>loan_amount — CONTRACT-ADAPTED — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "program",
        "operator": null,
        "value": "scoring system"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 15000000.0,
        "min": 100000.0
      },
      "type": "absolute"
    }
  },
  {
    "conditions": [
      {
        "dimension": "program",
        "operator": null,
        "value": "outside the scoring system"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 10000000.0,
        "min": 300000.0
      },
      "type": "absolute"
    }
  },
  {
    "conditions": [
      {
        "dimension": "program",
        "operator": null,
        "value": "outside the scoring system"
      }
    ],
    "value": {
      "max_multiple": 4.0,
      "min_multiple": null,
      "type": "salary_multiple"
    }
  },
  {
    "conditions": [
      {
        "dimension": "other",
        "operator": null,
        "value": "total card credit limit"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 100000000.0,
        "min": 100000.0
      },
      "type": "absolute"
    }
  }
]
```

Deterministic contract adaptation:

- loan_amount: adapted model JSON to the field's domain contract

```json
[
  {
    "value": {
      "range": {
        "currency": "AMD",
        "max": 15000000.0,
        "min": 100000.0
      },
      "type": "absolute"
    },
    "conditions": [
      {
        "dimension": "program",
        "value": "scoring system"
      }
    ]
  },
  {
    "value": {
      "range": {
        "currency": "AMD",
        "max": 10000000.0,
        "min": 300000.0
      },
      "type": "absolute"
    },
    "conditions": [
      {
        "dimension": "program",
        "value": "outside the scoring system"
      }
    ]
  },
  {
    "value": {
      "max_multiple": 4.0,
      "min_multiple": null,
      "type": "salary_multiple"
    },
    "conditions": [
      {
        "dimension": "program",
        "value": "outside the scoring system"
      }
    ]
  },
  {
    "value": {
      "range": {
        "currency": "AMD",
        "max": 100000000.0,
        "min": 100000.0
      },
      "type": "absolute"
    },
    "conditions": [
      {
        "dimension": "other",
        "value": "total card credit limit"
      }
    ]
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>interest_rate — CONTRACT-ADAPTED — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      },
      {
        "dimension": "card_tier",
        "operator": null,
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 21.0,
      "rate_type": "fixed"
    }
  },
  {
    "conditions": [
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      },
      {
        "dimension": "card_tier",
        "operator": null,
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 20.0,
      "rate_type": "fixed"
    }
  },
  {
    "conditions": [
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      },
      {
        "dimension": "other",
        "operator": null,
        "value": "scoring-based loans or loans to workers of specific industries"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21.0,
      "min": 15.0,
      "rate_type": "fixed"
    }
  }
]
```

Deterministic contract adaptation:

- interest_rate: adapted model JSON to the field's domain contract

```json
[
  {
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 21.0,
      "rate_type": "fixed"
    },
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      },
      {
        "dimension": "card_tier",
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      }
    ]
  },
  {
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 20.0,
      "rate_type": "fixed"
    },
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      },
      {
        "dimension": "card_tier",
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      }
    ]
  },
  {
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21.0,
      "min": 15.0,
      "rate_type": "fixed"
    },
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      },
      {
        "dimension": "other",
        "value": "scoring-based loans or loans to workers of specific industries"
      }
    ]
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>effective_rate — CONTRACT-ADAPTED — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      },
      {
        "dimension": "card_tier",
        "operator": null,
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 23.13,
      "rate_type": "unknown"
    }
  },
  {
    "conditions": [
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      },
      {
        "dimension": "card_tier",
        "operator": null,
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 21.92,
      "rate_type": "unknown"
    }
  },
  {
    "conditions": [
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      },
      {
        "dimension": "other",
        "operator": null,
        "value": "scoring-based loans or loans to workers of specific industries"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 23.13,
      "min": 16.06,
      "rate_type": "unknown"
    }
  }
]
```

Deterministic contract adaptation:

- effective_rate: adapted model JSON to the field's domain contract

```json
[
  {
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 23.13,
      "rate_type": "unknown"
    },
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      },
      {
        "dimension": "card_tier",
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      }
    ]
  },
  {
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 21.92,
      "rate_type": "unknown"
    },
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      },
      {
        "dimension": "card_tier",
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      }
    ]
  },
  {
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 23.13,
      "min": 16.06,
      "rate_type": "unknown"
    },
    "conditions": [
      {
        "dimension": "currency",
        "value": "AMD"
      },
      {
        "dimension": "other",
        "value": "scoring-based loans or loans to workers of specific industries"
      }
    ]
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>term — VALIDATED</strong></div>

```json
[
  {
    "conditions": [],
    "value": {
      "end_condition": "on_demand",
      "indefinite": true,
      "max_months": null,
      "min_months": null
    }
  }
]
```

---

## overdraft:terms_and_eligibility: terms_and_eligibility

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>fees — VALIDATED</strong></div>

```json
[
  {
    "amount": 5000.0,
    "conditions": [],
    "currency": "AMD",
    "description": "Increase of credit limit of card",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": null,
    "conditions": [],
    "currency": null,
    "description": "Early repayment fee: N/A",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": null,
    "conditions": [],
    "currency": null,
    "description": "Late payment fines and penalties: Fine in the amount of 0.13 % of overdue loan and interest for each day of delay",
    "rate_pct": 0.13,
    "scope": "product"
  },
  {
    "amount": 5000.0,
    "conditions": [],
    "currency": "AMD",
    "description": "Fee if you fail to pay the minimum installment",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": 30000.0,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the overdraft/line of credit account/card",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 10000.0,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the loan repayment date",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 50000.0,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the borrower/co-borrower/guarantor",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 10000.0,
    "conditions": [],
    "currency": "AMD",
    "description": "Modification of the condition subsequent for the loan (0.05% of the outstanding loan amount, minimum AMD 10,000)",
    "rate_pct": 0.05,
    "scope": "general_loan_service"
  },
  {
    "amount": 10000.0,
    "conditions": [],
    "currency": "AMD",
    "description": "Revision/modification of another loan term not specified in this document (including interest rate revision) (0.1% of the outstanding loan amount, minimum AMD 10,000)",
    "rate_pct": 0.1,
    "scope": "general_loan_service"
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>repayment — VALIDATED</strong></div>

```json
[
  {
    "conditions": [],
    "value": {
      "description": "3% of utilized amount as shown in the account statement, or AMD 5,000, whichever is greater, plus accrued interest on a monthly basis. The nominal interest rate is calculated on a daily basis for the actual number of calendar days based on a 365-day year and applied to used amounts starting from the first day of withdrawal.",
      "method": "minimum monthly payment plus interest"
    }
  },
  {
    "conditions": [],
    "value": {
      "description": "In case of differentiated repayment method, the amount of monthly loan payment is calculated according to the formula: R = p / t + p * r % / 365 * d. Applicable interest rate is increased by 0.5%.",
      "method": "differentiated"
    }
  },
  {
    "conditions": [],
    "value": {
      "description": "In case of mixed repayment schedule, applicable interest rate is increased by 0.5%.",
      "method": "mixed"
    }
  },
  {
    "conditions": [],
    "value": {
      "description": "In case of annuity, the amount of monthly payment is calculated according to the formula: R= P x r / (1–1/(1 +r)n).",
      "method": "annuity"
    }
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>eligibility — VALIDATED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia",
  "Aged 18-65 years old, provided that the borrower's age at the time of expiry of the loan agreement will not have exceeded 65, otherwise a co-borrower or guarantor is required"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>residency_requirements — VALIDATED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>age_requirements — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "borrower_type",
        "value": "client"
      }
    ],
    "value": {
      "max_age": 65,
      "measured_at": "at the time of expiry of the loan agreement",
      "min_age": 18
    }
  },
  {
    "conditions": [
      {
        "dimension": "borrower_type",
        "value": "co-borrower or guarantor"
      }
    ],
    "value": {
      "max_age": 65,
      "measured_at": "at the time of expiry of the agreement",
      "min_age": 18
    }
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>application_channel — VALIDATED</strong></div>

```json
[
  {
    "conditions": [],
    "value": {
      "available": true,
      "channel": "online"
    }
  },
  {
    "conditions": [],
    "value": {
      "available": true,
      "channel": "branch"
    }
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>special_conditions — VALIDATED</strong></div>

```json
[
  "If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%.",
  "If the creditworthiness ratios deviate from the ratios approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.",
  "In case of other deviations, the interest rate may be increased by 0.25%.",
  "Overdraft is issued by debit cards, without a grace period.",
  "The loan interest rate may not exceed the double of the bank rate declared by the Central Bank of Armenia.",
  "Consumers are allowed to cancel the credit agreement at their own discretion, for no particular reason, within 7 business days following its execution (cooling-off period)."
]
```

---

## overdraft:documents_and_details: documents_and_details

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>required_documents — CONTRACT-ADAPTED — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "channel",
        "operator": null,
        "value": "online"
      }
    ],
    "value": {
      "name": "Identity document (ID)",
      "requirement": "required"
    }
  },
  {
    "conditions": [
      {
        "dimension": "channel",
        "operator": null,
        "value": "online"
      }
    ],
    "value": {
      "name": "Public service number / social card (PPSN)",
      "requirement": "required"
    }
  },
  {
    "conditions": [
      {
        "dimension": "other",
        "operator": null,
        "value": "Filed together with loan application"
      }
    ],
    "value": {
      "name": "Loan application",
      "requirement": "required"
    }
  },
  {
    "conditions": [
      {
        "dimension": "other",
        "operator": null,
        "value": "Filed together with loan application"
      }
    ],
    "value": {
      "name": "ID (original)",
      "requirement": "required"
    }
  },
  {
    "conditions": [
      {
        "dimension": "other",
        "operator": null,
        "value": "After initial approval"
      }
    ],
    "value": {
      "name": "Proof of employment and/or other income",
      "requirement": "required"
    }
  },
  {
    "conditions": [
      {
        "dimension": "other",
        "operator": null,
        "value": "After initial approval"
      }
    ],
    "value": {
      "name": "Other documents as the bank's specialist may request",
      "requirement": "upon_request"
    }
  }
]
```

Deterministic contract adaptation:

- required_documents: adapted model JSON to the field's domain contract

```json
[
  {
    "value": {
      "name": "Identity document (ID)",
      "requirement": "required"
    },
    "conditions": [
      {
        "dimension": "channel",
        "value": "online"
      }
    ]
  },
  {
    "value": {
      "name": "Public service number / social card (PPSN)",
      "requirement": "required"
    },
    "conditions": [
      {
        "dimension": "channel",
        "value": "online"
      }
    ]
  },
  {
    "value": {
      "name": "Loan application",
      "requirement": "required"
    },
    "conditions": [
      {
        "dimension": "other",
        "value": "Filed together with loan application"
      }
    ]
  },
  {
    "value": {
      "name": "ID (original)",
      "requirement": "required"
    },
    "conditions": [
      {
        "dimension": "other",
        "value": "Filed together with loan application"
      }
    ]
  },
  {
    "value": {
      "name": "Proof of employment and/or other income",
      "requirement": "required"
    },
    "conditions": [
      {
        "dimension": "other",
        "value": "After initial approval"
      }
    ]
  },
  {
    "value": {
      "name": "Other documents as the bank's specialist may request",
      "requirement": "upon_request"
    },
    "conditions": [
      {
        "dimension": "other",
        "value": "After initial approval"
      }
    ]
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>credit_limit — VALIDATED</strong></div>

```json
[
  {
    "range": {
      "currency": "AMD",
      "max": 15000000,
      "min": 100000
    },
    "type": "absolute"
  },
  {
    "range": {
      "currency": "AMD",
      "max": 10000000,
      "min": 300000
    },
    "type": "absolute"
  },
  {
    "range": {
      "currency": "AMD",
      "max": 100000000,
      "min": 100000
    },
    "type": "absolute"
  },
  {
    "max_multiple": 4,
    "min_multiple": null,
    "type": "salary_multiple"
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>grace_period_days — VALIDATED</strong></div>

```json
0
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>revolving — VALIDATED</strong></div>

```json
true
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>linked_account_or_card — VALIDATED</strong></div>

```json
"debit card"
```

---

## overdraft:identity_and_core__repair_loan_amount: identity_and_core_repair

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>loan_amount — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "program",
        "value": "scoring system"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 15000000.0,
        "min": 100000.0
      },
      "type": "absolute"
    }
  },
  {
    "conditions": [
      {
        "dimension": "program",
        "value": "outside the scoring system"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 10000000.0,
        "min": 300000.0
      },
      "type": "absolute"
    }
  },
  {
    "conditions": [
      {
        "dimension": "program",
        "value": "outside the scoring system"
      },
      {
        "dimension": "other",
        "value": "Maximum 4 fold"
      }
    ],
    "value": {
      "max_multiple": 4.0,
      "min_multiple": null,
      "type": "salary_multiple"
    }
  },
  {
    "conditions": [
      {
        "dimension": "other",
        "value": "Minimum and maximum total credit limit for the card"
      }
    ],
    "value": {
      "range": {
        "currency": "AMD",
        "max": 100000000.0,
        "min": 100000.0
      },
      "type": "absolute"
    }
  }
]
```
