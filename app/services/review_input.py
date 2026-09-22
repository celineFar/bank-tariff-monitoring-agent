"""Deterministic plain-language entry for human tariff review values.

A reviewer is asked for a field value in the middle of a paused run, so the
prompt has to state what a valid answer looks like before the answer is typed,
and an entry such as ``Monthly annuity`` has to reach the field's structured
contract without the reviewer knowing that contract. Every rule here is
deterministic: the model is never asked to interpret reviewer input.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from app.domain.semantic_extraction import (
    ExtractionField,
    LoanCategory,
    PropertyMarket,
)
from app.services.semantic_extraction import (
    normalize_extraction_field_value,
    validate_review_field_value,
)

_CURRENCIES = {
    "AMD": "AMD",
    "USD": "USD",
    "EUR": "EUR",
    "֏": "AMD",
    "$": "USD",
    "€": "EUR",
}
_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "m": 1_000_000,
    "mln": 1_000_000,
    "million": 1_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
}
_RATE_TYPES = {
    "fixed": "fixed",
    "variable": "variable",
    "floating": "variable",
    "mixed": "mixed",
}
_TRUE_WORDS = {"yes", "y", "true", "required", "revolving"}
_FALSE_WORDS = {"no", "n", "false", "not required", "none", "n/a", "not applicable"}


@dataclass(frozen=True)
class ReviewFieldFormat:
    """What a reviewer may type for one field, and how that text is read."""

    instruction: str
    examples: tuple[str, ...]
    parse: Callable[[str], Any]
    # Parsers that already emit the contract shape skip the shared normalizer,
    # whose model-output heuristics would reinterpret a typed value.
    normalize_text: bool = True

    @property
    def help_text(self) -> str:
        if not self.examples:
            return self.instruction
        shown = ", ".join(f'"{example}"' for example in self.examples)
        return f"{self.instruction} For example: {shown}."


class ReviewInputError(ValueError):
    """Reviewer input that cannot be stored, explained with the accepted format."""

    def __init__(self, detail: str, field_format: ReviewFieldFormat) -> None:
        super().__init__(f"{detail} {field_format.help_text}")
        self.detail = detail
        self.field_format = field_format


def review_field_format(field: ExtractionField) -> ReviewFieldFormat:
    """Return the accepted entry format for a reviewable field."""
    return _FORMATS[field]


def parse_review_field_text(
    field: ExtractionField,
    text: str,
    *,
    excerpts: Sequence[str] = (),
) -> Any:
    """Turn a reviewer's typed answer into a validated value for this field.

    Raises ``ReviewInputError`` carrying the accepted format, so the reviewer is
    never told only that the value is invalid.
    """
    field_format = review_field_format(field)
    raw = text.strip()
    if not raw:
        raise ReviewInputError("Enter a value.", field_format)
    normalize = True
    if raw.startswith(("{", "[")):
        try:
            value = json.loads(raw)
        except ValueError as exc:
            raise ReviewInputError(
                "That structured value is not valid JSON.", field_format
            ) from exc
    else:
        try:
            value = field_format.parse(raw)
        except ReviewInputError:
            raise
        except ValueError as exc:
            raise ReviewInputError(str(exc), field_format) from exc
        normalize = field_format.normalize_text
    if field is ExtractionField.TERM:
        _require_indefinite_support(raw, value, excerpts, field_format)
    if normalize:
        value, _ = normalize_extraction_field_value(field, value)
    value = _jsonable(value)
    try:
        validate_review_field_value(field, value)
    except ValidationError as exc:
        raise ReviewInputError(_first_error(exc), field_format) from exc
    except ValueError as exc:
        raise ReviewInputError(str(exc), field_format) from exc
    return value


def _jsonable(value: Any) -> Any:
    """Keep review values JSON-native, since a decision travels as JSON."""
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _first_error(exc: ValidationError) -> str:
    errors = exc.errors(include_url=False, include_context=False)
    if not errors:
        return "The value does not match the field contract."
    message = str(errors[0].get("msg", "")).removeprefix("Value error, ").strip()
    if not message:
        return "Invalid value."
    return f"{message[:1].upper()}{message[1:]}."


def _require_indefinite_support(
    raw: str,
    value: Any,
    excerpts: Sequence[str],
    field_format: ReviewFieldFormat,
) -> None:
    """Keep an open-ended term tied to a passage that states its end condition."""
    if not (
        isinstance(value, list)
        and value
        and isinstance(value[0], dict)
        and isinstance(value[0].get("value"), dict)
        and value[0]["value"].get("indefinite") is True
    ):
        return
    if re.fullmatch(r"indefinite\s+term", raw, re.I) and not any(
        _states_end_condition(excerpt) for excerpt in excerpts
    ):
        raise ReviewInputError("The source must state the end condition.", field_format)


def _states_end_condition(excerpt: str) -> bool:
    return bool(
        re.search(
            r"indefinite\s+term\s*\(\s*until\s+requested\s+back\s*\)", excerpt, re.I
        )
    )


def term_supported_by_passage(raw: str, excerpt: str) -> bool:
    """Report whether a passage backs a typed term without a passage choice."""
    if re.fullmatch(r"indefinite\s+term", raw.strip(), re.I):
        return _states_end_condition(excerpt)
    return raw.strip().casefold() in excerpt.casefold()


def _lines(text: str) -> list[str]:
    parts = [
        " ".join(part.split())
        for chunk in text.splitlines()
        for part in chunk.split(";")
    ]
    return [part for part in parts if part]


def _number(text: str) -> Decimal:
    cleaned = text.replace(",", "").replace(" ", "").strip()
    multiplier = Decimal(1)
    for suffix, factor in sorted(_MULTIPLIERS.items(), key=lambda item: -len(item[0])):
        if cleaned.casefold().endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
            multiplier = Decimal(factor)
            break
    try:
        return Decimal(cleaned) * multiplier
    except InvalidOperation as exc:
        raise ValueError(f"'{text.strip()}' is not a number.") from exc


def _bounds(text: str, pattern: str) -> tuple[Decimal | None, Decimal | None]:
    """Read one value or a low-high range, honouring 'from' and 'up to'."""
    numbers = [_number(match.group(0)) for match in re.finditer(pattern, text)]
    if not numbers:
        raise ValueError("No number was entered.")
    lowered = text.casefold()
    if len(numbers) >= 2:
        return min(numbers), max(numbers)
    if any(
        marker in lowered
        for marker in ("up to", "maximum", "max ", "at most", "no more than")
    ):
        return None, numbers[0]
    if any(
        marker in lowered
        for marker in ("from ", "minimum", "min ", "at least", "starting")
    ):
        return numbers[0], None
    return numbers[0], numbers[0]


_AMOUNT = r"\d[\d, ]*(?:\.\d+)?\s*(?:thousand|million|billion|mln|bn|k|m)?"
_PLAIN_NUMBER = r"\d+(?:[.,]\d+)*"


def _currency(text: str) -> str | None:
    for token, code in _CURRENCIES.items():
        if token.isalpha():
            if re.search(rf"\b{token}\b", text, re.I):
                return code
        elif token in text:
            return code
    return None


def _money_range(text: str) -> dict[str, Any]:
    stripped = re.sub(r"\b(?:AMD|USD|EUR)\b", " ", text, flags=re.I)
    stripped = stripped.replace("֏", " ").replace("$", " ").replace("€", " ")
    minimum, maximum = _bounds(stripped, _AMOUNT)
    money: dict[str, Any] = {}
    if minimum is not None:
        money["min"] = minimum
    if maximum is not None:
        money["max"] = maximum
    currency = _currency(text)
    if currency is not None:
        money["currency"] = currency
    return {"type": "absolute", "range": money}


def _parse_amounts(text: str) -> list[dict[str, Any]]:
    return [_money_range(line) for line in _lines(text)]


def _parse_conditional_amounts(text: str) -> list[dict[str, Any]]:
    return [{"value": item, "conditions": []} for item in _parse_amounts(text)]


def _parse_rates(text: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line in _lines(text):
        minimum, maximum = _bounds(line.replace("%", " "), _PLAIN_NUMBER)
        rate: dict[str, Any] = {"basis": "annual"}
        if minimum is not None:
            rate["min"] = minimum
        if maximum is not None:
            rate["max"] = maximum
        lowered = line.casefold()
        rate["rate_type"] = next(
            (
                value
                for word, value in _RATE_TYPES.items()
                if re.search(rf"\b{word}\b", lowered)
            ),
            "unknown",
        )
        values.append({"value": rate, "conditions": []})
    return values


def _parse_terms(text: str) -> list[dict[str, Any]]:
    if re.fullmatch(
        r"indefinite\s+term(?:\s*\(\s*until\s+requested\s+back\s*\))?", text, re.I
    ):
        return [
            {
                "value": {"indefinite": True, "end_condition": "on_demand"},
                "conditions": [],
            }
        ]
    values: list[dict[str, Any]] = []
    for line in _lines(text):
        months = _months(line)
        values.append({"value": months, "conditions": []})
    return values


def _months(line: str) -> dict[str, Any]:
    years = bool(re.search(r"\byears?\b", line, re.I))
    minimum, maximum = _bounds(
        re.sub(r"[^\d\s,.\-a-z]", " ", line, flags=re.I), _PLAIN_NUMBER
    )
    factor = 12 if years else 1
    term: dict[str, Any] = {}
    if minimum is not None:
        term["min_months"] = int(minimum * factor)
    if maximum is not None:
        term["max_months"] = int(maximum * factor)
    return term


def _parse_percentages(text: str) -> list[dict[str, Any]]:
    values = []
    for line in _lines(text):
        numbers = [
            _number(match.group(0))
            for match in re.finditer(_PLAIN_NUMBER, line.replace("%", " "))
        ]
        if not numbers:
            raise ValueError("No percentage was entered.")
        values.append({"value": numbers[0], "conditions": []})
    return values


def _parse_fees(text: str) -> list[dict[str, Any]]:
    if text.strip().casefold() in _FALSE_WORDS:
        return []
    fees: list[dict[str, Any]] = []
    for line in _lines(text):
        description, _, amount_text = line.partition(":")
        if not amount_text.strip():
            description, amount_text = line, ""
        fee: dict[str, Any] = {
            "description": description.strip() or line,
            "scope": "product",
        }
        if "%" in amount_text:
            fee["rate_pct"] = _number(
                re.sub(r"[^\d., ]", " ", amount_text.split("%")[0])
            )
        elif amount_text.strip():
            fee["amount"] = _bounds(
                re.sub(r"\b(?:AMD|USD|EUR)\b", " ", amount_text, flags=re.I), _AMOUNT
            )[1]
            currency = _currency(amount_text)
            if currency is not None:
                fee["currency"] = currency
        fees.append(fee)
    return fees


def _parse_enum(enum: Any, text: str) -> str:
    wanted = "_".join(text.split()).casefold().replace("-", "_")
    for member in enum:
        if member.value == wanted:
            return member.value
    allowed = ", ".join(member.value for member in enum)
    raise ValueError(f"'{text.strip()}' is not one of: {allowed}.")


def _parse_requirement_policy(text: str) -> dict[str, Any]:
    lowered = " ".join(text.split()).casefold()
    if lowered in _TRUE_WORDS:
        return {"default_required": True}
    if lowered in _FALSE_WORDS:
        return {"default_required": False}
    raise ValueError(f"'{text.strip()}' is neither required nor not required.")


def _parse_bool(text: str) -> bool:
    lowered = " ".join(text.split()).casefold()
    if lowered in _TRUE_WORDS:
        return True
    if lowered in _FALSE_WORDS:
        return False
    raise ValueError(f"'{text.strip()}' is neither yes nor no.")


def _parse_int(text: str) -> int:
    match = re.search(r"\d+", text)
    if match is None:
        raise ValueError(f"'{text.strip()}' is not a whole number.")
    return int(match.group(0))


def _parse_text(text: str) -> str:
    return " ".join(text.split())


def _parse_list(text: str) -> list[str]:
    return _lines(text)


def _format(
    field: ExtractionField,
    instruction: str,
    examples: tuple[str, ...],
    parse: Callable[[str], Any],
    *,
    normalize_text: bool = True,
) -> tuple[ExtractionField, ReviewFieldFormat]:
    return field, ReviewFieldFormat(
        instruction=instruction,
        examples=examples,
        parse=parse,
        normalize_text=normalize_text,
    )


_FORMATS: dict[ExtractionField, ReviewFieldFormat] = dict(
    (
        _format(
            ExtractionField.PRODUCT_NAME,
            "Enter the product name as the passage prints it.",
            ("Overdrafts via Cards not secured with property",),
            _parse_text,
        ),
        _format(
            ExtractionField.FORMAL_TERMS_NAMES,
            "Enter each formal document name on its own line, or separate them with ';'.",
            ("Retail Lending Terms and Conditions",),
            _parse_list,
        ),
        _format(
            ExtractionField.VARIANTS,
            "Enter each variant name on its own line, or separate them with ';'.",
            ("Gold card overdraft; Classic card overdraft",),
            _parse_list,
        ),
        _format(
            ExtractionField.CATEGORY,
            "Enter one category: "
            + ", ".join(member.value for member in LoanCategory)
            + ".",
            ("overdraft",),
            lambda text: _parse_enum(LoanCategory, text),
        ),
        _format(
            ExtractionField.PURPOSE,
            "Enter each stated purpose on its own line, or separate them with ';'.",
            ("Payments; cash withdrawal",),
            _parse_list,
        ),
        _format(
            ExtractionField.LOAN_AMOUNT,
            "Enter the amount or range with its currency; one range per line.",
            ("AMD 100,000-100,000,000", "up to AMD 15 million"),
            _parse_conditional_amounts,
        ),
        _format(
            ExtractionField.INTEREST_RATE,
            "Enter the annual rate or range in percent; one range per line.",
            ("15-21%", "17% fixed"),
            _parse_rates,
        ),
        _format(
            ExtractionField.EFFECTIVE_RATE,
            "Enter the annual percentage rate or range in percent; one range per line.",
            ("16.06-23.13%",),
            _parse_rates,
        ),
        _format(
            ExtractionField.TERM,
            "Enter the term in months or years, or an open-ended term; an "
            "indefinite term needs a matching end condition in the passage.",
            ("12-60 months", "up to 5 years", "Indefinite term (until requested back)"),
            _parse_terms,
        ),
        _format(
            ExtractionField.FEES,
            "Enter one fee per line as 'description: amount', use a percentage for "
            "rate-based fees, or 'none' when the passage states no fees. Each fee is "
            "recorded against this product.",
            ("Change of the loan repayment date: AMD 10,000", "Card service fee: 1.5%"),
            _parse_fees,
        ),
        _format(
            ExtractionField.REPAYMENT,
            "Enter each repayment method on its own line, or separate them with ';'.",
            (
                "Interest is repaid monthly and the utilized amount at the end of the term",
                "Annuity; differentiated",
            ),
            _parse_list,
        ),
        _format(
            ExtractionField.ELIGIBILITY,
            "Enter each eligibility rule on its own line, or separate them with ';'.",
            ("Residents of Armenia aged 18-65",),
            _parse_list,
        ),
        _format(
            ExtractionField.RESIDENCY_REQUIREMENTS,
            "Enter each residency rule on its own line, or separate them with ';'.",
            ("Citizens and non-citizens resident in Armenia",),
            _parse_list,
        ),
        _format(
            ExtractionField.AGE_REQUIREMENTS,
            "Enter the age range; one range per line.",
            ("18-65", "at least 18"),
            _parse_list,
        ),
        _format(
            ExtractionField.APPLICATION_CHANNEL,
            "Enter each application channel on its own line, or separate them with ';'.",
            ("Branch; Online banking",),
            _parse_list,
        ),
        _format(
            ExtractionField.REQUIRED_DOCUMENTS,
            "Enter each document on its own line, or separate them with ';'. Add "
            "'upon request' to a document the passage marks that way.",
            ("Passport; Social card; Income statement upon request",),
            _parse_list,
        ),
        _format(
            ExtractionField.SPECIAL_CONDITIONS,
            "Enter each special condition on its own line, or separate them with ';'.",
            ("Interest rate increases by 0.5% for a differentiated schedule",),
            _parse_list,
        ),
        _format(
            ExtractionField.COLLATERAL,
            "Enter each collateral requirement on its own line, or 'none' when the "
            "passage states the loan is unsecured.",
            ("Residential property", "none"),
            _parse_list,
        ),
        _format(
            ExtractionField.INCOME_VERIFICATION_REQUIRED,
            "Enter 'required' or 'not required'.",
            ("required",),
            _parse_requirement_policy,
        ),
        _format(
            ExtractionField.CREDITWORTHINESS_ASSESSMENT_REQUIRED,
            "Enter 'required' or 'not required'.",
            ("required",),
            _parse_requirement_policy,
        ),
        _format(
            ExtractionField.PROPERTY_MARKET,
            "Enter one property market: "
            + ", ".join(member.value for member in PropertyMarket)
            + ".",
            ("secondary",),
            lambda text: _parse_enum(PropertyMarket, text),
        ),
        _format(
            ExtractionField.DOWN_PAYMENT_PCT,
            "Enter the down payment as a percentage; one value per line.",
            ("30%",),
            _parse_percentages,
            normalize_text=False,
        ),
        _format(
            ExtractionField.LTV_PCT,
            "Enter the loan-to-value ratio as a percentage; one value per line.",
            ("70%",),
            _parse_percentages,
            normalize_text=False,
        ),
        _format(
            ExtractionField.PROPERTY_REQUIREMENTS,
            "Enter each property requirement on its own line, or separate them with ';'.",
            ("Apartment in an apartment building",),
            _parse_list,
        ),
        _format(
            ExtractionField.CREDIT_LIMIT,
            "Enter the credit limit or range with its currency; one range per line.",
            ("AMD 100,000-10,000,000",),
            _parse_amounts,
        ),
        _format(
            ExtractionField.GRACE_PERIOD_DAYS,
            "Enter the grace period as a whole number of days.",
            ("55",),
            _parse_int,
        ),
        _format(
            ExtractionField.REVOLVING,
            "Enter 'yes' or 'no'.",
            ("yes",),
            _parse_bool,
        ),
        _format(
            ExtractionField.LINKED_ACCOUNT_OR_CARD,
            "Enter the linked account or card as the passage prints it.",
            ("Debit card account",),
            _parse_text,
        ),
    )
)
