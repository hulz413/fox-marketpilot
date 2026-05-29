from openai import OpenAI

from app.core.settings import get_settings
from app.integrations.langsmith import is_langsmith_tracing_enabled


def create_llm_client() -> OpenAI:
    settings = get_settings()
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    if not is_langsmith_tracing_enabled():
        return client

    from langsmith.wrappers import wrap_openai

    return wrap_openai(client)
