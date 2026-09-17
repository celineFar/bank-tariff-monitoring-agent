import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.discovery import IngestedSource, SourceCandidateType, StoredArtifact
from app.domain.extraction import ExtractedBlockType, ExtractedDocument
from app.services.content_extractor import (
    ContentExtractionError,
    ContentExtractionErrorCode,
    DocumentContentExtractor,
)
from app.services.local_artifact_store import LocalArtifactStore

NOW = datetime(2026, 9, 17, 6, tzinfo=UTC)
URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-finance"
HTML = b"""<!doctype html>
<html lang="en">
  <body>
    <header><p>Bank-wide header</p></header>
    <nav><a href="/other">Unrelated navigation</a></nav>
    <main id="wsc_main_content">
      <h1>Consumer finance</h1>
      <p>See the <a href="/en/terms">full terms</a>.</p>
      <div class="loan-fact">
        <span class="label">Loan amount</span>
        <span class="value">50,000 - 6,000,000 AMD</span>
      </div>
      <h2>Requirements</h2>
      <ul><li>Applicant must be an adult.</li><li>Proof of income.</li></ul>
      <table>
        <caption>Rates</caption>
        <tr><th>Currency</th><th>Rate</th></tr>
        <tr><td>AMD</td><td>14%</td></tr>
      </table>
      <script>throw new Error('must never be content')</script>
    </main>
    <footer><p>Bank-wide footer</p></footer>
  </body>
</html>"""


class RecordingRepository:
    def __init__(self) -> None:
        self.saved: list[ExtractedDocument] = []

    async def save_extraction(self, extraction: ExtractedDocument) -> None:
        self.saved.append(extraction)


async def _source(store: LocalArtifactStore, content: bytes = HTML) -> IngestedSource:
    checksum = hashlib.sha256(content).hexdigest()
    artifact = await store.put(
        content=content,
        sha256=checksum,
        mime_type="text/html",
    )
    return IngestedSource(
        product_id="consumer.finance",
        candidate_type=SourceCandidateType.PRODUCT_PAGE,
        source_url=URL,
        final_url=URL,
        retrieved_at=NOW,
        artifact=artifact,
    )


@pytest.mark.asyncio
async def test_extracts_saved_html_to_stable_structured_json(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    repository = RecordingRepository()
    source = await _source(store)
    extractor = DocumentContentExtractor(store, repository, clock=lambda: NOW)

    first = await extractor.extract(source)
    repeated = await extractor.extract(source)

    assert first.language == "en"
    assert first.representation_artifact.storage_key.startswith("extracted/")
    assert first.representation_artifact.storage_key.endswith(".json")
    assert repeated.representation_artifact.sha256 == first.representation_artifact.sha256
    assert repeated.representation_artifact.created is False
    assert [block.block_id for block in repeated.blocks] == [
        block.block_id for block in first.blocks
    ]
    assert len(repository.saved) == 2

    block_types = [block.block_type for block in first.blocks]
    assert block_types == [
        ExtractedBlockType.HEADING,
        ExtractedBlockType.PARAGRAPH,
        ExtractedBlockType.FACT,
        ExtractedBlockType.HEADING,
        ExtractedBlockType.LIST_ITEM,
        ExtractedBlockType.LIST_ITEM,
        ExtractedBlockType.TABLE,
    ]
    fact = first.blocks[2]
    assert fact.label == "Loan amount"
    assert fact.text == "50,000 - 6,000,000 AMD"
    assert fact.section == ("Consumer finance",)
    assert fact.source_locator.css_path == "main#wsc_main_content > div"
    assert first.blocks[1].links[0].target == "https://ameriabank.am/en/terms"
    assert first.blocks[-1].table is not None
    assert first.blocks[-1].table.rows[1].cells == ("AMD", "14%")
    assert all("header" not in block.text.casefold() for block in first.blocks)
    assert all("footer" not in block.text.casefold() for block in first.blocks)
    assert first.statistics.block_count == 7
    assert first.statistics.table_row_count == 2
    assert first.statistics.link_count == 1

    payload = json.loads(
        await store.read(first.representation_artifact.storage_key)
    )
    assert payload["source_sha256"] == source.artifact.sha256
    assert payload["blocks"][2]["block_type"] == "fact"
    assert payload["blocks"][2]["label"] == "Loan amount"
    assert "representation_artifact" not in payload
    assert "extracted_at" not in payload


@pytest.mark.asyncio
async def test_rejects_source_when_saved_bytes_do_not_match_metadata(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    source = await _source(store)
    tampered = source.model_copy(
        update={
            "artifact": StoredArtifact(
                storage_key=source.artifact.storage_key,
                sha256="0" * 64,
                mime_type="text/html",
                size_bytes=source.artifact.size_bytes,
                created=False,
            )
        }
    )
    extractor = DocumentContentExtractor(store, RecordingRepository())

    with pytest.raises(ContentExtractionError) as caught:
        await extractor.extract(tampered)

    assert caught.value.code is ContentExtractionErrorCode.ARTIFACT_INTEGRITY


@pytest.mark.asyncio
async def test_rejects_unregistered_mime_type(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    content = b"%PDF-1.7\n"
    checksum = hashlib.sha256(content).hexdigest()
    artifact = await store.put(
        content=content,
        sha256=checksum,
        mime_type="application/pdf",
    )
    source = IngestedSource(
        product_id="consumer.finance",
        candidate_type=SourceCandidateType.DOCUMENT,
        source_url=f"{URL}/terms.pdf",
        final_url=f"{URL}/terms.pdf",
        retrieved_at=NOW,
        artifact=artifact,
    )

    with pytest.raises(ContentExtractionError) as caught:
        await DocumentContentExtractor(store, RecordingRepository()).extract(source)

    assert caught.value.code is ContentExtractionErrorCode.UNSUPPORTED_MIME_TYPE
