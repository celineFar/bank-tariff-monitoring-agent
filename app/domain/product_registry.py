from app.domain.crawl import ProductCategory, ProductSeed

CONSUMER_PRODUCTS = (
    ProductSeed(
        product_id="consumer.unsecured",
        category=ProductCategory.CONSUMER,
        name="Consumer loan",
        url_en=(
            "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
        ),
    ),
    ProductSeed(
        product_id="consumer.overdraft",
        category=ProductCategory.CONSUMER,
        name="Overdraft",
        url_en="https://ameriabank.am/en/personal/loans/consumer-loans/overdraft",
    ),
    ProductSeed(
        product_id="consumer.credit_line",
        category=ProductCategory.CONSUMER,
        name="Credit line",
        url_en="https://ameriabank.am/en/personal/loans/consumer-loans/credit-line",
    ),
    ProductSeed(
        product_id="consumer.finance",
        category=ProductCategory.CONSUMER,
        name="Consumer finance",
        url_en=(
            "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-finance"
        ),
    ),
    ProductSeed(
        product_id="consumer.finance.online",
        category=ProductCategory.CONSUMER,
        name="Online consumer finance",
        url_en=(
            "https://ameriabank.am/en/personal/loans/consumer-loan/"
            "online-consumer-finance"
        ),
    ),
)

MORTGAGE_PRODUCTS = (
    ProductSeed(
        product_id="mortgage.online.primary_secondary",
        category=ProductCategory.MORTGAGE,
        name="Online mortgage - primary and secondary market",
        url_en="https://ameriabank.am/en/personal/loans/mortgage/online",
    ),
    ProductSeed(
        product_id="mortgage.purchase.primary",
        category=ProductCategory.MORTGAGE,
        name="Mortgage loan for primary market",
        url_en="https://ameriabank.am/en/personal/loans/mortgage/primary",
    ),
    ProductSeed(
        product_id="mortgage.diaspora",
        category=ProductCategory.MORTGAGE,
        name="Mortgage loan for Diaspora",
        url_en="https://ameriabank.am/en/campaigns/mortgage-loan-for-diaspora",
    ),
    ProductSeed(
        product_id="mortgage.purchase.secondary",
        category=ProductCategory.MORTGAGE,
        name="Real estate loan for secondary market",
        url_en="https://ameriabank.am/en/personal/loans/mortgage/secondary-market",
    ),
    ProductSeed(
        product_id="mortgage.commercial_real_estate",
        category=ProductCategory.MORTGAGE,
        name="Commercial real estate loan",
        url_en=("https://ameriabank.am/en/personal/loans/mortgage/commercial-mortgage"),
    ),
    ProductSeed(
        product_id="mortgage.quick",
        category=ProductCategory.MORTGAGE,
        name="Quick mortgage loan",
        url_en="https://ameriabank.am/en/personal/loans/mortgage/express-loan",
    ),
    ProductSeed(
        product_id="mortgage.no_income_verification",
        category=ProductCategory.MORTGAGE,
        name="Mortgage without income verification",
        url_en=(
            "https://ameriabank.am/en/personal/loans/mortgage/no-income-verification"
        ),
    ),
    ProductSeed(
        product_id="mortgage.renovation",
        category=ProductCategory.MORTGAGE,
        name="Renovation loan",
        url_en=("https://ameriabank.am/en/personal/loans/mortgage/renovation-mortgage"),
    ),
    ProductSeed(
        product_id="mortgage.construction",
        category=ProductCategory.MORTGAGE,
        name="Construction loan",
        url_en=(
            "https://ameriabank.am/en/personal/loans/mortgage/construction-mortgage"
        ),
    ),
)

PRODUCT_REGISTRY = CONSUMER_PRODUCTS + MORTGAGE_PRODUCTS

if len({product.product_id for product in PRODUCT_REGISTRY}) != len(PRODUCT_REGISTRY):
    raise RuntimeError("product registry contains duplicate product IDs")
