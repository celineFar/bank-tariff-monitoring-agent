"""Embedding retries are split by what the refusal means.

A 5xx is transient and clears in seconds. A 429 is a provider quota and clears
on its own schedule, so giving up on it after 30 seconds discards a whole
validated run for a blip. The quota wait stays in minutes all the same: a run
must not hold a worker and a waiting chat session for a daily quota window.
"""

from __future__ import annotations

import pytest
from google.genai import errors

from app.config.models import RagSettings
from app.services.knowledge_index import (
    EmbeddingError,
    EmbeddingQuotaExhausted,
    GeminiEmbeddingProvider,
)


class _Refusing:
    """A client whose embed_content always fails with one status."""

    def __init__(self, code: int, status: str) -> None:
        self._code = code
        self._status = status
        self.calls = 0
        self.aio = self

    @property
    def models(self):
        return self

    async def embed_content(self, **_):
        self.calls += 1
        raise errors.APIError(
            self._code, {"error": {"message": self._status, "status": self._status}}
        )


def _provider(client: _Refusing) -> GeminiEmbeddingProvider:
    return GeminiEmbeddingProvider(
        client,
        "gemini-embedding-001",
        max_attempts=3,
        backoff_base_seconds=0.0,
        quota_max_attempts=4,
        quota_backoff_base_seconds=0.0,
    )


@pytest.mark.asyncio
async def test_a_quota_refusal_is_retried_on_its_own_budget_and_named() -> None:
    client = _Refusing(429, "RESOURCE_EXHAUSTED")

    with pytest.raises(EmbeddingQuotaExhausted):
        await _provider(client).embed_documents(["chunk"])

    # Its own, larger budget -- not the transient one.
    assert client.calls == 4


@pytest.mark.asyncio
async def test_a_transient_refusal_keeps_the_shorter_budget() -> None:
    client = _Refusing(503, "UNAVAILABLE")

    with pytest.raises(EmbeddingError) as caught:
        await _provider(client).embed_documents(["chunk"])

    assert not isinstance(caught.value, EmbeddingQuotaExhausted)
    assert client.calls == 3


@pytest.mark.asyncio
async def test_a_refusal_that_is_not_retryable_is_not_retried() -> None:
    client = _Refusing(400, "INVALID_ARGUMENT")

    with pytest.raises(EmbeddingError) as caught:
        await _provider(client).embed_documents(["chunk"])

    assert not isinstance(caught.value, EmbeddingQuotaExhausted)
    assert client.calls == 1


def test_the_shipped_quota_wait_stays_within_minutes() -> None:
    """Deferring the index handles a long outage; sleeping through it must not."""
    settings = RagSettings()
    total = sum(
        settings.embedding_quota_backoff_base_seconds * (attempt + 1)
        for attempt in range(settings.embedding_quota_max_attempts - 1)
    )
    assert total <= 600
