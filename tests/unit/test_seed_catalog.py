from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from app.config.seed_catalog import SeedCatalogError, load_seed_catalog
from app.domain.catalog import CatalogLanguage, normalize_catalog_term
from app.domain.models import OfferingId, ProductType


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "seeds.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def _localized(english: str, armenian: str) -> dict[str, object]:
    return {
        "en": {"name": english, "aliases": [f"{english} alias"]},
        "hy": {"name": armenian, "aliases": [f"{armenian} տարբերակ"]},
    }


def _valid_payload() -> dict[str, object]:
    return {
        "version": 2,
        "families": [
            {
                "product": "consumer_loan",
                "localized_names": _localized("Consumer family", "Սպառողական ընտանիք"),
            },
            {
                "product": "mortgage",
                "localized_names": _localized("Mortgage family", "Հիփոթեքային ընտանիք"),
            },
        ],
        "offerings": [
            {
                "product": "consumer_loan",
                "offering_id": "consumer_standard",
                "display_name": "Consumer Loans",
                "seed_url": "https://ameriabank.am/consumer",
                "enabled": True,
                "language": "en",
                "localized_names": _localized("Consumer Loans", "Սպառողական վարկ"),
            },
            {
                "product": "mortgage",
                "offering_id": "mortgage_online",
                "display_name": "Online Mortgage",
                "seed_url": "https://ameriabank.am/mortgage",
                "enabled": True,
                "language": "en",
                "localized_names": _localized("Online Mortgage", "Օնլայն հիփոթեք"),
            },
        ],
    }


def _write_payload(tmp_path: Path, payload: dict[str, object]) -> Path:
    return _write(
        tmp_path,
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
    )


def test_default_catalog_contains_every_approved_offering() -> None:
    catalog = load_seed_catalog()

    assert catalog.version == 2
    assert len(catalog.families) == 2
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


def test_default_catalog_has_bilingual_resolution_terms_for_every_scope() -> None:
    catalog = load_seed_catalog()

    entries = [*catalog.families, *catalog.offerings]
    for entry in entries:
        assert set(entry.localized_names) == {
            CatalogLanguage.ENGLISH,
            CatalogLanguage.ARMENIAN,
        }
        for terms in entry.localized_names.values():
            assert terms.name.strip()
            assert all(normalize_catalog_term(term) for term in terms.all_terms())

    expected_armenian_names = {
        OfferingId.CONSUMER_STANDARD: "Սպառողական վարկ",
        OfferingId.OVERDRAFT: "Օվերդրաֆտ",
        OfferingId.CREDIT_LINE: "Վարկային գիծ",
        OfferingId.ONLINE_CONSUMER_FINANCE: "Օնլայն ապառիկ",
        OfferingId.MORTGAGE_ONLINE: (
            "Առաջնային և երկրորդային շուկաներից բնակարանի ձեռքբերման օնլայն վարկ"
        ),
        OfferingId.MORTGAGE_PRIMARY: "Հիփոթեքային վարկ առաջնային շուկայից",
        OfferingId.MORTGAGE_DIASPORA: "Հիփոթեքային վարկ Սփյուռքի համար",
        OfferingId.MORTGAGE_SECONDARY_MARKET: ("Հիփոթեքային վարկ երկրորդային շուկայից"),
        OfferingId.MORTGAGE_COMMERCIAL: "Առևտրային գույքի ձեռքբերման վարկ",
        OfferingId.MORTGAGE_EXPRESS: "Արագ հիփոթեք",
        OfferingId.MORTGAGE_NO_INCOME_VERIFICATION: (
            "Հիփոթեք առանց եկամուտների ստուգման"
        ),
        OfferingId.MORTGAGE_RENOVATION: "Վերանորոգման վարկ",
        OfferingId.MORTGAGE_CONSTRUCTION: "Կառուցապատման վարկ",
    }
    assert (
        catalog.family(ProductType.CONSUMER_LOAN)
        .localized_names[CatalogLanguage.ARMENIAN]
        .name
        == "Սպառողական վարկեր"
    )
    assert (
        catalog.family(ProductType.MORTGAGE)
        .localized_names[CatalogLanguage.ARMENIAN]
        .name
        == "Հիփոթեքային վարկեր"
    )
    for offering_id, expected_name in expected_armenian_names.items():
        assert (
            catalog.get(offering_id.product, offering_id)
            .localized_names[CatalogLanguage.ARMENIAN]
            .name
            == expected_name
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate_offering", "validation failed"),
        ("duplicate_url", "validation failed"),
        ("wrong_family", "validation failed"),
        ("insecure_url", "validation failed"),
        ("wrong_host", "invalid seed URL"),
    ],
)
def test_catalog_rejects_invalid_entries(
    tmp_path: Path, mutation: str, message: str
) -> None:
    payload = _valid_payload()
    offerings = payload["offerings"]
    assert isinstance(offerings, list)

    if mutation == "duplicate_offering":
        duplicate = deepcopy(offerings[0])
        duplicate["seed_url"] = "https://ameriabank.am/duplicate"
        offerings.append(duplicate)
    elif mutation == "duplicate_url":
        offerings[1]["seed_url"] = offerings[0]["seed_url"]
    elif mutation == "wrong_family":
        offerings[0]["product"] = "mortgage"
    elif mutation == "insecure_url":
        offerings[0]["seed_url"] = "http://ameriabank.am/insecure"
    elif mutation == "wrong_host":
        offerings[0]["seed_url"] = "https://example.com/not-official"

    with pytest.raises(SeedCatalogError, match=message):
        load_seed_catalog(_write_payload(tmp_path, payload))


@pytest.mark.parametrize(
    "mutation",
    [
        "offering_term_collision",
        "family_term_collision",
        "normalized_empty",
        "missing_language",
        "display_name_mismatch",
    ],
)
def test_catalog_rejects_invalid_resolution_vocabulary(
    tmp_path: Path, mutation: str
) -> None:
    payload = _valid_payload()
    families = payload["families"]
    offerings = payload["offerings"]
    assert isinstance(families, list)
    assert isinstance(offerings, list)

    if mutation == "offering_term_collision":
        offerings[1]["localized_names"]["en"]["aliases"] = ["Consumer Loans"]
    elif mutation == "family_term_collision":
        families[1]["localized_names"]["en"]["aliases"] = ["consumer FAMILY"]
    elif mutation == "normalized_empty":
        offerings[0]["localized_names"]["en"]["aliases"] = ["   "]
    elif mutation == "missing_language":
        del offerings[0]["localized_names"]["hy"]
    elif mutation == "display_name_mismatch":
        offerings[0]["display_name"] = "Different"

    with pytest.raises(SeedCatalogError, match="validation failed"):
        load_seed_catalog(_write_payload(tmp_path, payload))


def test_catalog_rejects_invalid_yaml_and_non_mapping_root(tmp_path: Path) -> None:
    with pytest.raises(SeedCatalogError, match="invalid seed catalog YAML"):
        load_seed_catalog(_write(tmp_path, "offerings: ["))

    with pytest.raises(SeedCatalogError, match="root must be a mapping"):
        load_seed_catalog(_write(tmp_path, "- item"))


def test_catalog_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SeedCatalogError, match="cannot read seed catalog"):
        load_seed_catalog(tmp_path / "missing.yaml")
