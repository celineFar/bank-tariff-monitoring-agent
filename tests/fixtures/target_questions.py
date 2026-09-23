"""The 25 target questions with their expected typed route and outcome.

Question texts are reconstructed from the coverage map in section 7 of
``Project Documents/Structured Tariff Retrieval Implementation Plan.md``:
single-offering facts (1-7, 9, 14-19), explicit comparison (8, 21, 22), family
extrema (10-12, 23-24), fee inventory (13), mortgage down payment and
alternative security (20), and accepted change history (25). Expected outcomes
are stated against the synthetic evaluation corpus in
``tests/fixtures/evaluation_corpus.py``, not against production data.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import OfferingId, ProductType
from app.domain.structured_tariffs import (
    FieldPath,
    QueryOperation,
    QueryStatus,
    RankDirection,
)


@dataclass(frozen=True)
class TargetQuestion:
    number: int
    case_id: str
    question: str
    language: str
    product: ProductType
    operation: QueryOperation
    offering_ids: tuple[OfferingId, ...]
    required_fields: tuple[FieldPath, ...]
    expected_status: QueryStatus
    rank_direction: RankDirection | None = None
    expected_winner: OfferingId | None = None
    deterministic_route: bool = True
    note: str = ""


C = ProductType.CONSUMER_LOAN
M = ProductType.MORTGAGE
CONSUMER_FAMILY = (
    OfferingId.CONSUMER_STANDARD,
    OfferingId.OVERDRAFT,
    OfferingId.CREDIT_LINE,
    OfferingId.ONLINE_CONSUMER_FINANCE,
)
MORTGAGE_FAMILY = tuple(item for item in OfferingId if item.product is M)

TARGET_QUESTIONS: tuple[TargetQuestion, ...] = (
    TargetQuestion(
        number=1,
        case_id="q01_overdraft_nominal_rate",
        question="What is the nominal interest rate of the Overdraft?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.OVERDRAFT,),
        required_fields=(
            FieldPath.NOMINAL_RATE_MINIMUM,
            FieldPath.NOMINAL_RATE_MAXIMUM,
        ),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=2,
        case_id="q02_credit_line_effective_rate",
        question="What is the effective interest rate of the Credit Line?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.CREDIT_LINE,),
        required_fields=(
            FieldPath.EFFECTIVE_RATE_MINIMUM,
            FieldPath.EFFECTIVE_RATE_MAXIMUM,
        ),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=3,
        case_id="q03_online_finance_amount",
        question="What loan amount does the Online Consumer Finance allow?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.ONLINE_CONSUMER_FINANCE,),
        required_fields=(FieldPath.AMOUNT_MINIMUM, FieldPath.AMOUNT_MAXIMUM),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=4,
        case_id="q04_primary_mortgage_term",
        question="What repayment term does the Primary Market Mortgage offer?",
        language="en",
        product=M,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.MORTGAGE_PRIMARY,),
        required_fields=(FieldPath.TERM_MAXIMUM_MONTHS,),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=5,
        case_id="q05_overdraft_usd_amount",
        question="What is the Overdraft loan amount in USD?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.OVERDRAFT,),
        required_fields=(FieldPath.AMOUNT_MINIMUM, FieldPath.AMOUNT_MAXIMUM),
        expected_status=QueryStatus.ANSWERED,
        note="Currency condition must narrow the answer to the USD variant only.",
    ),
    TargetQuestion(
        number=6,
        case_id="q06_overdraft_salary_privilege",
        question="Is there a salary customer privilege in the Overdraft tariff?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.OVERDRAFT,),
        required_fields=(FieldPath.SALARY_PRIVILEGE,),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=7,
        case_id="q07_credit_line_application_fee",
        question="What application fee applies to the Credit Line?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.CREDIT_LINE,),
        required_fields=(FieldPath.FEE_APPLICATION,),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=8,
        case_id="q08_compare_overdraft_credit_line_rate",
        question="Compare the Overdraft and the Credit Line interest rate.",
        language="en",
        product=C,
        operation=QueryOperation.COMPARE,
        offering_ids=(OfferingId.OVERDRAFT, OfferingId.CREDIT_LINE),
        required_fields=(
            FieldPath.NOMINAL_RATE_MINIMUM,
            FieldPath.EFFECTIVE_RATE_MINIMUM,
        ),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=9,
        case_id="q09_overdraft_rate_armenian",
        question="Օվերդրաֆտի տոկոսադրույքը որքա՞ն է։",  # noqa: RUF001
        language="hy",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.OVERDRAFT,),
        required_fields=(
            FieldPath.NOMINAL_RATE_MINIMUM,
            FieldPath.EFFECTIVE_RATE_MINIMUM,
        ),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=10,
        case_id="q10_consumer_lowest_nominal_rate",
        question=("Which consumer loan has the lowest nominal interest rate in AMD?"),
        language="en",
        product=C,
        operation=QueryOperation.FAMILY_RANK,
        offering_ids=CONSUMER_FAMILY,
        required_fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
        expected_status=QueryStatus.ANSWERED,
        rank_direction=RankDirection.LOWEST,
        expected_winner=OfferingId.ONLINE_CONSUMER_FINANCE,
    ),
    TargetQuestion(
        number=11,
        case_id="q11_mortgage_largest_amount",
        question="Which mortgage loans allow the largest amount in AMD?",
        language="en",
        product=M,
        operation=QueryOperation.FAMILY_RANK,
        offering_ids=MORTGAGE_FAMILY,
        required_fields=(FieldPath.AMOUNT_MAXIMUM,),
        expected_status=QueryStatus.ANSWERED,
        rank_direction=RankDirection.HIGHEST,
        expected_winner=OfferingId.MORTGAGE_PRIMARY,
    ),
    TargetQuestion(
        number=12,
        case_id="q12_mortgage_longest_term",
        question="Which mortgage loans have the longest repayment term?",
        language="en",
        product=M,
        operation=QueryOperation.FAMILY_RANK,
        offering_ids=MORTGAGE_FAMILY,
        required_fields=(FieldPath.TERM_MAXIMUM_MONTHS,),
        expected_status=QueryStatus.ANSWERED,
        rank_direction=RankDirection.HIGHEST,
        expected_winner=OfferingId.MORTGAGE_PRIMARY,
    ),
    TargetQuestion(
        number=13,
        case_id="q13_credit_line_fee_inventory",
        question="What fees apply to the Credit Line?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.CREDIT_LINE,),
        required_fields=(
            FieldPath.FEE_APPLICATION,
            FieldPath.FEE_SERVICE,
            FieldPath.FEE_OTHER,
        ),
        expected_status=QueryStatus.ANSWERED,
        note=(
            "Fee inventory by scope and type; a fixed fee and a percentage fee "
            "must not be ranked into one highest fee."
        ),
    ),
    TargetQuestion(
        number=14,
        case_id="q14_mortgage_collateral",
        question="What collateral does the Primary Market Mortgage require?",
        language="en",
        product=M,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.MORTGAGE_PRIMARY,),
        required_fields=(
            FieldPath.COLLATERAL_REQUIREMENT,
            FieldPath.COLLATERAL_ALTERNATIVE,
        ),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=15,
        case_id="q15_online_finance_purpose",
        question=("What purpose and terms does the Online Consumer Finance cover?"),
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.ONLINE_CONSUMER_FINANCE,),
        required_fields=(FieldPath.PURPOSE,),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=16,
        case_id="q16_overdraft_credit_limit",
        question="What amount can the Overdraft reach?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.OVERDRAFT,),
        required_fields=(
            FieldPath.AMOUNT_MAXIMUM,
            FieldPath.CREDIT_LIMIT_MAXIMUM,
        ),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=17,
        case_id="q17_credit_line_term",
        question="What repayment term applies to the Credit Line?",
        language="en",
        product=C,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.CREDIT_LINE,),
        required_fields=(FieldPath.TERM_MAXIMUM_MONTHS,),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=18,
        case_id="q18_express_mortgage_missing",
        question="What application fee applies to the Express Mortgage?",
        language="en",
        product=M,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
        required_fields=(FieldPath.FEE_APPLICATION,),
        expected_status=QueryStatus.MISSING,
        note="No accepted projection for this offering; abstain instead of guessing.",
    ),
    TargetQuestion(
        number=19,
        case_id="q19_diaspora_rate_freshness",
        question="What is the interest rate of the Mortgage Loan for Diaspora?",
        language="en",
        product=M,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.MORTGAGE_DIASPORA,),
        required_fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
        expected_status=QueryStatus.ANSWERED,
        note="Answer must carry the accepted-snapshot as_of freshness stamp.",
    ),
    TargetQuestion(
        number=20,
        case_id="q20_mortgage_down_payment",
        question=(
            "What down payment and collateral does the Primary Market Mortgage require?"
        ),
        language="en",
        product=M,
        operation=QueryOperation.SINGLE,
        offering_ids=(OfferingId.MORTGAGE_PRIMARY,),
        required_fields=(
            FieldPath.DOWN_PAYMENT_MINIMUM,
            FieldPath.COLLATERAL_ALTERNATIVE,
        ),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=21,
        case_id="q21_compare_primary_secondary",
        question=(
            "Compare the Primary Market Mortgage and the Secondary Market "
            "Mortgage amount, term and interest rate."
        ),
        language="en",
        product=M,
        operation=QueryOperation.COMPARE,
        offering_ids=(
            OfferingId.MORTGAGE_PRIMARY,
            OfferingId.MORTGAGE_SECONDARY_MARKET,
        ),
        required_fields=(
            FieldPath.AMOUNT_MAXIMUM,
            FieldPath.TERM_MAXIMUM_MONTHS,
            FieldPath.NOMINAL_RATE_MINIMUM,
        ),
        expected_status=QueryStatus.ANSWERED,
    ),
    TargetQuestion(
        number=22,
        case_id="q22_compare_online_diaspora_fee",
        question=(
            "Compare the Online Mortgage and the Mortgage Loan for Diaspora "
            "application fee."
        ),
        language="en",
        product=M,
        operation=QueryOperation.COMPARE,
        offering_ids=(OfferingId.MORTGAGE_ONLINE, OfferingId.MORTGAGE_DIASPORA),
        required_fields=(FieldPath.FEE_APPLICATION,),
        expected_status=QueryStatus.INCOMPARABLE,
        note="A percentage fee and a fixed fee have no shared numeric basis.",
    ),
    TargetQuestion(
        number=23,
        case_id="q23_consumer_lowest_effective_rate",
        question="Which consumer loan has the lowest effective interest rate?",
        language="en",
        product=C,
        operation=QueryOperation.FAMILY_RANK,
        offering_ids=CONSUMER_FAMILY,
        required_fields=(FieldPath.EFFECTIVE_RATE_MINIMUM,),
        expected_status=QueryStatus.ANSWERED,
        rank_direction=RankDirection.LOWEST,
        expected_winner=OfferingId.ONLINE_CONSUMER_FINANCE,
    ),
    TargetQuestion(
        number=24,
        case_id="q24_mortgage_lowest_application_fee",
        question="Which mortgage loans have the lowest application fee?",
        language="en",
        product=M,
        operation=QueryOperation.FAMILY_RANK,
        offering_ids=MORTGAGE_FAMILY,
        required_fields=(FieldPath.FEE_APPLICATION,),
        expected_status=QueryStatus.INCOMPARABLE,
        rank_direction=RankDirection.LOWEST,
        note="Fixed-amount and percentage application fees cannot be ranked.",
    ),
    TargetQuestion(
        number=25,
        case_id="q25_mortgage_accepted_changes",
        question="What changed in the Primary Market Mortgage tariff?",
        language="en",
        product=M,
        operation=QueryOperation.HISTORY,
        offering_ids=(OfferingId.MORTGAGE_PRIMARY,),
        required_fields=(),
        expected_status=QueryStatus.ANSWERED,
    ),
)

if len(TARGET_QUESTIONS) != 25:
    raise RuntimeError("the target-question registry must hold exactly 25 questions")
if len({item.number for item in TARGET_QUESTIONS}) != 25:
    raise RuntimeError("target-question numbers must be unique")
if len({item.case_id for item in TARGET_QUESTIONS}) != 25:
    raise RuntimeError("target-question case IDs must be unique")
