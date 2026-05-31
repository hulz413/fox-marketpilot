from __future__ import annotations

from collections import Counter
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
from app.modules.action_plans import service as action_plans_service
from app.modules.action_plans.models import ActionPlan
from app.modules.action_plans.service import ActionPlanGenerationError
from app.modules.agent_runs import service as agent_run_events_service
from app.modules.agent_runs.models import AgentRunEvent
from app.modules.research_tasks import service as research_task_service
from app.modules.research_tasks.models import ResearchTask


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


def test_action_plan_apis_return_fallback_plans(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    task_plans_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/action-plans"
    )
    opportunity_plans_response = test_client.get(
        f"/api/v1/opportunities/{opportunities[0]['uuid']}/action-plans"
    )

    assert task_plans_response.status_code == 200
    assert opportunity_plans_response.status_code == 200
    task_plans = task_plans_response.json()
    opportunity_plans = opportunity_plans_response.json()
    assert len(task_plans) == 3
    assert len(opportunity_plans) == 1
    assert Counter(plan["opportunity_uuid"] for plan in task_plans) == {
        opportunity["uuid"]: 1 for opportunity in opportunities
    }
    assert all("id" not in plan for plan in task_plans)
    assert all(plan["plan_status"] == "fallback" for plan in task_plans)
    assert all(plan["content_angles"] for plan in task_plans)
    assert all(plan["prelaunch_checklist"] for plan in task_plans)
    assert all("起订量" in plan["supplier_inquiry_script"] for plan in task_plans)
    assert all("保证成交" not in plan["validation_goal"] for plan in task_plans)

    with session_factory() as db:
        plan_event = db.execute(
            select(AgentRunEvent).where(AgentRunEvent.stage == "create_action_plans")
        ).scalar_one()

    assert plan_event.status == agent_run_events_service.STATUS_COMPLETED
    assert plan_event.event_metadata["saved_action_plan_count"] == 3
    assert plan_event.event_metadata["action_plan_status"] == "fallback"


def test_action_plans_are_replaced_on_rerun(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)
    initial_plans = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/action-plans"
    ).json()
    rerun_task(created["uuid"], session_factory)

    current_opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    current_plans_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/action-plans"
    )

    assert current_plans_response.status_code == 200
    current_plans = current_plans_response.json()
    assert len(current_plans) == 3
    assert {item["uuid"] for item in current_plans} != {
        item["uuid"] for item in initial_plans
    }
    assert {item["opportunity_uuid"] for item in current_plans} == {
        item["uuid"] for item in current_opportunities
    }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        plans = (
            db.execute(
                select(ActionPlan).where(ActionPlan.research_task_id == task.id)
            )
            .scalars()
            .all()
        )

    assert len(plans) == 6
    assert len([plan for plan in plans if plan.deleted_at is None]) == 3


def test_action_plan_validation_rejects_confirmed_claims(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    class InvalidActionPlanGenerator:
        def generate(self, context: dict[str, Any]) -> dict[str, Any]:
            return {
                "action_plans": [
                    {
                        "opportunity_uuid": opportunity["uuid"],
                        "validation_goal": "保证成交。",
                        "first_batch_plan": "保证回本。",
                        "product_validation_method": "无需验证。",
                        "content_angles": ["一定成交。"],
                        "title_suggestions": ["平台审核必过。"],
                        "selling_point_suggestions": ["确定转化。"],
                        "supplier_inquiry_script": "自动联系供应商。",
                        "prelaunch_checklist": ["上架必过。"],
                        "plan_status": "derived",
                    }
                    for opportunity in context["opportunities"]
                ]
            }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()

        with pytest.raises(ActionPlanGenerationError):
            action_plans_service.collect_action_plans(
                db,
                task,
                generator=InvalidActionPlanGenerator(),
            )


def test_action_plan_failure_does_not_block_core_results(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    def fake_collect(db: Session, task: ResearchTask) -> Any:
        raise RuntimeError("plan exploded")

    monkeypatch.setattr(
        graph_module.action_plans_service,
        "collect_action_plans",
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
        research_task_service.execute_research_run(
            db,
            UUID(created["uuid"]),
            task.run_id,
            generator=DeterministicDemoGenerator(),
        )

    task_response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}")
    opportunities_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    )
    plans_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/action-plans"
    )
    progress_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/progress"
    )

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert opportunities_response.status_code == 200
    assert len(opportunities_response.json()) == 3
    assert plans_response.status_code == 200
    assert plans_response.json() == []
    plan_events = [
        event
        for event in progress_response.json()["events"]
        if event["stage"] == "create_action_plans"
    ]
    assert len(plan_events) == 1
    assert plan_events[0]["status"] == agent_run_events_service.STATUS_FAILED
    assert "行动计划生成失败" in plan_events[0]["error_summary"]
    assert "Traceback" not in plan_events[0]["error_summary"]


def test_action_plan_missing_resources_return_expected_status(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = create_task(test_client)

    empty_task_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/action-plans"
    )
    missing_task_response = test_client.get(
        f"/api/v1/research-tasks/{uuid4()}/action-plans"
    )
    missing_opportunity_response = test_client.get(
        f"/api/v1/opportunities/{uuid4()}/action-plans"
    )

    assert empty_task_response.status_code == 200
    assert empty_task_response.json() == []
    assert missing_task_response.status_code == 404
    assert missing_opportunity_response.status_code == 404
