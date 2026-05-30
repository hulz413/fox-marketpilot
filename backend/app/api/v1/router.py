from fastapi import APIRouter

from app.api.v1.routes import health, opportunities, research_tasks, sources

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(research_tasks.router, tags=["research_tasks"])
api_router.include_router(opportunities.router, tags=["opportunities"])
api_router.include_router(sources.router, tags=["sources"])
