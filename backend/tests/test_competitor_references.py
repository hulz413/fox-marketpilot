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
from app.modules.competitor_references import service as competitor_references_service
from app.modules.competitor_references.models import CompetitorReference
from app.modules.competitor_references.service import CompetitorReferenceGenerationError
from app.modules.opportunities.models import Opportunity
from app.modules.rag_retrieval import service as rag_retrieval_service
from app.modules.sources.models import ResearchSource


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


def test_competitor_reference_apis_return_fallback_references(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    task_references_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/competitor-references"
    )
    opportunity_references_response = test_client.get(
        f"/api/v1/opportunities/{opportunities[0]['uuid']}/competitor-references"
    )

    assert task_references_response.status_code == 200
    assert opportunity_references_response.status_code == 200
    task_references = task_references_response.json()
    opportunity_references = opportunity_references_response.json()
    assert len(task_references) == 6
    assert len(opportunity_references) == 2
    assert Counter(reference["opportunity_uuid"] for reference in task_references) == {
        opportunity["uuid"]: 2 for opportunity in opportunities
    }
    assert all("id" not in reference for reference in task_references)
    assert all(
        "id" not in source
        for reference in task_references
        for source in reference["sources"]
    )
    assert all(reference["source_status"] == "fallback" for reference in task_references)
    assert all(reference["sources"] == [] for reference in task_references)
    assert all("参考" in reference["reference_name"] for reference in task_references)
    assert all(reference["common_selling_points"] for reference in task_references)
    assert all(reference["differentiation_angles"] for reference in task_references)
    assert all(
        reference["homogenization_level"] in {"low", "medium", "high"}
        for reference in task_references
    )
    assert all("市场已证明" not in reference["reference_note"] for reference in task_references)

    with session_factory() as db:
        competitor_event = db.execute(
            select(AgentRunEvent).where(
                AgentRunEvent.stage == "generate_competitor_references"
            )
        ).scalar_one()

    assert competitor_event.status == agent_run_events_service.STATUS_COMPLETED
    assert competitor_event.event_metadata["saved_competitor_reference_count"] == 6
    assert competitor_event.event_metadata["source_link_count"] == 0


def test_competitor_references_can_link_competitor_sources(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)
    opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        first_opportunity_id = db.execute(
            select(Opportunity.id).where(
                Opportunity.research_task_id == task.id,
                Opportunity.deleted_at.is_(None),
            )
        ).scalars().first()
        assert first_opportunity_id is not None
        db.add(
            ResearchSource(
                research_task_id=task.id,
                opportunity_id=first_opportunity_id,
                source_type="competitor",
                title="同类产品售价线索",
                url="https://example.com/competitor",
                summary="公开内容提到类似产品的卖点和价格区间，可作为初步参考。",
                snippet="类似产品强调场景化卖点。",
                publisher="Example",
                score=0.72,
                query="同类产品 售价 卖点",
                linked_claim="类似产品和售价信息可作为竞品初步参考",
                support_level="medium",
                raw_metadata={"provider": "test"},
            )
        )
        db.commit()
        rag_retrieval_service.index_task_evidence(db, task)
        result = competitor_references_service.collect_competitor_references(db, task)

        assert result.retrieval_query_count == 3
        assert result.retrieval_result_count >= 1
        assert result.retrieval_fallback_count < 3

    references = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/competitor-references"
    ).json()
    linked_references = [
        reference
        for reference in references
        if reference["opportunity_uuid"] == opportunities[0]["uuid"]
    ]

    assert all(reference["source_status"] == "linked" for reference in linked_references)
    assert all(reference["sources"] for reference in linked_references)
    assert all(
        source["uuid"] and "id" not in source
        for reference in linked_references
        for source in reference["sources"]
    )


def test_competitor_references_are_replaced_on_rerun(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)
    initial_candidates = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/competitor-references"
    ).json()
    rerun_task(created["uuid"], session_factory)

    current_opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    current_candidates_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/competitor-references"
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
            select(CompetitorReference).where(
                CompetitorReference.research_task_id == task.id
            )
        ).scalars().all()

    assert len(candidates) == 12
    assert len([candidate for candidate in candidates if candidate.deleted_at is None]) == 6


def test_competitor_reference_validation_rejects_confirmed_competitor_claims(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    class InvalidCompetitorReferenceGenerator:
        def generate(self, context: dict[str, Any]) -> dict[str, Any]:
            references: list[dict[str, Any]] = []

            for opportunity in context["opportunities"]:
                references.extend(
                    [
                        {
                            "opportunity_uuid": opportunity["uuid"],
                            "rank": 1,
                            "reference_name": "竞品已全面核验的参考",
                            "reference_market": "公开平台",
                            "price_range": "售价已确认。",
                            "common_selling_points": ["销量已确认。"],
                            "homogenization_level": "medium",
                            "differentiation_angles": ["继续观察。"],
                            "reference_note": "市场已证明。",
                        },
                        {
                            "opportunity_uuid": opportunity["uuid"],
                            "rank": 2,
                            "reference_name": "备用类似产品参考",
                            "reference_market": "公开内容平台",
                            "price_range": "售价待确认。",
                            "common_selling_points": ["场景化卖点。"],
                            "homogenization_level": "medium",
                            "differentiation_angles": ["用人群场景做差异化。"],
                            "reference_note": "作为初步参考。",
                        },
                    ]
                )

            return {"references": references}

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()

        with pytest.raises(CompetitorReferenceGenerationError):
            competitor_references_service.collect_competitor_references(
                db,
                task,
                generator=InvalidCompetitorReferenceGenerator(),
            )


def test_competitor_reference_failure_keeps_research_completed(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    def fake_collect(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        graph_module.competitor_references_service,
        "collect_competitor_references",
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
        f"/api/v1/research-tasks/{created['uuid']}/competitor-references"
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
    competitor_events = [
        event
        for event in progress_response.json()["events"]
        if event["stage"] == "generate_competitor_references"
    ]
    assert len(competitor_events) == 1
    assert competitor_events[0]["status"] == agent_run_events_service.STATUS_FAILED
    assert "竞品参考生成失败" in competitor_events[0]["error_summary"]
    assert "Traceback" not in competitor_events[0]["error_summary"]


def test_competitor_reference_missing_resources_return_expected_status(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = create_task(test_client)

    empty_task_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/competitor-references"
    )
    missing_task_response = test_client.get(
        f"/api/v1/research-tasks/{uuid4()}/competitor-references"
    )
    missing_opportunity_response = test_client.get(
        f"/api/v1/opportunities/{uuid4()}/competitor-references"
    )

    assert empty_task_response.status_code == 200
    assert empty_task_response.json() == []
    assert missing_task_response.status_code == 404
    assert missing_opportunity_response.status_code == 404
