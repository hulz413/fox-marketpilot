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
from app.modules.opportunities.models import Opportunity
from app.modules.opportunities.schemas import OpportunityGenerationResult
from app.modules.rag_retrieval.models import RagEvidenceChunk
from app.modules.research_quality_readiness import service as readiness_service
from app.modules.research_quality_readiness.models import ResearchQualityReadinessRun
from app.modules.research_tasks import service as research_task_service
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import ResearchTaskStage, ResearchTaskStatus


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


def complete_task_with_only_opportunities(
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
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.run_id = "manual-completed-run"
        db.add(task)
        db.commit()

    return created


def test_readiness_api_create_read_latest_and_stale(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = execute_task(test_client, session_factory)

    create_response = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/readiness-runs"
    )

    assert create_response.status_code == 201
    readiness = create_response.json()
    assert "id" not in readiness
    assert readiness["research_task_uuid"] == created["uuid"]
    assert readiness["status"] == "completed"
    assert readiness["overall_status"] in {"ready", "warning", "failed"}
    assert readiness["checks"]
    assert any(check["key"] == "rag_index_health" for check in readiness["checks"])
    assert readiness["rag_evaluation_run_uuid"]
    assert readiness["stale"] is False

    serialized = json.dumps(readiness, ensure_ascii=False)
    assert "chunk_text" not in serialized
    assert "Traceback" not in serialized

    latest_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/readiness-runs/latest"
    )

    assert latest_response.status_code == 200
    assert latest_response.json()["uuid"] == readiness["uuid"]

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        task.run_id = "newer-run"
        db.add(task)
        db.commit()

    stale_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/readiness-runs/latest"
    )

    assert stale_response.status_code == 200
    assert stale_response.json()["stale"] is True


def test_readiness_rejects_unfinished_tasks_without_state_change(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    response = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/readiness-runs"
    )

    assert response.status_code == 409
    assert "尚未完成" in response.json()["detail"]

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        assert task.status == ResearchTaskStatus.CREATED.value
        assert db.execute(select(ResearchQualityReadinessRun)).scalars().all() == []


def test_readiness_warns_for_missing_enhancements_and_generation_smoke(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = complete_task_with_only_opportunities(test_client, session_factory)

    response = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/readiness-runs"
    )

    assert response.status_code == 201
    checks = {check["key"]: check for check in response.json()["checks"]}
    assert checks["rag_index_health"]["status"] == "warning"
    assert checks["generation_content_smoke"]["status"] == "warning"
    assert "增强分析缺失" in " ".join(
        checks["generation_content_smoke"]["reasons"]
    )


def test_readiness_rag_evaluation_failure_is_non_blocking(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = execute_task(test_client, session_factory)

    def fail_evaluation(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Traceback (most recent call last): secret")

    monkeypatch.setattr(
        readiness_service.rag_quality_evaluation_service,
        "run_retrieval_evaluation",
        fail_evaluation,
    )

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        original_status = task.status
        original_opportunity_count = len(
            db.execute(
                select(Opportunity).where(Opportunity.research_task_id == task.id)
            )
            .scalars()
            .all()
        )
        original_chunk_count = len(
            db.execute(
                select(RagEvidenceChunk).where(
                    RagEvidenceChunk.research_task_id == task.id,
                    RagEvidenceChunk.deleted_at.is_(None),
                )
            )
            .scalars()
            .all()
        )

    response = test_client.post(
        f"/api/v1/research-tasks/{created['uuid']}/readiness-runs"
    )

    assert response.status_code == 201
    checks = {check["key"]: check for check in response.json()["checks"]}
    assert checks["rag_retrieval_evaluation"]["status"] == "warning"
    assert "RAG 检索评测失败" in " ".join(
        checks["rag_retrieval_evaluation"]["reasons"]
    )

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        assert task.status == original_status
        assert (
            len(
                db.execute(
                    select(Opportunity).where(Opportunity.research_task_id == task.id)
                )
                .scalars()
                .all()
            )
            == original_opportunity_count
        )
        assert (
            len(
                db.execute(
                    select(RagEvidenceChunk).where(
                        RagEvidenceChunk.research_task_id == task.id,
                        RagEvidenceChunk.deleted_at.is_(None),
                    )
                )
                .scalars()
                .all()
            )
            == original_chunk_count
        )


def test_latest_readiness_not_found_returns_null_and_unknown_task_404(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = create_task(test_client)

    latest_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/readiness-runs/latest"
    )
    missing_response = test_client.get(
        f"/api/v1/research-tasks/{uuid4()}/readiness-runs/latest"
    )

    assert latest_response.status_code == 200
    assert latest_response.json() is None
    assert missing_response.status_code == 404
