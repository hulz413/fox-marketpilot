from __future__ import annotations

from types import SimpleNamespace

from app.core.settings import get_settings
from app.integrations.embeddings import OpenAICompatibleEmbeddingClient


class FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.create_kwargs: dict[str, object] = {}

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.create_kwargs = kwargs
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[1, "2.5"]),
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
