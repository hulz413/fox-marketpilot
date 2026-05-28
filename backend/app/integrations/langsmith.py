import os

from app.core.settings import get_settings


def configure_langsmith_environment() -> None:
    settings = get_settings()
    os.environ.setdefault("LANGSMITH_TRACING", str(settings.langsmith_tracing).lower())
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    if settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
