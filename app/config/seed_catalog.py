from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.domain.catalog import SeedCatalog
from app.security.urls import validate_source_url

DEFAULT_SEED_CATALOG_PATH = Path(__file__).with_name("seed_catalog.yaml")


class SeedCatalogError(ValueError):
    pass


def load_seed_catalog(
    path: Path = DEFAULT_SEED_CATALOG_PATH,
    *,
    allowed_hosts: tuple[str, ...] = ("ameriabank.am", "www.ameriabank.am"),
) -> SeedCatalog:
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SeedCatalogError(f"cannot read seed catalog: {path}") from exc
    except yaml.YAMLError as exc:
        raise SeedCatalogError(f"invalid seed catalog YAML: {path}") from exc

    if not isinstance(raw, dict):
        raise SeedCatalogError("seed catalog root must be a mapping")
    try:
        catalog = SeedCatalog.model_validate(raw)
    except ValidationError as exc:
        raise SeedCatalogError("seed catalog validation failed") from exc

    for entry in catalog.offerings:
        try:
            validate_source_url(str(entry.seed_url), allowed_hosts)
        except ValueError as exc:
            raise SeedCatalogError(
                f"invalid seed URL for {entry.offering_id.value}: {exc}"
            ) from exc
    return catalog
