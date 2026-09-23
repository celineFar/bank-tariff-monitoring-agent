import hashlib

import pytest

from app.domain.models import OfferingId, ProductType
from app.repositories.structured_tariff_query import UnitEmbeddingInput
from app.services.structured_unit_embeddings import StructuredUnitEmbeddingService


@pytest.mark.asyncio
async def test_unit_embedding_reuses_identical_content_and_skips_second_run() -> None:
    content = "Synthetic supported purpose"
    checksum = hashlib.sha256(content.encode()).hexdigest()

    class Repository:
        pending = (
            UnitEmbeddingInput("a" * 64, content, checksum),
            UnitEmbeddingInput("b" * 64, content, checksum),
        )
        saved = ()

        async def missing(self, **kwargs):
            return self.pending

        async def save(self, *, model_id, vectors):
            self.saved = vectors
            self.pending = ()
            return len(vectors)

    class Cache:
        def __init__(self):
            self.values = {}

        async def get_many(self, model_id, dimensions, task_type, hashes):
            return {key: self.values[key] for key in hashes if key in self.values}

        async def put_many(self, model_id, dimensions, task_type, values):
            self.values.update(values)

    class DocumentProvider:
        model_name = "test-model"
        dimensions = 768

        def __init__(self):
            self.calls = []

        async def embed_documents(self, contents):
            self.calls.append(list(contents))
            return [[0.1] * 768 for _ in contents]

    class QueryProvider:
        model_name = "test-model"
        dimensions = 768

        async def embed_query(self, content):
            return [0.1] * 768

    repository = Repository()
    provider = DocumentProvider()
    service = StructuredUnitEmbeddingService(
        repository, Cache(), provider, QueryProvider()
    )
    scope = {
        "bank": "ameria",
        "product": ProductType.CONSUMER_LOAN,
        "offering_ids": (OfferingId.CONSUMER_STANDARD,),
    }
    assert await service.ensure(**scope) == 2
    assert provider.calls == [[content]]
    assert len(repository.saved) == 2
    assert await service.ensure(**scope) == 0
    assert provider.calls == [[content]]
