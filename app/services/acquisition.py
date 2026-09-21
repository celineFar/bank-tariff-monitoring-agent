from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import unquote, urlsplit

import httpx

from app.config import AcquisitionSettings, Settings
from app.domain.acquisition import (
    AcquisitionMode,
    DocumentArtifact,
    NetworkPayload,
    PageArtifact,
    StoredArtifact,
)
from app.services.artifact_store import FileSystemArtifactStore
from app.services.browser_renderer import (
    BrowserRenderer,
    BrowserRenderingError,
)
from app.services.failure_mapping import source_failure_code
from app.services.html_parser import HtmlArtifactParser, ParsedHtml
from app.services.html_retriever import HtmlRetriever
from app.services.pdf_downloader import (
    PdfCandidate,
    PdfDownloader,
    PdfDownloadError,
)

_INTERACTIVE_HTML = re.compile(
    r"aria-expanded\s*=\s*['\"]false|data-(?:bs-)?toggle\s*=|role\s*=\s*['\"]tab",
    re.IGNORECASE,
)
_APP_SHELL_HTML = re.compile(
    r"id\s*=\s*['\"](?:app|root|__next)['\"]|__NEXT_DATA__",
    re.IGNORECASE,
)


class AcquisitionFailure(StrEnum):
    BROWSER_REQUIRED = "BROWSER_REQUIRED"
    BROWSER_FAILED = "BROWSER_FAILED"
    INSUFFICIENT_CONTENT = "INSUFFICIENT_CONTENT"


class AcquisitionError(RuntimeError):
    def __init__(self, reason: AcquisitionFailure, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class ArtifactStore(Protocol):
    async def save(
        self,
        content: bytes,
        *,
        role: str,
        media_type: str,
        extension: str,
    ) -> StoredArtifact: ...


class AcquisitionService:
    """Acquire reproducible official source material without semantic extraction."""

    def __init__(
        self,
        *,
        html_retriever: HtmlRetriever,
        html_parser: HtmlArtifactParser,
        pdf_downloader: PdfDownloader,
        artifact_store: ArtifactStore,
        settings: AcquisitionSettings,
        browser_renderer: BrowserRenderer | None = None,
    ) -> None:
        self._html_retriever = html_retriever
        self._html_parser = html_parser
        self._pdf_downloader = pdf_downloader
        self._artifact_store = artifact_store
        self._settings = settings
        self._browser_renderer = browser_renderer

    async def acquire(self, url: str) -> PageArtifact:
        retrieved = await self._html_retriever.retrieve(url)
        raw_parsed = self._html_parser.parse(
            retrieved.html, source_url=retrieved.final_url
        )
        parsed = raw_parsed
        rendered_html: str | None = None
        final_url = retrieved.final_url
        network_payloads: tuple[NetworkPayload, ...] = ()
        mode = AcquisitionMode.STATIC
        warnings: list[str] = []

        requires_browser = self._requires_browser(retrieved.html, raw_parsed)
        if requires_browser:
            if not self._settings.browser_enabled:
                if not self._is_useful(raw_parsed):
                    raise AcquisitionError(
                        AcquisitionFailure.BROWSER_REQUIRED,
                        "Static HTML is insufficient and browser acquisition is disabled",
                    )
                warnings.append("Browser rendering was indicated but is disabled")
            elif self._browser_renderer is None:
                raise AcquisitionError(
                    AcquisitionFailure.BROWSER_REQUIRED,
                    "Static HTML requires browser rendering but no renderer is configured",
                )
            else:
                try:
                    rendered = await self._browser_renderer.render(retrieved.final_url)
                except BrowserRenderingError as exc:
                    if not self._is_useful(raw_parsed):
                        raise AcquisitionError(
                            AcquisitionFailure.BROWSER_FAILED,
                            "Browser rendering failed and static content is insufficient",
                        ) from exc
                    warnings.append(f"Browser rendering failed: {exc.reason.value}")
                else:
                    rendered_parsed = self._html_parser.parse(
                        rendered.html, source_url=rendered.final_url
                    )
                    if self._is_useful(rendered_parsed):
                        rendered_html = rendered.html
                        final_url = rendered.final_url
                        parsed = rendered_parsed
                        network_payloads = rendered.network_payloads
                        mode = AcquisitionMode.BROWSER
                    elif self._is_useful(raw_parsed):
                        warnings.append(
                            "Browser rendering returned insufficient content; using static HTML"
                        )

        if not self._is_useful(parsed):
            raise AcquisitionError(
                AcquisitionFailure.INSUFFICIENT_CONTENT,
                "Acquired page did not contain enough useful public content",
            )

        stored: list[StoredArtifact] = []
        raw_artifact = await self._artifact_store.save(
            retrieved.html.encode("utf-8"),
            role="raw_html",
            media_type="text/html",
            extension="html",
        )
        stored.append(raw_artifact)
        if rendered_html is not None:
            stored.append(
                await self._artifact_store.save(
                    rendered_html.encode("utf-8"),
                    role="rendered_html",
                    media_type="text/html",
                    extension="html",
                )
            )
        if parsed.markdown:
            stored.append(
                await self._artifact_store.save(
                    parsed.markdown.encode("utf-8"),
                    role="markdown",
                    media_type="text/markdown",
                    extension="md",
                )
            )

        persisted_payloads: list[NetworkPayload] = []
        for index, payload in enumerate(network_payloads, start=1):
            artifact = await self._artifact_store.save(
                payload.body_text.encode("utf-8"),
                role=f"network_payload_{index}",
                media_type=payload.mime_type,
                extension="json" if "json" in payload.mime_type else "txt",
            )
            stored.append(artifact)
            persisted_payloads.append(payload.model_copy(update={"artifact": artifact}))

        documents, document_warnings = await self._download_documents(parsed)
        warnings.extend(document_warnings)
        stored.extend(document.artifact for document in documents)

        content_hash = self._content_hash(
            canonical_url=parsed.canonical_url,
            raw_sha256=retrieved.sha256,
            rendered_html=rendered_html,
            parsed=parsed,
            documents=documents,
            network_payloads=tuple(persisted_payloads),
        )
        return PageArtifact(
            url=retrieved.source_url,
            canonical_url=parsed.canonical_url,
            final_url=final_url,
            title=parsed.title,
            language=parsed.language,
            acquisition_mode=mode,
            raw_html=retrieved.html,
            rendered_html=rendered_html,
            markdown=parsed.markdown,
            blocks=parsed.blocks,
            tables=parsed.tables,
            links=parsed.links,
            images=parsed.images,
            interactive_controls=parsed.interactive_controls,
            downloadable_documents=documents,
            network_payloads=tuple(persisted_payloads),
            stored_artifacts=tuple(stored),
            warnings=tuple(warnings),
            retrieved_at=retrieved.retrieved_at,
            content_hash=content_hash,
        )

    def _requires_browser(self, html: str, parsed: ParsedHtml) -> bool:
        return (
            not self._is_useful(parsed)
            or bool(_INTERACTIVE_HTML.search(html))
            or (bool(_APP_SHELL_HTML.search(html)) and len(parsed.visible_text) < 2_000)
        )

    def _is_useful(self, parsed: ParsedHtml) -> bool:
        return len(parsed.visible_text) >= self._settings.min_static_text_chars or bool(
            parsed.tables
        )

    async def _download_documents(
        self, parsed: ParsedHtml
    ) -> tuple[tuple[DocumentArtifact, ...], tuple[str, ...]]:
        documents: list[DocumentArtifact] = []
        warnings: list[str] = []
        candidates = []
        seen_urls: set[str] = set()
        for link in parsed.links:
            url = str(link.url)
            if (
                link.downloadable
                and link.same_allowlisted_source
                and url not in seen_urls
            ):
                candidates.append(link)
                seen_urls.add(url)
            if len(candidates) >= self._settings.max_linked_documents:
                break
        for link in candidates:
            try:
                downloaded = await self._pdf_downloader.download(
                    PdfCandidate(url=str(link.url))
                )
            except PdfDownloadError as exc:
                warnings.append(
                    f"Linked document {link.id} was not downloaded: "
                    f"{source_failure_code(exc, stage='acquisition').value}"
                )
                continue
            artifact = await self._artifact_store.save(
                downloaded.content,
                role=f"linked_document_{len(documents) + 1}",
                media_type=downloaded.mime_type,
                extension="pdf",
            )
            documents.append(
                DocumentArtifact(
                    source_url=downloaded.source_url,
                    final_url=downloaded.final_url,
                    document_name=self._document_name(link.text, downloaded.final_url),
                    mime_type=downloaded.mime_type,
                    size_bytes=downloaded.size_bytes,
                    sha256=downloaded.sha256,
                    retrieved_at=downloaded.retrieved_at,
                    artifact=artifact,
                    link_id=link.id,
                    link_text=link.text,
                    link_title=link.title,
                    **self._document_origin(parsed, link.id),
                )
            )
        return tuple(documents), tuple(warnings)

    @staticmethod
    def _document_origin(parsed: ParsedHtml, link_id: str) -> dict[str, object]:
        for block in parsed.blocks:
            if link_id in block.link_ids:
                return {
                    "origin_block_id": block.id,
                    "origin_heading_path": block.heading_path,
                    "nearby_text": block.text[:5000],
                }
        return {}

    @staticmethod
    def _document_name(link_text: str, url: str) -> str:
        if link_text.strip():
            return link_text.strip()[:1000]
        filename = PurePosixPath(unquote(urlsplit(url).path)).name
        return filename[:1000] or "linked-document.pdf"

    @staticmethod
    def _content_hash(
        *,
        canonical_url: str,
        raw_sha256: str,
        rendered_html: str | None,
        parsed: ParsedHtml,
        documents: tuple[DocumentArtifact, ...],
        network_payloads: tuple[NetworkPayload, ...],
    ) -> str:
        material = {
            "canonical_url": canonical_url,
            "raw_sha256": raw_sha256,
            "rendered_sha256": (
                hashlib.sha256(rendered_html.encode("utf-8")).hexdigest()
                if rendered_html is not None
                else None
            ),
            "blocks": [block.model_dump(mode="json") for block in parsed.blocks],
            "tables": [table.model_dump(mode="json") for table in parsed.tables],
            "links": [link.model_dump(mode="json") for link in parsed.links],
            "images": [image.model_dump(mode="json") for image in parsed.images],
            "interactive_controls": [
                control.model_dump(mode="json")
                for control in parsed.interactive_controls
            ],
            "documents": [
                {
                    "sha256": document.sha256,
                    "link_id": document.link_id,
                    "link_text": document.link_text,
                    "link_title": document.link_title,
                    "origin_block_id": document.origin_block_id,
                    "origin_heading_path": document.origin_heading_path,
                    "nearby_text": document.nearby_text,
                }
                for document in documents
            ],
            "network_payloads": [payload.sha256 for payload in network_payloads],
        }
        encoded = json.dumps(
            material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def build_file_system_artifact_store(path: str) -> FileSystemArtifactStore:
    """Small composition helper for entry points that own configuration."""
    return FileSystemArtifactStore(Path(path))


def build_acquisition_service(
    client: httpx.AsyncClient, settings: Settings
) -> AcquisitionService:
    """Compose acquisition for API/worker ownership; never expose it to Gemini."""
    from app.services.browser_renderer import PlaywrightBrowserRenderer

    browser = (
        PlaywrightBrowserRenderer(settings.http, settings.acquisition)
        if settings.acquisition.browser_enabled
        else None
    )
    return AcquisitionService(
        html_retriever=HtmlRetriever(client, settings.http),
        html_parser=HtmlArtifactParser(settings.http.allowed_source_hosts),
        pdf_downloader=PdfDownloader(client, settings.http),
        artifact_store=FileSystemArtifactStore(settings.application.artifact_temp_dir),
        settings=settings.acquisition,
        browser_renderer=browser,
    )
