import httpx
import pytest

from app.config import HttpSettings
from app.services.document_downloader import (
    DocumentCandidate,
    DocumentDownloader,
    DocumentDownloadError,
)

SOURCE_URL = "https://ameriabank.am/files/document"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mime_type", "content"),
    [
        ("application/pdf", b"%PDF-1.7\ntest\n%%EOF"),
        ("application/msword", bytes.fromhex("D0CF11E0A1B11AE1") + b"doc"),
        (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"PK\x03\x04docx",
        ),
    ],
)
async def test_downloads_supported_documents_with_matching_signatures(
    mime_type: str, content: bytes
) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"Content-Type": mime_type},
            content=content,
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        document = await DocumentDownloader(client, HttpSettings()).download(
            DocumentCandidate(SOURCE_URL)
        )

    assert document.mime_type == mime_type
    assert document.content == content
    assert document.size_bytes == len(content)


@pytest.mark.asyncio
async def test_rejects_document_bytes_that_do_not_match_declared_type() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            content=b"not a pdf",
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        downloader = DocumentDownloader(client, HttpSettings())
        with pytest.raises(DocumentDownloadError) as caught:
            await downloader.download(DocumentCandidate(SOURCE_URL))

    assert caught.value.reason == "INVALID_DOCUMENT_SIGNATURE"
