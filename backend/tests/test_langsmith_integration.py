from __future__ import annotations

import os

from app.core.settings import get_settings
from app.integrations.langsmith import configure_langsmith_environment


def test_configure_langsmith_environment_sets_optional_routing_env(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setenv("LANGSMITH_PROJECT", "marketpilot-test")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://eu.api.smith.langchain.com")
    monkeypatch.setenv("LANGSMITH_WORKSPACE_ID", "workspace-test-id")
    get_settings.cache_clear()

    configure_langsmith_environment()

    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGSMITH_PROJECT"] == "marketpilot-test"
    assert os.environ["LANGSMITH_ENDPOINT"] == "https://eu.api.smith.langchain.com"
    assert os.environ["LANGSMITH_WORKSPACE_ID"] == "workspace-test-id"
    get_settings.cache_clear()
