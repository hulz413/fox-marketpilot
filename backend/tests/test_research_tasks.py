from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
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


def test_create_research_task(client: tuple[TestClient, sessionmaker[Session]]) -> None:
    test_client, _ = client

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
    body = response.json()
    assert UUID(body["uuid"])
    assert "id" not in body
    assert body["brief"] == "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。"
    assert body["title"] == "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。"
    assert body["budget"] == "5000 元以内"
    assert body["target_channels"] == ["小红书种草"]
    assert body["excluded_categories"] == ["食品", "电子产品"]
    assert body["status"] == "created"
    assert body["current_stage"] == "intake"
    assert body["run_id"] is None
    assert body["trace_id"] is None
    assert body["failure_reason"] is None
    assert body["deleted_at"] is None


def test_rejects_missing_brief(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client

    response = test_client.post(
        "/api/v1/research-tasks",
        json={"brief": "   "},
    )

    assert response.status_code == 422
    assert test_client.get("/api/v1/research-tasks").json() == []


def test_lists_active_tasks_newest_first(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client

    first = test_client.post(
        "/api/v1/research-tasks",
        json={"brief": "第一个研究任务"},
    )
    second = test_client.post(
        "/api/v1/research-tasks",
        json={"brief": "第二个研究任务"},
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = test_client.get("/api/v1/research-tasks")

    assert response.status_code == 200
    assert [task["brief"] for task in response.json()] == [
        "第二个研究任务",
        "第一个研究任务",
    ]


def test_get_research_task_by_uuid(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = test_client.post(
        "/api/v1/research-tasks",
        json={"brief": "读取单个研究任务"},
    ).json()

    response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}")

    assert response.status_code == 200
    assert response.json()["uuid"] == created["uuid"]
    assert response.json()["brief"] == "读取单个研究任务"


def test_soft_deleted_tasks_are_filtered(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = test_client.post(
        "/api/v1/research-tasks",
        json={"brief": "会被软删除的研究任务"},
    ).json()

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        task.deleted_at = datetime.now(timezone.utc)
        db.commit()

    list_response = test_client.get("/api/v1/research-tasks")
    detail_response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}")

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert detail_response.status_code == 404


def test_get_missing_research_task_returns_404(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client

    response = test_client.get(f"/api/v1/research-tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Research task not found"}
