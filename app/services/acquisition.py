from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import unquote, urlsplit

import httpx

from app.config import AcquisitionSettings, Settings
from app.domain.acquisition import (
    AcquisitionInventory,
    AcquisitionMode,
    AcquisitionWarning,
    AcquisitionWarningCode,
    DocumentArtifact,
    PageArtifact,
    StoredArtifact,
)
from app.domain.monitoring import SourceFailureCode
from app.services.acquisition_errors import AcquisitionError, AcquisitionFailure
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

__all__ = [
    "AcquisitionError",
    "AcquisitionFailure",
    "AcquisitionService",
    "build_acquisition_service",
    "build_file_system_artifact_store",
    "completeness_floor_failures",
]


class ArtifactStore(Protocol):
    async def save(
        self,
        content: bytes,
        *,
        role: str,
        media_type: str,
        extension: str,
    ) -> StoredArtifact: ...


def completeness_floor_failures(
    inventory: AcquisitionInventory, settings: AcquisitionSettings
) -> tuple[str, ...]:
    """Why an acquisition is too thin to monitor from, or () when it is not.

    Two conditions, both required. The page must carry real text outside the
    site's header, menus and footer -- every bank page has ~9k characters of
    those, so counting the whole page proves nothing. And it must carry one of
    the structures tariffs are published in, a table or a PDF link -- or, for a
    page that publishes its terms as text (a campaign landing page), a clearly
    larger body of main text. A page rendered from its menus alone has 75-1,179
    characters of main text.
    """
    failures: list[str] = []
    if inventory.main_chars < settings.min_main_content_chars:
        failures.append(
            f"main_chars {inventory.main_chars} < {settings.min_main_content_chars}"
        )
    if not (
        inventory.tables
        or inventory.pdf_links
        or inventory.main_chars >= settings.min_main_content_chars_without_structure
    ):
        failures.append(
            "no tables or PDF links, and main_chars "
            f"{inventory.main_chars} < "
            f"{settings.min_main_content_chars_without_structure}"
        )
    return tuple(failures)


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
        parsed = self._html_parser.parse(retrieved.html, source_url=retrieved.final_url)
        rendered_html: str | None = None
        final_url = retrieved.final_url
        mode = AcquisitionMode.STATIC
        interactions = 0
        warnings: list[AcquisitionWarning] = []

        # With the browser enabled, every page is rendered: the bank's tariff
        # tables and PDF links exist only in the rendered page,
        # and static HTML never carries them. A render that fails fails the
        # acquisition -- falling back to static HTML used to monitor six of
        # thirteen seeds from their navigation menus.
        if self._settings.browser_enabled:
            if self._browser_renderer is None:
                raise AcquisitionError(
                    AcquisitionFailure.BROWSER_UNAVAILABLE,
                    "Browser acquisition is enabled but no renderer is configured",
                )
            try:
                rendered = await self._browser_renderer.render(retrieved.final_url)
            except BrowserRenderingError as exc:
                raise AcquisitionError(
                    AcquisitionFailure.BROWSER_FAILED,
                    f"Browser rendering failed: {exc.reason.value}",
                ) from exc
            rendered_html = rendered.html
            final_url = rendered.final_url
            parsed = self._html_parser.parse(
                rendered.html, source_url=rendered.final_url
            )
            mode = AcquisitionMode.BROWSER
            interactions = rendered.interactions
            if rendered.interaction_cap_reached:
                warnings.append(
                    AcquisitionWarning(
                        code=AcquisitionWarningCode.INTERACTION_CAP_REACHED,
                        detail=f"stopped after {interactions} interactions",
                    )
                )

        inventory = AcquisitionInventory(
            main_chars=len(parsed.main_text),
            tables=len(parsed.tables),
            pdf_links=len(self._pdf_link_urls(parsed)),
        )
        if failures := completeness_floor_failures(inventory, self._settings):
            raise AcquisitionError(
                AcquisitionFailure.INCOMPLETE_CONTENT,
                "Acquired page is too incomplete to monitor: " + "; ".join(failures),
                reasons=failures,
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

        documents, document_warnings = await self._download_documents(parsed)
        warnings.extend(document_warnings)
        stored.extend(document.artifact for document in documents)

        page_content_hash = self._page_content_hash(
            canonical_url=parsed.canonical_url, parsed=parsed
        )
        content_hash = self._content_hash(
            page_content_hash=page_content_hash,
            documents=documents,
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
            stored_artifacts=tuple(stored),
            warnings=tuple(warnings),
            inventory=inventory,
            interactions=interactions,
            retrieved_at=retrieved.retrieved_at,
            content_hash=content_hash,
            page_content_hash=page_content_hash,
        )

    @staticmethod
    def _pdf_link_urls(parsed: ParsedHtml) -> tuple[str, ...]:
        """The distinct same-host document links the page advertises, in page order."""
        urls: dict[str, None] = {}
        for link in parsed.links:
            if link.downloadable and link.same_allowlisted_source:
                urls.setdefault(str(link.url), None)
        return tuple(urls)

    async def _download_documents(
        self, parsed: ParsedHtml
    ) -> tuple[tuple[DocumentArtifact, ...], tuple[AcquisitionWarning, ...]]:
        documents: list[DocumentArtifact] = []
        warnings: list[AcquisitionWarning] = []
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
        if len(candidates) > self._settings.max_linked_documents:
            skipped = len(candidates) - self._settings.max_linked_documents
            warnings.append(
                AcquisitionWarning(
                    code=AcquisitionWarningCode.LINKED_DOCUMENT_CAP_REACHED,
                    detail=(
                        f"{skipped} of {len(candidates)} linked documents not "
                        f"downloaded (cap {self._settings.max_linked_documents})"
                    ),
                )
            )
            candidates = candidates[: self._settings.max_linked_documents]
        for link in candidates:
            try:
                downloaded = await self._pdf_downloader.download(
                    PdfCandidate(url=str(link.url))
                )
            except PdfDownloadError as exc:
                code = source_failure_code(exc, stage="acquisition")
                warnings.append(
                    AcquisitionWarning(
                        code=(
                            AcquisitionWarningCode.LINKED_DOCUMENT_MISSING
                            if code is SourceFailureCode.NOT_FOUND
                            else AcquisitionWarningCode.LINKED_DOCUMENT_FAILED
                        ),
                        detail=f"{link.id}: {code.value}",
                    )
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
        # The link's own row, item or paragraph describes it; the whole block
        # (a table, a list) would lend it its neighbours' dates and words.
        link = next((item for item in parsed.links if item.id == link_id), None)
        for block in parsed.blocks:
            if link_id in block.link_ids:
                context = link.context_text if link is not None else ""
                return {
                    "origin_block_id": block.id,
                    "origin_heading_path": block.heading_path,
                    "nearby_text": (context or block.text)[:5000],
                }
        return {}

    @staticmethod
    def _document_name(link_text: str, url: str) -> str:
        if link_text.strip():
            return link_text.strip()[:1000]
        filename = PurePosixPath(unquote(urlsplit(url).path)).name
        return filename[:1000] or "linked-document.pdf"

    @staticmethod
    def _page_content_hash(*, canonical_url: str, parsed: ParsedHtml) -> str:
        """Identify the page by what it shows, with nothing linked folded in.

        Built from the parsed structure only, never from the raw or rendered
        HTML bytes: the bank's ASP.NET pages carry `__VIEWSTATE`,
        `__EVENTVALIDATION` and `__RequestVerificationToken` values that change
        on every request, so hashing the bytes gave an unchanged page a new id
        on every fetch -- and, through the evidence ids built on it, missed
        every extraction cache. The bytes are still stored as artifacts.

        The site's header, navigation and footer are left out too. They are the
        same on every page and carry no tariff, but a footer module that loads
        late (the consumer-loan page's language notice) made two renders of an
        unchanged page disagree and renamed it.
        """
        chrome = parsed.chrome_ids
        material = {
            "canonical_url": canonical_url,
            "blocks": [
                block.model_dump(mode="json")
                for block in parsed.blocks
                if block.id not in chrome
            ],
            "tables": [
                table.model_dump(mode="json")
                for table in parsed.tables
                if table.id not in chrome
            ],
            "links": [
                link.model_dump(mode="json")
                for link in parsed.links
                if link.id not in chrome
            ],
            "images": [
                image.model_dump(mode="json")
                for image in parsed.images
                if image.id not in chrome
            ],
            "interactive_controls": [
                control.model_dump(mode="json")
                for control in parsed.interactive_controls
                if control.id not in chrome
            ],
        }
        return _digest(material)

    @staticmethod
    def _content_hash(
        *,
        page_content_hash: str,
        documents: tuple[DocumentArtifact, ...],
    ) -> str:
        """Identify the whole acquisition: the page and everything reached from it."""
        material = {
            "page_content_hash": page_content_hash,
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
        }
        return _digest(material)


def _digest(material: dict[str, object]) -> str:
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
