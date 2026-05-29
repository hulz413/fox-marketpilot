from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MarketPilot API"
    environment: str = "local"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    database_url: str = (
        "postgresql+psycopg://marketpilot:marketpilot@localhost:5432/marketpilot"
    )
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "marketpilot"
    s3_access_key_id: str = "marketpilot"
    s3_secret_access_key: str = "marketpilot-secret"

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "marketpilot-dev"
    langsmith_endpoint: str = ""
    langsmith_workspace_id: str = ""

    tavily_api_key: str = ""

    llm_provider: str = "deepseek"
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
