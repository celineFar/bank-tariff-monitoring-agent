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
    "gemini-embedding-001": (
        ModelPrice(
            model="gemini-embedding-001",
            starts_on=date(2026, 9, 22),
            ends_on=None,
            input_per_million_tokens_usd=0.15,
            output_per_million_tokens_usd=0.0,
        ),
    ),
    "gemini-2.5-flash-lite": (
        ModelPrice(
            model="gemini-2.5-flash-lite",
            starts_on=date(2025, 1, 1),
            ends_on=None,
            input_per_million_tokens_usd=0.10,
            output_per_million_tokens_usd=0.40,
        ),
    ),
    "gemini-2.5-flash": (
        ModelPrice(
            model="gemini-2.5-flash",
            starts_on=date(2025, 1, 1),
            ends_on=None,
            input_per_million_tokens_usd=0.30,
            output_per_million_tokens_usd=2.50,
        ),
    ),
    "gemini-3.8-flash": (
        ModelPrice(
            model="gemini-3.8-flash",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            input_per_million_tokens_usd=0.75,
            output_per_million_tokens_usd=3.75,
        ),
        ModelPrice(
            model="gemini-3.8-flash",
            starts_on=date(2027, 1, 1),
            ends_on=None,
            input_per_million_tokens_usd=1.50,
            output_per_million_tokens_usd=7.50,
        ),
    ),
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
    "gemini-3.6-flash": (
        ModelPrice(
            model="gemini-3.6-flash",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            input_per_million_tokens_usd=0.75,
            output_per_million_tokens_usd=3.75,
        ),
        ModelPrice(
            model="gemini-3.6-flash",
            starts_on=date(2027, 1, 1),
            ends_on=None,
            input_per_million_tokens_usd=1.50,
            output_per_million_tokens_usd=7.50,
        ),
    ),
    "gemini-3.5-flash-lite": (
        ModelPrice(
            model="gemini-3.5-flash-lite",
            starts_on=date(2026, 7, 1),
            ends_on=None,
            input_per_million_tokens_usd=0.30,
            output_per_million_tokens_usd=2.50,
        ),
    ),
    "gemini-3.1-flash-lite": (
        ModelPrice(
            model="gemini-3.1-flash-lite",
            starts_on=date(2026, 5, 1),
            ends_on=date(2027, 5, 7),
            input_per_million_tokens_usd=0.25,
            output_per_million_tokens_usd=1.50,
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


def enforce_model_price_cap(
    models: tuple[str, ...],
    *,
    max_price_per_million_tokens_usd: float,
    on_date: date | None = None,
) -> None:
    for model in models:
        price = get_model_price(model, on_date=on_date)
        if (
            price.input_per_million_tokens_usd > max_price_per_million_tokens_usd
            or price.output_per_million_tokens_usd > max_price_per_million_tokens_usd
        ):
            raise ValueError(
                f"Model {model!r} exceeds the configured ${max_price_per_million_tokens_usd:.2f} "
                "per-million-token ceiling: "
                f"input=${price.input_per_million_tokens_usd:.2f}, "
                f"output=${price.output_per_million_tokens_usd:.2f}"
            )
