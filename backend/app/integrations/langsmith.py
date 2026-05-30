import os
from contextlib import contextmanager
from dataclasses import dataclass
import logging
from typing import Any, Iterator, Optional
from urllib.parse import urlsplit, urlunsplit

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TraceContext:
    trace_id: Optional[str]
    trace_url: Optional[str]


def configure_langsmith_environment() -> None:
    settings = get_settings()
    os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    if settings.langsmith_workspace_id:
        os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id


def is_langsmith_tracing_enabled() -> bool:
    settings = get_settings()
    return settings.langsmith_tracing and bool(settings.langsmith_api_key)


def _langsmith_app_host_from_endpoint(endpoint: str) -> Optional[str]:
    if not endpoint:
        return None

    hostname = urlsplit(endpoint).hostname

    if hostname == "api.smith.langchain.com":
        return "smith.langchain.com"

    suffix = ".api.smith.langchain.com"
    if hostname and hostname.endswith(suffix):
        region = hostname.removesuffix(suffix)
        if region:
            return f"{region}.smith.langchain.com"

    return None


def normalize_langsmith_trace_url(trace_url: Optional[str]) -> Optional[str]:
    if not trace_url:
        return trace_url

    app_host = _langsmith_app_host_from_endpoint(get_settings().langsmith_endpoint)
    if not app_host:
        return trace_url

    parsed = urlsplit(trace_url)
    if not parsed.scheme or not parsed.netloc:
        return trace_url

    current_host = parsed.hostname or ""
    if not current_host.endswith("smith.langchain.com"):
        return trace_url

    netloc = app_host
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


def get_current_trace_context() -> Optional[TraceContext]:
    try:
        from langsmith.run_helpers import get_current_run_tree

        run_tree = get_current_run_tree()
    except Exception:
        logger.warning("Failed to read current LangSmith run tree", exc_info=True)
        return None

    if run_tree is None:
        return None

    trace_id = getattr(run_tree, "trace_id", None) or getattr(run_tree, "id", None)
    trace_url = None

    try:
        trace_url = run_tree.get_url()
    except Exception:
        logger.warning("Failed to build LangSmith trace URL", exc_info=True)

    return TraceContext(
        trace_id=str(trace_id) if trace_id else None,
        trace_url=normalize_langsmith_trace_url(trace_url),
    )


@contextmanager
def langsmith_trace(
    name: str,
    *,
    inputs: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
    run_type: str = "chain",
) -> Iterator[Optional[TraceContext]]:
    if not is_langsmith_tracing_enabled():
        yield None
        return

    settings = get_settings()

    try:
        from langsmith import trace

        trace_context = trace(
            name,
            run_type=run_type,
            inputs=inputs,
            metadata=metadata,
            project_name=settings.langsmith_project,
        )
        run_tree = trace_context.__enter__()
    except Exception:
        logger.warning("Failed to start LangSmith trace", exc_info=True)
        yield None
        return

    try:
        trace_id = getattr(run_tree, "trace_id", None) or getattr(run_tree, "id", None)
        trace_url = None
        try:
            trace_url = run_tree.get_url()
        except Exception:
            logger.warning("Failed to build LangSmith trace URL", exc_info=True)
        yield TraceContext(
            trace_id=str(trace_id) if trace_id else None,
            trace_url=normalize_langsmith_trace_url(trace_url),
        )
    except BaseException as exc:
        try:
            trace_context.__exit__(type(exc), exc, exc.__traceback__)
        except Exception:
            logger.warning("Failed to close LangSmith trace", exc_info=True)
        raise
    else:
        try:
            trace_context.__exit__(None, None, None)
        except Exception:
            logger.warning("Failed to close LangSmith trace", exc_info=True)
