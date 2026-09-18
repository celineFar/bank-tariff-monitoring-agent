from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ModelPrice:
    model: str
    starts_on: date
    ends_on: date | None
    input_per_million_tokens_usd: float
    output_per_million_tokens_usd: float
    basis: str = "Gemini Developer API paid tier"
    source: str = "https://ai.google.dev/gemini-api/docs/pricing"


MODEL_PRICE_CATALOG: dict[str, tuple[ModelPrice, ...]] = {
    "gemini-3.7-flash": (
        ModelPrice(
            model="gemini-3.7-flash",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            input_per_million_tokens_usd=0.75,
            output_per_million_tokens_usd=3.75,
        ),
        ModelPrice(
            model="gemini-3.7-flash",
            starts_on=date(2027, 1, 1),
            ends_on=None,
            input_per_million_tokens_usd=1.50,
            output_per_million_tokens_usd=7.50,
        ),
    ),
}


def get_model_price(model: str, *, on_date: date | None = None) -> ModelPrice:
    effective_date = on_date or date.today()
    for price in MODEL_PRICE_CATALOG.get(model, ()):
        if price.starts_on <= effective_date and (
            price.ends_on is None or effective_date <= price.ends_on
        ):
            return price
    raise ValueError(
        f"No Gemini Developer API price is stored for {model!r} on {effective_date}"
    )
