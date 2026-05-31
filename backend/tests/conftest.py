from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.settings import get_settings


@pytest.fixture(autouse=True)
def isolate_external_service_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGSMITH_API_KEY", "")
    monkeypatch.setenv("LANGSMITH_PROJECT", "marketpilot-test")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "")
    monkeypatch.setenv("LANGSMITH_WORKSPACE_ID", "")
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("EMBEDDING_API_KEY", "")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "")
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()
