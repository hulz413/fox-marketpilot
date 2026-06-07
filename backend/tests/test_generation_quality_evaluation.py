from __future__ import annotations

from collections.abc import Iterator
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.action_plans.models import ActionPlan
from app.modules.competitor_references.models import CompetitorReference
from app.modules.demand_insights.models import OpportunityDemandInsight
from app.modules.generation_quality_evaluation import repository
from app.modules.generation_quality_evaluation import service as evaluation_service
from app.modules.generation_quality_evaluation.models import (
    GenerationEvaluationCase,
    GenerationEvaluationResult,
)
from app.modules.generation_quality_evaluation.schemas import (
    GenerationEvaluationOverallStatus,
    GenerationEvaluationResultStatus,
    GenerationEvaluationRunStatus,
)
from app.modules.generation_quality_evaluation.scorer import (
    GenerationEvaluationContext,
    check_constraints,
    check_cautious_boundary,
    check_structure,
)
from app.modules.opportunities.models import Opportunity
from app.modules.opportunity_risks.models import OpportunityRisk
from app.modules.research_quality_readiness import service as readiness_service
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import ResearchTaskStatus
from app.modules.supply_candidates.models import SupplyCandidate
from app.modules.validation_budgets.models import ValidationBudget


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


def create_completed_task_with_generation_outputs(db: Session) -> ResearchTask:
    task = ResearchTask(
        title="桌面收纳研究",
        brief="预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。",
        budget="5000 元以内",
        target_channels=["小红书种草"],
        excluded_categories=["食品", "电子产品"],
        target_audience="租房办公人群",
        expected_profit="30%",
        supply_preferences=["1688"],
        constraints="不做食品和电子产品，先小预算验证。",
        status=ResearchTaskStatus.COMPLETED.value,
        current_stage="completed",
        run_id="generation-run-1",
    )
    db.add(task)
    db.flush()

    for index in range(3):
        opportunity = Opportunity(
            research_task_id=task.id,
            rank=index + 1,
            name=f"桌面收纳托盘 {index + 1}",
            product_direction="租房办公桌面整理",
            target_audience="租房办公人群",
            recommendation_reason="适合小红书种草的待验证收纳商机。",
            suitable_channels=["小红书种草"],
            price_band="29-69 元",
            rough_margin="30%-45%",
            risk_level="medium",
            priority_label="优先验证",
            next_step_summary="先采购样品并记录收藏、询单和反馈。",
        )
        db.add(opportunity)
        db.flush()

        db.add(
            OpportunityDemandInsight(
                research_task_id=task.id,
                opportunity_id=opportunity.id,
                summary="该方向是初步参考，仍需待验证。",
                audience_profile="租房办公人群希望改善桌面空间。",
                use_cases=["桌面整理", "办公氛围改善"],
                purchase_motivations=["低预算改善空间"],
                content_angles=["小红书前后对比"],
                trend_signals=["内容平台可继续观察"],
                seasonality_notes="日常场景，季节性待确认。",
                source_status="fallback",
            )
        )
        db.add(
            SupplyCandidate(
                research_task_id=task.id,
                opportunity_id=opportunity.id,
                rank=1,
                candidate_name="桌面收纳托盘基础款",
                supply_market="1688 或同类公开批发市场",
                search_keywords=["桌面收纳", "1688", "批发"],
                price_range="按 29-69 元售价倒推询价，待供应商确认。",
                minimum_order_quantity="先问样品或 20-50 件小批量。",
                specification_notes=["确认材质、尺寸和包装。"],
                supplier_questions=["是否支持样品和小批量？"],
                recommendation_note="作为初步参考，价格和库存需要确认。",
                source_status="fallback",
            )
        )
        db.add(
            CompetitorReference(
                research_task_id=task.id,
                opportunity_id=opportunity.id,
                rank=1,
                reference_name="同类桌面收纳参考",
                reference_market="小红书和电商公开线索",
                price_range="类似产品售价仍需继续核对。",
                common_selling_points=["桌面整理", "颜值展示"],
                homogenization_level="medium",
                differentiation_angles=["用租房场景做差异化"],
                reference_note="竞品信息作为初步参考，待验证。",
                source_status="fallback",
            )
        )
        db.add(
            ValidationBudget(
                research_task_id=task.id,
                opportunity_id=opportunity.id,
                estimated_unit_cost="按售价 40%-60% 倒推，待询价确认。",
                estimated_selling_price="29-69 元待验证。",
                rough_gross_margin="30%-45% 待核算。",
                first_batch_quantity="20-50 件小批量。",
                first_batch_budget="控制在 5000 元以内的一小部分。",
                key_assumptions=["支持小批量", "运费不显著压缩毛利"],
                calculation_note="仅作初步参考，需要继续确认。",
                estimate_status="fallback",
            )
        )
        db.add(
            OpportunityRisk(
                research_task_id=task.id,
                opportunity_id=opportunity.id,
                overall_risk_level="medium",
                risk_summary="质量、履约、售后和竞争都需要首轮验证。",
                quality_risk="需要检查材质、做工、气味和包装质量，避免只看图片。",
                fulfillment_risk="需要确认起订量、发货时效、破损补发和补货稳定性。",
                after_sales_risk="需要准备破损、尺寸不符和色差的退换货边界。",
                compliance_risk="需要确认平台规则和宣传边界，不作为合规结论。",
                inventory_risk="先用小批量样品验证，避免首轮压库存。",
                competition_risk="类似产品较多，需要测试场景和包装差异化。",
                platform_risk="标题和功效表达需要继续排查平台规则。",
                risk_triggers=["供应商履约待确认", "竞品同质化待验证"],
                mitigation_suggestions=["先问 2-3 家供应商", "先采购样品测试"],
                review_status="fallback",
            )
        )
        db.add(
            ActionPlan(
                research_task_id=task.id,
                opportunity_id=opportunity.id,
                validation_goal="验证租房办公人群是否收藏、询单和下单。",
                first_batch_plan="先采购样品或 20-50 件小批量，记录反馈。",
                product_validation_method="向 2-3 家供应商询样，拍摄小红书内容测试。",
                content_angles=["桌面前后对比", "租房办公场景"],
                title_suggestions=["桌面收纳小预算试用记录"],
                selling_point_suggestions=["先看样品和真实反馈"],
                supplier_inquiry_script="请确认样品价格、起订量、发货时效、包装和售后责任。",
                prelaunch_checklist=["检查材质", "确认发货", "记录询单反馈"],
                plan_status="fallback",
            )
        )

    db.commit()
    db.refresh(task)
    return task


def make_context(task: ResearchTask) -> GenerationEvaluationContext:
    opportunity = Opportunity(
        research_task_id=task.id,
        rank=1,
        name="电子食品礼盒",
        product_direction="电子食品组合",
        target_audience="泛泛人群",
        recommendation_reason="已核验市场且保证利润。",
        suitable_channels=["抖音"],
        price_band="99 元",
        rough_margin="50%",
        risk_level="low",
        priority_label="优先",
        next_step_summary="自动联系供应商。",
    )
    return GenerationEvaluationContext(
        task=task,
        opportunities=[opportunity],
        demand_insights=[],
        supply_candidates=[],
        competitor_references=[],
        validation_budgets=[],
        opportunity_risks=[],
        action_plans=[],
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
            "constraints",
            "structure",
            "consistency",
            "risk_quality",
            "action_quality",
            "cautious_boundary",
        }

        action_cases = evaluation_service.list_active_evaluation_cases(
            db,
            categories=["action_quality"],
        )
        assert len(action_cases) == 2

        repository.soft_delete_case(db, action_cases[0])
        db.commit()
        active_action_cases = evaluation_service.list_active_evaluation_cases(
            db,
            categories=["action_quality"],
        )
        snapshot = evaluation_service.build_case_snapshot(active_action_cases[0])

    assert len(active_action_cases) == 1
    assert snapshot["uuid"] == str(active_action_cases[0].uuid)
    assert "id" not in snapshot
    assert "rubric" in snapshot


def test_scorer_flags_structure_and_boundary_issues() -> None:
    task = ResearchTask(
        title="违规任务",
        brief="不做食品和电子产品。",
        budget="5000 元以内",
        target_channels=["小红书种草"],
        excluded_categories=["食品", "电子产品"],
        target_audience="租房办公人群",
        expected_profit="30%",
        supply_preferences=["1688"],
        status="completed",
        current_stage="completed",
    )
    context = make_context(task)

    constraints = check_constraints(context)
    structure = check_structure(context)
    boundary = check_cautious_boundary(context)

    assert constraints.status == GenerationEvaluationResultStatus.WARNING
    assert any("预算约束" in reason for reason in constraints.reasons)
    assert any("期望利润约束" in reason for reason in constraints.reasons)
    assert structure.status == GenerationEvaluationResultStatus.FAILED
    assert any("active 商机少于 3 个" in reason for reason in structure.reasons)
    assert boundary.status == GenerationEvaluationResultStatus.FAILED
    assert any("已核验" in reason for reason in boundary.reasons)
    assert any("保证利润" in reason for reason in boundary.reasons)


def test_run_generation_evaluation_persists_metrics_and_safe_output(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        task = create_completed_task_with_generation_outputs(db)
        evaluation_run = evaluation_service.run_generation_evaluation(db, task)
        results = repository.list_active_results_by_run_id(db, evaluation_run.id)
        exported = evaluation_service.export_run_results(db, task, evaluation_run)

    assert evaluation_run.status == GenerationEvaluationRunStatus.COMPLETED.value
    assert evaluation_run.overall_status == GenerationEvaluationOverallStatus.PASSED.value
    assert evaluation_run.case_total == 8
    assert evaluation_run.case_passed_count == 8
    assert evaluation_run.summary_metrics["status_counts"]["passed"] == 8
    assert len(results) == 8
    assert all(result.status == "passed" for result in results)

    exported_json = json.dumps(exported, ensure_ascii=False)
    assert "research_task_id" not in exported_json
    assert "opportunity_id" not in exported_json
    assert "Traceback" not in exported_json
    assert "sk-secret" not in exported_json


def test_generation_evaluation_rejects_unfinished_task_without_state_change(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        task = ResearchTask(
            title="未完成任务",
            brief="还没完成。",
            status="created",
            current_stage="intake",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        with pytest.raises(evaluation_service.GenerationEvaluationUnavailableError):
            evaluation_service.run_generation_evaluation(db, task)

        db.refresh(task)
        runs = db.execute(select(GenerationEvaluationResult)).scalars().all()

    assert task.status == "created"
    assert runs == []


def test_generation_evaluation_degrades_for_case_failure(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session_factory() as db:
        task = create_completed_task_with_generation_outputs(db)
        for index in range(2):
            repository.add_case(
                db,
                GenerationEvaluationCase(
                    category="constraints",
                    name=f"失败降级 case {index}",
                    input_constraints={},
                    expected_signals=[],
                    rubric={"dimension": "constraints"},
                    grading_rubric="测试失败降级。",
                    enabled=True,
                ),
            )
        db.commit()

        calls = {"count": 0}
        original_score = evaluation_service.score_generation_case

        def flaky_score(*args: object, **kwargs: object) -> object:
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("sk-secret-token Traceback with internal stack")
            return original_score(*args, **kwargs)

        monkeypatch.setattr(evaluation_service, "score_generation_case", flaky_score)

        evaluation_run = evaluation_service.run_generation_evaluation(
            db,
            task,
            load_defaults=False,
        )
        results = repository.list_active_results_by_run_id(db, evaluation_run.id)

    assert evaluation_run.status == GenerationEvaluationRunStatus.PARTIAL.value
    assert evaluation_run.overall_status == GenerationEvaluationOverallStatus.FAILED.value
    assert evaluation_run.case_failed_count == 1
    assert [result.status for result in results] == ["passed", "failed"]
    assert "RuntimeError" not in (results[1].error_summary or "")
    assert "sk-secret-token" not in (results[1].error_summary or "")
    assert "Traceback" not in (results[1].error_summary or "")


def test_readiness_includes_generation_evaluation_summary(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        task = create_completed_task_with_generation_outputs(db)
        evaluation_run = evaluation_service.run_generation_evaluation(db, task)
        readiness_run = readiness_service.create_readiness_run(
            db,
            task,
            run_rag_evaluation=False,
        )
        checks = {check["key"]: check for check in readiness_run.checks}

        assert readiness_run.generation_evaluation_run_uuid == evaluation_run.uuid
        assert checks["generation_content_smoke"]["metrics"][
            "generation_evaluation_run_uuid"
        ] == str(evaluation_run.uuid)
        assert checks["generation_content_smoke"]["metrics"][
            "generation_evaluation_overall_status"
        ] == "passed"

        task.run_id = "newer-generation-run"
        db.add(task)
        db.commit()
        stale_readiness_run = readiness_service.create_readiness_run(
            db,
            task,
            run_rag_evaluation=False,
        )
        stale_checks = {check["key"]: check for check in stale_readiness_run.checks}

    assert stale_checks["generation_content_smoke"]["status"] == "warning"
    assert stale_checks["generation_content_smoke"]["metrics"][
        "generation_evaluation_stale"
    ] is True
