import pytest

from app.domain.acquisition import StoredArtifact
from app.services.artifact_store import ArtifactStoreError, FileSystemArtifactStore


@pytest.mark.asyncio
async def test_artifact_store_reads_and_verifies_saved_content(tmp_path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    artifact = await store.save(
        b"source bytes",
        role="linked_document",
        media_type="application/pdf",
        extension="pdf",
    )

    assert await store.read(artifact) == b"source bytes"


@pytest.mark.asyncio
async def test_artifact_store_rejects_path_escape(tmp_path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    artifact = StoredArtifact(
        role="linked_document",
        sha256="a" * 64,
        size_bytes=1,
        media_type="application/pdf",
        relative_path="../outside.pdf",
    )

    with pytest.raises(ArtifactStoreError, match="escaped"):
        await store.read(artifact)
