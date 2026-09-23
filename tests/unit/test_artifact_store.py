import asyncio

import pytest

from app.services.artifact_store import ArtifactStoreError, FileSystemArtifactStore


@pytest.mark.asyncio
async def test_content_addressed_store_is_idempotent(tmp_path) -> None:
    store = FileSystemArtifactStore(tmp_path / "artifacts")

    first, second = await asyncio.gather(
        store.save(
            b"official content",
            role="raw_html",
            media_type="text/html",
            extension="html",
        ),
        store.save(
            b"official content",
            role="raw_html",
            media_type="text/html",
            extension="html",
        ),
    )

    assert first.sha256 == second.sha256
    assert first.relative_path == second.relative_path
    assert (
        tmp_path / "artifacts" / first.relative_path
    ).read_bytes() == b"official content"


@pytest.mark.asyncio
async def test_artifact_store_rejects_unsafe_extension(tmp_path) -> None:
    store = FileSystemArtifactStore(tmp_path)

    with pytest.raises(ArtifactStoreError):
        await store.save(
            b"content",
            role="raw",
            media_type="text/plain",
            extension="../html",
        )
