from app.domain.crawl import ProductCategory, ProductSeed

CONSUMER_PRODUCTS = (
    ProductSeed(
        product_id="consumer.unsecured",
        category=ProductCategory.CONSUMER,
        name="Consumer loan",
        aliases=("consumer loan", "personal loan", "սպառողական վարկ"),
        url_en=(
            "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
        ),
    ),
    ProductSeed(
        product_id="consumer.overdraft",
        category=ProductCategory.CONSUMER,
        name="Overdraft",
        aliases=("overdraft", "օվերդրաֆտ"),
        url_en="https://ameriabank.am/en/personal/loans/consumer-loans/overdraft",
    ),
    ProductSeed(
        product_id="consumer.credit_line",
        category=ProductCategory.CONSUMER,
        name="Credit line",
        aliases=("credit line", "վարկային գիծ"),
        url_en="https://ameriabank.am/en/personal/loans/consumer-loans/credit-line",
    ),
    ProductSeed(
        product_id="consumer.finance",
        category=ProductCategory.CONSUMER,
        name="Consumer finance",
        aliases=("consumer finance", "installment loan", "ապառիկ"),
        url_en=(
            "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-finance"
        ),
    ),
    ProductSeed(
        product_id="consumer.finance.online",
        category=ProductCategory.CONSUMER,
        name="Online consumer finance",
        aliases=("online consumer finance", "online installment", "օնլայն ապառիկ"),
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
        aliases=("online mortgage", "primary and secondary market", "առցանց հիփոթեք"),
        url_en="https://ameriabank.am/en/personal/loans/mortgage/online",
    ),
    ProductSeed(
        product_id="mortgage.purchase.primary",
        category=ProductCategory.MORTGAGE,
        name="Mortgage loan for primary market",
        aliases=("primary market mortgage", "առաջնային շուկայի հիփոթեք"),
        url_en="https://ameriabank.am/en/personal/loans/mortgage/primary",
    ),
    ProductSeed(
        product_id="mortgage.diaspora",
        category=ProductCategory.MORTGAGE,
        name="Mortgage loan for Diaspora",
        aliases=("diaspora mortgage", "mortgage for diaspora", "սփյուռքի հիփոթեք"),
        url_en="https://ameriabank.am/en/campaigns/mortgage-loan-for-diaspora",
    ),
    ProductSeed(
        product_id="mortgage.purchase.secondary",
        category=ProductCategory.MORTGAGE,
        name="Real estate loan for secondary market",
        aliases=("secondary market mortgage", "երկրորդային շուկայի հիփոթեք"),
        url_en="https://ameriabank.am/en/personal/loans/mortgage/secondary-market",
    ),
    ProductSeed(
        product_id="mortgage.commercial_real_estate",
        category=ProductCategory.MORTGAGE,
        name="Commercial real estate loan",
        aliases=("commercial mortgage", "commercial real estate loan"),
        url_en=("https://ameriabank.am/en/personal/loans/mortgage/commercial-mortgage"),
    ),
    ProductSeed(
        product_id="mortgage.quick",
        category=ProductCategory.MORTGAGE,
        name="Quick mortgage loan",
        aliases=("quick mortgage", "express mortgage", "արագ հիփոթեք"),
        url_en="https://ameriabank.am/en/personal/loans/mortgage/express-loan",
    ),
    ProductSeed(
        product_id="mortgage.no_income_verification",
        category=ProductCategory.MORTGAGE,
        name="Mortgage without income verification",
        aliases=(
            "mortgage without income verification",
            "no income verification mortgage",
            "հիփոթեք առանց եկամուտների հիմնավորման",
        ),
        url_en=(
            "https://ameriabank.am/en/personal/loans/mortgage/no-income-verification"
        ),
    ),
    ProductSeed(
        product_id="mortgage.renovation",
        category=ProductCategory.MORTGAGE,
        name="Renovation loan",
        aliases=("renovation mortgage", "renovation loan", "վերանորոգման վարկ"),
        url_en=("https://ameriabank.am/en/personal/loans/mortgage/renovation-mortgage"),
    ),
    ProductSeed(
        product_id="mortgage.construction",
        category=ProductCategory.MORTGAGE,
        name="Construction loan",
        aliases=("construction mortgage", "construction loan", "կառուցապատման վարկ"),
        url_en=(
            "https://ameriabank.am/en/personal/loans/mortgage/construction-mortgage"
        ),
    ),
)

PRODUCT_REGISTRY = CONSUMER_PRODUCTS + MORTGAGE_PRODUCTS

if len({product.product_id for product in PRODUCT_REGISTRY}) != len(PRODUCT_REGISTRY):
    raise RuntimeError("product registry contains duplicate product IDs")
