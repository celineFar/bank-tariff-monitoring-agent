# Semantic extraction audit

Product: **consumer_loan**  
Model: **gemini-3.7-flash**

Before Gemini extraction, a deterministic extraction planner groups requested fields (for example rates, fees, or eligibility), ranks accepted evidence by its source-discovery role, keywords, and authority precedence, and enforces configured item/character limits. It does not decide whether a tariff value is true and it does not use an LLM.

**NOT SENT TO SEMANTIC LLM** therefore means the evidence was accepted by source discovery but was not included in any bounded field packet after that deterministic ranking and size/count limiting. It was not rejected as false or irrelevant.

In the document overlays below, only exact quotations cited by successful `found` results are highlighted. Text that was inspected but not cited remains visually unchanged.

## Field outcomes

---

<a id="ex-013"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-013] product_name — EXTRACTED</strong></div>

```json
"Overdraft"
```
---

<a id="ex-008"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-008] formal_terms_names — EXTRACTED</strong></div>

```json
[
  "Information Guide",
  "Retail Lending Terms and Conditions (Overdrafts via Cards not secured with property (unsecured))",
  "SERVICE FEES FOR LOANS TO INDIVIDUALS"
]
```
---


<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>variants — NOT STATED</strong></div>

```json
null
```
Explanation: No distinct named sub-variants are defined under the umbrella product; different card tiers and evaluation methods apply as conditions.

---

<a id="ex-003"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-003] category — EXTRACTED</strong></div>

```json
"overdraft"
```
---

<a id="ex-014"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-014] purpose — EXTRACTED</strong></div>

```json
[
  "Payments",
  "cash withdrawal"
]
```
---

<a id="ex-012"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-012] loan_amount — EXTRACTED</strong></div>

```json
[
  {
    "value": {
      "range": {
        "currency": "AMD",
        "max": 15000000,
        "min": 100000
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
        "max": 10000000,
        "min": 300000
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
      "max_multiple": 4,
      "min_multiple": null,
      "type": "salary_multiple"
    },
    "conditions": [
      {
        "dimension": "program",
        "value": "outside the scoring system"
      },
      {
        "dimension": "other",
        "value": "salary multiple"
      }
    ]
  },
  {
    "value": {
      "range": {
        "currency": "AMD",
        "max": 100000000,
        "min": 100000
      },
      "type": "absolute"
    },
    "conditions": []
  }
]
```
---

<a id="ex-010"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-010] interest_rate — EXTRACTED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "card_tier",
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21,
      "min": 21,
      "rate_type": "fixed"
    }
  },
  {
    "conditions": [
      {
        "dimension": "card_tier",
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 20,
      "min": 20,
      "rate_type": "fixed"
    }
  },
  {
    "conditions": [
      {
        "dimension": "program",
        "value": "scoring-based loans or loans to workers of specific industries"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21,
      "min": 15,
      "rate_type": "fixed"
    }
  }
]
```
---

<a id="ex-005"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-005] effective_rate — EXTRACTED</strong></div>

```json
[
  {
    "conditions": [
      {
        "dimension": "card_tier",
        "value": "Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 23.13,
      "min": 23.13,
      "rate_type": "fixed"
    }
  },
  {
    "conditions": [
      {
        "dimension": "card_tier",
        "value": "Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 21.92,
      "min": 21.92,
      "rate_type": "fixed"
    }
  },
  {
    "conditions": [
      {
        "dimension": "program",
        "value": "scoring-based loans or loans to workers of specific industries"
      }
    ],
    "value": {
      "basis": "annual",
      "formula": null,
      "max": 23.13,
      "min": 16.06,
      "rate_type": "fixed"
    }
  }
]
```
---

<a id="ex-020"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-020] term — EXTRACTED</strong></div>

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

<a id="ex-007"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-007] fees — EXTRACTED</strong></div>

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
    "description": "No extra fees when applying online",
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
    "currency": null,
    "description": "Early repayment fee",
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
    "amount": 5000,
    "conditions": [],
    "currency": "AMD",
    "description": "Fee if you fail to pay the minimum installment (for cards where lump-sum applies)",
    "rate_pct": null,
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
    "amount": 50000,
    "conditions": [],
    "currency": "AMD",
    "description": "Change of the borrower/co-borrower/guarantor",
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
    "amount": 10000,
    "conditions": [],
    "currency": "AMD",
    "description": "Modification of the condition subsequent for the loan: 0.05% of the outstanding loan amount, minimum AMD 10,000",
    "rate_pct": 0.05,
    "scope": "general_loan_service"
  },
  {
    "amount": 10000,
    "conditions": [],
    "currency": "AMD",
    "description": "Revision/modification of another loan term not specified in this document (including interest rate revision): 0.1% of the outstanding loan amount, minimum AMD 10,000",
    "rate_pct": 0.1,
    "scope": "general_loan_service"
  }
]
```
---

<a id="ex-015"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-015] repayment — EXTRACTED</strong></div>

```json
[
  {
    "conditions": [],
    "value": {
      "description": "In the case of an overdraft, you should pay the interest accrued as of the payment date and 3% of the used amount, as specified in the account statement for the previous month or AMD 5,000 whichever is greater, on a monthly basis. Utilized amounts are repaid at the end of the term.",
      "method": "Monthly minimum payment (interest + 3% of used amount or AMD 5,000)"
    }
  }
]
```
---

<a id="ex-006"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-006] eligibility — EXTRACTED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia",
  "Aged 18-65 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 65, otherwise a co-borrower or guarantor is required"
]
```
---

<a id="ex-017"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-017] residency_requirements — EXTRACTED</strong></div>

```json
[
  "Citizens and non-citizens of Armenia who are resident in Armenia"
]
```
---

<a id="ex-001"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-001] age_requirements — EXTRACTED</strong></div>

```json
[
  {
    "conditions": [],
    "value": {
      "max_age": 65,
      "measured_at": "at the time of expiry of the loan agreement",
      "min_age": 18
    }
  }
]
```
---

<a id="ex-002"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-002] application_channel — EXTRACTED</strong></div>

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
---

<a id="ex-019"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-019] special_conditions — EXTRACTED</strong></div>

```json
[
  "The loan is provided online, no need to visit the bank if you have an active card issued by Ameriabank",
  "If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%",
  "If the creditworthiness ratios deviate from the ratios approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%",
  "In case of other deviations, the interest rate may be increased by 0.25%",
  "Interest accrues only on used amounts based on a 365-day year starting from the first day of withdrawal"
]
```
---

<a id="ex-016"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-016] required_documents — EXTRACTED</strong></div>

```json
[
  {
    "value": {
      "name": "ID",
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
      "name": "PPSN / social card",
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
        "value": "Standard application"
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
        "value": "Standard application"
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
Explanation: Extracts standard and online document requirements from the terms and conditions.

---

<a id="ex-004"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-004] credit_limit — EXTRACTED</strong></div>

```json
[
  {
    "range": {
      "currency": "AMD",
      "max": 100000000,
      "min": 100000
    },
    "type": "absolute"
  },
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
    "max_multiple": 4,
    "min_multiple": null,
    "type": "salary_multiple"
  }
]
```
Explanation: Credit limit encompasses the overall limits (AMD 100,000-100,000,000), scoring-based limits (AMD 100,000-15,000,000), non-scoring limits (AMD 300,000-10,000,000), and the 4-fold multiplier rule.

---

<a id="ex-009"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-009] grace_period_days — EXTRACTED</strong></div>

```json
0
```
Explanation: The product is stated as issued without a grace period (0 days).

---

<a id="ex-018"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-018] revolving — EXTRACTED</strong></div>

```json
true
```
Explanation: The overdraft operates within the limit of a revolving credit line.

---

<a id="ex-011"></a>
<div style="border-left:5px solid #12b76a;background:#ecfdf3;padding:0.55em 0.8em;"><strong>[EX-011] linked_account_or_card — EXTRACTED</strong></div>

```json
"card"
```
Explanation: The overdraft is issued on debit/payment cards.

## Extraction overlay

### Label index

| Label | Field | Status |
|---|---|---|
| `EX-013` | `product_name` | `found` |
| `EX-008` | `formal_terms_names` | `found` |
| `—` | `variants` | `not_stated` |
| `EX-003` | `category` | `found` |
| `EX-014` | `purpose` | `found` |
| `EX-012` | `loan_amount` | `found` |
| `EX-010` | `interest_rate` | `found` |
| `EX-005` | `effective_rate` | `found` |
| `EX-020` | `term` | `found` |
| `EX-007` | `fees` | `found` |
| `EX-015` | `repayment` | `found` |
| `EX-006` | `eligibility` | `found` |
| `EX-017` | `residency_requirements` | `found` |
| `EX-001` | `age_requirements` | `found` |
| `EX-002` | `application_channel` | `found` |
| `EX-019` | `special_conditions` | `found` |
| `EX-016` | `required_documents` | `found` |
| `EX-004` | `credit_limit` | `found` |
| `EX-009` | `grace_period_days` | `found` |
| `EX-018` | `revolving` | `found` |
| `EX-011` | `linked_account_or_card` | `found` |

---

## Overdraft | Card loan | Apply online

Source: <https://tariff-mirror.demo/overdraft>

## <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Overdraft<sup title="product_name"><a href="#ex-013">EX-013</a></sup></mark>

Money that is always at hand

Apply now

Loan Amount: AMD 100,000 -15 mln ¹

## <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Indefinite term (until requested back)*<sup title="term"><a href="#ex-020">EX-020</a></sup></mark>

Until the cancellation of the loan by the Bank, which may occur in accordance with the agreement, based on the results of the monitoring by the Bank

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">¹ Credit limit for loans issued under the scoring system – AMD 100,000-15 million<sup title="loan_amount"><a href="#ex-012">EX-012</a></sup></mark>

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">¹ Credit limit for loans issued beyond the scoring system – AMD 300,000-10 million<sup title="loan_amount"><a href="#ex-012">EX-012</a></sup></mark>

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">¹ Minimum and maximum total credit limit for the card – AMD 100,000-100 million<sup title="loan_amount"><a href="#ex-012">EX-012</a></sup></mark>

## <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Overdraft<sup title="category"><a href="#ex-003">EX-003</a></sup></mark>

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">We offer the card overdraft. There is no need to deposit cash in your card account beforehand. Just use the loan amount provided by the Bank.<sup title="category, linked_account_or_card"><a href="#ex-003">EX-003</a> <a href="#ex-011">EX-011</a></sup></mark>  
You may use your overdraft both for cash and non-cash payments.

### ADVANTAGES

Free cash withdrawal from Ameriabank ATMs using a code generated by the My Ameria system (in Armenian drams) free of charge

Low cash withdrawal fee for ATMs of both Ameriabank and other banks (as well as abroad)

The interest accrues only on used amounts.

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">There are no extra fees when applying online.<sup title="fees"><a href="#ex-007">EX-007</a></sup></mark>

## Advantages

### Get a response in 1 minute

Submit your loan application online and get the response in 1 minute.

### The loan is provided online, no need to visit the bank

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">You may obtain the loan on your existing Ameriabank card (if any) or on a new card or account, without visiting the Bank ¹<sup title="special_conditions"><a href="#ex-019">EX-019</a></sup></mark>

1 Provided that you meet the requirements of the Bank and follow the defined procedure.

### Safe and Secure

Transactions with Ameriabank&#x27;s cards are safe and secure. We are always at your side to ensure the security of your funds and data.  
For any questions about cards call us at +37410 56 11 11. We are available 24/7.

### Set your own PIN

If you want an easy to remember PIN, set it yourself via ATM. If your PIN has become available to third parties or you suspect so, you can change it for security reasons.

### Manage Your Accounts Without Visiting the Bank

Ameria Online and Mobile banking platforms and our phone banking services enable you to make transfers and payments, including loan payments, check your account and much more.

### USSD service

You may block your card, get information about your account balance, available services, latest operations anytime anywhere via USSD instructions.

## Terms and conditions

- FAQ

- Overdrafts via Cards not secured with property (unsecured)

- Required documents

- Loans service fee

- Useful information

How can I make repayments?

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">In the case of an overdraft, you should pay the interest accrued as of the payment date and 3% of the used amount, as specified in the account statement for the previous month or AMD 5,000 whichever is greater, on a monthly basis.<sup title="repayment"><a href="#ex-015">EX-015</a></sup></mark> <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">The nominal interest rate is calculated on a daily basis for the actual number of calendar days based on a 365-day year and applied to used amounts starting from the first day of withdrawal.<sup title="special_conditions"><a href="#ex-019">EX-019</a></sup></mark>

What is an online loan?

This service allows you to apply online for loans from AMD 100,000 (one hundred thousand) to AMD 15 (fifteen) million or equivalent in another currency (consumer loan, credit facility, or overdraft). No extra fee, collateral, or guarantee is required for online loans. If you have an active card issued by Ameriabank, you may receive the loan online, without visiting the Bank. <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Otherwise, in order to complete the process of executing the loan, you should visit any of Ameriabank’s offices within 7 calendar days upon the submission of the loan application and present your ID specified in the loan application and your PPSN/social card.<sup title="application_channel"><a href="#ex-002">EX-002</a></sup></mark>

How does the bank determine the amount and interest rate of the loan?

Your loan, as well as the amount and interest rate of the loan, are approved based on your creditworthiness criteria.

How much will I pay monthly?

The amount of monthly installments depends on the type of loan, approved amount, interest rate, and maturity period. Note that the decision about the loan approval, as well as the amount and interest rate of the loan, are based on the criteria of your creditworthiness

Can I apply for an online loan if I have outstanding loans at other banks?

Outstanding loans in other banks are not an obstacle. The decision on the provision of the loan, as well as on the amount and interest rate of the loan, is made based on your creditworthiness criteria.

May I obtain a loan without visiting the Bank?

Yes, if you have an active card issued by Ameriabank. Once approved, the loan will be transferred to your account or card. There is no need to visit the Bank.  
If you are not an Ameriabank cardholder, in order to complete the process of executing the loan, you will need to visit any of Ameriabank’s offices within 7 calendar days upon the submission of the loan application and present your ID specified in the loan application and your PPSN/social card.

What documents are required?

To apply for an online loan, you will need to specify your ID and social card/PPSN.

Is a collateral or a guarantee required when submitting an online loan application?

You may apply online only for loans not secured by collateral or guarantee. To apply for a secured loan, you should submit the loan application in the branch.

Is it mandatory to be an Ameriabank client for submitting an online loan application?

No, it is not necessary to be an Ameriabank client when applying for an online loan. After the has been approved, you will just need to visit any of the Bank’s offices in order to complete the process of executing the loan in just a few minutes.

How can I apply for an online loan?

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Click here https://customer.ameriabank.am/signin to fill in the online loan application. Register as a user and enter your personal data, type of loan, requested amount, and currency.<sup title="application_channel"><a href="#ex-002">EX-002</a></sup></mark> Visit https://www.youtube.com/watch?v=cwEiC_GkVxM to view the step-by-step guide on how to fill in the loan application.  
<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">If you fail to pay the minimum installment, the bank will charge a fee in the amount of AMD 5,000.<sup title="fees"><a href="#ex-007">EX-007</a></sup></mark> For credit cards issued after January 2015, late payment penalties, as prescribed by the Retail Lending Terms and Conditions, will be applied instead of a lump-sum fee.

### Overdrafts via Cards not secured with property (unsecured)

| Card type ¹ | Card type ¹ | Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital | Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital | Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital | Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital | Mastercard Gold/VISA Gold, VISA Gold Digital/ Mastercard Gold Digital,Mastercard World/VISA Platinum, VISA Platinum Digital/ Mastercard World Digital, Visa Signature , Visa Signature Digital |
| --- | --- | --- | --- | --- | --- | --- |
| Purpose | Purpose | Payments, cash withdrawal |  |  |  |  |
| Client’s personal details | Eligible age of the client/co-borrower/guarantor | 18-65 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 65, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-65 provided that at the time of expiry of the agreement it will not have exceeded 65.<br>If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age is 18-65 provided that at the time of expiry of agreement it will not have exceeded 65. |  |  |  |  |
| Client’s personal details | Residency | Citizens and non-citizens of Armenia who are resident in Armenia |  |  |  |  |
| Loan terms ³ | Currency | AMD |  |  |  |  |
| Loan terms ³ | Minimum and total maximum credit limits | AMD: 100,000-100,000,000 ² |  |  |  |  |
| Loan terms ³ | Credit limit | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">If the loan application is reviewed outside the scoring system:<br>Maximum amount: AMD 10 million<br>Maximum 4 fold<sup title="loan_amount"><a href="#ex-012">EX-012</a></sup></mark><br>If the loan application is reviewed on the basis of the scoring system:<br>Maximum amount: AMD 15 million |  |  |  |  |
| Loan terms ³ | Increase of credit limit of card | AMD 5,000 |  |  |  |  |
| Loan terms ³ | Term (months) | <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Indefinite term (until requested back): until loan cancellation by the Bank, which may occur in accordance with the agreement, based on the results of the monitoring by the Bank<sup title="term"><a href="#ex-020">EX-020</a></sup></mark> |  |  |  |  |
| Loan terms ³ | Interest rate | AMD: 21% |  | AMD: 20% |  |  |
| Loan terms ³ | Interest rate | If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. |  |  |  |  |
| Loan terms ³ | Interest rate | If the creditworthiness ratios deviate from the ratios approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. |  |  |  |  |
| Loan terms ³ | Interest rate | In case of other deviations, the interest rate may be increased by 0.25%. |  |  |  |  |
| Loan terms ³ | Annual percentage rate (APR) ⁴ | AMD: 23.13 % |  | AMD: 21.92 % |  |  |
| Forms of line of credit/overdraft repayment | Minimum payment required | 3% of utilized amount as shown in the account statement, or AMD 5,000, whichever is greater, plus accrued interest<br>(Not applicable to loans secured by cash/bonds and credit cards issued to Premium and Partner clients) |  |  |  |  |
| Required documents | Required documents | Required documents filed together with the loan application<br>• Loan application<br>• ID (original)<br>Documents required after initial approval<br>• Proof of employment and/or other income<br>• Other documents as the bank&#x27;s specialist may request |  |  |  |  |
| Other amounts payable | Early repayment fee | N/A |  |  |  |  |
| Other amounts payable | Late payment fines and penalties | Fine in the amount of 0.13 % of overdue loan and interest for each day of delay. The interest rate specified in the loan agreement will continue to be applied to overdue loans. |  |  |  |  |
| Other terms | Security | The Bank may request guarantee of individuals and/or companies as security. |  |  |  |  |

> These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.

> Card service and cash withdrawal tariffs are subject to Ameriabank CJSC Card Rates and Fees (11RBD PL 72-56, approved by Management Board Resolution # 02/20/15 dated July 29, 2015) Available at https://ameriabank.am/useful-links

> If the loan application is considered outside the scoring system, the minimum loan limit is AMD 300,000.

> Other terms can be applied for applications for scoring-based loans or loans to workers of specific industries. In particular, the nominal interest rate for AMD denominated loans may be 15% -21%, while the annual percentage rate may be 16.06-23.13% in case of loans in AMD.

> The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors:
- When the borrower selects differentiated or mixed form of loan repayment
- If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank
- If there are other deviations

> This service is available to the clients who don’t have a line of credit/overdraft.

**Row-level citation labels:**

- `t1:row:1`: EX-014 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:2`: EX-001, EX-006 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:3`: EX-017 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:4`: EX-005, EX-010 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:5`: EX-004 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:6`: EX-004 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:7`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:9`: EX-010 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:13`: EX-005 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:14`: EX-015 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:15`: EX-016 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:17`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t1:row:18`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.

Overdrafts via Cards not secured with property (unsecured)

### Required documents

| Column 1 | Column 2 |
| --- | --- |
| Required documents filed together with loan application | • Loan application<br>• ID (original) |
| Documents required after initial approval | • Proof of employment and/or other income<br>• Other documents as the bank&#x27;s specialist may request |

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">In case of submitting a loan application online, only an identity document and public service number / social card is required.<sup title="required_documents"><a href="#ex-016">EX-016</a></sup></mark>

### Loans service fee

| Purpose | Rates and Fees (AMD) |
| --- | --- |
| 1. Term extension for mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000 |
| 2. Granting a grace period for the principal amount of mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000 |
| 3. Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000 |
| 4. Change of the overdraft/line of credit account/card | AMD 30,000 |
| 5. Change of the borrower/co-borrower/guarantor | AMD 50,000 |
| 6. Release/substitution of the collateral | AMD 50,000 |
| 7. Issuing consent for change of a pledged vehicle plate number | AMD 50,000<br>(VAT included) |
| 8. Collateral-related change (including change of the collateral owner) | AMD 15,000 |
| 9. Change of the loan repayment date | AMD 10,000 |
| 10. Provision of loan before submitting to the Bank the document certifying state registration of the security interest | AMD 25,000 (per issue) |
| 11. Issuing other consent not established by this document and not related to the collateral | AMD 10,000<br>(VAT included) |
| 12. Revision/modification of another loan term not specified in this document (including interest rate revision) | 0.1% of the outstanding loan amount, minimum AMD 10,000 |

**Row-level citation labels:**

- `t3:row:3`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t3:row:4`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t3:row:5`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t3:row:9`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.
- `t3:row:12`: EX-007 cites combined row evidence; the exact quote could not be localized to one cell.

Overdraft: without collateral

- Informational summary of unsecured overdraft

- Lending terms for individuals / Card overdrafts

- Be informed when taking a loan

- Loan service fees

- Lending terms for individuals without collateral / Card overdrafts (effective from 23.02.26 to 06.07.26)

---

## Informational summary of unsecured overdraft

Source: <https://tariff-mirror.demo/docs/Overdraft_unsecured_eng.pdf>

Effective date: July 07, 2026 Terms and conditions specified in the Guide may be outdated. For more information, please visit ameriabank.am | 010 56 11 11

## <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Information Guide<sup title="formal_terms_names"><a href="#ex-008">EX-008</a></sup></mark>

### Overdrafts via Cards not secured with property (unsecured)

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">The overdraft issued through payment cards offers you an opportunity to use money within the limit of revolving credit line opened by the Bank, without adding money to the card account.<sup title="revolving"><a href="#ex-018">EX-018</a></sup></mark> The maximum amount of the revolving credit that can be borrowed on card is your credit limit.

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Overdraft is issued by debit cards, without a grace period.<sup title="grace_period_days, linked_account_or_card"><a href="#ex-009">EX-009</a> <a href="#ex-011">EX-011</a></sup></mark> Debit cards may be used both for cash and non-cash transactions and have a low cash withdrawal rate both for Ameriabank ATMs and ATMs of other banks (including abroad).

- <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Other terms related to the interest rate:
- • If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%.
- • If the creditworthiness ratios deviate from the ratios approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%.
- • In case of other deviations, the interest rate may be increased by 0.25%.<sup title="special_conditions"><a href="#ex-019">EX-019</a></sup></mark>

## Loan service fees

The fee is charged if the modification is requested by the client. Where there are several applicable fees for the same modification, the highest fee is charged and only once. Fees are not applicable in case of loans secured by cash, bonds and metal accounts. If the modification implies adding new collateral or involving a new guarantor, no fee is charged.

- Required documents filed together with the loan application:
- • Loan application
- • ID (original)

- Documents required after initial approval:
- • Proof of employment and/or other income
- • Other documents as the Bank specialist may request
- When applying online, only ID and PPSN/social card are required.

Manner of disbursement: Loan is disbursed in non-cash form by crediting the amount to the card account.

## METHOD AND FREQUENCY OF PAYMENTS

<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Repayment: Interest accrued on overdraft is repaid on monthly basis and the utilized amounts are repaid at the of the term. There are no conditions limiting accessibility of loan proceeds. There are no required charges to be paid by the borrower.<sup title="repayment"><a href="#ex-015">EX-015</a></sup></mark>

Loan decision: The Bank reviews the loan application and makes a preliminary decision within 2 business days upon receipt of the application. If approved, the final loan decision is made within no more than 8 (eight) business days upon receipt of the complete set of documents. The Bank informs the client about the decision within 1 business day. The loan is issued to the borrower only after execution of security agreements specified in the agreement. The loan is disbursed within 1 (one) business day after fulfillment of the lending conditions by the borrower. Once the Bank makes a loan decision, if the client confirms his/her intention to receive the loan within 45 calendar days after getting loan approval notice, the process moves to the formalization stage. If the client takes longer than 45 calendar days upon getting loan approval notice to confirm his/her intention to receive the loan, re-approval is needed.

- What may help you to get your loan approved:
- • Established business relationship between the Bank and the client
- • Business reputation
- • Turnover of your funds through Ameriabank accounts
- • Average balance on the accounts with Ameriabank, etc.

- Why your application might be rejected:
- • The information (documents and other data) is not trustworthy or is incomplete.
- • The borrower&#x27;s declared income is not sufficient to repay the obligations.
- • The borrower has bad credit history, overdue and/or classified liabilities (including liabilities to third parties).
- • Failure to meet other requirements of the Bank.

Down payment: N/a for this loan facility

Early repayment: In case of consumer loans, car loans, line of credit or overdraft the client has the right to repay the liabilities

before the due date irrespective of whether or not such provision is included in the loan agreement. Attention! If you fail to pay the minimum installment, the Bank will charge a fee in the amount of AMD 5,000. For credit cards issued after January 2015 late payment penalties prescribed by the Retail Lending Terms and Conditions will be applicable instead of lump-sum fee. Attention! No limitations are set on the repayment of the loan before due date.

Information for the Guarantor: If the Borrower fails to meet his/her loan obligations in a proper manner, the guarantor will take on responsibility of the debt and will have to repay the outstanding loan. The guarantor is entitled to receive reimbursement from the borrower for the repaid debt, i.e. the guarantor may request the borrower to reimburse the amount paid to the lender, the interest and other expenses incurred as a result of taking responsibility instead of the borrower. The lender must warn the guarantor in advance about pending loan repayment, i.e., if the borrower fails to meet his/her obligations in due manner, the guarantor is required to repay the outstanding debt within the period defined in the guarantee agreement after getting the respective notice from the lender. The guarantor’s name may appear in the BAD BORROWER LIST, i.e., if the borrower doesn’t repay his/her obligations, the guarantor’s name may be reported to the Credit Bureau, where the credit history is originated. This may affect the guarantor’s future loan applications.

Statements, references: We will provide to you the statements of your credit accounts through communication channels and at frequency agreed between you and us and/or in accordance with the Armenian laws and regulations. The statements are provided by post, email, Internet-Bank/MyAmeria or in person at any branch of the Bank.

Attention! WHEN YOU APPLY FOR A LOAN, WE WILL PROVIDE YOU AN INDIVIDUAL LEAFLET DETAILING ALL ESSENTIAL TERMS OF YOUR CONSUMER LOAN. Attention! THE LOAN INTEREST RATE MAY NOT EXCEED THE DOUBLE OF THE BANK RATE DECLARED BY THE CENTRAL BANK OF ARMENIA. Attention! LOAN INTEREST IS CALCULATED AT THE NOMINAL INTEREST RATE. THE LATTER SHOWS THE ANNUAL INTEREST ACCRUED AS PERCENTAGE OF THE OUTSTANDING LOAN. THE LOAN INTEREST IS ACCRUED ON THE OUTSTANDING LOAN PRINCIPAL IN THE LOAN CURRENCY DAILY, BASED ON A 365-DAY CALENDAR YEAR. ANNUAL PERCENTAGE RATE SHOWS THE COST OF LOAN IN CASE OF PROPER AND TIMELY PERFORMANCE OF ALL CONTRACTUAL OBLIGATIONS.

Procedure of interest calculation: In case of differentiated repayment method, the amount of monthly loan payment is calculated according to the following formula: R = p / t + p * r % / 365 * d, where R – monthly repayment of the loan, p – amount of loan principal, t – loan term (in months), r – annual interest rate of the loan, d – number of days in a month. In case of annuity, the amount of monthly payment is calculated according to the following formula: R= P x r / (1–1/(1 +r)n), where R – monthly repayment for the loan P – loan principal n – total number of payments during the whole term of loan (number of months) r – monthly interest rate, which is equal to 1/12 of the annual interest rate under the loan agreement at the time of provision of the loan

The amount of monthly payments is rounded to one decimal place. The outstanding loan is calculated according to the following formula: Pt = R x ((1-1/(1+r)n ) / r, where Pt – actual Loan outstanding by the end of the period R – monthly repayment for the loan t – number of repayments due before the end of the loan term (number of months) r – monthly interest rate, which is equal to 1/12 of the annual interest rate under the loan agreement at the time of provision of the loan. APR is calculated by the following formula: A = Σ (Kn / (1+i)^Dn/365) where i – annual percentage rate (APR). A – the amount of the credit (initial amount provided by the lender to the borrower) n – sequence number of payment N – sequence number of the last payment Kn – amount of the nth payment Dn – period between the day of provision of loan and the day of the nth payment, expressed in days i – annual percentage rate, calculable if other input data are known from loan agreement or otherwise

APR Calculation Example: Loan product: consumer loan secured by property Amount: AMD 15,000,000 Fixed interest rate: 17% Term: 60 months Repayment method: annuity (equal installments consisting of a portion of loan and some interest) Lump sum disbursement fee: AMD 75,000 Insurance fee: 0.16% of the outstanding loan principal each year Real estate appraisal fee: AMD 15,000 Fee for the unified statement on real estate encumbrance: AMD 10,300 Pledge agreement notarization fee: AMD 13,000 Security interest filing fee: AMD 26,000 Loan disbursement day: September 16, 2014 First payment day: October 11, 2014 Annual percentage rate (APR): 19.14 % The annual percentage rate is calculated on the basis of the underlying components, is indicative and can change during the Agreement term due to early repayment of loan by the borrower or change of the components included in its calculation.

Initial loan principal: AMD 1,000,000 Annual interest rate: 20% Term: 36 months Daily interest will make: 1,000,000*20/100/365=548 AMD The amount of monthly payments in case of annuity: AMD 37,163.6.

INFORMATION ON FACTORS AFFECTING CREDIT HISTORY AND CREDIT SCORE: Credit History is the information on the customer’s financial obligations, which shows the customer’s debt, payments, as well as other data related to the customer’s obligations or their performance. The credit score is the quantified measure of the customer’s borrowing capacity and creditworthiness determined based on the study of the customer’s credit history. Based on the customer consent, Ameriabank CJSC (the “Bank”) makes inquiries on the financial obligations of the customer, whether current or past, for the customer to undertake financial obligations to the Bank, act as a guarantor to secure third party obligations, to consider lending to the customer on the latter’s initiative. The number of inquiries for the purposes specified in this clause may have an influence (including negative one) on the customer’s credit score. The Bank uses internally developed scoring methodology for lending to customers. The factors affecting the credit score include FICO score, loan service quality, availability of late payments in the credit history, duration of payment delays, debt burden, income, ratio of loan obligations to income. More detailed information may be found at the following links: www.abcfinance.am and www.acra.am.

- To improve your credit history and/or credit score we recommend you to:
- • Fully repay any overdue obligations you may have had in the past,
- • Make sure you don’t have any late payments, even 1-day delays, in relation to your current obligations,
- • Reduce the number of loans you have at a time repaying them either in whole or in part,
- • Reduce the balance of your outstanding loans,
- • Limit the number and amount of provided guarantees,
- • Make sure that any overdue amounts guaranteed by you are fully repaid.

Attention! IF YOU FAIL TO PERFORM YOUR PAYMENT OBLIGATIONS WHEN DUE OR DO NOT PERFORM THEM PROPERLY, OVERDUE AMOUNTS SHALL BEAR FINES AND PENALTIES AS DEFINED BY AGREEMENT, AND THE INFORMATION ABOUT YOUR OVERDUE LIABILITIES WILL BE REPORTED TO CREDIT BUREAU WITHIN 3 BUSINESS DAYS. YOU

HAVE THE RIGHT TO OBTAIN YOUR CREDIT HISTORY FROM THE CREDIT BUREAU ONCE A YEAR, AT NO COST. When you repay your overdue debt, the payment will be made in the following order: • Fines and penalties • Interest • Principal YOUR BAD CREDIT HISTORY MAY AFFECT YOUR FUTURE LOAN APPLICATIONS.

Change of interest rates. The bank is entitled to change the interest rates depending on the volatility of interest rates on funds borrowed and/or allocated by the bank on financial market, and/or occurrence of preconditions for change of annual interest rate applied to the loan. The Bank shall inform the borrower of any change in the nominal interest rate made at the sole discretion of the Bank in advance, within the term specified in the agreement (at least 7 days in advance), via the channels specified in the agreement, which shall serve as a basis for applying the new terms from the date specified in the notice. If the borrower doesn’t consent to the new interest rate, the borrower may terminate the respective agreement before the maturity date, repaying the obligations to the Bank under such agreement in full. Consumers are allowed to cancel the credit agreement at their own discretion, for no particular reason, within 7 business days following its execution unless a longer period is stipulated therein (cooling-off period). In such cases, consumers are required to pay the interest accrued at the effective annual rate under the credit agreement. The consumer will not be required to pay any other reimbursement in relation to the cancellation of the credit agreement.

### Overdraft Details

| Loan type | Overdraft (on debit cards) |
| --- | --- |
| Who may apply | Citizens and non-citizens of Armenia who are resident in Armenia and are aged 18-65 |
| Loan purpose | Payments, cash withdrawal |
| Manner of disbursement | Loan is disbursed in non-cash form by crediting the amount to the card account. |
| Currency | AMD |
| Minimum and maximum total credit limits | AMD: 100,000-100,000,0001 |
| Credit limit If the loan application is reviewed outside the scoring system: | Maximum amount: AMD 10 million Maximum 4 fold |

> 1 If the loan application is considered outside the scoring system, the minimum loan limit is AMD 300,000.

**Row-level citation labels:**

- `document:3472fe8d3966:page:1:table:0:row:0`: EX-006 cites combined row evidence; the exact quote could not be localized to one cell.

### Overdraft Details Continued

| Feature | Details |
| --- | --- |
| Credit limit If the loan application is reviewed based on the scoring system: | Maximum amount: AMD 15 million |
| Increase of credit limit of card | AMD 5,000 |
| Term (months) | Indefinite term (until requested back): until loan cancellation by the Bank, which may occur in accordance with the agreement, based on the results of the monitoring by the Bank |
| Card type2 | Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/ Master Card Standard Digital (Column 1) / Master Card Gold/VISA Gold, Master Card World/VISA Platinum, Visa Signature, VISA Gold Digital/ Master Card Gold Digital, VISA Platinum Digital/ Master Card World Digital / Visa Signature Digital (Column 2) |
| Interest rate3 | AMD: 21% (Column 1) / AMD: 20% (Column 2) |
| Annual percentage rate (APR)4 | AMD: 23.13 % (Column 1) / AMD: 21.92 % (Column 2) |
| Minimum payment required | 3 % of utilized amount as shown in the account statement, or AMD 5,000, whichever is greater, plus accrued interest (Not applicable to loans secured by cash/bonds and credit cards issued to Premium and Partner clients) |
| Early repayment fee | N/A |

> 2 Card service and cash withdrawal tariffs are subject to Ameriabank CJSC Card Rates and Fees (11RBD PL 72-56, approved by Management Board Resolution # 02/20/15 dated July 29, 2015) Available at https://ameriabank.am/useful-links

> 3 Other terms can be applied for applications for scoring-based loans or loans to workers of specific industries. In particular, the nominal interest rate for AMD denominated loans may be 15% - 21%, while the annual percentage rate may be 16.06-23.13% in case of loans in AMD.

> 4 The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors: - When the borrower selects differentiated or mixed form of loan repayment - If the creditworthiness criteria deviate from those approved by the internal regulations of the Bank - If there are other deviations

### Late Payment and Security

| Category | Details |
| --- | --- |
| Late payment fines and penalties | Fine in the amount of 0.13 % of overdue loan and interest for each day of delay. The interest rate specified in the loan agreement will continue to be applied to overdue loans. |
| Security | The Bank may request guarantee of individuals and/or companies as security. |

### Loan service fees

| Purpose | Fee |
| --- | --- |
| Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000 |
| Change of the overdraft/line of credit account/card | AMD 30,000 |
| Revision/modification of another loan term not specified in this document | 0.1% of the outstanding loan amount, minimum AMD 10,000 |
| Change of the loan repayment date | AMD 10,000 |

### Provision of statements, information and copies of documents

| Service | Rates &amp; Fees |
| --- | --- |
| 1.1. Provision of up to 6 month-old account statements, copies of account statements or other documents kept in electronic form | Free |
| 1.2. Provision of from 6 months to 1 year old account statement, copies of account statement or other document kept in electronic form5 | AMD 3,000, VAT included per annual statement per account and each electronically stored document, VAT included |
| 1.3. Provision of more than 1 year-old account statements, copies of account statements or other documents kept in electronic form1 | AMD 5,000, VAT included per annual statement per account and each electronically stored document, VAT included |
| 1.4. Provision of more than 1 year-old account statement or other electronic document, by emailing to the customer without a stamp1 | AMD 3,000, VAT included per annual statement per account and each electronically stored document, VAT included |
| 1.5. Provision of references |  |
| 1.5.1. Provision of a reference on a Bank template, if ordered on the Bank premises6 | AMD 3,000, VAT included |
| 1.5.2. Provision of a reference in a form different from a Bank template, if ordered on the Bank premises | AMD 5,000, VAT included |
| 1.5.3. Provision of a reference on a Bank template, if ordered online by Internet/ Mobile Banking/on the | AMD 1,000, VAT included |

> 5 The fee is not charged for provision of home loan statements (i.e. loans for purchase/renovation/construction of residential real estate).

> 6 The template contains information about turnover with respect to the service and the balance. The Bank has templates for account, card, savings account, deposit, securities (when the Bank acts as a custodian of the customer’s securities) references.

### Statements and References Continued

| Service | Rates &amp; Fees |
| --- | --- |
| Bank’s website7 |  |
| 1.5.4. Provision of a reference in a form different from a Bank template, if ordered online by Internet/ Mobile Banking/on the Bank’s website8 | AMD 3,000, VAT included |
| 1.6. Delivery of account statement |  |
| 1.6.1. By electronic means | Free |
| 1.6.2. By post within Armenia9 | AMD 1,000 monthly, VAT included |
| 1.6.3. By post outside Armenia10 | As per postal service bills |

> 7 Requests for references should be submitted at least one banking day in advance.

> 8 Requests for references should be submitted at least three banking days in advance.

> 9 The fee is charged for the month when the statement was received, until the last business day of the month following such month.

> 10 The delivery is provided by regular mail.

---

## Lending terms for individuals / Card overdrafts

Source: <https://tariff-mirror.demo/docs/unsecured_overdraft_eng.pdf>

## <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">Retail Lending Terms and Conditions (Overdrafts via Cards not secured with property (unsecured))*<sup title="formal_terms_names"><a href="#ex-008">EX-008</a></sup></mark>

*These terms have been previously known as Retail Lending Terms and Conditions under code 11RBD PL 72-03-01. Some of the Bank documents may contain references to these terms and conditions under the former name and code.

1 Card service and cash withdrawal tariffs are subject to Ameriabank CJSC Card Rates and Fees (11RBD PL 72-56, approved by Management Board Resolution # 02/20/15 dated July 29, 2015) Available at https://ameriabank.am/useful-links

2 If the loan application is considered outside the scoring system, the minimum loan limit is AMD 300,000.

3 Other terms can be applied for applications for scoring-based loans or loans to workers of specific industries. In particular, the nominal interest rate for AMD denominated loans may be 15% -21%, while the annual percentage rate may be 16.06-23.13% in case of loans in AMD.

4 The annual percentage rate (APR) may differ from the above specified values if there is any or a few of the following factors: - When the borrower selects differentiated or mixed form of loan repayment - If there are deviations from the creditworthiness criteria approved under the internal regulations of the Bank - If there are other deviations

5 This service is available to the clients who don’t have a line of credit/overdraft.

### Document Information

| Entity | Code | Edition | Effective Date |
| --- | --- | --- | --- |
| AMERIABANK CJSC | 11RBD PL 72-03-96 | 69 | July 07, 2026 |

### Card Types

| Card type |
| --- |
| Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/Master Card Standard Digital |
| Mastercard Gold/VISA Gold, VISA Gold Digital/Mastercard Gold Digital,Mastercard World/VISA Platinum , VISA Platinum Digital/Mastercard World Digital, Visa Signature , Visa Signature Digital |

### Loan Terms

| Purpose | Feature | Arca Classic, Master Card Standard/VISA Classic, VISA Classic Digital/Master Card Standard Digital | Mastercard Gold/VISA Gold, VISA Gold Digital/Mastercard Gold Digital,Mastercard World/VISA Platinum , VISA Platinum Digital/Mastercard World Digital, Visa Signature , Visa Signature Digital |
| --- | --- | --- | --- |
| Client’s personal details | Eligible age of the client/co-borrower/guarantor | 18-65 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 65, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-65 provided that at the time of expiry of the agreement it will not have exceeded 65. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age is 18-65 provided that at the time of expiry of agreement it will not have exceeded 65. | 18-65 years old, provided that the borrower’s age at the time of expiry of the loan agreement will not have exceeded 65, otherwise a co-borrower or guarantor is required. The eligible age of the co-borrower or guarantor is 18-65 provided that at the time of expiry of the agreement it will not have exceeded 65. If involvement of a co-borrower or guarantor is a required condition under loan terms (except where co-borrowers or guarantors possess at least 70% of income included in OTI calculation), the eligible age is 18-65 provided that at the time of expiry of agreement it will not have exceeded 65. |
| Client’s personal details | Residency | Citizens and non-citizens of Armenia who are resident in Armenia | Citizens and non-citizens of Armenia who are resident in Armenia |
| Loan terms | Currency | AMD | AMD |
| Loan terms | Minimum and total maximum credit limits | AMD: 100,000-100,000,000 | AMD: 100,000-100,000,000 |
| Loan terms | Credit limit | If the loan application is reviewed outside the scoring system: Maximum amount: AMD 10 million; Maximum 4 fold. If the loan application is reviewed on the basis of the scoring system: Maximum amount: AMD 15 million | If the loan application is reviewed outside the scoring system: Maximum amount: AMD 10 million; Maximum 4 fold. If the loan application is reviewed on the basis of the scoring system: Maximum amount: AMD 15 million |
| Loan terms | Increase of credit limit of card | Minimum amount: AMD 5,000 | Minimum amount: AMD 5,000 |
| Loan terms | Term (months) | Indefinite term (until requested back): until loan cancellation by the Bank, which may occur in accordance with the agreement, based on the results of the monitoring by the Bank | Indefinite term (until requested back): until loan cancellation by the Bank, which may occur in accordance with the agreement, based on the results of the monitoring by the Bank |
| Loan terms | Annual percentage rate (APR) | AMD: 21% | AMD: 21.92% |
| Loan terms | Interest rate | AMD: 20% | AMD: 23.13% |
| Loan terms | Forms of line of credit/overdraft repayment | If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. In case of other deviations, the interest rate may be increased by 0.25%. If the creditworthiness ratios deviate from the ratios approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. | If repayment schedule is differentiated or mixed, the applicable interest rate is increased by 0.5%. In case of other deviations, the interest rate may be increased by 0.25%. If the creditworthiness ratios deviate from the ratios approved by the internal regulations of the Bank, the applicable interest rate is increased by 0.25%. |
| Loan terms | Minimum payment required | 3% of utilized amount as shown in the account statement, or AMD 5,000, whichever is greater, plus accrued interest (Not applicable to loans secured by cash/bonds and credit cards issued to Premium and Partner clients) | 3% of utilized amount as shown in the account statement, or AMD 5,000, whichever is greater, plus accrued interest (Not applicable to loans secured by cash/bonds and credit cards issued to Premium and Partner clients) |
| Loan terms | Early repayment fee | N/A | N/A |
| Loan terms | Late payment fines and penalties | Fine in the amount of 0.13 % of overdue loan and interest for each day of delay. The interest rate specified in the loan agreement will continue to be applied to overdue loans. | Fine in the amount of 0.13 % of overdue loan and interest for each day of delay. The interest rate specified in the loan agreement will continue to be applied to overdue loans. |
| Loan terms | Other terms | Security: The Bank may request guarantee of individuals and/or companies as security. | Security: The Bank may request guarantee of individuals and/or companies as security. |

### Required Documents

| Required documents |
| --- |
| Required documents filed together with the loan application: Loan application, ID (original). Documents required after initial approval: Proof of employment and/or other income, Other documents as the bank&#x27;s specialist may request |

---

## Loan service fees

Source: <https://tariff-mirror.demo/docs/Loan_tariffs_eng.pdf>

## <mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">SERVICE FEES FOR LOANS TO INDIVIDUALS<sup title="formal_terms_names"><a href="#ex-008">EX-008</a></sup></mark>

Approved by Management Board resolution # 01/68/18 dated May 14, 2018.

Current edition approved by resolution # .... dated ... , effective from July 14, 2026.

### General Provisions

- 1. Under this document, “loan” means the loan types envisaged by the Retail Lending Terms and Conditions of the Bank.
- 2. The changes specified in this document are made based on the client’s application, subject to its approval in accordance with the Bank’s internal regulations.
- 3. These fees apply to changes initiated by the client. The changes made in order to ensure the client’s performance of the condition subsequent established by the Bank are not considered as the client’s initiative.

- 4. The fees specified in this document do not apply to the automatically approved consumer loans secured by deposit, bonds and metal accounts in gold.
- 5. Where several fees are applicable due to change of several terms of the same loan as per the application submitted by the client, only the highest of them shall be charged, once.
- 6. To apply a fee(s) established by this document for modification of the same term for several loans, the total outstanding amount of those loans is considered.
- 7. The fee amount is rounded to AMD 1,000 in favor of the client and shall be no less than the minimum amount of the respective fee (if established by this document).
- 8. Where a new collateral or guarantor is added due to modification of a loan term(s), no fee is charged.
- 9. In case of lines of credit and overdrafts, the outstanding loan amount means the bigger of the used amount of the line of credit/overdraft and the line of credit/overdraft limit currently available to the client.

### SERVICE FEES FOR LOANS TO INDIVIDUALS

| Purpose | Rates and Fees (AMD) |
| --- | --- |
| 1. Term extension for mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000 |
| 2. Granting a grace period for the principal amount of mortgage/investment loans | 0.1% of the outstanding loan amount, minimum AMD 50,000 |
| 3. Modification of the condition subsequent for the loan | 0.05% of the outstanding loan amount, minimum AMD 10,000 |
| 4. Change of the overdraft/line of credit account/card | AMD 30,000 |
| 5. Change of the borrower/co-borrower/guarantor | AMD 50,000 |
| 6. Release/substitution of the collateral | AMD 50,000 |
| 7. Issuing consent for change of a pledged vehicle plate number | AMD 50,000 (VAT included) |
| 8. Collateral-related change (including change of the collateral owner) | AMD 15,000 |
| 9. Change of the loan repayment date | AMD 10,000 |
| 10. Provision of loan before submitting to the Bank the document certifying state registration of the security interest | AMD 25,000 (per issue) |
| 11. Issuing other consent not established by this document and not related to the collateral | AMD 10,000 (VAT included) |
| 12. Revision/modification of another loan term not specified in this document (including interest rate revision) | 0.1% of the outstanding loan amount, minimum AMD 10,000 |

## Planner audit

- `ev_189d3937ac9aa6a3f1bf9381` / `b17` — **EXTRACTED: product_name**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_87056c6d4f16a2fa6b4fcf6f` / `b18` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_d37915ae523450eb107f7f35` / `b19` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c3a8cc1d62592023ebc23cd0` / `b20` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c7bfd7426e3bf47f445a6c60` / `b22` — **EXTRACTED: term**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_42f010d7f7fcc9fb12a5295f` / `b23` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_55bcefb83083e0615a6c7a9c` / `b24` — **EXTRACTED: loan_amount**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_dc93ae10ff2f1f9dd224a38c` / `b25` — **EXTRACTED: loan_amount**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8c806cb69e349006f9027951` / `b26` — **EXTRACTED: loan_amount**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_2dd1c18e4b651446bb567807` / `b27` — **EXTRACTED: category**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_652aed8a07f18908ed974557` / `b28` — **EXTRACTED: category, linked_account_or_card**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_206a01dc494334c1c9bd0c9f` / `b29` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_27218632f304ef3adc4c1295` / `b30` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_7de648d8407b7efc1e49dfee` / `b31` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_24753254904b71fb57510c4c` / `b32` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_05562e28266c490f60b9cbb8` / `b33` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_fbcdc270b9175b7985b0d54f` / `b34` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_00b0f7e4337df965f82dd722` / `b35` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_77d8592d816ad4715b8598ad` / `b36` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_18ff9fe0325a49c919716726` / `b37` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c9a8c7cf5208861958c8e1c4` / `b38` — **EXTRACTED: special_conditions**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c7c98de558c64e00c0558498` / `b39` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_cc61f9083c6a55858e63ca2c` / `b40` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_5859eee7fad8329e8c3155aa` / `b41` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_df5b5eb88e7b02ed7868e5db` / `b42` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_a691c0aa8ae194081f54f229` / `b43` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_402cd455dcbe446365b05686` / `b44` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_67e791c12716b635641671d4` / `b45` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3acc77f777935278b4e74d3d` / `b47` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9dbd7323c6f8cfede2ee5c43` / `b48` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_0a00e716655ae96c678b37b7` / `b50` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4b863f0cdf2c1c5a9cb47e8f` / `b51` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_e651b9751cbe8a7072dd03f5` / `b52` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_868c966ebd6919c031342d00` / `b53` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_34f87ce3c626db0f61db46b4` / `b54` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8bea4798458d211ec371c837` / `b55` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_1d52721e7480d92f1b4c2eeb` / `b57` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4c883022ff7c7cbca201526c` / `b58` — **EXTRACTED: repayment, special_conditions**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_a64174f1b99ba142cf64ed9f` / `b59` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6c3814274b73d283a6771b2e` / `b60` — **EXTRACTED: application_channel**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_30da79e6656ef7cdadbb8b4b` / `b61` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_ffe6f8d0f223cc085fe66013` / `b62` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_05558d319d6b84f6fe17bc1e` / `b63` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9a38d5cdf14517ca9ec7d3ff` / `b64` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_0e3f703b1e4b5f49a71fcddd` / `b65` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_10204c5d70e3c5e57c1938d2` / `b66` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_28a5618b3337dba17c766fec` / `b67` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_ea7579614bc9b0008e5856e0` / `b68` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9c7f7c75712e33ea2503b5e3` / `b69` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c506f48ef672dbd72aee82cc` / `b70` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_f22c03fe1871ab21e54061f8` / `b71` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_d0f662a126c71103e9489462` / `b72` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_e9317caa1ef34f88bc634094` / `b73` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8870e15ad7f82bb197d6ccc0` / `b74` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_46a1911904be153d6fb24317` / `b75` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_1ea34285937fe73a1ffa19f6` / `b76` — **EXTRACTED: application_channel, fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_f568c18c5b7ce9c0980f917e` / `t1:row:1` — **EXTRACTED: purpose**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_49f60567e67dc0cd9bd75506` / `t1:row:2` — **EXTRACTED: age_requirements, eligibility**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_bc9fac588f439592a0e745db` / `t1:row:3` — **EXTRACTED: residency_requirements**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_aeb4dd2e0eb26c6ecc2dcf38` / `t1:row:4` — **EXTRACTED: effective_rate, interest_rate**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_5a55b464f996d802e083c4eb` / `t1:row:5` — **EXTRACTED: credit_limit**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_63e7acdab47981b1f1e88a40` / `t1:row:6` — **EXTRACTED: credit_limit, loan_amount**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_27c0efdc2d922e221e26e451` / `t1:row:7` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_aa21193fec72f3d3993aa646` / `t1:row:8` — **EXTRACTED: term**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_7de516852b865ee511e71138` / `t1:row:9` — **EXTRACTED: interest_rate**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_32195c8de3438174b1157793` / `t1:row:10` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_144bac3fe656ed5b3bb78bca` / `t1:row:11` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_808c0bc432ed519b518fbd70` / `t1:row:12` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9d825972a6868f2914d9579b` / `t1:row:13` — **EXTRACTED: effective_rate**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8ff1a5911bc7359ad8866077` / `t1:row:14` — **EXTRACTED: repayment**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_2693ed91b569659043254a55` / `t1:row:15` — **EXTRACTED: required_documents**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_42cdd4936086db86183b1e91` / `t1:row:17` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b85bb7386ead29fcb1967b60` / `t1:row:18` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4762c2d678e2d0e6f9158c90` / `t1:row:19` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_39be05a8497f53ad6b995893` / `t1:note:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b239e5f2f90024ab8eddf15f` / `t1:note:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_fa79f597a3e49c004decd8a6` / `t1:note:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_e189a736df32c94e8cb4acd5` / `t1:note:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_a076e44acfe7587b5eb2ded1` / `t1:note:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_29c5212ef47afdba0ae5e913` / `t1:note:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_5199a4dbd3c0ddb1467673eb` / `b78` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_7dbdd2ae1cc51e0f9fd4dbf5` / `t2:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_700a01ae3cbc957347589d7b` / `t2:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_874185abdf6881ea2ce956ea` / `b80` — **EXTRACTED: required_documents**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6d218f727ed98b6318b5c40d` / `t3:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_bdce48e16b299345d0dad011` / `t3:row:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_ef5dc3a4ae7a86dc76751f6f` / `t3:row:3` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c1cb5fc2a9b602ebca1dad63` / `t3:row:4` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_75e01f916e789415bae0efcb` / `t3:row:5` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b9741c081a387634b29d7ba3` / `t3:row:6` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3ae368a6dd3421d8829fd0c2` / `t3:row:7` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3b5769ec1a2c1f4dd49560b0` / `t3:row:8` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4834b2e6128a06b8c32a4f0c` / `t3:row:9` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6128c4321256294b64f09724` / `t3:row:10` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c2a92151546b1c0528dbb88d` / `t3:row:11` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_12cdc9156e92e8cae5b061d1` / `t3:row:12` — **EXTRACTED: fees**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_a6cad3c488d6e6c658247223` / `b82` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_d686fe178acc746202e17d09` / `b83` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_33bd869510dc64149d4850c5` / `b84` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_fa12b534545ec6892d3e70db` / `b86` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_7d0e69c96c24bc553c7fbd75` / `b87` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_d6f2335390cbc13ebefb098f` / `b93` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_148d5f579b16b59a046c743b` / `document:3472fe8d3966:page:1:block:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_25cd61917da88198ccdb4b5e` / `document:3472fe8d3966:page:1:block:1` — **EXTRACTED: formal_terms_names**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_5a47b31986edfbf04012b03a` / `document:3472fe8d3966:page:1:block:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3c3de9001b01477d902d46b3` / `document:3472fe8d3966:page:1:block:3` — **EXTRACTED: revolving**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3978eacdfffa8a22ac08536f` / `document:3472fe8d3966:page:1:block:4` — **EXTRACTED: grace_period_days, linked_account_or_card**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3aec7f1bee1aacb8eb6676e1` / `document:3472fe8d3966:page:3:block:0` — **EXTRACTED: special_conditions**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_02834706e57ed90e2151084e` / `document:3472fe8d3966:page:3:block:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3841713cc585cd5c85d42301` / `document:3472fe8d3966:page:3:block:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6c8a1b1c4246cb9fc2b250c2` / `document:3472fe8d3966:page:3:block:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8256935c5f16bcbf652ae75d` / `document:3472fe8d3966:page:4:block:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_a524ab4a5f4223dc456b8f75` / `document:3472fe8d3966:page:4:block:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_7e33953987ec445a29b0441c` / `document:3472fe8d3966:page:4:block:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3258e67d9d651cb94bf8541a` / `document:3472fe8d3966:page:4:block:3` — **EXTRACTED: repayment**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_e1aee304ea0bdc393ebe2365` / `document:3472fe8d3966:page:4:block:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_00ca5fa8399ebeae2bc13973` / `document:3472fe8d3966:page:4:block:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8b1ddbc3f5dedd229a64ad92` / `document:3472fe8d3966:page:4:block:6` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_2484c0110fd3529fc73be657` / `document:3472fe8d3966:page:4:block:7` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_88aaf1c84ea6e6fe97e21c84` / `document:3472fe8d3966:page:4:block:8` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_e2f4fa0ffe479677e905e2d8` / `document:3472fe8d3966:page:5:block:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_5c013fc7fa843063c57ec3a1` / `document:3472fe8d3966:page:5:block:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_fb6ffe563594dcf6f20e8c3c` / `document:3472fe8d3966:page:5:block:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9903765c3ac4132c7db2239c` / `document:3472fe8d3966:page:6:block:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8e9990b40f6984b8c77f8880` / `document:3472fe8d3966:page:6:block:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6944bac03917c870a7b2c720` / `document:3472fe8d3966:page:7:block:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9ee6bdda20f69faaca154b3a` / `document:3472fe8d3966:page:7:block:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_e705110bc0be608655d1b5ce` / `document:3472fe8d3966:page:8:block:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3e082d40274259921c15b013` / `document:3472fe8d3966:page:8:block:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6bdb5e680038d5d64062e75e` / `document:3472fe8d3966:page:8:block:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_92a1a26eb477bf60db52a6a5` / `document:3472fe8d3966:page:8:block:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_840668f2d860e6d1ab547ccb` / `document:3472fe8d3966:page:9:block:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_88e0c4c4dfadf4bf643b9476` / `document:3472fe8d3966:page:9:block:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3dac31e0641fdde4864cee91` / `document:3472fe8d3966:page:1:table:0:row:0` — **EXTRACTED: eligibility**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8396c9cafb7d015e23d185bd` / `document:3472fe8d3966:page:1:table:0:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_1231a90ce48448967edb6702` / `document:3472fe8d3966:page:1:table:0:row:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_82ef97f5c64cb5e05ae66381` / `document:3472fe8d3966:page:1:table:0:row:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_1e5dc176d5f2f7c42c914537` / `document:3472fe8d3966:page:1:table:0:row:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_7d48ff3662954aed8566a1ed` / `document:3472fe8d3966:page:1:table:0:row:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_0ef411a70c31aef1dd48aa36` / `document:3472fe8d3966:page:1:table:0:note:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c5d2f471ac147d9c0beb07f6` / `document:3472fe8d3966:page:2:table:0:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_0bb622e809f49c1da036e5e6` / `document:3472fe8d3966:page:2:table:0:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_47cb05be243c0b0a46018b9f` / `document:3472fe8d3966:page:2:table:0:row:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_de6c8dc166bf9a99ed244c2a` / `document:3472fe8d3966:page:2:table:0:row:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4dd5a21039a158fe3c7d2610` / `document:3472fe8d3966:page:2:table:0:row:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6994bd9305fcaf81e7e41e79` / `document:3472fe8d3966:page:2:table:0:row:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b076132e7f4bd752eb0f65a3` / `document:3472fe8d3966:page:2:table:0:row:6` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_5ffe7bb91191b42a5069752f` / `document:3472fe8d3966:page:2:table:0:row:7` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_43567e5301f18452329501a7` / `document:3472fe8d3966:page:2:table:0:note:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b8bc21177ca2984814d115b1` / `document:3472fe8d3966:page:2:table:0:note:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_0f12fe228c1a30ccf8b0f647` / `document:3472fe8d3966:page:2:table:0:note:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_189ff8362d18d06a69e704a8` / `document:3472fe8d3966:page:3:table:0:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_d5a44c37acc3d1c53dbe92a0` / `document:3472fe8d3966:page:3:table:0:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6c59db864f41b01e02c51749` / `document:3472fe8d3966:page:3:table:1:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_69d14537a236341a8f32a964` / `document:3472fe8d3966:page:3:table:1:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_e36c0dcc26b017a651cea2b0` / `document:3472fe8d3966:page:3:table:1:row:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_7b1be5286067bdbbbf7c1212` / `document:3472fe8d3966:page:3:table:1:row:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_d97717f816d570c1a299fb11` / `document:3472fe8d3966:page:5:table:0:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c6f0917f3d6d48871d482114` / `document:3472fe8d3966:page:5:table:0:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_15f6c4e8fb6f1985acd1a8f7` / `document:3472fe8d3966:page:5:table:0:row:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_f54da3876399628d56b773f1` / `document:3472fe8d3966:page:5:table:0:row:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_a64847985e9763ba7b9c4c22` / `document:3472fe8d3966:page:5:table:0:row:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_37568a8af1381835b8a6b643` / `document:3472fe8d3966:page:5:table:0:row:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_849081918bc151c3d1adea20` / `document:3472fe8d3966:page:5:table:0:row:6` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_1dd42eea75c44c7a1f861661` / `document:3472fe8d3966:page:5:table:0:row:7` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_ba860eba7a79131c13a77551` / `document:3472fe8d3966:page:5:table:0:note:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9b29ae1fe3d1103fcbb8dd3e` / `document:3472fe8d3966:page:5:table:0:note:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_2fa00f840c3f9133a56bec8f` / `document:3472fe8d3966:page:6:table:0:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3d2ab466897fd8fab8d22d27` / `document:3472fe8d3966:page:6:table:0:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_2f6d1fba783b239c920166da` / `document:3472fe8d3966:page:6:table:0:row:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_ac522d1f417895839ccc45e5` / `document:3472fe8d3966:page:6:table:0:row:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4f26886cd2c8010bed97041f` / `document:3472fe8d3966:page:6:table:0:row:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_61678b432c3979efb21736bd` / `document:3472fe8d3966:page:6:table:0:row:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_ac17e7ae27901062491873da` / `document:3472fe8d3966:page:6:table:0:note:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b9a8b10254a55afc390ef749` / `document:3472fe8d3966:page:6:table:0:note:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6babc60d473fe75c7209887a` / `document:3472fe8d3966:page:6:table:0:note:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_330a4da499b4d08f94180c1c` / `document:3472fe8d3966:page:6:table:0:note:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4054b5d197cfaba55c4a1b73` / `document:64566c7add62:page:1:block:0` — **EXTRACTED: formal_terms_names**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b0fa4e682ef754b6a5187ab4` / `document:64566c7add62:page:1:note:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b18e11b9f5250852685adf70` / `document:64566c7add62:page:1:note:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3d83fbb5d6e325ed049fc3c0` / `document:64566c7add62:page:1:note:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c47c4dce21c92b0687b3f434` / `document:64566c7add62:page:1:note:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3782e6494a74c80f9715465e` / `document:64566c7add62:page:1:note:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_24e8f9296192f1bc324ac5c5` / `document:64566c7add62:page:1:note:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_79e66eb4bf730e54f0c0b6e1` / `document:64566c7add62:page:1:table:0:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_7525f1c7172846bd2642e004` / `document:64566c7add62:page:1:table:1:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_2235daf7a2d34a7132406ee2` / `document:64566c7add62:page:1:table:1:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b0e9f802918a5041beeb7e15` / `document:64566c7add62:page:1:table:2:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_59174a609b11f9b155f86860` / `document:64566c7add62:page:1:table:2:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6995cb34febaa73fe4fe70bb` / `document:64566c7add62:page:1:table:2:row:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9bcc5a9e1036e498d2fd7190` / `document:64566c7add62:page:1:table:2:row:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_289c660480bb7ba70340f7f1` / `document:64566c7add62:page:1:table:2:row:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_0d006d837fb18e52871562fd` / `document:64566c7add62:page:1:table:2:row:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4f8bc77e154de9de28df8a6b` / `document:64566c7add62:page:1:table:2:row:6` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_432e07edad4fdc9caa8f78ba` / `document:64566c7add62:page:1:table:2:row:7` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_805ce4a20bab90d2385612e1` / `document:64566c7add62:page:1:table:2:row:8` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_b7ddc1b649d6f38b4a2718b4` / `document:64566c7add62:page:1:table:2:row:9` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_811664768a5f4d199fcbe615` / `document:64566c7add62:page:1:table:2:row:10` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_717c2b308e2ad510ddccb669` / `document:64566c7add62:page:1:table:2:row:11` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_2d54effd3aef0ee4718a021e` / `document:64566c7add62:page:1:table:2:row:12` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c5274fa7222af69490b55104` / `document:64566c7add62:page:1:table:2:row:13` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_f73dfbd232c8e2bec181166c` / `document:64566c7add62:page:1:table:3:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_0e144e95ef831dbd35f5d762` / `document:7b405d165676:page:1:block:0` — **EXTRACTED: formal_terms_names**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_62f173fa2583f4939ff7c46c` / `document:7b405d165676:page:1:block:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_306403c57018a626497c165d` / `document:7b405d165676:page:1:block:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_5d57da585678dabf16a27657` / `document:7b405d165676:page:1:block:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6c783e41e81fb8ff9049b489` / `document:7b405d165676:page:1:block:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_8f31480aa1d0ed7ba56a6d4a` / `document:7b405d165676:page:2:block:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_16dece3bdd88ebbad36e7bda` / `document:7b405d165676:page:1:table:0:row:0` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_a5c76e808a413973f7af3b96` / `document:7b405d165676:page:1:table:0:row:1` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_544704c2dcec22effa056176` / `document:7b405d165676:page:1:table:0:row:2` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_9216c2d824bc02781c1a9de6` / `document:7b405d165676:page:1:table:0:row:3` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_bd671d1f81cc7f637a931739` / `document:7b405d165676:page:1:table:0:row:4` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_4efdaa0d783904a166d25982` / `document:7b405d165676:page:1:table:0:row:5` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_c8d203795490e5061e105714` / `document:7b405d165676:page:1:table:0:row:6` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3d95bd46a1d64a66009b51d8` / `document:7b405d165676:page:1:table:0:row:7` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_27eb86cda48fcfc64f223418` / `document:7b405d165676:page:1:table:0:row:8` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_d696ace90d92adf793af07a8` / `document:7b405d165676:page:1:table:0:row:9` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_6011e89c650e068359f682a0` / `document:7b405d165676:page:1:table:0:row:10` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
- `ev_3241e325b34bf0f5c1b9344a` / `document:7b405d165676:page:1:table:0:row:11` — **SENT, NOT CITED**; packets: documents_and_details, identity_and_core, terms_and_eligibility
