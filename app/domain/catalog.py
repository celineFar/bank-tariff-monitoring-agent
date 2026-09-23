from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import validate_offering_product


class CatalogModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class CatalogLanguage(StrEnum):
    ENGLISH = "en"
    ARMENIAN = "hy"


def normalize_catalog_term(value: str) -> str:
    """Return the stable catalog-key form used for validation and exact matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"[_\W]+", " ", normalized, flags=re.UNICODE).strip()


class LocalizedCatalogTerms(CatalogModel):
    name: str = Field(min_length=1, max_length=200)
    aliases: tuple[str, ...] = ()
    synonyms: tuple[str, ...] = ()
    transliterations: tuple[str, ...] = ()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("localized catalog name must not be empty")
        return normalized

    @field_validator("aliases", "synonyms", "transliterations")
    @classmethod
    def validate_terms(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        stripped = tuple(value.strip() for value in values)
        if any(not value for value in stripped):
            raise ValueError("catalog resolution terms must not be empty")
        normalized = [normalize_catalog_term(value) for value in stripped]
        if len(normalized) != len(set(normalized)):
            raise ValueError("catalog resolution terms must be unique")
        return stripped

    def all_terms(self) -> tuple[str, ...]:
        return (self.name, *self.aliases, *self.synonyms, *self.transliterations)


def _validate_localized_names(
    localized_names: dict[CatalogLanguage, LocalizedCatalogTerms],
) -> dict[CatalogLanguage, LocalizedCatalogTerms]:
    required = {CatalogLanguage.ENGLISH, CatalogLanguage.ARMENIAN}
    if set(localized_names) != required:
        raise ValueError("catalog entries require exactly English and Armenian names")
    return localized_names


class ProductFamilyCatalogEntry(CatalogModel):
    product: ProductType
    localized_names: dict[CatalogLanguage, LocalizedCatalogTerms]

    @field_validator("localized_names")
    @classmethod
    def validate_localized_names(
        cls, value: dict[CatalogLanguage, LocalizedCatalogTerms]
    ) -> dict[CatalogLanguage, LocalizedCatalogTerms]:
        return _validate_localized_names(value)


class SeedCatalogEntry(CatalogModel):
    product: ProductType
    offering_id: OfferingId
    display_name: str = Field(min_length=1, max_length=200)
    seed_url: HttpUrl
    enabled: bool = True
    language: str | None = Field(default=None, min_length=2, max_length=35)
    localized_names: dict[CatalogLanguage, LocalizedCatalogTerms]
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display_name must not be empty")
        return normalized

    @field_validator("localized_names")
    @classmethod
    def validate_localized_names(
        cls, value: dict[CatalogLanguage, LocalizedCatalogTerms]
    ) -> dict[CatalogLanguage, LocalizedCatalogTerms]:
        return _validate_localized_names(value)

    @model_validator(mode="after")
    def validate_entry(self) -> SeedCatalogEntry:
        validate_offering_product(self.product, self.offering_id)
        if self.seed_url.scheme != "https":
            raise ValueError("seed_url must use HTTPS")
        english_name = self.localized_names[CatalogLanguage.ENGLISH].name
        if normalize_catalog_term(self.display_name) != normalize_catalog_term(
            english_name
        ):
            raise ValueError("display_name must match the English localized name")
        return self


class SeedCatalog(CatalogModel):
    version: int = Field(default=2, ge=2)
    families: tuple[ProductFamilyCatalogEntry, ...] = Field(min_length=1)
    offerings: tuple[SeedCatalogEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_entries(self) -> SeedCatalog:
        family_products = [entry.product for entry in self.families]
        if len(family_products) != len(set(family_products)):
            raise ValueError("catalog family product values must be unique")
        if set(family_products) != set(ProductType):
            raise ValueError("catalog must define every supported product family")
        offering_ids = [entry.offering_id for entry in self.offerings]
        if len(offering_ids) != len(set(offering_ids)):
            raise ValueError("catalog offering_id values must be unique")
        active_urls = [str(entry.seed_url) for entry in self.offerings if entry.enabled]
        if len(active_urls) != len(set(active_urls)):
            raise ValueError("enabled catalog seed_url values must be unique")
        self._validate_term_collisions(
            ((entry.product.value, entry.localized_names) for entry in self.families),
            kind="family",
        )
        self._validate_term_collisions(
            (
                (entry.offering_id.value, entry.localized_names)
                for entry in self.offerings
            ),
            kind="offering",
        )
        return self

    @staticmethod
    def _validate_term_collisions(entries, *, kind: str) -> None:
        owners: dict[str, str] = {}
        for owner, localized_names in entries:
            owner_terms: set[str] = set()
            for terms in localized_names.values():
                for term in terms.all_terms():
                    normalized = normalize_catalog_term(term)
                    if not normalized:
                        raise ValueError("normalized catalog term must not be empty")
                    if normalized in owner_terms:
                        raise ValueError(
                            f"duplicate normalized {kind} term for {owner}: {term}"
                        )
                    owner_terms.add(normalized)
                    previous_owner = owners.get(normalized)
                    if previous_owner is not None and previous_owner != owner:
                        raise ValueError(
                            f"normalized {kind} term collision between "
                            f"{previous_owner} and {owner}: {term}"
                        )
                    owners[normalized] = owner

    def enabled_for(self, product: ProductType) -> tuple[SeedCatalogEntry, ...]:
        return tuple(
            entry
            for entry in self.offerings
            if entry.enabled and entry.product is product
        )

    def get(self, product: ProductType, offering_id: OfferingId) -> SeedCatalogEntry:
        validate_offering_product(product, offering_id)
        for entry in self.offerings:
            if entry.product is product and entry.offering_id is offering_id:
                return entry
        raise KeyError(offering_id.value)

    def find_by_seed_url(self, url: str) -> SeedCatalogEntry | None:
        """Return the offering a URL is the seed of, ignoring a trailing slash."""
        wanted = url.strip().rstrip("/")
        for entry in self.offerings:
            if str(entry.seed_url).rstrip("/") == wanted:
                return entry
        return None

    def family(self, product: ProductType) -> ProductFamilyCatalogEntry:
        for entry in self.families:
            if entry.product is product:
                return entry
        raise KeyError(product.value)
