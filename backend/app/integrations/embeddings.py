from __future__ import annotations

import hashlib
import math
import re
from typing import Optional, Protocol

from openai import OpenAI

from app.core.settings import get_settings
from app.integrations.langsmith import is_langsmith_tracing_enabled


class EmbeddingClient(Protocol):
    model: str
    provider: str
    is_fallback: bool

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding per input text."""


class OpenAICompatibleEmbeddingClient:
    is_fallback = False

    def __init__(self, client: Optional[OpenAI] = None) -> None:
        settings = get_settings()
        client_kwargs = {"api_key": settings.embedding_api_key}
        if settings.embedding_base_url:
            client_kwargs["base_url"] = settings.embedding_base_url

        self.client = client or OpenAI(**client_kwargs)
        if is_langsmith_tracing_enabled():
            from langsmith.wrappers import wrap_openai

            self.client = wrap_openai(self.client)

        self.model = settings.embedding_model
        self.provider = settings.embedding_provider
        self.dimension = settings.embedding_dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimension,
        )
        embeddings = [item.embedding for item in response.data]

        if len(embeddings) != len(texts):
            raise RuntimeError("Embedding provider returned an unexpected result count.")

        return [[float(value) for value in embedding] for embedding in embeddings]


class DeterministicEmbeddingClient:
    provider = "deterministic"
    model = "deterministic-local-hashing"
    is_fallback = True

    def __init__(self, dimension: int) -> None:
        self.dimension = max(8, int(dimension))

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0 for _ in range(self.dimension)]
        tokens = tokenize_text(text)

        if not tokens:
            tokens = [text.strip() or "empty"]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            weight = 1.0 + (digest[4] / 255.0)
            vector[index] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]


def tokenize_text(text: str) -> list[str]:
    normalized = text.lower()
    ascii_tokens = re.findall(r"[a-z0-9_]+", normalized)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    return ascii_tokens + chinese_chars


def get_embedding_client() -> Optional[EmbeddingClient]:
    settings = get_settings()

    if not settings.rag_retrieval_enabled:
        return None

    if settings.embedding_api_key:
        return OpenAICompatibleEmbeddingClient()

    if settings.environment.lower() in {"local", "test"}:
        return DeterministicEmbeddingClient(settings.embedding_dimension)

    return None
