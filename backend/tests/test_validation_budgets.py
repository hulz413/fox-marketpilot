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
from app.modules.agent_runs import service as agent_run_events_service
from app.modules.agent_runs.models import AgentRunEvent
from app.modules.research_tasks import service as research_task_service
from app.modules.research_tasks.models import ResearchTask
from app.modules.validation_budgets import service as validation_budgets_service
from app.modules.validation_budgets.models import ValidationBudget
from app.modules.validation_budgets.service import ValidationBudgetGenerationError


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


def test_validation_budget_apis_return_fallback_budgets(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    task_budgets_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/validation-budgets"
    )
    opportunity_budgets_response = test_client.get(
        f"/api/v1/opportunities/{opportunities[0]['uuid']}/validation-budgets"
    )

    assert task_budgets_response.status_code == 200
    assert opportunity_budgets_response.status_code == 200
    task_budgets = task_budgets_response.json()
    opportunity_budgets = opportunity_budgets_response.json()
    assert len(task_budgets) == 3
    assert len(opportunity_budgets) == 1
    assert Counter(budget["opportunity_uuid"] for budget in task_budgets) == {
        opportunity["uuid"]: 1 for opportunity in opportunities
    }
    assert all("id" not in budget for budget in task_budgets)
    assert all(budget["estimate_status"] == "fallback" for budget in task_budgets)
    assert all(budget["key_assumptions"] for budget in task_budgets)
    assert all("粗略" in budget["calculation_note"] for budget in task_budgets)
    assert all("利润已确认" not in budget["calculation_note"] for budget in task_budgets)

    with session_factory() as db:
        budget_event = db.execute(
            select(AgentRunEvent).where(
                AgentRunEvent.stage == "estimate_validation_budgets"
            )
        ).scalar_one()

    assert budget_event.status == agent_run_events_service.STATUS_COMPLETED
    assert budget_event.event_metadata["saved_validation_budget_count"] == 3
    assert budget_event.event_metadata["validation_budget_status"] == "fallback"


def test_validation_budgets_are_replaced_on_rerun(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)
    initial_budgets = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/validation-budgets"
    ).json()
    rerun_task(created["uuid"], session_factory)

    current_opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    current_budgets_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/validation-budgets"
    )

    assert current_budgets_response.status_code == 200
    current_budgets = current_budgets_response.json()
    assert len(current_budgets) == 3
    assert {item["uuid"] for item in current_budgets} != {
        item["uuid"] for item in initial_budgets
    }
    assert {item["opportunity_uuid"] for item in current_budgets} == {
        item["uuid"] for item in current_opportunities
    }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        budgets = db.execute(
            select(ValidationBudget).where(
                ValidationBudget.research_task_id == task.id
            )
        ).scalars().all()

    assert len(budgets) == 6
    assert len([budget for budget in budgets if budget.deleted_at is None]) == 3


def test_validation_budget_validation_rejects_confirmed_financial_claims(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    class InvalidValidationBudgetGenerator:
        def generate(self, context: dict[str, Any]) -> dict[str, Any]:
            return {
                "budgets": [
                    {
                        "opportunity_uuid": opportunity["uuid"],
                        "estimated_unit_cost": "采购价已确认。",
                        "estimated_selling_price": "售价已确认。",
                        "rough_gross_margin": "利润已确认。",
                        "first_batch_quantity": "20 件。",
                        "first_batch_budget": "保证回本。",
                        "key_assumptions": ["真实成交价已确认。"],
                        "calculation_note": "确定毛利。",
                        "estimate_status": "derived",
                    }
                    for opportunity in context["opportunities"]
                ]
            }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()

        with pytest.raises(ValidationBudgetGenerationError):
            validation_budgets_service.collect_validation_budgets(
                db,
                task,
                generator=InvalidValidationBudgetGenerator(),
            )


def test_validation_budget_failure_does_not_block_core_results(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    def fake_collect(db: Session, task: ResearchTask) -> Any:
        raise RuntimeError("budget exploded")

    monkeypatch.setattr(
        graph_module.validation_budgets_service,
        "collect_validation_budgets",
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
    budgets_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/validation-budgets"
    )
    progress_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/progress"
    )

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert opportunities_response.status_code == 200
    assert len(opportunities_response.json()) == 3
    assert budgets_response.status_code == 200
    assert budgets_response.json() == []
    budget_events = [
        event
        for event in progress_response.json()["events"]
        if event["stage"] == "estimate_validation_budgets"
    ]
    assert len(budget_events) == 1
    assert budget_events[0]["status"] == agent_run_events_service.STATUS_FAILED
    assert "验证预算估算失败" in budget_events[0]["error_summary"]
    assert "Traceback" not in budget_events[0]["error_summary"]


def test_validation_budget_missing_resources_return_expected_status(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = create_task(test_client)

    empty_task_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/validation-budgets"
    )
    missing_task_response = test_client.get(
        f"/api/v1/research-tasks/{uuid4()}/validation-budgets"
    )
    missing_opportunity_response = test_client.get(
        f"/api/v1/opportunities/{uuid4()}/validation-budgets"
    )

    assert empty_task_response.status_code == 200
    assert empty_task_response.json() == []
    assert missing_task_response.status_code == 404
    assert missing_opportunity_response.status_code == 404
