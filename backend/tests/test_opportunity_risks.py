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
from app.modules.opportunity_risks import service as opportunity_risks_service
from app.modules.opportunity_risks.models import OpportunityRisk
from app.modules.opportunity_risks.service import OpportunityRiskGenerationError
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


def test_opportunity_risk_apis_return_fallback_risks(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    task_risks_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunity-risks"
    )
    opportunity_risks_response = test_client.get(
        f"/api/v1/opportunities/{opportunities[0]['uuid']}/opportunity-risks"
    )

    assert task_risks_response.status_code == 200
    assert opportunity_risks_response.status_code == 200
    task_risks = task_risks_response.json()
    opportunity_risks = opportunity_risks_response.json()
    assert len(task_risks) == 3
    assert len(opportunity_risks) == 1
    assert Counter(risk["opportunity_uuid"] for risk in task_risks) == {
        opportunity["uuid"]: 1 for opportunity in opportunities
    }
    assert all("id" not in risk for risk in task_risks)
    assert all(risk["review_status"] == "fallback" for risk in task_risks)
    assert all(risk["risk_triggers"] for risk in task_risks)
    assert all(risk["mitigation_suggestions"] for risk in task_risks)
    assert all("继续排查" in risk["platform_risk"] for risk in task_risks)
    assert all("合规已确认" not in risk["risk_summary"] for risk in task_risks)

    with session_factory() as db:
        risk_event = db.execute(
            select(AgentRunEvent).where(
                AgentRunEvent.stage == "review_opportunity_risks"
            )
        ).scalar_one()

    assert risk_event.status == agent_run_events_service.STATUS_COMPLETED
    assert risk_event.event_metadata["saved_opportunity_risk_count"] == 3
    assert risk_event.event_metadata["opportunity_risk_status"] == "fallback"


def test_opportunity_risks_are_replaced_on_rerun(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)
    initial_risks = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunity-risks"
    ).json()
    rerun_task(created["uuid"], session_factory)

    current_opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    current_risks_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunity-risks"
    )

    assert current_risks_response.status_code == 200
    current_risks = current_risks_response.json()
    assert len(current_risks) == 3
    assert {item["uuid"] for item in current_risks} != {
        item["uuid"] for item in initial_risks
    }
    assert {item["opportunity_uuid"] for item in current_risks} == {
        item["uuid"] for item in current_opportunities
    }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        risks = (
            db.execute(
                select(OpportunityRisk).where(
                    OpportunityRisk.research_task_id == task.id
                )
            )
            .scalars()
            .all()
        )

    assert len(risks) == 6
    assert len([risk for risk in risks if risk.deleted_at is None]) == 3


def test_opportunity_risk_validation_rejects_confirmed_claims(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    class InvalidOpportunityRiskGenerator:
        def generate(self, context: dict[str, Any]) -> dict[str, Any]:
            return {
                "risks": [
                    {
                        "opportunity_uuid": opportunity["uuid"],
                        "overall_risk_level": "medium",
                        "risk_summary": "合规已确认。",
                        "quality_risk": "无质量风险。",
                        "fulfillment_risk": "供应商履约已验证。",
                        "after_sales_risk": "无售后风险。",
                        "compliance_risk": "合规已确认。",
                        "inventory_risk": "库存风险已排除。",
                        "competition_risk": "风险已经排除。",
                        "platform_risk": "平台规则无风险。",
                        "risk_triggers": ["履约已确认。"],
                        "mitigation_suggestions": ["库存已确认。"],
                        "review_status": "derived",
                    }
                    for opportunity in context["opportunities"]
                ]
            }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()

        with pytest.raises(OpportunityRiskGenerationError):
            opportunity_risks_service.collect_opportunity_risks(
                db,
                task,
                generator=InvalidOpportunityRiskGenerator(),
            )


def test_opportunity_risk_failure_does_not_block_core_results(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    def fake_collect(db: Session, task: ResearchTask) -> Any:
        raise RuntimeError("risk exploded")

    monkeypatch.setattr(
        graph_module.opportunity_risks_service,
        "collect_opportunity_risks",
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
    risks_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunity-risks"
    )
    progress_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/progress"
    )

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert opportunities_response.status_code == 200
    assert len(opportunities_response.json()) == 3
    assert risks_response.status_code == 200
    assert risks_response.json() == []
    risk_events = [
        event
        for event in progress_response.json()["events"]
        if event["stage"] == "review_opportunity_risks"
    ]
    assert len(risk_events) == 1
    assert risk_events[0]["status"] == agent_run_events_service.STATUS_FAILED
    assert "风险复核失败" in risk_events[0]["error_summary"]
    assert "Traceback" not in risk_events[0]["error_summary"]


def test_opportunity_risk_missing_resources_return_expected_status(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = create_task(test_client)

    empty_task_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunity-risks"
    )
    missing_task_response = test_client.get(
        f"/api/v1/research-tasks/{uuid4()}/opportunity-risks"
    )
    missing_opportunity_response = test_client.get(
        f"/api/v1/opportunities/{uuid4()}/opportunity-risks"
    )

    assert empty_task_response.status_code == 200
    assert empty_task_response.json() == []
    assert missing_task_response.status_code == 404
    assert missing_opportunity_response.status_code == 404
