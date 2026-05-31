from __future__ import annotations

import json
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
from app.main import app
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.schemas import OpportunityGenerationResult
from app.modules.report_sharing.models import ReportShare
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
) -> dict[str, Any]:
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

    return created


def create_task_with_only_opportunities(
    test_client: TestClient,
    session_factory: sessionmaker[Session],
) -> dict[str, Any]:
    created = create_task(test_client)

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        raw_result = DeterministicDemoGenerator().generate(
            {
                "target_channels": task.target_channels,
                "target_audience": task.target_audience,
                "budget": task.budget,
                "excluded_categories": task.excluded_categories,
            }
        )
        generated = OpportunityGenerationResult.model_validate(raw_result)
        opportunities_service.replace_task_opportunities(
            db,
            task,
            generated.opportunities,
        )
        db.commit()

    return created


def test_report_share_create_public_read_and_sanitize_snapshot(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = execute_task(test_client, session_factory)

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        task.trace_id = "trace-secret"
        task.trace_url = "https://trace.example/secret"
        task.failure_reason = "Traceback (most recent call last): internal details"
        db.commit()

    response = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/report-shares"
    )

    assert response.status_code == 201
    share = response.json()
    assert "id" not in share
    assert share["status"] == "active"
    assert len(share["share_token"]) >= 32
    assert share["share_token"] != created["uuid"]

    public_response = test_client.get(f"/api/v1/report-shares/{share['share_token']}")

    assert public_response.status_code == 200
    public_share = public_response.json()
    snapshot = public_share["snapshot"]
    assert snapshot["task"]["uuid"] == created["uuid"]
    assert len(snapshot["opportunities"]) == 3
    assert snapshot["demand_insights"]
    assert snapshot["supply_candidates"]
    assert snapshot["competitor_references"]
    assert snapshot["validation_budgets"]
    assert snapshot["opportunity_risks"]
    assert snapshot["action_plans"]
    assert snapshot["boundary_notes"]
    assert_no_forbidden_keys(public_share)
    serialized = json.dumps(public_share, ensure_ascii=False)
    assert "trace-secret" not in serialized
    assert "https://trace.example/secret" not in serialized
    assert "Traceback" not in serialized
    assert "run_id" not in serialized


def test_report_share_handles_missing_enhancements_and_rejects_empty_results(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    empty_task = create_task(test_client)

    empty_response = test_client.post(
        f"/api/v1/research-tasks/{empty_task['uuid']}/report-shares"
    )

    assert empty_response.status_code == 409

    created = create_task_with_only_opportunities(test_client, session_factory)
    response = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/report-shares"
    )

    assert response.status_code == 201
    token = response.json()["share_token"]
    public_response = test_client.get(f"/api/v1/report-shares/{token}")

    assert public_response.status_code == 200
    snapshot = public_response.json()["snapshot"]
    assert len(snapshot["opportunities"]) == 3
    assert snapshot["sources"] == []
    assert snapshot["demand_insights"] == []
    assert snapshot["action_plans"] == []

    missing_response = test_client.get(f"/api/v1/report-shares/{uuid4()}")

    assert missing_response.status_code == 404


def test_revoked_report_share_is_not_publicly_readable(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = execute_task(test_client, session_factory)
    share = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/report-shares"
    ).json()

    revoke_response = test_client.post(
        f"/api/v1/report-shares/{share['uuid']}/revoke"
    )
    public_response = test_client.get(f"/api/v1/report-shares/{share['share_token']}")

    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"
    assert revoke_response.json()["revoked_at"] is not None
    assert public_response.status_code == 404


def test_rerun_keeps_old_snapshot_and_new_share_gets_new_token(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = execute_task(test_client, session_factory)
    first_share = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/report-shares"
    ).json()
    first_public = test_client.get(
        f"/api/v1/report-shares/{first_share['share_token']}"
    ).json()

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

    second_share = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/report-shares"
    ).json()
    first_public_after_rerun = test_client.get(
        f"/api/v1/report-shares/{first_share['share_token']}"
    ).json()

    assert second_share["uuid"] != first_share["uuid"]
    assert second_share["share_token"] != first_share["share_token"]
    assert (
        first_public_after_rerun["snapshot"]["shared_at"]
        == first_public["snapshot"]["shared_at"]
    )

    with session_factory() as db:
        shares = db.execute(select(ReportShare)).scalars().all()

    assert len(shares) == 2


def assert_no_forbidden_keys(value: Any) -> None:
    forbidden = {
        "id",
        "run_id",
        "trace_id",
        "trace_url",
        "current_stage",
        "events",
        "failure_reason",
        "error_summary",
        "stage",
        "raw_metadata",
        "config",
    }

    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden
            assert_no_forbidden_keys(child)
        return

    if isinstance(value, list):
        for item in value:
            assert_no_forbidden_keys(item)
