"""Quiet entry point for the interactive tariff CLI."""

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore",
    message=r"\[EXPERIMENTAL\] ResumabilityConfig:",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"\[EXPERIMENTAL\] feature FeatureName.JSON_SCHEMA_FOR_FUNC_DECL",
    category=UserWarning,
)

from app.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
