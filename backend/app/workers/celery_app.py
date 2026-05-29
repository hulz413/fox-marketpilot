from celery import Celery

from app.core.settings import get_settings
from app.integrations.langsmith import configure_langsmith_environment

configure_langsmith_environment()
settings = get_settings()

celery_app = Celery(
    "marketpilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.research"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
)
