from __future__ import annotations

from typing import Any, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents import graph as graph_module
from app.agents.graph import DeterministicDemoGenerator
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.agent_runs import service as agent_run_events_service
from app.modules.agent_runs.models import AgentRunEvent
from app.modules.demand_insights import service as demand_insights_service
from app.modules.demand_insights.models import OpportunityDemandInsight
from app.modules.demand_insights.service import DemandInsightGenerationError
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks import service as research_task_service


@pytest.fixture()
def client() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator[Session]:
        db = testing_session_local()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, testing_session_local

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def create_task(test_client: TestClient) -> dict[str, Any]:
    response = test_client.post(
        "/api/v1/research-tasks",
        json={
            "brief": "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。",
            "budget": "5000 元以内",
            "target_channels": ["小红书种草"],
            "supply_preferences": ["1688"],
            "excluded_categories": ["食品", "电子产品"],
        },
    )

    assert response.status_code == 201
    return response.json()


def execute_task(
    test_client: TestClient,
    session_factory: sessionmaker[Session],
) -> tuple[dict[str, Any], str]:
    created = create_task(test_client)

    with session_factory() as db:
        task = research_task_service.start_research_run(
            db,
            UUID(created["uuid"]),
            enqueue=False,
        )
        assert task is not None
        assert task.run_id is not None
        research_task_service.execute_research_run(
            db,
            UUID(created["uuid"]),
            task.run_id,
            generator=DeterministicDemoGenerator(),
        )
        return created, task.run_id


def rerun_task(
    task_uuid: str,
    session_factory: sessionmaker[Session],
) -> str:
    with session_factory() as db:
        task = research_task_service.start_research_run(
            db,
            UUID(task_uuid),
            enqueue=False,
        )
        assert task is not None
        assert task.run_id is not None
        research_task_service.execute_research_run(
            db,
            UUID(task_uuid),
            task.run_id,
            generator=DeterministicDemoGenerator(),
        )
        return task.run_id


def test_demand_insight_apis_return_fallback_insights_with_sources(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    task_insights_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/demand-insights"
    )
    opportunity_insight_response = test_client.get(
        f"/api/v1/opportunities/{opportunities[0]['uuid']}/demand-insight"
    )

    assert task_insights_response.status_code == 200
    assert opportunity_insight_response.status_code == 200
    task_insights = task_insights_response.json()
    opportunity_insight = opportunity_insight_response.json()
    assert len(task_insights) == 3
    assert opportunity_insight["opportunity_uuid"] == opportunities[0]["uuid"]
    assert all("id" not in insight for insight in task_insights)
    assert all(insight["source_status"] == "linked" for insight in task_insights)
    assert all(insight["sources"] for insight in task_insights)
    assert all("id" not in source for insight in task_insights for source in insight["sources"])
    assert all("初步参考" in insight["summary"] for insight in task_insights)
    assert all("已证明" not in insight["summary"] for insight in task_insights)

    with session_factory() as db:
        demand_event = db.execute(
            select(AgentRunEvent).where(
                AgentRunEvent.stage == "generate_demand_insights"
            )
        ).scalar_one()

    assert demand_event.status == agent_run_events_service.STATUS_COMPLETED
    assert demand_event.event_metadata["saved_demand_insight_count"] == 3
    assert demand_event.event_metadata["source_link_count"] == 3


def test_demand_insights_are_replaced_on_rerun(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)
    initial_insights = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/demand-insights"
    ).json()
    rerun_task(created["uuid"], session_factory)

    current_opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    current_insights_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/demand-insights"
    )

    assert current_insights_response.status_code == 200
    current_insights = current_insights_response.json()
    assert len(current_insights) == 3
    assert {item["uuid"] for item in current_insights} != {
        item["uuid"] for item in initial_insights
    }
    assert {item["opportunity_uuid"] for item in current_insights} == {
        item["uuid"] for item in current_opportunities
    }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        insights = db.execute(
            select(OpportunityDemandInsight).where(
                OpportunityDemandInsight.research_task_id == task.id
            )
        ).scalars().all()

    assert len(insights) == 6
    assert len([insight for insight in insights if insight.deleted_at is None]) == 3


def test_demand_insight_validation_rejects_proof_like_claims(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    class InvalidDemandInsightGenerator:
        def generate(self, context: dict[str, Any]) -> dict[str, Any]:
            return {
                "insights": [
                    {
                        "opportunity_uuid": opportunity["uuid"],
                        "summary": "已证明这个方向确定有市场。",
                        "audience_profile": "已证明的人群。",
                        "use_cases": ["已证明的使用场景。"],
                        "purchase_motivations": ["已证明的购买动机。"],
                        "content_angles": ["已证明的内容角度。"],
                        "trend_signals": ["已证明的趋势。"],
                        "seasonality_notes": "已证明没有季节性风险。",
                    }
                    for opportunity in context["opportunities"]
                ]
            }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()

        with pytest.raises(DemandInsightGenerationError):
            demand_insights_service.collect_demand_insights(
                db,
                task,
                generator=InvalidDemandInsightGenerator(),
            )


def test_demand_insight_failure_keeps_research_completed(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    def fake_collect(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        graph_module.demand_insights_service,
        "collect_demand_insights",
        fake_collect,
    )

    with session_factory() as db:
        task = research_task_service.start_research_run(
            db,
            UUID(created["uuid"]),
            enqueue=False,
        )
        assert task is not None
        assert task.run_id is not None
        run_id = task.run_id
        research_task_service.execute_research_run(
            db,
            UUID(created["uuid"]),
            run_id,
            generator=DeterministicDemoGenerator(),
        )

    task_response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}")
    opportunities_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    )
    insights_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/demand-insights"
    )
    progress_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/progress"
    )

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert opportunities_response.status_code == 200
    assert len(opportunities_response.json()) == 3
    assert insights_response.status_code == 200
    assert insights_response.json() == []
    demand_events = [
        event
        for event in progress_response.json()["events"]
        if event["stage"] == "generate_demand_insights"
    ]
    assert len(demand_events) == 1
    assert demand_events[0]["status"] == agent_run_events_service.STATUS_FAILED
    assert "需求洞察生成失败" in demand_events[0]["error_summary"]
    assert "Traceback" not in demand_events[0]["error_summary"]


def test_demand_insight_missing_resources_return_expected_status(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    empty_task_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/demand-insights"
    )
    missing_task_response = test_client.get(
        f"/api/v1/research-tasks/{uuid4()}/demand-insights"
    )
    missing_opportunity_response = test_client.get(
        f"/api/v1/opportunities/{uuid4()}/demand-insight"
    )

    assert empty_task_response.status_code == 200
    assert empty_task_response.json() == []
    assert missing_task_response.status_code == 404
    assert missing_opportunity_response.status_code == 404
