from pathlib import Path

import pytest

from app.config.seed_catalog import SeedCatalogError, load_seed_catalog
from app.domain.models import OfferingId, ProductType


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "seeds.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_default_catalog_contains_every_approved_offering() -> None:
    catalog = load_seed_catalog()

    assert len(catalog.offerings) == 13
    assert len(catalog.enabled_for(ProductType.CONSUMER_LOAN)) == 4
    assert len(catalog.enabled_for(ProductType.MORTGAGE)) == 9
    assert (
        catalog.get(
            ProductType.CONSUMER_LOAN,
            OfferingId.CONSUMER_STANDARD,
        ).seed_url.host
        == "ameriabank.am"
    )


@pytest.mark.parametrize(
    ("offerings", "message"),
    [
        (
            """
  - product: consumer_loan
    offering_id: consumer_standard
    display_name: First
    seed_url: https://ameriabank.am/first
  - product: consumer_loan
    offering_id: consumer_standard
    display_name: Duplicate
    seed_url: https://ameriabank.am/second
""",
            "validation failed",
        ),
        (
            """
  - product: consumer_loan
    offering_id: consumer_standard
    display_name: First
    seed_url: https://ameriabank.am/same
  - product: consumer_loan
    offering_id: overdraft
    display_name: Duplicate URL
    seed_url: https://ameriabank.am/same
""",
            "validation failed",
        ),
        (
            """
  - product: mortgage
    offering_id: consumer_standard
    display_name: Wrong family
    seed_url: https://ameriabank.am/wrong
""",
            "validation failed",
        ),
        (
            """
  - product: consumer_loan
    offering_id: consumer_standard
    display_name: Insecure
    seed_url: http://ameriabank.am/insecure
""",
            "validation failed",
        ),
        (
            """
  - product: consumer_loan
    offering_id: consumer_standard
    display_name: Wrong host
    seed_url: https://example.com/not-official
""",
            "invalid seed URL",
        ),
    ],
)
def test_catalog_rejects_invalid_entries(
    tmp_path: Path, offerings: str, message: str
) -> None:
    path = _write(tmp_path, f"version: 1\nofferings:{offerings}")

    with pytest.raises(SeedCatalogError, match=message):
        load_seed_catalog(path)


def test_catalog_rejects_invalid_yaml_and_non_mapping_root(tmp_path: Path) -> None:
    with pytest.raises(SeedCatalogError, match="invalid seed catalog YAML"):
        load_seed_catalog(_write(tmp_path, "offerings: ["))

    with pytest.raises(SeedCatalogError, match="root must be a mapping"):
        load_seed_catalog(_write(tmp_path, "- item"))


def test_catalog_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SeedCatalogError, match="cannot read seed catalog"):
        load_seed_catalog(tmp_path / "missing.yaml")
