from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
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
from app.modules.agent_runs.models import AgentRunEvent
from app.modules.agent_runs import service as agent_run_events_service
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks import service as research_task_service
from app.modules.sources.models import ResearchSource
from app.modules.sources import service as sources_service
from app.modules.sources.service import SourceCollectionResult, SourceSearchResult


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


def test_research_source_apis_return_fallback_sources(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    opportunities = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/opportunities"
    ).json()
    task_sources_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/sources"
    )
    opportunity_sources_response = test_client.get(
        f"/api/v1/opportunities/{opportunities[0]['uuid']}/sources"
    )

    assert task_sources_response.status_code == 200
    assert opportunity_sources_response.status_code == 200
    task_sources = task_sources_response.json()
    opportunity_sources = opportunity_sources_response.json()
    assert len(task_sources) == 6
    assert len(opportunity_sources) == 2
    assert {"demand", "supply"} <= {source["source_type"] for source in task_sources}
    assert all("id" not in source for source in task_sources)
    assert all(source["research_task_uuid"] == created["uuid"] for source in task_sources)
    assert all(source["opportunity_uuid"] for source in task_sources)
    assert all("初步参考" in source["summary"] for source in task_sources)
    assert all("已证明" not in source["summary"] for source in task_sources)


def test_research_source_apis_filter_deleted_and_missing_resources(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    initial_sources = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/sources"
    ).json()

    with session_factory() as db:
        source = db.execute(
            select(ResearchSource).where(
                ResearchSource.uuid == UUID(initial_sources[0]["uuid"])
            )
        ).scalar_one()
        source.deleted_at = datetime.now(timezone.utc)
        db.commit()

    filtered_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/sources"
    )
    missing_task_response = test_client.get(f"/api/v1/research-tasks/{uuid4()}/sources")
    missing_opportunity_response = test_client.get(
        f"/api/v1/opportunities/{uuid4()}/sources"
    )

    assert filtered_response.status_code == 200
    assert len(filtered_response.json()) == len(initial_sources) - 1
    assert missing_task_response.status_code == 404
    assert missing_opportunity_response.status_code == 404


def test_source_collector_uses_search_extract_and_deduplicates_urls(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created, _ = execute_task(test_client, session_factory)

    class FakeSearchClient:
        def __init__(self) -> None:
            self.calls = 0

        def search(self, query: str, max_results: int) -> list[SourceSearchResult]:
            self.calls += 1
            return [
                SourceSearchResult(
                    title="重复来源",
                    url="https://example.com/shared",
                    content="桌面收纳与小红书内容场景相关。",
                    score=0.91,
                    raw_metadata={"provider": "fake"},
                ),
                SourceSearchResult(
                    title=f"唯一来源 {self.calls}",
                    url=f"https://example.com/source/{self.calls}",
                    content="公开信息提示可以继续做小批量验证。",
                    score=0.48,
                    raw_metadata={"provider": "fake"},
                ),
            ][:max_results]

        def extract(self, urls: list[str]) -> dict[str, str]:
            return {urls[0]: "提取正文显示该方向有内容讨论和初步验证价值。"}

    with session_factory() as db:
        task = db.execute(
            select(ResearchTask).where(ResearchTask.uuid == UUID(created["uuid"]))
        ).scalar_one()
        result = sources_service.collect_research_sources(
            db,
            task,
            search_client=FakeSearchClient(),
        )
        sources = sources_service.list_task_sources(db, task)

    urls = [source.url for source in sources]
    assert result.status == "completed"
    assert result.saved_count == len(sources)
    assert len(urls) == len(set(urls))
    assert Counter(urls)["https://example.com/shared"] == 1
    assert any(source.raw_metadata.get("extract_used") for source in sources)
    assert all("初步参考" in source.summary for source in sources)
    assert all("已证明" not in source.summary for source in sources)


def test_source_collection_failure_keeps_research_completed(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    def fake_collect(*args: Any, **kwargs: Any) -> SourceCollectionResult:
        return SourceCollectionResult(
            status="failed",
            saved_count=0,
            query_count=3,
            error_summary="来源收集失败，基础商机结果已保留。",
        )

    monkeypatch.setattr(graph_module.sources_service, "collect_research_sources", fake_collect)

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
    sources_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/sources"
    )
    progress_response = test_client.get(
        f"/api/v1/research-tasks/{created['uuid']}/progress"
    )

    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert sources_response.status_code == 200
    assert sources_response.json() == []
    assert progress_response.status_code == 200
    collect_events = [
        event
        for event in progress_response.json()["events"]
        if event["stage"] == "collect_research_sources"
    ]
    assert len(collect_events) == 1
    assert collect_events[0]["status"] == agent_run_events_service.STATUS_FAILED
    assert "来源收集失败" in collect_events[0]["error_summary"]
    assert "Traceback" not in collect_events[0]["error_summary"]


def test_source_collection_trace_context_is_recorded(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    @contextmanager
    def fake_langsmith_trace(*args: Any, **kwargs: Any) -> Iterator[Any]:
        from app.integrations.langsmith import TraceContext

        yield TraceContext(
            trace_id="22222222-2222-2222-2222-222222222222",
            trace_url="https://smith.langchain.com/public/trace/22222222",
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

        collect_event = db.execute(
            select(AgentRunEvent).where(
                AgentRunEvent.stage == "collect_research_sources"
            )
        ).scalar_one()

    assert collect_event.trace_id == "22222222-2222-2222-2222-222222222222"
    assert collect_event.event_metadata["source_collection_status"] == "fallback"
