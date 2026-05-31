from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID

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
from app.modules.opportunities.models import Opportunity
from app.modules.rag_retrieval import service as rag_retrieval_service
from app.modules.rag_retrieval.models import RagEvidenceChunk
from app.modules.rag_retrieval.schemas import RagIndexResult
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks import service as research_task_service
from app.modules.sources.models import ResearchSource
from app.modules.sources.schemas import ResearchSourceType


@pytest.fixture()
def session_factory() -> Iterator[sessionmaker[Session]]:
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
    yield testing_session_local
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(
    session_factory: sessionmaker[Session],
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    def override_get_db() -> Iterator[Session]:
        db = session_factory()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, session_factory

    app.dependency_overrides.clear()


def create_task_graph(session_factory: sessionmaker[Session]) -> tuple[int, int, int]:
    with session_factory() as db:
        task = ResearchTask(
            title="桌面收纳研究",
            brief="预算 5000 元以内，寻找桌面收纳类产品。",
            target_channels=["小红书种草"],
            supply_preferences=["1688"],
            status="completed",
            current_stage="completed",
        )
        db.add(task)
        db.flush()
        opportunity = Opportunity(
            research_task_id=task.id,
            rank=1,
            name="桌面收纳香薰托盘",
            product_direction="租房办公桌面整理与氛围改善",
            target_audience="租房办公人群",
            recommendation_reason="适合做图文种草的待验证商机。",
            suitable_channels=["小红书种草"],
            price_band="29-69 元",
            rough_margin="30%-45%",
            risk_level="low",
            priority_label="优先验证",
            next_step_summary="先测试内容互动。",
        )
        db.add(opportunity)
        db.flush()
        competitor_source = ResearchSource(
            research_task_id=task.id,
            opportunity_id=opportunity.id,
            source_type="competitor",
            title="桌面收纳托盘类似产品售价线索",
            url="https://example.com/desk-tray",
            summary="公开线索提到桌面收纳托盘类似产品常见售价和颜值卖点，可作为初步参考。",
            snippet="类似产品强调桌面整理、香薰氛围和低门槛装饰。",
            publisher="Example",
            score=0.88,
            query="桌面收纳托盘 类似产品 售价 卖点",
            linked_claim="类似产品和售价信息可作为竞品初步参考",
            support_level="strong",
            raw_metadata={"provider": "test"},
        )
        supply_source = ResearchSource(
            research_task_id=task.id,
            opportunity_id=opportunity.id,
            source_type="supply",
            title="供给线索",
            url="https://example.com/supply",
            summary="该来源只提示供给方向，不应在竞品检索中优先命中。",
            snippet="供给市场可继续确认价格。",
            publisher="Example",
            score=0.5,
            query="供给 起订量",
            linked_claim="供给方向需要继续确认",
            support_level="medium",
            raw_metadata={"provider": "test"},
        )
        db.add_all([competitor_source, supply_source])
        db.commit()
        return task.id, opportunity.id, competitor_source.id


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


def test_index_task_evidence_builds_chunks_and_rebuilds_active_index(
    session_factory: sessionmaker[Session],
) -> None:
    task_id, _, source_id = create_task_graph(session_factory)

    with session_factory() as db:
        task = db.get(ResearchTask, task_id)
        assert task is not None
        result = rag_retrieval_service.index_task_evidence(db, task)

    assert result.status == "fallback"
    assert result.indexed_count == 2

    with session_factory() as db:
        active_chunks = db.execute(
            select(RagEvidenceChunk).where(RagEvidenceChunk.deleted_at.is_(None))
        ).scalars().all()
        assert len(active_chunks) == 2
        competitor_chunk = next(
            chunk for chunk in active_chunks if chunk.research_source_id == source_id
        )
        assert "标题：桌面收纳托盘类似产品售价线索" in competitor_chunk.chunk_text
        assert "关联判断：类似产品和售价信息可作为竞品初步参考" in competitor_chunk.chunk_text
        assert competitor_chunk.embedding_dimension == 1536

        task = db.get(ResearchTask, task_id)
        assert task is not None
        second_result = rag_retrieval_service.index_task_evidence(db, task)
        assert second_result.indexed_count == 2

        all_chunks = db.execute(select(RagEvidenceChunk)).scalars().all()
        active_count = sum(chunk.deleted_at is None for chunk in all_chunks)
        deleted_count = sum(chunk.deleted_at is not None for chunk in all_chunks)

    assert active_count == 2
    assert deleted_count == 2


def test_retrieve_evidence_is_task_scoped_and_filters_source_types(
    session_factory: sessionmaker[Session],
) -> None:
    task_id, opportunity_id, source_id = create_task_graph(session_factory)

    with session_factory() as db:
        other_task = ResearchTask(
            title="其他任务",
            brief="其他研究",
            status="completed",
            current_stage="completed",
        )
        db.add(other_task)
        db.flush()
        db.add(
            ResearchSource(
                research_task_id=other_task.id,
                opportunity_id=None,
                source_type="competitor",
                title="其他任务强相关桌面收纳售价线索",
                url="https://example.com/other",
                summary="这条来源属于其他任务，不能被当前任务召回。",
                snippet="桌面收纳售价。",
                publisher="Example",
                score=0.99,
                query="桌面收纳 售价",
                linked_claim="其他任务来源",
                support_level="strong",
                raw_metadata={"provider": "test"},
            )
        )
        db.commit()

        task = db.get(ResearchTask, task_id)
        opportunity = db.get(Opportunity, opportunity_id)
        assert task is not None
        assert opportunity is not None
        other_task = db.get(ResearchTask, other_task.id)
        assert other_task is not None
        rag_retrieval_service.index_task_evidence(db, task)
        rag_retrieval_service.index_task_evidence(db, other_task)

        result = rag_retrieval_service.retrieve_evidence(
            db,
            task,
            query="桌面收纳托盘 类似产品 常见售价 卖点",
            opportunity=opportunity,
            source_types=[ResearchSourceType.COMPETITOR],
            top_k=3,
        )

    assert result.status == "fallback"
    assert len(result.evidence) == 1
    assert result.evidence[0].research_source_id == source_id
    assert result.evidence[0].source_type == "competitor"
    assert "其他任务" not in result.evidence[0].summary


def test_retrieve_evidence_degrades_when_embedding_is_unavailable(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id, _, _ = create_task_graph(session_factory)
    monkeypatch.setattr(rag_retrieval_service, "get_embedding_client", lambda: None)

    with session_factory() as db:
        task = db.get(ResearchTask, task_id)
        assert task is not None
        result = rag_retrieval_service.index_task_evidence(db, task)
        retrieval = rag_retrieval_service.retrieve_evidence(
            db,
            task,
            query="桌面收纳 常见售价",
            source_types=[ResearchSourceType.COMPETITOR],
        )

    assert result.status == "skipped"
    assert result.skipped_reason == "embedding_unavailable"
    assert retrieval.status == "skipped"
    assert retrieval.fallback_reason == "embedding_unavailable"


def test_graph_records_rag_index_failure_without_blocking_research(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    created = create_task(test_client)

    def fail_index(db: Session, task: ResearchTask) -> RagIndexResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(graph_module.rag_retrieval_service, "index_task_evidence", fail_index)

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
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"

    with session_factory() as db:
        events = (
            db.execute(
                select(AgentRunEvent)
                .where(AgentRunEvent.run_id == run_id)
                .order_by(AgentRunEvent.id.asc())
            )
            .scalars()
            .all()
        )

    index_event = next(event for event in events if event.stage == "index_rag_evidence")
    assert index_event.status == agent_run_events_service.STATUS_FAILED
    assert index_event.error_summary == "RAG 证据索引失败，基础商机结果已保留。"
    assert any(event.stage == "generate_competitor_references" for event in events)
