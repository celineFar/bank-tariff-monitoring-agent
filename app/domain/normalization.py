import re
import unicodedata
from decimal import Decimal, InvalidOperation

_SPACE_RE = re.compile(r"[\s\u00a0]+")
_NUMBER_SEPARATORS_RE = re.compile(r"(?<=\d)[ ,](?=\d{3}(?:\D|$))")


def normalize_text(value: str) -> str:
    return _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value)).strip()


def normalize_money_text(value: str) -> str:
    return _NUMBER_SEPARATORS_RE.sub("", normalize_text(value).upper())


def normalize_percentage(value: str) -> str:
    normalized = normalize_text(value).replace(",", ".").replace("%", "").strip()
    try:
        number = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid percentage: {value!r}") from exc
    return f"{number.normalize()}%"
