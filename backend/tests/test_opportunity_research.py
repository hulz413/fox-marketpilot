from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.graph import DeterministicDemoGenerator
from app.db.base import Base
from app.db.session import get_db
from app.integrations.langsmith import TraceContext
from app.main import app
from app.modules.agent_runs.models import AgentRunEvent
from app.modules.agent_runs import service as agent_run_events_service
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
    assert body["trace_id"] is None
    assert body["trace_url"] is None
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


def test_research_progress_for_created_task_has_empty_events(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = create_task(test_client)

    response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}/progress")

    assert response.status_code == 200
    body = response.json()
    assert body["task"]["uuid"] == created["uuid"]
    assert body["status"] == "created"
    assert body["current_stage"] == "intake"
    assert body["run_id"] is None
    assert body["events"] == []
    assert "start" in body["available_actions"]
    assert "back_to_tasks" in body["available_actions"]
    assert "id" not in body["task"]


def test_execute_research_run_generates_opportunities(
    client: tuple[TestClient, sessionmaker[Session]],
    caplog: pytest.LogCaptureFixture,
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
        run_id = task.run_id
        with caplog.at_level("INFO"):
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

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert task_response.json()["current_stage"] == "completed"
    assert task_response.json()["trace_id"] is None
    assert task_response.json()["trace_url"] is None
    assert opportunities_response.status_code == 200
    opportunities = opportunities_response.json()
    assert len(opportunities) == 3
    assert [item["rank"] for item in opportunities] == [1, 2, 3]
    assert all("uuid" in item for item in opportunities)
    assert all("source" not in item for item in opportunities)

    detail_response = test_client.get(f"/api/v1/opportunities/{opportunities[0]['uuid']}")

    assert detail_response.status_code == 200
    assert detail_response.json()["research_task_uuid"] == created["uuid"]

    with session_factory() as db:
        events = db.execute(
            select(AgentRunEvent)
            .where(AgentRunEvent.research_task_id == 1)
            .order_by(AgentRunEvent.started_at.asc(), AgentRunEvent.id.asc())
        ).scalars().all()

    assert [event.stage for event in events] == [
        "opportunity_research",
        "normalize_intake",
        "generate_opportunities",
        "validate_results",
        "persist_results",
        "collect_research_sources",
        "generate_demand_insights",
        "generate_supply_candidates",
        "generate_competitor_references",
        "estimate_validation_budgets",
    ]
    assert all(event.status == agent_run_events_service.STATUS_COMPLETED for event in events)
    assert all(event.started_at is not None for event in events)
    assert all(event.completed_at is not None for event in events)
    assert all(event.duration_ms is not None for event in events)
    assert any(
        record.message == "Agent run stage completed"
        and getattr(record, "stage", None) == "generate_opportunities"
        and getattr(record, "run_id", None) == run_id
        for record in caplog.records
    )


def test_research_progress_returns_completed_event_timeline(
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
        run_id = task.run_id
        research_task_service.execute_research_run(
            db,
            UUID(created["uuid"]),
            run_id,
            generator=DeterministicDemoGenerator(),
        )

    response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}/progress")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["run_id"] == run_id
    assert body["trace_id"] is None
    assert body["trace_url"] is None
    assert [event["stage"] for event in body["events"]] == [
        "opportunity_research",
        "normalize_intake",
        "generate_opportunities",
        "validate_results",
        "persist_results",
        "collect_research_sources",
        "generate_demand_insights",
        "generate_supply_candidates",
        "generate_competitor_references",
        "estimate_validation_budgets",
    ]
    assert all(event["run_id"] == run_id for event in body["events"])
    assert all("id" not in event for event in body["events"])
    assert all(event["uuid"] for event in body["events"])
    assert "view_opportunities" in body["available_actions"]
    assert "view_report" in body["available_actions"]


def test_execute_research_run_persists_trace_context(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    @contextmanager
    def fake_langsmith_trace(*args: Any, **kwargs: Any) -> Iterator[TraceContext]:
        yield TraceContext(
            trace_id="11111111-1111-1111-1111-111111111111",
            trace_url="https://smith.langchain.com/public/trace/11111111",
        )

    monkeypatch.setattr(research_task_service, "langsmith_trace", fake_langsmith_trace)

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

    assert task_response.status_code == 200
    assert task_response.json()["trace_id"] == "11111111-1111-1111-1111-111111111111"
    assert task_response.json()["trace_url"] == "https://smith.langchain.com/public/trace/11111111"

    with session_factory() as db:
        events = db.execute(
            select(AgentRunEvent).order_by(
                AgentRunEvent.started_at.asc(),
                AgentRunEvent.id.asc(),
            )
        ).scalars().all()

    assert events
    assert all(
        event.trace_id == "11111111-1111-1111-1111-111111111111"
        for event in events
    )


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

    with session_factory() as db:
        events = db.execute(
            select(AgentRunEvent).order_by(
                AgentRunEvent.started_at.asc(),
                AgentRunEvent.id.asc(),
            )
        ).scalars().all()

    failed_events = [
        event for event in events if event.status == agent_run_events_service.STATUS_FAILED
    ]
    assert {event.stage for event in failed_events} == {
        "generate_opportunities",
        "opportunity_research",
    }
    assert all(event.error_summary for event in failed_events)


def test_research_progress_returns_failed_safe_summary(
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
        run_id = task.run_id
        research_task_service.execute_research_run(
            db,
            UUID(created["uuid"]),
            run_id,
            generator=InvalidGenerator(),
        )
        failed_event = db.execute(
            select(AgentRunEvent).where(
                AgentRunEvent.run_id == run_id,
                AgentRunEvent.stage == "generate_opportunities",
            )
        ).scalar_one()
        failed_event.error_summary = 'Traceback (most recent call last):\n  File "x.py"'
        db.commit()

    response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}/progress")

    assert response.status_code == 200
    body = response.json()
    failed_events = [
        event
        for event in body["events"]
        if event["status"] == agent_run_events_service.STATUS_FAILED
    ]
    assert body["status"] == "failed"
    assert "基础商机生成失败" in body["failure_reason"]
    assert "rerun" in body["available_actions"]
    assert failed_events
    assert all("Traceback" not in event["error_summary"] for event in failed_events)
    assert all("File " not in event["error_summary"] for event in failed_events)


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
        first_run_id = task.run_id
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
        second_run_id = task.run_id
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
    assert first_run_id != second_run_id

    with session_factory() as db:
        first_events = db.execute(
            select(AgentRunEvent).where(AgentRunEvent.run_id == first_run_id)
        ).scalars().all()
        second_events = db.execute(
            select(AgentRunEvent).where(AgentRunEvent.run_id == second_run_id)
        ).scalars().all()

    assert first_events
    assert second_events
    assert {event.stage for event in first_events} == {
        "opportunity_research",
        "normalize_intake",
        "generate_opportunities",
        "validate_results",
        "persist_results",
        "collect_research_sources",
        "generate_demand_insights",
        "generate_supply_candidates",
        "generate_competitor_references",
        "estimate_validation_budgets",
    }
    assert {event.stage for event in second_events} == {
        "opportunity_research",
        "normalize_intake",
        "generate_opportunities",
        "validate_results",
        "persist_results",
        "collect_research_sources",
        "generate_demand_insights",
        "generate_supply_candidates",
        "generate_competitor_references",
        "estimate_validation_budgets",
    }


def test_research_progress_uses_current_run_and_filters_deleted_events(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    with session_factory() as db:
        first_task = research_task_service.start_research_run(
            db,
            UUID(created["uuid"]),
            enqueue=False,
        )
        assert first_task is not None
        assert first_task.run_id is not None
        first_run_id = first_task.run_id
        research_task_service.execute_research_run(
            db,
            UUID(created["uuid"]),
            first_run_id,
            generator=DeterministicDemoGenerator(),
        )

        second_task = research_task_service.start_research_run(
            db,
            UUID(created["uuid"]),
            enqueue=False,
        )
        assert second_task is not None
        assert second_task.run_id is not None
        second_run_id = second_task.run_id
        research_task_service.execute_research_run(
            db,
            UUID(created["uuid"]),
            second_run_id,
            generator=DeterministicDemoGenerator(),
        )

        deleted_event = db.execute(
            select(AgentRunEvent).where(
                AgentRunEvent.run_id == second_run_id,
                AgentRunEvent.stage == "validate_results",
            )
        ).scalar_one()
        deleted_event.deleted_at = datetime.now(timezone.utc)
        db.commit()

    response = test_client.get(f"/api/v1/research-tasks/{created['uuid']}/progress")

    assert response.status_code == 200
    body = response.json()
    stages = [event["stage"] for event in body["events"]]

    assert body["run_id"] == second_run_id
    assert all(event["run_id"] == second_run_id for event in body["events"])
    assert first_run_id not in [event["run_id"] for event in body["events"]]
    assert "validate_results" not in stages
