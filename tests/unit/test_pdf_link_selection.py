"""PDF link selection: Gemini picks the offering's PDFs from their links (SD2)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import ClassVar

import pytest
from google.genai.errors import ClientError

from app.domain.acquisition import (
    AcquisitionInventory,
    AcquisitionMode,
    DocumentArtifact,
    PageArtifact,
    StoredArtifact,
)
from app.domain.models import ProductType
from app.domain.normalization import NormalizationWarningCode
from app.domain.pdf_extraction import (
    PdfAdmissionRole,
    PdfLinkChoice,
    PdfLinkLabel,
    PdfLinkSelection,
)
from app.domain.source_discovery import (
    DecisionSource,
    OfferingContext,
    PdfLinkBatch,
    PdfLinkBatchResponse,
    PdfLinkModelDecision,
    ProductAssociation,
    Relevance,
)
from app.services.normalization import StructuralNormalizationService
from app.services.pdf_link_selection import (
    InMemoryPdfLinkSelectionRepository,
    PdfLinkResponseError,
    PdfLinkSelectionService,
)
from app.services.source_discovery import (
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)

PAGE_URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"
OFFERING = OfferingContext(
    offering_id="mortgage_primary",
    product=ProductType.MORTGAGE,
    display_name="Primary Market Mortgage",
    seed_url=PAGE_URL,
)
NOW = datetime(2026, 9, 26, tzinfo=UTC)


def _document(file_name: str, link_text: str, **extra) -> DocumentArtifact:
    checksum = hashlib.sha256(file_name.encode()).hexdigest()
    url = f"https://ameriabank.am/Content/PDF/{file_name}"
    return DocumentArtifact(
        source_url=url,
        final_url=url,
        document_name=link_text,
        mime_type="application/pdf",
        size_bytes=100,
        sha256=checksum,
        retrieved_at=NOW,
        artifact=StoredArtifact(
            role="linked_document",
            sha256=checksum,
            size_bytes=100,
            media_type="application/pdf",
            relative_path=f"{checksum[:2]}/{checksum}.pdf",
        ),
        link_text=link_text,
        **extra,
    )


OWN = _document(
    "mortgage_personal_purchase_eng.pdf",
    "Terms of the loan for purchase of residential real estate from primary market",
)
FEES = _document("Loan_tariffs_eng.pdf", "Loan service fees")
EXPRESS = _document(
    "mortgage_personal_express_eng.pdf",
    "Terms of express Home Mortgage Loan (Purchase, Construction and Renovation)",
)
OLD = _document(
    "mortgage_personal_purchase_04.06.25_eng.pdf",
    "Terms of the loan (effective from 04.06.25 to 01.09.25)",
)
PRIVACY = _document("privacy-policy.pdf", "Privacy policy")
WEB_INFO = _document("web-info-eng.pdf", "Terms and Conditions")


def _page(*documents: DocumentArtifact) -> PageArtifact:
    return PageArtifact(
        url=PAGE_URL,
        canonical_url=PAGE_URL,
        final_url=PAGE_URL,
        acquisition_mode=AcquisitionMode.BROWSER,
        raw_html=None,
        rendered_html="",
        markdown=None,
        title="Primary Market Mortgage",
        blocks=(),
        tables=(),
        links=(),
        downloadable_documents=documents,
        retrieved_at=NOW,
        inventory=AcquisitionInventory(main_chars=0, tables=0, pdf_links=1),
        content_hash="a" * 64,
        page_content_hash="b" * 64,
    )


class _Selector:
    """Answers by file name, as a model reading the links would."""

    LABELS: ClassVar[dict[str, PdfLinkLabel]] = {
        "mortgage_personal_purchase_eng.pdf": PdfLinkLabel.CURRENT_PRODUCT,
        "Loan_tariffs_eng.pdf": PdfLinkLabel.SHARED_TERMS,
        "mortgage_personal_express_eng.pdf": PdfLinkLabel.RELATED_PRODUCT,
    }

    def __init__(self, *, bad_answers: int = 0, error: Exception | None = None):
        self.batches: list[PdfLinkBatch] = []
        self.bad_answers = bad_answers
        self.error = error

    async def classify(self, batch: PdfLinkBatch) -> PdfLinkBatchResponse:
        self.batches.append(batch)
        if self.error is not None:
            raise self.error
        items = tuple(
            PdfLinkModelDecision(
                id=link.id,
                label=self.LABELS.get(link.file_name, PdfLinkLabel.UNCLEAR),
                role=PdfAdmissionRole.PRODUCT_TERMS,
                reason=f"Judged from the link {link.file_name}.",
            )
            for link in batch.links
        )
        if self.bad_answers:
            self.bad_answers -= 1
            items = items[:-1]
        return PdfLinkBatchResponse(items=items)


def _service(*models, repository=None) -> PdfLinkSelectionService:
    return PdfLinkSelectionService(
        models,
        repository or InMemoryPdfLinkSelectionRepository(),
        policy_version="2",
    )


@pytest.mark.asyncio
async def test_only_admitted_links_are_asked_and_once() -> None:
    selector = _Selector()
    service = _service(("model-a", selector))
    page = _page(OWN, FEES, EXPRESS, OLD, PRIVACY)

    first = await service.select(page, OFFERING)
    second = await service.select(page, OFFERING)

    assert len(selector.batches) == 1
    asked = {link.file_name for link in selector.batches[0].links}
    assert asked == {
        "mortgage_personal_purchase_eng.pdf",
        "Loan_tariffs_eng.pdf",
        "mortgage_personal_express_eng.pdf",
    }
    assert selector.batches[0].offering.display_name == "Primary Market Mortgage"
    assert first.choices[EXPRESS.sha256].label is PdfLinkLabel.RELATED_PRODUCT
    assert not first.choices[EXPRESS.sha256].transcribe
    assert first.choices[FEES.sha256].transcribe
    assert {choice.decided_by for choice in second.choices.values()} == {"cache"}
    assert OLD.sha256 not in first.choices and PRIVACY.sha256 not in first.choices


@pytest.mark.asyncio
async def test_the_cache_is_per_offering() -> None:
    selector = _Selector()
    repository = InMemoryPdfLinkSelectionRepository()
    service = _service(("model-a", selector), repository=repository)

    await service.select(_page(EXPRESS), OFFERING)
    await service.select(
        _page(EXPRESS),
        OFFERING.model_copy(update={"offering_id": "mortgage_express"}),
    )

    assert len(selector.batches) == 2


@pytest.mark.asyncio
async def test_a_wrong_answer_is_asked_again_then_rejected() -> None:
    recovering = _Selector(bad_answers=1)
    assert (
        await _service(("m", recovering)).select(_page(OWN, FEES), OFFERING)
    ).choices
    assert len(recovering.batches) == 2

    with pytest.raises(PdfLinkResponseError):
        await _service(("m", _Selector(bad_answers=5))).select(
            _page(OWN, FEES), OFFERING
        )


@pytest.mark.asyncio
async def test_a_provider_error_moves_to_the_next_model() -> None:
    retired = _Selector(error=ClientError(404, {"error": {"status": "NOT_FOUND"}}))
    fallback = _Selector()

    selection = await _service(("old", retired), ("new", fallback)).select(
        _page(OWN), OFFERING
    )

    assert selection.choices[OWN.sha256].model_name == "new"


def _choice(label: PdfLinkLabel) -> PdfLinkChoice:
    return PdfLinkChoice(
        label=label,
        role=PdfAdmissionRole.PRODUCT_TERMS,
        reason="fixture",
        decided_by="llm",
        model_name="m",
        link_fingerprint="c" * 64,
    )


class _CountingReader:
    def __init__(self) -> None:
        self.reads = 0

    async def read(self, artifact) -> bytes:
        self.reads += 1
        raise OSError("not stored")


@pytest.mark.asyncio
async def test_normalization_does_not_read_a_pdf_that_was_not_selected() -> None:
    reader = _CountingReader()
    normalizer = StructuralNormalizationService(
        artifact_reader=reader, pdf_extractor=None
    )
    selection = PdfLinkSelection(
        offering_id="mortgage_primary",
        choices={
            EXPRESS.sha256: _choice(PdfLinkLabel.RELATED_PRODUCT),
            OWN.sha256: _choice(PdfLinkLabel.CURRENT_PRODUCT),
        },
    )

    bundle = await normalizer.normalize(_page(OWN, EXPRESS), pdf_selection=selection)

    documents = {document.content_sha256: document for document in bundle.documents}
    assert reader.reads == 1  # only the selected PDF was read
    assert documents[EXPRESS.sha256].extraction_method == "pdf_not_selected"
    assert documents[EXPRESS.sha256].pdf_selection.label is PdfLinkLabel.RELATED_PRODUCT
    assert documents[OWN.sha256].pdf_selection.label is PdfLinkLabel.CURRENT_PRODUCT
    codes = [warning.code for warning in bundle.warnings]
    assert NormalizationWarningCode.PDF_SKIPPED_NOT_SELECTED in codes


@pytest.mark.asyncio
async def test_selected_pdfs_are_checked_on_content_and_unselected_decided_by_rule() -> (
    None
):
    from app.config import SourceDiscoverySettings
    from app.domain.acquisition import SourceLocator, SourceType
    from app.domain.normalization import (
        NormalizedBlock,
        NormalizedBlockType,
        NormalizedDocument,
        NormalizedSourceBundle,
        SourceReference,
    )

    def pdf(document: DocumentArtifact, label: PdfLinkLabel, *, content: bool):
        block_id = f"{document.sha256[:8]}:page:1:block:0"
        blocks = (
            (
                NormalizedBlock(
                    id=block_id,
                    type=NormalizedBlockType.PARAGRAPH,
                    raw_text="Nominal rate 12.9%",
                    text="Nominal rate 12.9%",
                    source_refs=(
                        SourceReference(
                            source_item_id=block_id,
                            locator=SourceLocator(
                                source_url=document.final_url,
                                source_type=SourceType.PDF,
                                pdf_page=1,
                            ),
                        ),
                    ),
                ),
            )
            if content
            else ()
        )
        return NormalizedDocument(
            id=f"document:{document.sha256[:12]}",
            name=document.document_name,
            source_url=document.final_url,
            source_type=SourceType.PDF,
            mime_type="application/pdf",
            content_sha256=document.sha256,
            extraction_method="gemini" if content else "pdf_not_selected",
            pdf_selection=_choice(label),
            blocks=blocks,
        )

    page = NormalizedDocument(
        id="page:1",
        name="Primary Market Mortgage",
        source_url=PAGE_URL,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256="a" * 64,
        extraction_method="browser",
    )
    bundle = NormalizedSourceBundle(
        canonical_url=PAGE_URL,
        acquisition_content_hash="d" * 64,
        documents=(
            page,
            pdf(OWN, PdfLinkLabel.CURRENT_PRODUCT, content=True),
            pdf(FEES, PdfLinkLabel.SHARED_TERMS, content=True),
            pdf(EXPRESS, PdfLinkLabel.RELATED_PRODUCT, content=False),
            pdf(WEB_INFO, PdfLinkLabel.CURRENT_PRODUCT, content=True),
        ),
    )

    class _ContentCheck:
        """Reads the website-profile PDF as bank-wide, everything else as own."""

        def __init__(self) -> None:
            self.seen: list[str] = []

        async def classify(self, batch):
            from app.domain.source_discovery import (
                Authority,
                DiscoveryBatchResponse,
                InformationRole,
                ModelSourceAssessment,
                TemporalStatus,
            )

            self.seen.extend(item.title for item in batch.items)
            return DiscoveryBatchResponse(
                items=tuple(
                    ModelSourceAssessment(
                        source_id=item.source_id,
                        product_association=(
                            ProductAssociation.GENERIC_BANK_INFORMATION
                            if "Terms and Conditions" == item.title
                            else ProductAssociation.CURRENT_PRODUCT
                        ),
                        role=InformationRole.PRODUCT_TERMS,
                        relevance=(
                            Relevance.IRRELEVANT
                            if "Terms and Conditions" == item.title
                            else Relevance.RELEVANT
                        ),
                        authority=Authority.OFFICIAL_TERMS,
                        temporal_status=TemporalStatus.CURRENT,
                        reason="content check",
                    )
                    for item in batch.items
                )
            )

    checker = _ContentCheck()
    service = SourceDiscoveryService(
        checker,
        InMemorySourceDiscoveryRepository(),
        SourceDiscoverySettings(),
        model_name="m",
    )

    result = await service.discover(bundle, OFFERING)

    documents = {
        a.document_id: a
        for a in result.assessments
        if a.source_id.startswith("document::")
    }
    own = documents[f"document:{OWN.sha256[:12]}"]
    express = documents[f"document:{EXPRESS.sha256[:12]}"]
    web_info = documents[f"document:{WEB_INFO.sha256[:12]}"]
    # Every transcribed PDF is checked on its content, whatever its link said.
    assert sorted(checker.seen) == sorted(
        [OWN.document_name, FEES.document_name, WEB_INFO.document_name]
    )
    assert own.decision_source is DecisionSource.LLM
    assert own.product_association is ProductAssociation.CURRENT_PRODUCT
    # "Terms and Conditions" looked like the loan's terms from its link; its
    # content shows the website's profile terms.
    assert web_info.relevance is Relevance.IRRELEVANT
    # A PDF the link step dropped has no content: decided by that step.
    assert express.decision_source is DecisionSource.LINK_SELECTION
    assert express.product_association is ProductAssociation.RELATED_PRODUCT
