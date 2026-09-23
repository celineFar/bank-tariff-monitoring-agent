from datetime import UTC, datetime

from app.domain.acquisition import NetworkPayload, SourceLocator, SourceType
from app.domain.normalization import NormalizedBlockType
from app.services.api_payload_normalizer import normalize_network_payload


def _payload(body: str, mime_type: str = "application/json") -> NetworkPayload:
    url = "https://ameriabank.am/api/terms"
    return NetworkPayload(
        url=url,
        method="GET",
        status_code=200,
        mime_type=mime_type,
        body_text=body,
        size_bytes=len(body.encode()),
        sha256="a" * 64,
        retrieved_at=datetime.now(UTC),
        locator=SourceLocator(source_url=url, source_type=SourceType.API),
    )


def test_json_payload_is_flattened_with_json_path_evidence() -> None:
    document, warnings = normalize_network_payload(
        _payload('{"rates":[{"currency":"AMD","value":"13%"}]}')
    )

    assert warnings == ()
    assert [block.fields["path"] for block in document.blocks] == [
        "$['rates'][0]['currency']",
        "$['rates'][0]['value']",
    ]
    assert document.blocks[1].type is NormalizedBlockType.KEY_VALUE
    assert (
        document.blocks[1].source_refs[0].locator.json_path == "$['rates'][0]['value']"
    )
    assert document.blocks[1].scalar_candidates[0].unit == "percent"


def test_invalid_json_is_retained_as_raw_text_with_warning() -> None:
    document, warnings = normalize_network_payload(_payload("{broken"))

    assert document.blocks[0].text == "{broken"
    assert len(warnings) == 1
