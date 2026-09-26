from types import SimpleNamespace

import pytest

from app.config import AcquisitionSettings, HttpSettings
from app.services.browser_renderer import (
    BrowserRenderingError,
    BrowserRenderingFailure,
    PlaywrightBrowserRenderer,
    _RouteDecision,
)

MAIN_FRAME = object()
PAGE = SimpleNamespace(main_frame=MAIN_FRAME)
RENDERER = PlaywrightBrowserRenderer(HttpSettings(), AcquisitionSettings())


def _request(
    url="https://ameriabank.am/api/terms",
    *,
    method="GET",
    resource_type="fetch",
    navigation=False,
    frame=MAIN_FRAME,
):
    return SimpleNamespace(
        url=url,
        method=method,
        resource_type=resource_type,
        frame=frame,
        is_navigation_request=lambda: navigation,
    )


def test_an_allowlisted_read_is_let_through() -> None:
    assert RENDERER.decide(_request(), page=PAGE, loaded=True) is _RouteDecision.ALLOW


@pytest.mark.parametrize(
    "request_",
    [
        _request(method="POST"),
        _request(resource_type="image"),
        _request(url="https://tracker.example.com/pixel"),
    ],
)
def test_writes_heavy_assets_and_other_hosts_are_blocked(request_) -> None:
    assert RENDERER.decide(request_, page=PAGE, loaded=True) is _RouteDecision.BLOCK


def test_the_first_navigation_is_allowed() -> None:
    request = _request(
        "https://ameriabank.am/overdraft", resource_type="document", navigation=True
    )

    assert RENDERER.decide(request, page=PAGE, loaded=False) is _RouteDecision.ALLOW


def test_a_main_frame_navigation_after_load_keeps_the_page() -> None:
    request = _request(
        "https://ameriabank.am/other", resource_type="document", navigation=True
    )

    assert RENDERER.decide(request, page=PAGE, loaded=True) is _RouteDecision.STAY


def test_an_embedded_frame_may_still_navigate() -> None:
    request = _request(
        "https://ameriabank.am/widget",
        resource_type="document",
        navigation=True,
        frame=object(),
    )

    assert RENDERER.decide(request, page=PAGE, loaded=True) is _RouteDecision.ALLOW


def _chain(*urls):
    request = None
    for url in urls:
        request = SimpleNamespace(url=url, redirected_from=request)
    return request


def test_an_allowlisted_redirect_chain_passes() -> None:
    RENDERER._check_redirect_chain(
        _chain("https://ameriabank.am/a", "https://www.ameriabank.am/a")
    )


def test_a_redirect_hop_outside_the_allowlist_fails() -> None:
    with pytest.raises(BrowserRenderingError) as caught:
        RENDERER._check_redirect_chain(
            _chain(
                "https://ameriabank.am/a",
                "https://sso.example.com/bounce",
                "https://ameriabank.am/b",
            )
        )

    assert caught.value.reason is BrowserRenderingFailure.DISALLOWED_REDIRECT


def test_too_many_redirect_hops_fail() -> None:
    hops = [f"https://ameriabank.am/{index}" for index in range(8)]

    with pytest.raises(BrowserRenderingError) as caught:
        RENDERER._check_redirect_chain(_chain(*hops))

    assert caught.value.reason is BrowserRenderingFailure.REDIRECT_LIMIT_EXCEEDED
