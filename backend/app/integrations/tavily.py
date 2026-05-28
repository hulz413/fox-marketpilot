from tavily import TavilyClient

from app.core.settings import get_settings


def create_tavily_client() -> TavilyClient:
    settings = get_settings()
    return TavilyClient(api_key=settings.tavily_api_key)
