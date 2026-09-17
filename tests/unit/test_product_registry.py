from app.domain.crawl import ProductCategory
from app.domain.product_registry import (
    CONSUMER_PRODUCTS,
    MORTGAGE_PRODUCTS,
    PRODUCT_REGISTRY,
)


def test_phase_one_registry_contains_every_configured_subproduct() -> None:
    assert len(CONSUMER_PRODUCTS) == 5
    assert len(MORTGAGE_PRODUCTS) == 9
    assert len(PRODUCT_REGISTRY) == 14
    assert len({product.product_id for product in PRODUCT_REGISTRY}) == 14
    assert {product.category for product in CONSUMER_PRODUCTS} == {
        ProductCategory.CONSUMER
    }
    assert {product.category for product in MORTGAGE_PRODUCTS} == {
        ProductCategory.MORTGAGE
    }


def test_registry_preserves_nonstandard_seed_paths() -> None:
    by_id = {product.product_id: str(product.url_en) for product in PRODUCT_REGISTRY}

    assert "/consumer-loan/online-consumer-finance" in by_id["consumer.finance.online"]
    assert "/campaigns/mortgage-loan-for-diaspora" in by_id["mortgage.diaspora"]
