# Ameriabank Loan Extraction System

## Scope

This component extracts structured loan-product information from the following Ameriabank pages:

### Consumer lending
- https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans
- https://ameriabank.am/en/personal/loans/consumer-loans/overdraft
- https://ameriabank.am/en/personal/loans/consumer-loans/credit-line
- https://ameriabank.am/en/personal/loans/consumer-loan/online-consumer-finance

### Mortgages
- https://ameriabank.am/en/personal/loans/mortgage/online
- https://ameriabank.am/en/personal/loans/mortgage/primary
- https://ameriabank.am/en/campaigns/mortgage-loan-for-diaspora
- https://ameriabank.am/en/personal/loans/mortgage/secondary-market
- https://ameriabank.am/en/personal/loans/mortgage/commercial-mortgage
- https://ameriabank.am/en/personal/loans/mortgage/express-loan
- https://ameriabank.am/en/personal/loans/mortgage/no-income-verification
- https://ameriabank.am/en/personal/loans/mortgage/renovation-mortgage
- https://ameriabank.am/en/personal/loans/mortgage/construction-mortgage

The pages use different layouts and may expose important information through rendered HTML, accordions, tables, linked documents, or network responses.

The system therefore separates:

1. acquisition;
2. structural normalization;
3. source discovery;
4. semantic extraction;
5. claim generation;
6. verification and repair.

The LLM is used only where semantic interpretation is required. Fetching, parsing, normalization, validation, and most verification signals remain deterministic Python.

---

# 1. Acquisition Tool

## Purpose

The acquisition tool retrieves all potentially useful official source material for one loan-product URL.

It should not decide what a loan field means. Its responsibility is only to collect the source faithfully and make it reproducible.

## Responsibilities

The acquisition tool should:

- request the original page;
- launch Playwright when JavaScript rendering is required;
- wait until useful page content has loaded;
- expand accordions and collapsible sections;
- inspect tabs;
- click content-revealing controls such as `Terms and conditions`, `See more`, or similar controls when safe;
- collect the final rendered DOM;
- capture useful XHR/fetch responses;
- collect links;
- detect downloadable documents such as PDFs;
- download relevant linked documents;
- preserve tables and visible text;
- save source metadata and raw artifacts;
- compute hashes so that later runs can determine whether the source changed.

The tool should not perform semantic extraction.

## Output

```python
class PageArtifact(BaseModel):
    url: str
    canonical_url: str

    raw_html: str | None
    rendered_html: str | None
    markdown: str | None

    blocks: list["ContentBlock"]
    tables: list["TableArtifact"]
    links: list["LinkArtifact"]

    downloadable_documents: list["DocumentArtifact"]
    network_payloads: list["NetworkPayload"]

    retrieved_at: datetime
    content_hash: str
```

Example:

```python
PageArtifact(
    url=...,
    rendered_html=...,
    markdown=...,
    blocks=[...],
    tables=[...],
    links=[...],
    downloadable_documents=[...],
    network_payloads=[...],
)
```

## Artifact provenance

Every extracted source fragment should retain enough information to find it again:

```python
class SourceLocator(BaseModel):
    source_url: str
    source_type: Literal["page", "pdf", "api", "linked_document"]

    block_id: str | None = None
    css_selector: str | None = None
    xpath: str | None = None
    pdf_page: int | None = None
    json_path: str | None = None
```

This provenance is required later for evidence verification.

---

# 2. Loan Schema

## Design decision

Do not use one completely flat model for every product.

Use:

- a shared `LoanProduct` model for fields common across products;
- subtype-specific detail models for mortgage, overdraft, credit-line, and standard consumer-loan concepts;
- discriminated unions where the same business concept can have multiple representations.

This avoids two problems:

1. forcing every loan type into fields that do not apply;
2. losing important product-specific semantics.

The schema should be derived from the information that is actually present across the target pages and official linked terms, then evolved when new product semantics are discovered.

The schema is a contract, not a guess. Unknown or unrepresented concepts should be surfaced during extraction rather than silently discarded.

---

## Shared primitives

```python
class MoneyRange(BaseModel):
    min: Decimal | None = None
    max: Decimal | None = None
    currency: Literal["AMD", "USD", "EUR"] | None = None


class Rate(BaseModel):
    min: Decimal | None = None
    max: Decimal | None = None

    rate_type: Literal[
        "fixed",
        "variable",
        "mixed",
        "unknown",
    ]

    basis: Literal["annual", "monthly"] = "annual"


class TermRange(BaseModel):
    min_months: int | None = None
    max_months: int | None = None


class Evidence(BaseModel):
    source_url: str
    source_type: Literal["page", "pdf", "api", "linked_document"]

    quote: str
    section: str | None = None
    locator: str | None = None
```

---

## Extracted values

Every semantic value must carry evidence and an extraction state.

```python
T = TypeVar("T")


class ExtractedValue(BaseModel, Generic[T]):
    value: T | None
    evidence: list[Evidence]

    status: Literal[
        "found",
        "not_stated",
        "ambiguous",
        "conflicting",
    ]
```

Rules:

- `found`: source explicitly supports the value;
- `not_stated`: relevant sources were inspected and the value was not found;
- `ambiguous`: relevant text exists but cannot safely be represented as one value;
- `conflicting`: authoritative sources contain incompatible values.

A missing value must never be converted into a guessed value.

---

## Loan amount

Loan amount cannot always be represented as a simple currency range.

For example:

> Amount: up to a 4-fold salary

must not become an invented AMD amount.

Use a discriminated union:

```python
class AbsoluteMoneyRange(BaseModel):
    type: Literal["absolute"]
    range: MoneyRange


class SalaryMultiple(BaseModel):
    type: Literal["salary_multiple"]
    min_multiple: Decimal | None = None
    max_multiple: Decimal | None = None


class PropertyValuePercentage(BaseModel):
    type: Literal["property_value_percentage"]
    min_pct: Decimal | None = None
    max_pct: Decimal | None = None


class OtherAmountFormula(BaseModel):
    type: Literal["other_formula"]
    expression: str


LoanAmount = (
    AbsoluteMoneyRange
    | SalaryMultiple
    | PropertyValuePercentage
    | OtherAmountFormula
)
```

---

## Conditional values

Rates, amounts, fees, and down payments may depend on conditions.

Do not flatten these conditions away.

```python
class Condition(BaseModel):
    dimension: str
    operator: str | None = None
    value: str


class ConditionalValue(BaseModel, Generic[T]):
    value: T
    conditions: list[Condition] = []
```

Examples of conditions:

- currency = AMD;
- salary customer = true;
- property market = primary;
- income verification = false;
- application channel = online;
- residency = non-resident.

---

## Shared loan model

```python
class LoanProduct(BaseModel):
    product_name: ExtractedValue[str]

    category: Literal[
        "consumer_loan",
        "overdraft",
        "credit_line",
        "mortgage",
    ]

    purpose: ExtractedValue[list[str]]

    loan_amount: ExtractedValue[list[ConditionalValue[LoanAmount]]]

    interest_rate: ExtractedValue[
        list[ConditionalValue[Rate]]
    ]

    effective_rate: ExtractedValue[
        list[ConditionalValue[Rate]]
    ]

    term: ExtractedValue[
        list[ConditionalValue[TermRange]]
    ]

    fees: ExtractedValue[list[str]]
    repayment: ExtractedValue[list[str]]

    eligibility: ExtractedValue[list[str]]
    residency_requirements: ExtractedValue[list[str]]
    age_requirements: ExtractedValue[str]

    application_channel: ExtractedValue[list[str]]
    required_documents: ExtractedValue[list[str]]
    special_conditions: ExtractedValue[list[str]]

    details: (
        "ConsumerLoanDetails"
        | "OverdraftDetails"
        | "CreditLineDetails"
        | "MortgageDetails"
    )

    canonical_url: str
    retrieved_at: datetime
```

---

## Product-specific models

### Consumer loan

```python
class ConsumerLoanDetails(BaseModel):
    type: Literal["consumer_loan"]

    collateral: ExtractedValue[list[str]]
    income_verification_required: ExtractedValue[bool]
```

### Overdraft

```python
class OverdraftDetails(BaseModel):
    type: Literal["overdraft"]

    credit_limit: ExtractedValue[list[LoanAmount]]
    grace_period_days: ExtractedValue[int]
    revolving: ExtractedValue[bool]
    linked_account_or_card: ExtractedValue[str]
```

### Credit line

```python
class CreditLineDetails(BaseModel):
    type: Literal["credit_line"]

    credit_limit: ExtractedValue[list[LoanAmount]]
    grace_period_days: ExtractedValue[int]
    revolving: ExtractedValue[bool]
```

### Mortgage

```python
class MortgageDetails(BaseModel):
    type: Literal["mortgage"]

    property_market: ExtractedValue[
        Literal[
            "primary",
            "secondary",
            "commercial",
            "construction",
            "renovation",
            "mixed",
            "not_applicable",
        ]
    ]

    down_payment_pct: ExtractedValue[
        list[ConditionalValue[Decimal]]
    ]

    ltv_pct: ExtractedValue[
        list[ConditionalValue[Decimal]]
    ]

    collateral: ExtractedValue[list[str]]

    income_verification_required: ExtractedValue[bool]

    property_requirements: ExtractedValue[list[str]]
```

The subtype schemas should remain small. Add a subtype field only when it represents a real recurring concept in the target products.

---

# 3. Layout Normalizer

## Purpose

The layout normalizer converts heterogeneous HTML, tables, PDF text, and API fragments into consistent structural blocks.

It does not determine loan semantics.

For example, it should understand that this:

```text
up to 240 months
```

contains a numeric range expression, but it should not decide whether it is the loan term unless the surrounding block identifies it as such.

---

## Structural blocks

Example:

```python
class ContentBlock(BaseModel):
    id: str

    type: Literal[
        "heading",
        "paragraph",
        "list",
        "key_value",
        "table",
        "accordion",
        "card",
        "link",
        "other",
    ]

    text: str

    heading_path: list[str]
    parent_id: str | None

    locator: SourceLocator

    visible: bool
```

Example normalized page:

```json
[
  {
    "id": "b17",
    "type": "heading",
    "text": "Credit line",
    "heading_path": []
  },
  {
    "id": "b24",
    "type": "paragraph",
    "text": "A grace period of up to 51 days...",
    "heading_path": ["Credit line", "Advantages"]
  }
]
```

---

## Scalar normalization

Keep both raw and normalized forms.

Input:

```text
up to 240 months
```

Parsed form:

```json
{
  "raw": "up to 240 months",
  "operator": "<=",
  "value": 240,
  "unit": "month"
}
```

Derived normalization:

```json
{
  "max_months": 240
}
```

If a convenience conversion is useful:

```json
{
  "max_months": 240,
  "max_years": 20
}
```

The original value must remain available.

Another example:

```json
{
  "raw": "up to 51 days",
  "normalized": {
    "operator": "<=",
    "value": 51,
    "unit": "day"
  }
}
```

---

## Deterministic normalization responsibilities

Python should normalize:

- currency symbols and names;
- numeric separators;
- percentages;
- ranges;
- `from`, `up to`, `at least`;
- months and years;
- dates;
- obvious fixed units;
- table row/column structure;
- duplicate whitespace and formatting.

The normalizer should not infer missing financial meaning.

---

# 4. Source Discovery

## Purpose

Source Discovery determines which acquired material belongs to the current product and which sources should be used for extraction.

It is primarily semantic and can be LLM-based.

It should not simply remove FAQ or related sections using fixed rules.

A FAQ may contain valid eligibility information. A campaign page may contain valid temporary conditions. A related-product card should normally be excluded. A linked terms PDF may be more authoritative than the marketing page.

The output should therefore classify sources instead of merely keeping or dismissing them.

---

## Source Discovery responsibilities

For every block, table, document, or network payload, determine:

### Product association

```text
current_product
related_product
global_navigation
generic_bank_information
unknown
```

### Information role

```text
product_terms
product_description
eligibility
pricing
fees
repayment
documents
faq
campaign_terms
legal_disclosure
related_product
navigation
other
```

### Relevance

```text
relevant
possibly_relevant
irrelevant
```

### Authority

```text
official_terms
official_product_content
official_faq
official_campaign_content
marketing_content
unknown
```

### Temporal status

```text
current
time_bounded
possibly_stale
unknown
```

The LLM should also identify explicit effective dates or campaign periods when present.

---

## Example output

```json
{
  "items": [
    {
      "source_id": "b24",
      "product_association": "current_product",
      "role": "pricing",
      "relevance": "relevant",
      "authority": "official_product_content",
      "temporal_status": "current",
      "reason": "Block is inside the current Credit Line product section."
    },
    {
      "source_id": "b91",
      "product_association": "related_product",
      "role": "related_product",
      "relevance": "irrelevant",
      "authority": "marketing_content",
      "temporal_status": "unknown",
      "reason": "Block describes a separate consumer-loan product."
    },
    {
      "source_id": "doc1",
      "product_association": "current_product",
      "role": "product_terms",
      "relevance": "relevant",
      "authority": "official_terms",
      "temporal_status": "current",
      "reason": "Linked product-specific terms document."
    }
  ]
}
```

---

## Source selection rules

Python should convert Source Discovery results into the extraction context.

Recommended precedence:

```text
1. product-specific official terms / tariff document
2. product-specific structured terms table
3. current product body content
4. official product FAQ
5. campaign content when the product is explicitly campaign-based
6. generic marketing copy
```

Precedence does not mean lower-ranked sources are discarded. It means conflicts are surfaced and resolved according to source authority.

The extraction context should exclude:

- global navigation;
- footer content;
- unrelated product cards;
- generic site search content;
- unrelated loan products.

Potentially useful FAQ, legal disclosures, campaign terms, and linked documents should remain available when they refer to the current product.

---

## Source Discovery should detect conditions

Source discovery should preserve important contextual scope, for example:

```text
"for salary customers"
"for non-residents"
"when applying online"
"for primary-market property"
"valid until 31 December"
```

These qualifiers must travel with the block into extraction so they are not lost.

---

# 5. Data Extraction and Claim Generation

## Extraction purpose

The extraction agent maps relevant source material into the `LoanProduct` schema.

Every populated field must include evidence.

The extractor must preserve:

- conditions;
- currencies;
- min/max semantics;
- nominal versus effective rates;
- product-specific formulas;
- exceptions;
- source conflicts.

The extractor must never infer a value from general banking knowledge.

---

## Extraction rules

For every field:

1. use only supplied official source material;
2. preserve qualifiers such as `up to`, `from`, and conditional wording;
3. attach evidence;
4. return `not_stated` when the information is absent;
5. return `ambiguous` when multiple interpretations are plausible;
6. return `conflicting` when authoritative sources disagree;
7. do not merge condition-specific values into one unconditional value.

---

## Claims

After Pydantic validation, Python converts the structured product into atomic claims.

Example:

```json
[
  {
    "claim_id": "interest_rate.0.value.min",
    "claim": "The minimum annual nominal interest rate is 13%.",
    "value": 13,
    "evidence": ["b41"]
  },
  {
    "claim_id": "loan_amount.0.value.range.currency",
    "claim": "The loan amount currency is AMD.",
    "value": "AMD",
    "evidence": ["b38"]
  }
]
```

Claims are the unit of verification.

This makes failures local and makes repair possible without re-extracting the whole product.

---

# 6. Data Verification and Repair

## Purpose

Verification decides whether each extracted claim is actually supported by the supplied official source evidence.

Verification should combine deterministic checks with semantic entailment.

No single confidence number should decide whether a field is accepted.

---

## Verification signals

Use the following signals.

### 1. Schema validity

Pydantic confirms:

- correct data type;
- valid enum;
- required structure;
- valid union subtype.

Failure means the extraction is rejected before semantic verification.

### 2. Evidence existence

Python verifies that every referenced:

- block ID;
- document;
- PDF page;
- API path;

actually exists in the acquired artifact.

### 3. Quote grounding

If the extractor provides a quote, verify that the quote exists in the referenced source after safe text normalization.

### 4. Numeric lexical grounding

For numeric claims, verify that compatible numeric text exists in evidence.

Examples:

```text
claim: 51 days
evidence must contain: 51
```

```text
claim: 13%
evidence should contain a compatible representation of 13%
```

This is a supporting signal, not enough by itself.

### 5. Unit grounding

Verify compatible units:

```text
months
years
%
AMD
USD
EUR
days
```

A numeric match with an incompatible unit should fail or be escalated.

### 6. Condition preservation

Check whether qualifiers present in evidence survive into the structured claim.

Example:

```text
Source:
12% for salary customers
```

The following is incomplete:

```text
interest_rate = 12%
```

The condition must be represented.

### 7. Source/product consistency

Evidence must belong to the current product or an explicitly accepted source for that product.

A rate from a related product must not verify a current-product claim.

### 8. Source authority

If two relevant official sources disagree, compare their source classification and effective dates.

Do not silently select a value if the conflict cannot be resolved deterministically.

### 9. Semantic entailment

A small LLM verifier receives:

- one atomic claim;
- its evidence;
- necessary surrounding context.

It returns:

```text
SUPPORTED
CONTRADICTED
INSUFFICIENT_EVIDENCE
AMBIGUOUS
SOURCE_CONFLICT
```

The verifier should not receive the extractor's reasoning.

---

## Deterministic financial checks

### Hard checks

```python
0 <= down_payment_pct <= 100
0 <= ltv_pct <= 100

min_amount <= max_amount
min_rate <= max_rate

min_months > 0
max_months > 0

min_months <= max_months
```

Only run comparisons when both values exist and belong to the same condition/currency branch.

### Warning-level checks

Some checks are useful but not universally true.

For example:

```python
nominal_rate <= effective_rate
```

This should normally be a warning requiring inspection rather than a universal assertion.

---

## Domain completeness checks

Completeness checks identify suspicious omissions. They do not manufacture missing values.

Example:

```python
if product.category == "overdraft":
    inspect_for([
        "credit_limit",
        "revolving",
        "interest_rate",
    ])
```

```python
if product.category == "mortgage":
    inspect_for([
        "collateral",
        "down_payment_pct",
        "ltv_pct",
        "property_market",
        "term",
        "interest_rate",
    ])
```

A missing expected concept produces a completeness warning.

It does not automatically mean the extractor is wrong because the source may genuinely omit it.

---

## Verification decision

Each claim should end in an operational state such as:

```text
VERIFIED
REPAIRABLE
REVIEW_REQUIRED
MISSING
CONFLICTING
```

Example decision rules:

```python
if schema_invalid:
    REPAIRABLE

elif evidence_reference_missing:
    REPAIRABLE

elif lexical_grounding_failed:
    REPAIRABLE

elif semantic_verifier == "CONTRADICTED":
    REPAIRABLE

elif semantic_verifier == "SOURCE_CONFLICT":
    REVIEW_REQUIRED

elif semantic_verifier == "AMBIGUOUS":
    REVIEW_REQUIRED

elif semantic_verifier == "SUPPORTED":
    VERIFIED
```

---

## Re-extraction / repair

Do not re-run the entire product extraction when one field fails.

Repair receives only:

- failed field;
- previous extracted value;
- verification failure;
- relevant evidence;
- nearby context.

Example:

```json
{
  "field": "interest_rate",
  "previous_value": {
    "min": 13.5,
    "max": 13.5
  },
  "failure": "Evidence states a range of 13%-15%.",
  "sources": ["b41", "b42"]
}
```

Repair should return only the corrected field.

The corrected value then goes through the full verification pipeline again.

---

## HITL triggers

Human review should be used when the system cannot resolve the issue safely.

Recommended triggers:

- two authoritative current sources conflict;
- the source contains genuinely ambiguous wording;
- conditions cannot be represented by the current schema;
- the verifier and extractor repeatedly disagree after one repair attempt;
- a critical financial field is supported only by low-authority marketing content;
- source effective dates are unclear;
- the current page and linked official terms appear to describe different product versions.

Critical fields typically include:

- interest rate;
- effective rate;
- amount / credit limit;
- term;
- down payment;
- LTV;
- fees;
- eligibility constraints.

---

# End-to-End Flow

```text
URL
 │
 ▼
Acquisition Tool
 │
 │ HTML / rendered DOM / tables / PDFs / API responses
 ▼
Layout Normalizer
 │
 │ stable blocks + parsed scalar structures + provenance
 ▼
Source Discovery
 │
 │ current-product sources + role + authority + temporal scope
 ▼
Extraction Agent
 │
 │ LoanProduct + Evidence
 ▼
Pydantic Validation
 │
 ▼
Claim Generator
 │
 │ atomic claims
 ▼
Deterministic Verification
 │
 │ schema / source / quote / number / unit / invariant checks
 ▼
Semantic Verifier
 │
 ├──────── SUPPORTED ────────────────► VERIFIED
 │
 ├──────── repairable problem ──────► field-level repair ──┐
 │                                                         │
 └──────── conflict / ambiguity ────► HITL                 │
                                                           │
                           verification ◄───────────────────┘
```

---

# Responsibility Boundary

## Deterministic Python

Python owns:

- acquisition;
- Playwright control;
- downloads;
- PDF parsing;
- network capture;
- DOM parsing;
- block generation;
- table parsing;
- scalar normalization;
- Pydantic validation;
- claim generation;
- evidence-reference validation;
- quote matching;
- numeric/unit grounding;
- financial invariants;
- source precedence rules;
- verification routing;
- repair routing;
- HITL routing.

## LLM

The LLM owns only semantic tasks:

### Source Discovery

Determines:

> Which acquired blocks and documents actually describe this product, what role do they play, and how authoritative/current are they?

### Extraction

Determines:

> What financial meaning does the relevant source express, and how should it map into the loan schema without losing conditions?

### Semantic Verification

Determines:

> Does this exact evidence semantically support this atomic claim?

### Repair

Determines:

> Given a specific failed field and its evidence, what corrected structured value is supported?

This keeps the agentic surface small and makes the system testable, auditable, and safe to evolve.
