from __future__ import annotations

from collections.abc import Iterator
import json
import math
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.opportunities.models import Opportunity
from app.modules.rag_quality_evaluation import repository
from app.modules.rag_quality_evaluation import service as evaluation_service
from app.modules.rag_quality_evaluation.models import (
    RagEvaluationCase,
    RagEvaluationResult,
)
from app.modules.rag_quality_evaluation.schemas import RagEvaluationRunStatus
from app.modules.rag_retrieval import service as rag_retrieval_service
from app.modules.rag_retrieval.schemas import RagRetrievalEvidence, RagRetrievalResult
from app.modules.research_tasks.models import ResearchTask
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


def create_completed_task_with_sources(db: Session) -> ResearchTask:
    task = ResearchTask(
        title="桌面收纳研究",
        brief="寻找适合小红书种草的桌面收纳产品。",
        target_channels=["小红书种草"],
        supply_preferences=["1688"],
        status="completed",
        current_stage="completed",
        run_id="research-test-run",
        trace_id="trace-test",
        trace_url="https://smith.langchain.com/public/test",
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

    db.add(
        ResearchSource(
            research_task_id=task.id,
            opportunity_id=opportunity.id,
            source_type=ResearchSourceType.COMPETITOR.value,
            title="桌面收纳托盘类似产品售价和差异化线索",
            url="https://example.com/desk-tray",
            summary=(
                "公开线索提到同类产品、类似产品、售价、价格、卖点、同质化和差异化，"
                "可作为竞品初步参考。"
            ),
            snippet="类似产品强调桌面整理、香薰氛围和低门槛装饰。",
            publisher="Example",
            score=0.88,
            query="桌面收纳托盘 类似产品 售价 卖点 差异化",
            linked_claim="类似产品和售价信息可作为竞品初步参考；同类产品常见卖点可帮助判断差异化空间",
            support_level="strong",
            raw_metadata={"provider": "test"},
        )
    )
    db.commit()
    db.refresh(task)
    return task


def make_case() -> RagEvaluationCase:
    return RagEvaluationCase(
        category="competitor",
        question="这个商机有哪些类似产品？",
        expected_source_types=["competitor"],
        expected_keywords=["类似产品", "售价", "卖点"],
        expected_claims=["类似产品和售价信息可作为竞品初步参考"],
        top_k=5,
        grading_rubric="覆盖类似产品、售价或卖点越多，相关性越高。",
        enabled=True,
    )


def make_evidence(
    *,
    title: str,
    text: str,
    source_type: str = "competitor",
    score: float = 0.8,
) -> RagRetrievalEvidence:
    return RagRetrievalEvidence(
        chunk_uuid=uuid4(),
        research_source_id=123,
        research_source_uuid=uuid4(),
        opportunity_id=456,
        opportunity_uuid=None,
        source_type=source_type,
        support_level="strong",
        title=title,
        url="https://example.com/evidence",
        summary=text,
        linked_claim=text,
        chunk_text=text,
        relevance_score=score,
    )


def test_default_fixture_loading_filters_and_snapshots_cases(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        loaded_cases = evaluation_service.load_default_evaluation_cases(db)
        assert len(loaded_cases) == 8

        active_cases = evaluation_service.list_active_evaluation_cases(db)
        assert len(active_cases) == 8
        assert {case.category for case in active_cases} == {
            "demand",
            "supply",
            "competitor",
            "risk",
        }

        competitor_cases = evaluation_service.list_active_evaluation_cases(
            db,
            categories=["competitor"],
        )
        assert len(competitor_cases) == 2

        repository.soft_delete_case(db, competitor_cases[0])
        db.commit()
        active_competitor_cases = evaluation_service.list_active_evaluation_cases(
            db,
            categories=["competitor"],
        )

        snapshot = evaluation_service.build_case_snapshot(active_competitor_cases[0])

    assert len(active_competitor_cases) == 1
    assert snapshot["uuid"] == str(active_competitor_cases[0].uuid)
    assert "id" not in snapshot
    assert "expected_keywords" in snapshot


def test_retrieval_metric_calculation_covers_p0_metrics() -> None:
    evaluation_case = make_case()
    graded_evidence = [
        evaluation_service.GradedEvidence(
            make_evidence(title="无关来源", text="泛泛背景", source_type="supply"),
            grade=0,
            note="不相关",
        ),
        evaluation_service.GradedEvidence(
            make_evidence(
                title="强相关来源",
                text="类似产品 售价 卖点 类似产品和售价信息可作为竞品初步参考",
            ),
            grade=3,
            note="强相关",
        ),
        evaluation_service.GradedEvidence(
            make_evidence(title="相关来源", text="类似产品 卖点"),
            grade=2,
            note="相关",
        ),
        evaluation_service.GradedEvidence(
            make_evidence(title="无关来源 2", text="供给起订量", source_type="supply"),
            grade=0,
            note="不相关",
        ),
        evaluation_service.GradedEvidence(
            make_evidence(title="弱相关来源", text="售价"),
            grade=1,
            note="弱相关",
        ),
    ]

    metrics = evaluation_service.calculate_retrieval_metrics(
        evaluation_case,
        graded_evidence,
        top_k=5,
    )

    assert metrics.hit_rate == 1.0
    assert metrics.recall == 1.0
    assert metrics.precision == 0.6
    assert metrics.mrr == 0.5
    assert metrics.relevant_count == 3
    assert metrics.expected_count == 4
    assert math.isclose(metrics.ndcg, 0.671085, rel_tol=0.000001)
    assert evaluation_service.calculate_recall(2, 4, True) == 0.5
    assert evaluation_service.calculate_precision([0, 3, 2], 5) == 0.4
    assert evaluation_service.calculate_mrr([0, 0, 1]) == 0.333333


def test_run_retrieval_evaluation_persists_metrics_and_safe_output(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        task = create_completed_task_with_sources(db)
        index_result = rag_retrieval_service.index_task_evidence(db, task)
        evaluation_run = evaluation_service.run_retrieval_evaluation(
            db,
            task,
            categories=["competitor"],
            top_k=3,
        )
        results = repository.list_active_results_by_run_id(db, evaluation_run.id)
        exported = evaluation_service.export_run_results(db, task, evaluation_run)

    assert index_result.status == "fallback"
    assert evaluation_run.status == RagEvaluationRunStatus.COMPLETED.value
    assert evaluation_run.case_total == 2
    assert evaluation_run.case_completed_count == 2
    assert evaluation_run.average_hit_rate == 1.0
    assert evaluation_run.average_mrr == 1.0
    assert len(results) == 2

    for result in results:
        assert result.status == "completed"
        assert result.retrieval_status == "fallback"
        assert result.hit_rate == 1.0
        assert result.retrieved_evidence
        evidence = result.retrieved_evidence[0]
        assert evidence["research_source_uuid"]
        assert evidence["chunk_uuid"]
        assert evidence["relevance_grade"] > 0
        assert "research_source_id" not in evidence
        assert "opportunity_id" not in evidence
        assert "chunk_text" not in evidence

    exported_json = json.dumps(exported, ensure_ascii=False)
    assert "research_source_id" not in exported_json
    assert "opportunity_id" not in exported_json
    assert "chunk_text" not in exported_json


def test_evaluation_degrades_for_skipped_empty_and_failed_cases(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session_factory() as db:
        task = create_completed_task_with_sources(db)
        for index in range(3):
            repository.add_case(
                db,
                RagEvaluationCase(
                    category="risk",
                    question=f"风险评测问题 {index}",
                    expected_source_types=["risk"],
                    expected_keywords=["风险"],
                    expected_claims=["风险需要确认"],
                    top_k=5,
                    grading_rubric="风险来源优先。",
                    enabled=True,
                ),
            )
        db.commit()

        responses = [
            RagRetrievalResult(
                status="skipped",
                query="风险",
                top_k=5,
                source_types=["risk"],
                evidence=[],
                fallback_reason="embedding_unavailable",
            ),
            RagRetrievalResult(
                status="empty",
                query="风险",
                top_k=5,
                source_types=["risk"],
                evidence=[],
                fallback_reason="no_chunks",
            ),
        ]

        def fake_retrieve(*args: object, **kwargs: object) -> RagRetrievalResult:
            if responses:
                return responses.pop(0)
            raise RuntimeError("sk-secret-token Traceback with internal stack")

        monkeypatch.setattr(
            evaluation_service.rag_retrieval_service,
            "retrieve_evidence",
            fake_retrieve,
        )

        evaluation_run = evaluation_service.run_retrieval_evaluation(
            db,
            task,
            categories=["risk"],
            load_defaults=False,
        )
        results = (
            db.execute(
                select(RagEvaluationResult)
                .where(RagEvaluationResult.evaluation_run_id == evaluation_run.id)
                .order_by(RagEvaluationResult.id.asc())
            )
            .scalars()
            .all()
        )

    assert evaluation_run.status == RagEvaluationRunStatus.PARTIAL.value
    assert evaluation_run.case_completed_count == 1
    assert evaluation_run.case_skipped_count == 1
    assert evaluation_run.case_failed_count == 1
    assert [result.status for result in results] == ["skipped", "completed", "failed"]
    assert results[0].hit_rate == 0.0
    assert results[1].retrieval_status == "empty"
    assert results[1].precision == 0.0
    assert "RuntimeError" in (results[2].error_summary or "")
    assert "sk-secret-token" not in (results[2].error_summary or "")
    assert "Traceback" not in (results[2].error_summary or "")


def test_safe_error_summary_redacts_sensitive_text() -> None:
    assert (
        evaluation_service.safe_error_summary("Traceback (most recent call last):")
        == "RAG 检索评测失败，请查看应用日志。"
    )
    assert evaluation_service.safe_error_summary(
        "Authorization: Bearer secret-token"
    ) == "authorization: *** bearer ***"
    assert evaluation_service.safe_error_summary(
        "provider failed: sk-secret-token"
    ) == "provider failed: sk-***"
