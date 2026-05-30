from __future__ import annotations

import os

from app.core.settings import get_settings
from app.integrations.langsmith import (
    configure_langsmith_environment,
    normalize_langsmith_trace_url,
)


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


def test_normalize_langsmith_trace_url_uses_regional_app_domain(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://apac.api.smith.langchain.com")
    get_settings.cache_clear()

    trace_url = (
        "https://smith.langchain.com/o/example/projects/p/marketpilot/r/trace-1"
        "?poll=true"
    )

    assert normalize_langsmith_trace_url(trace_url) == (
        "https://apac.smith.langchain.com/o/example/projects/p/marketpilot/r/trace-1"
        "?poll=true"
    )
    get_settings.cache_clear()


def test_normalize_langsmith_trace_url_keeps_default_app_domain(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    get_settings.cache_clear()

    trace_url = "https://smith.langchain.com/o/example/projects/p/marketpilot/r/trace-1"

    assert normalize_langsmith_trace_url(trace_url) == trace_url
    get_settings.cache_clear()


def test_normalize_langsmith_trace_url_ignores_self_hosted_links(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://langsmith.example.com/api")
    get_settings.cache_clear()

    trace_url = "https://langsmith.example.com/o/example/projects/p/marketpilot/r/trace-1"

    assert normalize_langsmith_trace_url(trace_url) == trace_url
    get_settings.cache_clear()
