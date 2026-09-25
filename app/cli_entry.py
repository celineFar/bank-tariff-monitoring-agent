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

from app.config import get_settings  # noqa: E402
from app.services.logging_setup import configure_application_logging  # noqa: E402
from app.services.telemetry import configure_telemetry  # noqa: E402

_settings = get_settings()
configure_application_logging(_settings.observability, console_output=False)
# Chat-initiated monitoring runs execute in this process (the ADK-native
# monitoring node), so the CLI exports spans for the whole turn.
configure_telemetry(_settings.observability, component="cli")

from app.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
