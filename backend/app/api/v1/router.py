from fastapi import APIRouter

from app.api.v1.routes import (
    competitor_references,
    demand_insights,
    health,
    opportunities,
    research_tasks,
    sources,
    supply_candidates,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(research_tasks.router, tags=["research_tasks"])
api_router.include_router(opportunities.router, tags=["opportunities"])
api_router.include_router(sources.router, tags=["sources"])
api_router.include_router(demand_insights.router, tags=["demand_insights"])
api_router.include_router(supply_candidates.router, tags=["supply_candidates"])
api_router.include_router(competitor_references.router, tags=["competitor_references"])
