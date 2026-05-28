from openai import OpenAI

from app.core.settings import get_settings


def create_llm_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
