from __future__ import annotations

from types import SimpleNamespace

from app.core.settings import get_settings
from app.integrations.embeddings import OpenAICompatibleEmbeddingClient


class FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.create_kwargs: dict[str, object] = {}
        self.create_calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.create_kwargs = kwargs
        self.create_calls.append(kwargs)
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[index, "2.5"])
                for index, _ in enumerate(kwargs["input"], start=1)
            ]
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()


def test_openai_compatible_embedding_client_passes_configured_dimensions(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-v4")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "1536")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    get_settings.cache_clear()

    fake_client = FakeOpenAIClient()

    try:
        client = OpenAICompatibleEmbeddingClient(client=fake_client)
        vectors = client.embed_texts(["MarketPilot embedding test"])
    finally:
        get_settings.cache_clear()

    assert vectors == [[1.0, 2.5]]
    assert fake_client.embeddings.create_kwargs == {
        "model": "text-embedding-v4",
        "input": ["MarketPilot embedding test"],
        "dimensions": 1536,
    }


def test_openai_compatible_embedding_client_splits_large_batches(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-v4")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "1536")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    get_settings.cache_clear()

    fake_client = FakeOpenAIClient()
    texts = [f"text {index}" for index in range(25)]

    try:
        client = OpenAICompatibleEmbeddingClient(client=fake_client)
        vectors = client.embed_texts(texts)
    finally:
        get_settings.cache_clear()

    assert [len(call["input"]) for call in fake_client.embeddings.create_calls] == [
        10,
        10,
        5,
    ]
    assert len(vectors) == len(texts)
    assert vectors[0] == [1.0, 2.5]
    assert vectors[10] == [1.0, 2.5]
    assert vectors[20] == [1.0, 2.5]
