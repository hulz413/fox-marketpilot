from __future__ import annotations

from uuid import UUID

from app.db.session import SessionLocal
from app.modules.research_tasks import service
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.research.run_opportunity_research")
def run_opportunity_research(task_uuid: str, run_id: str) -> None:
    db = SessionLocal()

    try:
        service.execute_research_run(db, UUID(task_uuid), run_id)
    finally:
        db.close()
