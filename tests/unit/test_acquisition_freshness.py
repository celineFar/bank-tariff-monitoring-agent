from datetime import UTC, datetime, timedelta

import pytest

from app.domain.acquisition import (
    AcquisitionInventory,
    AcquisitionMode,
    AcquisitionWarning,
    AcquisitionWarningCode,
    DocumentArtifact,
    PageArtifact,
    StoredArtifact,
)
from app.services.acquisition_errors import AcquisitionError, AcquisitionFailure
from app.services.acquisition_freshness import FreshnessGatedAcquisitionService

URL = "https://ameriabank.am/en/personal/loans/consumer-loans/overdraft"
NOW = datetime(2026, 9, 22, 18, 0, tzinfo=UTC)


def _artifact(retrieved_at: datetime, *, documents=(), warnings=()) -> PageArtifact:
    return PageArtifact(
        url=URL,
        canonical_url=URL,
        final_url=URL,
        title="Overdraft",
        language="en",
        acquisition_mode=AcquisitionMode.BROWSER,
        raw_html="<html></html>",
        rendered_html=None,
        markdown="# Overdraft",
        blocks=(),
        tables=(),
        links=(),
        downloadable_documents=documents,
        network_payloads=(),
        warnings=warnings,
        retrieved_at=retrieved_at,
        inventory=AcquisitionInventory(main_chars=0, tables=0, pdf_links=0, payloads=0),
        content_hash="a" * 64,
        page_content_hash="b" * 64,
    )


def _document() -> DocumentArtifact:
    return DocumentArtifact(
        source_url="https://ameriabank.am/terms.pdf",
        final_url="https://ameriabank.am/terms.pdf",
        document_name="Official terms",
        mime_type="application/pdf",
        size_bytes=17,
        sha256="c" * 64,
        retrieved_at=NOW,
        artifact=StoredArtifact(
            role="linked_document_1",
            sha256="c" * 64,
            size_bytes=17,
            media_type="application/pdf",
            relative_path="cc/" + "c" * 64 + ".pdf",
        ),
    )


class _Acquisition:
    def __init__(self, artifact: PageArtifact) -> None:
        self._artifact = artifact
        self.calls: list[str] = []

    async def acquire(self, url: str) -> PageArtifact:
        self.calls.append(url)
        return self._artifact


class _Snapshots:
    def __init__(self, stored: PageArtifact | None = None) -> None:
        self.stored = stored
        self.saved: list[tuple[str, PageArtifact]] = []

    async def get_latest(self, url: str) -> PageArtifact | None:
        return self.stored

    async def save(self, url: str, artifact: PageArtifact) -> None:
        self.saved.append((url, artifact))
        self.stored = artifact


class _Reader:
    def __init__(self, *, readable: bool) -> None:
        self._readable = readable

    async def read(self, artifact: StoredArtifact) -> bytes:
        if not self._readable:
            raise OSError("artifact was swept")
        return b"%PDF-1.7 official"


def _service(acquisition, snapshots, *, hours=1.0, reader=None, now=NOW):
    return FreshnessGatedAcquisitionService(
        acquisition,
        snapshots,
        freshness_hours=hours,
        artifact_reader=reader,
        now=lambda: now,
    )


@pytest.mark.asyncio
async def test_a_recent_acquisition_is_reused_without_fetching() -> None:
    stored = _artifact(NOW - timedelta(minutes=16), documents=(_document(),))
    acquisition = _Acquisition(_artifact(NOW))

    result = await _service(
        acquisition, _Snapshots(stored), reader=_Reader(readable=True)
    ).acquire(URL)

    assert acquisition.calls == []
    assert result.retrieved_at == stored.retrieved_at
    assert result.reused is True
    assert stored.reused is False


@pytest.mark.asyncio
async def test_an_acquisition_past_the_window_is_fetched_again() -> None:
    stored = _artifact(NOW - timedelta(hours=1, minutes=1))
    acquisition = _Acquisition(_artifact(NOW))

    result = await _service(acquisition, _Snapshots(stored)).acquire(URL)

    assert acquisition.calls == [URL]
    assert result.retrieved_at == NOW
    assert result.reused is False


@pytest.mark.asyncio
async def test_a_zero_window_always_fetches() -> None:
    stored = _artifact(NOW)
    acquisition = _Acquisition(_artifact(NOW))

    await _service(acquisition, _Snapshots(stored), hours=0).acquire(URL)

    assert acquisition.calls == [URL]


@pytest.mark.asyncio
async def test_a_fresh_acquisition_whose_downloads_are_gone_is_fetched_again() -> None:
    # The page markup travels inside the stored artifact, but its PDFs live in
    # temporary storage. Reusing the artifact without them would normalize the
    # page as if the bank had published no tariff documents.
    stored = _artifact(NOW - timedelta(minutes=5), documents=(_document(),))
    acquisition = _Acquisition(_artifact(NOW))

    await _service(
        acquisition, _Snapshots(stored), reader=_Reader(readable=False)
    ).acquire(URL)

    assert acquisition.calls == [URL]


@pytest.mark.asyncio
async def test_a_fresh_acquisition_is_stored_for_the_next_run() -> None:
    acquisition = _Acquisition(_artifact(NOW))
    snapshots = _Snapshots()

    await _service(acquisition, snapshots).acquire(URL)

    assert [url for url, _ in snapshots.saved] == [URL]


@pytest.mark.asyncio
async def test_a_failing_store_costs_a_fetch_not_the_run() -> None:
    class _Broken(_Snapshots):
        async def get_latest(self, url: str) -> PageArtifact | None:
            raise RuntimeError("database is unreachable")

        async def save(self, url: str, artifact: PageArtifact) -> None:
            raise RuntimeError("database is unreachable")

    acquisition = _Acquisition(_artifact(NOW))

    result = await _service(acquisition, _Broken()).acquire(URL)

    assert acquisition.calls == [URL]
    assert result.content_hash == "a" * 64


@pytest.mark.asyncio
async def test_a_failed_acquisition_never_falls_back_to_stored_content() -> None:
    class _Failing:
        async def acquire(self, url: str) -> PageArtifact:
            raise RuntimeError("the bank is unreachable")

    stored = _artifact(NOW - timedelta(days=3))

    with pytest.raises(RuntimeError, match="unreachable"):
        await _service(_Failing(), _Snapshots(stored)).acquire(URL)


@pytest.mark.asyncio
async def test_a_partial_acquisition_is_not_stored_and_is_fetched_again() -> None:
    partial = _artifact(
        NOW,
        warnings=(
            AcquisitionWarning(
                code=AcquisitionWarningCode.LINKED_DOCUMENT_FAILED,
                detail="l12: source.timeout",
            ),
        ),
    )
    acquisition = _Acquisition(partial)
    snapshots = _Snapshots()
    service = _service(acquisition, snapshots)

    await service.acquire(URL)
    await service.acquire(URL)

    assert snapshots.saved == []
    assert acquisition.calls == [URL, URL]


@pytest.mark.asyncio
async def test_a_permanently_dead_link_does_not_prevent_reuse() -> None:
    # A 404 is the same on every fetch: refusing to reuse the acquisition would
    # refetch the page and every PDF on every run without ever filling the gap.
    with_dead_link = _artifact(
        NOW,
        warnings=(
            AcquisitionWarning(
                code=AcquisitionWarningCode.LINKED_DOCUMENT_MISSING,
                detail="l55: source.not_found",
            ),
        ),
    )
    acquisition = _Acquisition(with_dead_link)
    snapshots = _Snapshots()
    service = _service(acquisition, snapshots)

    await service.acquire(URL)
    second = await service.acquire(URL)

    assert [url for url, _ in snapshots.saved] == [URL]
    assert acquisition.calls == [URL]
    assert second.reused is True


@pytest.mark.asyncio
async def test_a_cap_warning_alone_does_not_prevent_reuse() -> None:
    capped = _artifact(
        NOW,
        warnings=(
            AcquisitionWarning(
                code=AcquisitionWarningCode.LINKED_DOCUMENT_CAP_REACHED,
                detail="2 of 42",
            ),
        ),
    )
    snapshots = _Snapshots()

    await _service(_Acquisition(capped), snapshots).acquire(URL)

    assert [url for url, _ in snapshots.saved] == [URL]


@pytest.mark.asyncio
async def test_an_acquisition_failing_the_gate_is_not_stored() -> None:
    class _Incomplete:
        async def acquire(self, url: str) -> PageArtifact:
            raise AcquisitionError(
                AcquisitionFailure.INCOMPLETE_CONTENT,
                "thin",
                reasons=("tables 3 -> 0",),
            )

    snapshots = _Snapshots()

    with pytest.raises(AcquisitionError):
        await _service(_Incomplete(), snapshots).acquire(URL)

    assert snapshots.saved == []
