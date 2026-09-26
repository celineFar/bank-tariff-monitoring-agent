"""Words that label each extraction field, for the budgeted evidence mode.

Retrieval terms only: they decide which labelled units of evidence a budgeted
call reads first, and never produce or check a value. They match whole words
(an optional plural `s`/`es` allowed), so `age` finds "Customer Age" but not
"percentage" or "mortgage" (SE6, SE14). They are matched against labels --
headings, table titles, row labels, column paths and keys -- never against
body text, where "annual interest rate" also appears in a credit-history
disclosure.

Full evidence mode, the default, uses none of this: every call reads the
offering's whole selected evidence.
"""

from __future__ import annotations

import re
from functools import cache

from app.domain.semantic_extraction import ExtractionField

FIELD_TERMS: dict[ExtractionField, tuple[str, ...]] = {
    ExtractionField.PRODUCT_NAME: (
        "product name",
        "loan name",
        "mortgage loan",
        "consumer loan",
        "consumer finance",
        "overdraft",
        "credit line",
    ),
    ExtractionField.FORMAL_TERMS_NAMES: (
        "information summary",
        "terms and conditions",
        "loan terms",
        "tariff",
        "tarif",
    ),
    ExtractionField.VARIANTS: (
        "type of financing",
        "financing type",
        "types of",
        "card type",
        "type of credit card",
        "variant",
    ),
    ExtractionField.CATEGORY: (
        "mortgage",
        "consumer loan",
        "consumer finance",
        "overdraft",
        "credit line",
        "loan type",
    ),
    ExtractionField.PURPOSE: ("purpose", "loan purpose"),
    ExtractionField.LOAN_AMOUNT: (
        "loan amount",
        "loan limit",
        "minimum and maximum loan limit",
        "maximum amount",
        "minimum amount",
        "financing limit",
        "amount",
    ),
    ExtractionField.INTEREST_RATE: (
        "annual interest rate",
        "nominal interest rate",
        "nominal annual interest rate",
        "interest rate",
    ),
    ExtractionField.EFFECTIVE_RATE: (
        "annual percentage rate",
        "apr",
        "effective interest rate",
        "actual interest rate",
        "actual percentage rate",
    ),
    ExtractionField.TERM: (
        "term",
        "loan term",
        "term of finance",
        "repayment period",
        "repayment term",
        "duration",
    ),
    ExtractionField.FEES: (
        "fee",
        "commission",
        "charge",
        "fine",
        "penalty",
        "penalties",
        "cashing",
        "costs",
        "service fee",
    ),
    ExtractionField.REPAYMENT: (
        "repayment",
        "repayment method",
        "forms of loan repayment",
        "minimum payment",
        "prepayment",
        "payment method",
    ),
    ExtractionField.ELIGIBILITY: (
        "eligibility",
        "eligible customer",
        "eligible",
        "who may apply",
        "customer",
        "borrower",
        "personal details",
    ),
    ExtractionField.RESIDENCY_REQUIREMENTS: ("residency", "resident"),
    ExtractionField.AGE_REQUIREMENTS: ("age", "eligible age", "customer age"),
    ExtractionField.APPLICATION_CHANNEL: (
        "application",
        "apply",
        "how to apply",
        "online",
        "branch",
    ),
    ExtractionField.REQUIRED_DOCUMENTS: (
        "required documents",
        "documents",
        "document",
    ),
    ExtractionField.SPECIAL_CONDITIONS: (
        "special conditions",
        "other terms",
        "campaign",
        "incentive",
        "developer",
    ),
    ExtractionField.COLLATERAL: (
        "collateral",
        "security",
        "pledge",
        "guarantee",
    ),
    ExtractionField.INCOME_VERIFICATION_REQUIRED: (
        "income verification",
        "proof of income",
        "income",
    ),
    ExtractionField.CREDITWORTHINESS_ASSESSMENT_REQUIRED: (
        "creditworthiness",
        "creditworthiness assessment",
        "credit history",
    ),
    ExtractionField.PROPERTY_MARKET: (
        "primary market",
        "secondary market",
        "property market",
    ),
    ExtractionField.DOWN_PAYMENT_PCT: (
        "down payment",
        "advance payment",
        "minimum down payment",
    ),
    ExtractionField.LTV_PCT: (
        "loan-to-value",
        "ltv",
        "loan-to-collateral",
    ),
    ExtractionField.PROPERTY_REQUIREMENTS: (
        "property",
        "real estate",
        "property requirements",
    ),
    ExtractionField.CREDIT_LIMIT: ("credit limit", "limit", "loan amount"),
    ExtractionField.GRACE_PERIOD_DAYS: ("grace period", "interest-free period"),
    ExtractionField.REVOLVING: ("revolving", "line of credit", "renewable"),
    ExtractionField.LINKED_ACCOUNT_OR_CARD: (
        "card",
        "card type",
        "linked account",
        "account",
    ),
}


@cache
def term_pattern(term: str) -> re.Pattern[str]:
    """A whole-word match for `term`, allowing a plural ending."""
    return re.compile(
        rf"(?<![\w-]){re.escape(term.casefold())}(?:s|es)?(?![\w-])", re.IGNORECASE
    )


def mentions_field(field: ExtractionField, text: str) -> bool:
    """Whether `text` names `field` with one of its terms, as a whole word."""
    return any(term_pattern(term).search(text) for term in FIELD_TERMS[field])


def matched_terms(field: ExtractionField, text: str) -> tuple[str, ...]:
    return tuple(term for term in FIELD_TERMS[field] if term_pattern(term).search(text))
