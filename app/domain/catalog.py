from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import validate_offering_product


class CatalogModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class SeedCatalogEntry(CatalogModel):
    product: ProductType
    offering_id: OfferingId
    display_name: str = Field(min_length=1, max_length=200)
    seed_url: HttpUrl
    enabled: bool = True
    language: str | None = Field(default=None, min_length=2, max_length=35)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_entry(self) -> SeedCatalogEntry:
        validate_offering_product(self.product, self.offering_id)
        if self.seed_url.scheme != "https":
            raise ValueError("seed_url must use HTTPS")
        return self


class SeedCatalog(CatalogModel):
    version: int = Field(default=1, ge=1)
    offerings: tuple[SeedCatalogEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_entries(self) -> SeedCatalog:
        offering_ids = [entry.offering_id for entry in self.offerings]
        if len(offering_ids) != len(set(offering_ids)):
            raise ValueError("catalog offering_id values must be unique")
        active_urls = [str(entry.seed_url) for entry in self.offerings if entry.enabled]
        if len(active_urls) != len(set(active_urls)):
            raise ValueError("enabled catalog seed_url values must be unique")
        return self

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
