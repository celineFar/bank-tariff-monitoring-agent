import pytest

from app.security.urls import DisallowedSourceUrl, validate_source_url

ALLOWED = ("ameriabank.am", "www.ameriabank.am")


def test_official_https_url_is_allowed() -> None:
    assert validate_source_url("https://ameriabank.am/loans", ALLOWED)


def test_the_default_https_port_may_be_explicit() -> None:
    assert validate_source_url("https://ameriabank.am:443/loans", ALLOWED)


@pytest.mark.parametrize(
    "url",
    [
        "http://ameriabank.am/loans",
        "https://evil.example/loans",
        "https://ameriabank.am.evil.example/loans",
        "https://127.0.0.1/document.pdf",
        "https://user:password@ameriabank.am/document.pdf",
        "https://ameriabank.am:8443/loans",
        "https://ameriabank.am:99999/loans",
    ],
)
def test_unsafe_source_url_fails_closed(url: str) -> None:
    with pytest.raises(DisallowedSourceUrl):
        validate_source_url(url, ALLOWED)
