from __future__ import annotations

import pytest

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.normalization import SourceReference
from app.domain.semantic_extraction import (
    ExtractionBatchResponse,
    ExtractionField,
    ExtractionStatus,
    ModelFieldResult,
)
from app.domain.source_discovery import (
    Authority,
    DecisionSource,
    DiscoveryScope,
    InformationRole,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    TemporalStatus,
)
from app.repositories.file_semantic_extraction import (
    FileSystemSemanticExtractionRepository,
)
from app.repositories.file_source_discovery import (
    FileSystemSourceDiscoveryRepository,
)
from scripts.demonstrate_end_to_end import _import_previous_run_caches

URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"


@pytest.mark.asyncio
async def test_file_source_discovery_cache_reuses_exact_and_structural_entries(
    tmp_path,
) -> None:
    repository = FileSystemSourceDiscoveryRepository(tmp_path)
    assessment = SourceAssessment(
        source_id="terms",
        document_id="page",
        scope=DiscoveryScope.BLOCK,
        product_association=ProductAssociation.CURRENT_PRODUCT,
        role=InformationRole.PRODUCT_TERMS,
        relevance=Relevance.RELEVANT,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        reason="Current official terms",
        decision_source=DecisionSource.LLM,
        input_fingerprint="a" * 64,
        structural_fingerprint="b" * 64,
        source_refs=(
            SourceReference(
                source_item_id="terms",
                locator=SourceLocator(source_url=URL, source_type=SourceType.PAGE),
            ),
        ),
    )

    await repository.save(
        product=ProductType.MORTGAGE,
        policy_version="1",
        prompt_version="2",
        model_name="test-model",
        assessments=(assessment,),
    )

    exact = await repository.get_exact(
        product=ProductType.MORTGAGE,
        policy_version="1",
        prompt_version="2",
        model_name="test-model",
        content_fingerprints=("a" * 64,),
    )
    structural = await repository.get_structural_priors(
        product=ProductType.MORTGAGE,
        policy_version="1",
        prompt_version="2",
        model_name="test-model",
        structural_fingerprints=("b" * 64,),
    )

    assert exact["a" * 64] == assessment
    assert structural["b" * 64] == assessment


@pytest.mark.asyncio
async def test_file_semantic_cache_reuses_an_exact_batch(tmp_path) -> None:
    repository = FileSystemSemanticExtractionRepository(tmp_path)
    response = ExtractionBatchResponse(
        results=(
            ModelFieldResult(
                field=ExtractionField.FEES,
                status=ExtractionStatus.NOT_STATED,
            ),
        )
    )

    await repository.save(
        product=ProductType.MORTGAGE,
        schema_version="2",
        prompt_version="3",
        model_name="test-model",
        values=(("c" * 64, response),),
    )
    cached = await repository.get_exact(
        product=ProductType.MORTGAGE,
        schema_version="2",
        prompt_version="3",
        model_name="test-model",
        fingerprints=("c" * 64,),
    )

    assert cached["c" * 64] == response


@pytest.mark.asyncio
async def test_end_to_end_imports_pdf_cache_from_earlier_numbered_runs(
    tmp_path,
) -> None:
    root = tmp_path / "end-to-end"
    legacy = root / "run_001" / "acquisition" / "source files" / "pdf_cache"
    cached_response = legacy / "ab" / "cached.json"
    cached_response.parent.mkdir(parents=True)
    cached_response.write_text('{"pages": []}', encoding="utf-8")
    flat_cache = root / "acquisition" / "source files" / "pdf_cache"
    flat_response = flat_cache / "cd" / "cached.json"
    flat_response.parent.mkdir(parents=True)
    flat_response.write_text('{"pages": []}', encoding="utf-8")
    current = root / "run_002"
    current.mkdir()
    shared = root / ".cache"

    counts = await _import_previous_run_caches(
        root,
        current_run=current,
        pdf_cache=shared / "pdf-extraction",
        discovery_repository=FileSystemSourceDiscoveryRepository(
            shared / "source-discovery"
        ),
        semantic_repository=FileSystemSemanticExtractionRepository(
            shared / "semantic-extraction"
        ),
    )

    assert counts["pdf"] == 2
    assert (shared / "pdf-extraction" / "ab" / "cached.json").is_file()
    assert (shared / "pdf-extraction" / "cd" / "cached.json").is_file()
