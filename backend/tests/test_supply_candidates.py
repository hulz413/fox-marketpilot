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
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks import service as research_task_service
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.supply_candidates.models import SupplyCandidate
from app.modules.supply_candidates.service import SupplyCandidateGenerationError


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


def test_supply_candidate_apis_return_fallback_candidates_with_sources(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    task_candidates_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/supply-candidates"
    )
    opportunity_candidates_response = test_client.get(
        f"/api/v1/opportunities/{opportunities[0]['uuid']}/supply-candidates"
    )

    assert task_candidates_response.status_code == 200
    assert opportunity_candidates_response.status_code == 200
    task_candidates = task_candidates_response.json()
    opportunity_candidates = opportunity_candidates_response.json()
    assert len(task_candidates) == 6
    assert len(opportunity_candidates) == 2
    assert Counter(candidate["opportunity_uuid"] for candidate in task_candidates) == {
        opportunity["uuid"]: 2 for opportunity in opportunities
    }
    assert all("id" not in candidate for candidate in task_candidates)
    assert all(
        "id" not in source
        for candidate in task_candidates
        for source in candidate["sources"]
    )
    assert all(candidate["source_status"] == "linked" for candidate in task_candidates)
    assert all(candidate["sources"] for candidate in task_candidates)
    assert all("候选" in candidate["candidate_name"] for candidate in task_candidates)
    assert all("待确认" in candidate["minimum_order_quantity"] for candidate in task_candidates)
    assert all("已确认供给" not in candidate["recommendation_note"] for candidate in task_candidates)

    with session_factory() as db:
        supply_event = db.execute(
            select(AgentRunEvent).where(
                AgentRunEvent.stage == "generate_supply_candidates"
            )
        ).scalar_one()

    assert supply_event.status == agent_run_events_service.STATUS_COMPLETED
    assert supply_event.event_metadata["saved_supply_candidate_count"] == 6
    assert supply_event.event_metadata["source_link_count"] == 6


def test_supply_candidates_are_replaced_on_rerun(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)
    initial_candidates = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/supply-candidates"
    ).json()
    rerun_task(created["uuid"], session_factory)

    current_opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    current_candidates_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/supply-candidates"
    )

    assert current_candidates_response.status_code == 200
    current_candidates = current_candidates_response.json()
    assert len(current_candidates) == 6
    assert {item["uuid"] for item in current_candidates} != {
        item["uuid"] for item in initial_candidates
    }
    assert {item["opportunity_uuid"] for item in current_candidates} == {
        item["uuid"] for item in current_opportunities
    }

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        candidates = db.execute(
            select(SupplyCandidate).where(
                SupplyCandidate.research_task_id == task.id
            )
        ).scalars().all()

    assert len(candidates) == 12
    assert len([candidate for candidate in candidates if candidate.deleted_at is None]) == 6


def test_supply_candidate_validation_rejects_confirmed_supply_claims(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    class InvalidSupplyCandidateGenerator:
        def generate(self, context: dict[str, Any]) -> dict[str, Any]:
            candidates: list[dict[str, Any]] = []

            for opportunity in context["opportunities"]:
                candidates.extend(
                    [
                        {
                            "opportunity_uuid": opportunity["uuid"],
                            "rank": 1,
                            "candidate_name": "库存已确认的候选",
                            "supply_market": "1688",
                            "search_keywords": ["已确认供给"],
                            "price_range": "价格已确认。",
                            "minimum_order_quantity": "起订量待确认。",
                            "specification_notes": ["规格待确认。"],
                            "supplier_questions": ["供应商已核验吗？"],
                            "recommendation_note": "库存已确认。",
                        },
                        {
                            "opportunity_uuid": opportunity["uuid"],
                            "rank": 2,
                            "candidate_name": "备用候选",
                            "supply_market": "公开市场",
                            "search_keywords": ["批发"],
                            "price_range": "报价待确认。",
                            "minimum_order_quantity": "起订量待确认。",
                            "specification_notes": ["规格待确认。"],
                            "supplier_questions": ["是否支持样品？"],
                            "recommendation_note": "作为初步参考。",
                        },
                    ]
                )

            return {"candidates": candidates}

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()

        with pytest.raises(SupplyCandidateGenerationError):
            supply_candidates_service.collect_supply_candidates(
                db,
                task,
                generator=InvalidSupplyCandidateGenerator(),
            )


def test_supply_candidate_failure_keeps_research_completed(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    def fake_collect(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        graph_module.supply_candidates_service,
        "collect_supply_candidates",
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
    candidates_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/supply-candidates"
    )
    progress_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/progress"
    )

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert opportunities_response.status_code == 200
    assert len(opportunities_response.json()) == 3
    assert candidates_response.status_code == 200
    assert candidates_response.json() == []
    supply_events = [
        event
        for event in progress_response.json()["events"]
        if event["stage"] == "generate_supply_candidates"
    ]
    assert len(supply_events) == 1
    assert supply_events[0]["status"] == agent_run_events_service.STATUS_FAILED
    assert "货源候选生成失败" in supply_events[0]["error_summary"]
    assert "Traceback" not in supply_events[0]["error_summary"]


def test_supply_candidate_missing_resources_return_expected_status(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = create_task(test_client)

    empty_task_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/supply-candidates"
    )
    missing_task_response = test_client.get(
        f"/api/v1/research-tasks/{uuid4()}/supply-candidates"
    )
    missing_opportunity_response = test_client.get(
        f"/api/v1/opportunities/{uuid4()}/supply-candidates"
    )

    assert empty_task_response.status_code == 200
    assert empty_task_response.json() == []
    assert missing_task_response.status_code == 404
    assert missing_opportunity_response.status_code == 404
