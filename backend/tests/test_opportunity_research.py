from __future__ import annotations

from typing import Any, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.graph import DeterministicDemoGenerator
from app.db.base import Base
from app.db.session import get_db
from app.main import app
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
            "excluded_categories": ["食品", "电子产品"],
        },
    )

    assert response.status_code == 201
    return response.json()


def test_start_research_run_queues_task_once(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, _ = client
    created = create_task(test_client)
    enqueued_runs: list[tuple[UUID, str]] = []

    def fake_enqueue(task_uuid: UUID, run_id: str) -> None:
        enqueued_runs.append((task_uuid, run_id))

    monkeypatch.setattr(research_task_service, "enqueue_research_run", fake_enqueue)

    response = test_client.post(f"/api/v1/research-tasks/{created['uuid']}/runs")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["current_stage"] == "queued"
    assert body["run_id"]
    assert body["failure_reason"] is None
    assert len(enqueued_runs) == 1

    duplicate_response = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/runs"
    )

    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["run_id"] == body["run_id"]
    assert len(enqueued_runs) == 1


def test_start_research_run_missing_task_returns_404(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client

    response = test_client.post(f"/api/v1/research-tasks/{uuid4()}/runs")

    assert response.status_code == 404
    assert response.json() == {"detail": "Research task not found"}


def test_execute_research_run_generates_opportunities(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
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

    task_response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}")
    opportunities_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    )

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert task_response.json()["current_stage"] == "completed"
    assert opportunities_response.status_code == 200
    opportunities = opportunities_response.json()
    assert len(opportunities) == 3
    assert [item["rank"] for item in opportunities] == [1, 2, 3]
    assert all("uuid" in item for item in opportunities)
    assert all("source" not in item for item in opportunities)

    detail_response = test_client.get(f"/api/v1/opportunities/{opportunities[0]['uuid']}")

    assert detail_response.status_code == 200
    assert detail_response.json()["research_task_uuid"] == created["uuid"]


def test_execute_research_run_failure_sets_task_failed(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    class InvalidGenerator:
        def generate(self, context: dict[str, Any]) -> dict[str, Any]:
            return {"opportunities": [{"rank": 1}]}

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
            generator=InvalidGenerator(),
        )

    task_response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}")
    opportunities_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    )

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "failed"
    assert task_response.json()["current_stage"] == "failed"
    assert "基础商机生成失败" in task_response.json()["failure_reason"]
    assert opportunities_response.json() == []


def test_rerun_replaces_old_opportunities(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
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

    first_run = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    old_opportunity_uuid = first_run[0]["uuid"]

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

    second_run = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    old_detail_response = test_client.get(f"/api/v1/opportunities/{old_opportunity_uuid}")

    assert len(second_run) == 3
    assert old_opportunity_uuid not in [item["uuid"] for item in second_run]
    assert old_detail_response.status_code == 404
