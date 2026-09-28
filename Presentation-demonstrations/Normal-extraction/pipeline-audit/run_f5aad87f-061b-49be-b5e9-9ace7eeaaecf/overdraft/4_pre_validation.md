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
null
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>category — VALIDATED</strong></div>

```json
"overdraft"
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>purpose — VALIDATED</strong></div>

```json
[
  "Payments",
  "cash withdrawal"
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>loan_amount — CONTRACT-ADAPTED — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "other",
        "operator": null,
        "value": "Credit limit for loans issued under the scoring system"
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
        "dimension": "other",
        "operator": null,
        "value": "Credit limit for loans issued beyond the scoring system"
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
        "dimension": "other",
        "operator": null,
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
        "dimension": "other",
        "value": "Credit limit for loans issued under the scoring system"
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
        "dimension": "other",
        "value": "Credit limit for loans issued beyond the scoring system"
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
        "value": "Minimum and maximum total credit limit for the card"
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
        "dimension": "card_tier",
        "operator": null,
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      },
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 21.0,
      "rate_type": "unknown"
    }
  },
  {
    "conditions": [
      {
        "dimension": "card_tier",
        "operator": null,
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      },
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 20.0,
      "rate_type": "unknown"
    }
  },
  {
    "conditions": [
      {
        "dimension": "other",
        "operator": null,
        "value": "scoring-based loans or loans to workers of specific industries"
      },
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21.0,
      "min": 15.0,
      "rate_type": "unknown"
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
      "rate_type": "unknown"
    },
    "conditions": [
      {
        "dimension": "card_tier",
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      },
      {
        "dimension": "currency",
        "value": "AMD"
      }
    ]
  },
  {
    "value": {
      "basis": "annual",
      "formula": null,
      "max": null,
      "min": 20.0,
      "rate_type": "unknown"
    },
    "conditions": [
      {
        "dimension": "card_tier",
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      },
      {
        "dimension": "currency",
        "value": "AMD"
      }
    ]
  },
  {
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21.0,
      "min": 15.0,
      "rate_type": "unknown"
    },
    "conditions": [
      {
        "dimension": "other",
        "value": "scoring-based loans or loans to workers of specific industries"
      },
      {
        "dimension": "currency",
        "value": "AMD"
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
        "dimension": "card_tier",
        "operator": null,
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      },
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
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
        "dimension": "card_tier",
        "operator": null,
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      },
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
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
        "dimension": "other",
        "operator": null,
        "value": "scoring-based loans or loans to workers of specific industries"
      },
      {
        "dimension": "currency",
        "operator": null,
        "value": "AMD"
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
        "dimension": "card_tier",
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      },
      {
        "dimension": "currency",
        "value": "AMD"
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
        "dimension": "card_tier",
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      },
      {
        "dimension": "currency",
        "value": "AMD"
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
        "dimension": "other",
        "value": "scoring-based loans or loans to workers of specific industries"
      },
      {
        "dimension": "currency",
        "value": "AMD"
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
    "amount": 0,
    "conditions": [
      {
        "dimension": "channel",
        "value": "online"
      }
    ],
    "currency": "AMD",
    "description": "Online application fee",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": 5000,
    "conditions": [],
    "currency": "AMD",
    "description": "Increase of credit limit of card",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": 0,
    "conditions": [],
    "currency": "AMD",
    "description": "Early repayment fee",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": null,
    "conditions": [],
    "currency": null,
    "description": "Late payment fines and penalties",
    "rate_pct": 0.13,
    "scope": "product"
  },
  {
    "amount": 30000,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the overdraft/line of credit account/card",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 10000,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the loan repayment date",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": null,
    "conditions": [],
    "currency": "AMD",
    "description": "Modification of the condition subsequent for the loan (minimum AMD 10,000)",
    "rate_pct": 0.05,
    "scope": "general_loan_service"
  },
  {
    "amount": 50000,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the borrower/co-borrower/guarantor",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 50000,
    "conditions": [],
    "currency": "AMD",
    "description": "Release/substitution of the collateral",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 15000,
    "conditions": [],
    "currency": "AMD",
    "description": "Collateral-related change (including change of the collateral owner)",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": null,
    "conditions": [],
    "currency": "AMD",
    "description": "Revision/modification of another loan term not specified in this document (including interest rate revision, minimum AMD 10,000)",
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
      "description": "3% of utilized amount as shown in the account statement, or AMD 5,000, whichever is greater, plus accrued interest on a monthly basis; utilized amounts are repaid at the end of the term",
      "method": "monthly minimum payment plus accrued interest"
    }
  }
]
```

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>eligibility — VALIDATED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia",
  "Aged 18-65 years old (provided that the borrower's age at the time of expiry of the loan agreement will not have exceeded 65, otherwise a co-borrower or guarantor is required)",
  "Meets creditworthiness criteria approved under the internal regulations of the Bank"
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
        "value": "client/co-borrower/guarantor"
      }
    ],
    "value": {
      "max_age": 65,
      "measured_at": "at the time of expiry of the loan agreement",
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
  "Overdraft is issued by debit cards, without a grace period.",
  "Interest accrues only on used amounts.",
  "Loan is disbursed in non-cash form by crediting the amount to the card account.",
  "If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%.",
  "If creditworthiness ratios deviate from the ratios approved by internal regulations of the Bank, applicable interest rate is increased by 0.25%.",
  "In case of other deviations, interest rate may be increased by 0.25%.",
  "Consumers are allowed to cancel the credit agreement within 7 business days following execution (cooling-off period)."
]
```

---

## overdraft:documents_and_details: documents_and_details

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>required_documents — VALIDATED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "channel",
        "operator": "eq",
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
        "operator": "eq",
        "value": "online"
      }
    ],
    "value": {
      "name": "Public Services Number (PSN) / social card",
      "requirement": "required"
    }
  },
  {
    "conditions": [],
    "value": {
      "name": "Loan application",
      "requirement": "required"
    }
  },
  {
    "conditions": [],
    "value": {
      "name": "ID (original)",
      "requirement": "required"
    }
  },
  {
    "conditions": [],
    "value": {
      "name": "Proof of employment and/or other income",
      "requirement": "required"
    }
  },
  {
    "conditions": [],
    "value": {
      "name": "Other documents as the bank's specialist may request",
      "requirement": "upon_request"
    }
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
"debit card / card account"
```

---

## overdraft:terms_and_eligibility__repair_fees: terms_and_eligibility_repair

<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;margin-top:1em;"><strong>fees — VALIDATED</strong></div>

```json
[
  {
    "amount": 0,
    "conditions": [
      {
        "dimension": "channel",
        "value": "online"
      }
    ],
    "currency": "AMD",
    "description": "Online application fee",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": 5000,
    "conditions": [],
    "currency": "AMD",
    "description": "Increase of credit limit of card",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": 0,
    "conditions": [],
    "currency": "AMD",
    "description": "Early repayment fee",
    "rate_pct": null,
    "scope": "product"
  },
  {
    "amount": null,
    "conditions": [],
    "currency": null,
    "description": "Late payment fines and penalties",
    "rate_pct": 0.13,
    "scope": "product"
  },
  {
    "amount": 30000,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the overdraft/line of credit account/card",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 10000,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the loan repayment date",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": null,
    "conditions": [],
    "currency": "AMD",
    "description": "Modification of the condition subsequent for the loan (minimum AMD 10,000)",
    "rate_pct": 0.05,
    "scope": "general_loan_service"
  },
  {
    "amount": 50000,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the borrower/co-borrower/guarantor",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 50000,
    "conditions": [],
    "currency": "AMD",
    "description": "Release/substitution of the collateral",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": 15000,
    "conditions": [],
    "currency": "AMD",
    "description": "Collateral-related change (including change of the collateral owner)",
    "rate_pct": null,
    "scope": "general_loan_service"
  },
  {
    "amount": null,
    "conditions": [],
    "currency": "AMD",
    "description": "Revision/modification of another loan term not specified in this document (including interest rate revision, minimum AMD 10,000)",
    "rate_pct": 0.1,
    "scope": "general_loan_service"
  }
]
```
