from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.integrations.langsmith import langsmith_trace
from app.modules.rag_quality_evaluation import repository
from app.modules.rag_quality_evaluation.fixtures import DEFAULT_RAG_EVALUATION_CASES
from app.modules.rag_quality_evaluation.models import (
    RagEvaluationCase,
    RagEvaluationResult,
    RagEvaluationRun,
)
from app.modules.rag_quality_evaluation.schemas import (
    EvidenceRelevanceScore,
    RagEvaluationCaseCreate,
    RagEvaluationResultRead,
    RagEvaluationResultStatus,
    RagEvaluationRunRead,
    RagEvaluationRunStatus,
    RetrievalMetricScores,
)
from app.modules.rag_retrieval import service as rag_retrieval_service
from app.modules.rag_retrieval.schemas import RagRetrievalEvidence
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources.schemas import ResearchSourceType

MAX_STORED_TEXT_LENGTH = 360


@dataclass(frozen=True)
class GradedEvidence:
    evidence: RagRetrievalEvidence
    grade: int
    note: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_default_evaluation_cases(db: Session) -> list[RagEvaluationCase]:
    cases: list[RagEvaluationCase] = []

    for item in DEFAULT_RAG_EVALUATION_CASES:
        payload = RagEvaluationCaseCreate.model_validate(item)
        existing = (
            repository.get_case_by_uuid(db, payload.uuid)
            if payload.uuid is not None
            else None
        )

        if existing is None:
            evaluation_case = RagEvaluationCase(
                uuid=payload.uuid,
                category=payload.category.value,
                question=payload.question,
                expected_source_types=[
                    source_type.value for source_type in payload.expected_source_types
                ],
                expected_keywords=payload.expected_keywords,
                expected_claims=payload.expected_claims,
                top_k=payload.top_k,
                grading_rubric=payload.grading_rubric,
                enabled=payload.enabled,
                case_metadata=payload.case_metadata,
            )
            repository.add_case(db, evaluation_case)
            cases.append(evaluation_case)
            continue

        if existing.deleted_at is None:
            existing.category = payload.category.value
            existing.question = payload.question
            existing.expected_source_types = [
                source_type.value for source_type in payload.expected_source_types
            ]
            existing.expected_keywords = payload.expected_keywords
            existing.expected_claims = payload.expected_claims
            existing.top_k = payload.top_k
            existing.grading_rubric = payload.grading_rubric
            existing.enabled = payload.enabled
            existing.case_metadata = payload.case_metadata
            db.add(existing)
            cases.append(existing)

    db.commit()

    for evaluation_case in cases:
        db.refresh(evaluation_case)

    return cases


def list_active_evaluation_cases(
    db: Session,
    *,
    categories: Optional[list[str]] = None,
) -> list[RagEvaluationCase]:
    return repository.list_active_cases(db, categories=categories)


def build_case_snapshot(evaluation_case: RagEvaluationCase) -> dict[str, Any]:
    return {
        "uuid": str(evaluation_case.uuid),
        "category": evaluation_case.category,
        "question": evaluation_case.question,
        "expected_source_types": list(evaluation_case.expected_source_types),
        "expected_keywords": list(evaluation_case.expected_keywords),
        "expected_claims": list(evaluation_case.expected_claims),
        "top_k": evaluation_case.top_k,
        "grading_rubric": evaluation_case.grading_rubric,
    }


def build_retrieval_query(evaluation_case: RagEvaluationCase) -> str:
    query_parts = [
        evaluation_case.question,
        *evaluation_case.expected_keywords[:6],
        *evaluation_case.expected_claims[:3],
    ]
    return normalize_space(" ".join(query_parts))


def run_retrieval_evaluation(
    db: Session,
    task: ResearchTask,
    *,
    name: Optional[str] = None,
    categories: Optional[list[str]] = None,
    top_k: Optional[int] = None,
    load_defaults: bool = True,
) -> RagEvaluationRun:
    if load_defaults:
        load_default_evaluation_cases(db)

    evaluation_cases = list_active_evaluation_cases(db, categories=categories)
    evaluation_run = RagEvaluationRun(
        research_task_id=task.id,
        name=name or f"RAG 检索评测 - {task.title}",
        status=RagEvaluationRunStatus.RUNNING.value,
        run_id=task.run_id,
        trace_id=task.trace_id,
        trace_url=task.trace_url,
        config={
            "categories": categories or [],
            "top_k": top_k,
            "metric_names": [
                "hit_rate@k",
                "recall@k",
                "precision@k",
                "mrr@k",
                "ndcg@k",
            ],
        },
        summary_metrics={},
        case_total=len(evaluation_cases),
        started_at=utc_now(),
    )
    repository.add_run(db, evaluation_run)
    db.commit()
    db.refresh(evaluation_run)

    with langsmith_trace(
        "rag_retrieval_evaluation",
        inputs={
            "task_uuid": str(task.uuid),
            "case_count": len(evaluation_cases),
        },
        metadata={
            "evaluation_run_uuid": str(evaluation_run.uuid),
            "task_uuid": str(task.uuid),
            "research_run_id": task.run_id,
            "case_count": len(evaluation_cases),
            "categories": categories or [],
        },
    ) as trace_context:
        if trace_context is not None:
            evaluation_run.trace_id = trace_context.trace_id
            evaluation_run.trace_url = trace_context.trace_url
            db.add(evaluation_run)
            db.commit()
            db.refresh(evaluation_run)

        if not evaluation_cases:
            evaluation_run.status = RagEvaluationRunStatus.FAILED.value
            evaluation_run.error_summary = "没有可用的 RAG 检索评测 case。"
            evaluation_run.completed_at = utc_now()
            db.add(evaluation_run)
            db.commit()
            db.refresh(evaluation_run)
            return evaluation_run

        for evaluation_case in evaluation_cases:
            execute_evaluation_case(
                db,
                task,
                evaluation_run,
                evaluation_case,
                top_k_override=top_k,
            )

    complete_evaluation_run(db, evaluation_run)
    db.refresh(evaluation_run)
    return evaluation_run


def execute_evaluation_case(
    db: Session,
    task: ResearchTask,
    evaluation_run: RagEvaluationRun,
    evaluation_case: RagEvaluationCase,
    *,
    top_k_override: Optional[int] = None,
) -> RagEvaluationResult:
    started_at = utc_now()
    top_k = top_k_override or evaluation_case.top_k
    retrieval_query = build_retrieval_query(evaluation_case)
    case_snapshot = build_case_snapshot(evaluation_case)

    try:
        source_types = [
            ResearchSourceType(source_type)
            for source_type in evaluation_case.expected_source_types
        ]

        with langsmith_trace(
            "rag_retrieval_evaluation_case",
            inputs={
                "query": retrieval_query,
                "top_k": top_k,
                "case_uuid": str(evaluation_case.uuid),
            },
            metadata={
                "evaluation_run_uuid": str(evaluation_run.uuid),
                "case_uuid": str(evaluation_case.uuid),
                "task_uuid": str(task.uuid),
                "category": evaluation_case.category,
                "top_k": top_k,
            },
        ):
            retrieval_result = rag_retrieval_service.retrieve_evidence(
                db,
                task,
                query=retrieval_query,
                source_types=source_types,
                top_k=top_k,
            )

        graded_evidence = [
            grade_retrieval_evidence(evaluation_case, evidence)
            for evidence in retrieval_result.evidence[:top_k]
        ]
        metrics = calculate_retrieval_metrics(
            evaluation_case,
            graded_evidence,
            top_k=top_k,
        )
        result_status = status_from_retrieval_status(retrieval_result.status)
        retrieved_evidence = [
            evidence_to_safe_dict(item)
            for item in graded_evidence
        ]
        scoring_notes = "\n".join(item.note for item in graded_evidence) or (
            "未召回可评分证据。"
        )
        error_summary = safe_error_summary(retrieval_result.error_summary)

        evaluation_result = RagEvaluationResult(
            evaluation_run_id=evaluation_run.id,
            evaluation_case_id=evaluation_case.id,
            status=result_status,
            category=evaluation_case.category,
            question=evaluation_case.question,
            case_snapshot=case_snapshot,
            retrieval_query=retrieval_query,
            top_k=top_k,
            retrieval_status=retrieval_result.status,
            retrieved_evidence=retrieved_evidence,
            relevant_count=metrics.relevant_count,
            expected_count=metrics.expected_count,
            hit_rate=metrics.hit_rate,
            recall=metrics.recall,
            precision=metrics.precision,
            mrr=metrics.mrr,
            ndcg=metrics.ndcg,
            scoring_notes=scoring_notes,
            error_summary=error_summary,
            started_at=started_at,
            completed_at=utc_now(),
        )
    except Exception as exc:
        evaluation_result = RagEvaluationResult(
            evaluation_run_id=evaluation_run.id,
            evaluation_case_id=evaluation_case.id,
            status=RagEvaluationResultStatus.FAILED.value,
            category=evaluation_case.category,
            question=evaluation_case.question,
            case_snapshot=case_snapshot,
            retrieval_query=retrieval_query,
            top_k=top_k,
            retrieval_status="failed",
            retrieved_evidence=[],
            relevant_count=0,
            expected_count=count_expected_items(evaluation_case),
            hit_rate=0.0,
            recall=0.0,
            precision=0.0,
            mrr=0.0,
            ndcg=0.0,
            scoring_notes="检索评测 case 执行失败。",
            error_summary=f"RAG 检索评测 case 执行失败（{type(exc).__name__}）。",
            started_at=started_at,
            completed_at=utc_now(),
        )

    repository.add_result(db, evaluation_result)
    db.commit()
    db.refresh(evaluation_result)
    trace_case_result(task, evaluation_run, evaluation_result)
    return evaluation_result


def trace_case_result(
    task: ResearchTask,
    evaluation_run: RagEvaluationRun,
    evaluation_result: RagEvaluationResult,
) -> None:
    with langsmith_trace(
        "rag_retrieval_evaluation_case_result",
        inputs={
            "case_uuid": str(evaluation_result.case_snapshot.get("uuid")),
            "query": evaluation_result.retrieval_query,
        },
        metadata={
            "evaluation_run_uuid": str(evaluation_run.uuid),
            "task_uuid": str(task.uuid),
            "case_uuid": str(evaluation_result.case_snapshot.get("uuid")),
            "category": evaluation_result.category,
            "top_k": evaluation_result.top_k,
            "retrieval_status": evaluation_result.retrieval_status,
            "status": evaluation_result.status,
            "retrieval_count": len(evaluation_result.retrieved_evidence),
            "relevance_grades": [
                item.get("relevance_grade")
                for item in evaluation_result.retrieved_evidence
            ],
            "hit_rate@k": evaluation_result.hit_rate,
            "recall@k": evaluation_result.recall,
            "precision@k": evaluation_result.precision,
            "mrr@k": evaluation_result.mrr,
            "ndcg@k": evaluation_result.ndcg,
        },
    ):
        return None


def complete_evaluation_run(db: Session, evaluation_run: RagEvaluationRun) -> None:
    results = repository.list_active_results_by_run_id(db, evaluation_run.id)
    completed = [
        result
        for result in results
        if result.status == RagEvaluationResultStatus.COMPLETED.value
    ]
    failed = [
        result
        for result in results
        if result.status == RagEvaluationResultStatus.FAILED.value
    ]
    skipped = [
        result
        for result in results
        if result.status == RagEvaluationResultStatus.SKIPPED.value
    ]
    scored = completed + skipped

    evaluation_run.case_total = len(results)
    evaluation_run.case_completed_count = len(completed)
    evaluation_run.case_failed_count = len(failed)
    evaluation_run.case_skipped_count = len(skipped)
    evaluation_run.average_hit_rate = average([result.hit_rate for result in scored])
    evaluation_run.average_recall = average([result.recall for result in scored])
    evaluation_run.average_precision = average([result.precision for result in scored])
    evaluation_run.average_mrr = average([result.mrr for result in scored])
    evaluation_run.average_ndcg = average([result.ndcg for result in scored])
    evaluation_run.summary_metrics = {
        "hit_rate@k": evaluation_run.average_hit_rate,
        "recall@k": evaluation_run.average_recall,
        "precision@k": evaluation_run.average_precision,
        "mrr@k": evaluation_run.average_mrr,
        "ndcg@k": evaluation_run.average_ndcg,
    }
    evaluation_run.completed_at = utc_now()

    if failed and len(failed) == len(results):
        evaluation_run.status = RagEvaluationRunStatus.FAILED.value
    elif failed:
        evaluation_run.status = RagEvaluationRunStatus.PARTIAL.value
    else:
        evaluation_run.status = RagEvaluationRunStatus.COMPLETED.value

    db.add(evaluation_run)
    db.commit()


def status_from_retrieval_status(status: str) -> str:
    if status == "failed":
        return RagEvaluationResultStatus.FAILED.value
    if status == "skipped":
        return RagEvaluationResultStatus.SKIPPED.value
    return RagEvaluationResultStatus.COMPLETED.value


def grade_retrieval_evidence(
    evaluation_case: RagEvaluationCase,
    evidence: RagRetrievalEvidence,
) -> GradedEvidence:
    score = score_evidence_relevance(evaluation_case, evidence)
    return GradedEvidence(evidence=evidence, grade=score.grade, note=score.note)


def score_evidence_relevance(
    evaluation_case: RagEvaluationCase,
    evidence: RagRetrievalEvidence,
) -> EvidenceRelevanceScore:
    text = normalize_for_match(
        " ".join(
            [
                evidence.title,
                evidence.summary,
                evidence.linked_claim,
                evidence.chunk_text,
            ]
        )
    )
    source_type_match = (
        not evaluation_case.expected_source_types
        or evidence.source_type in evaluation_case.expected_source_types
    )
    keyword_hits = matched_items(evaluation_case.expected_keywords, text)
    claim_hits = matched_items(evaluation_case.expected_claims, text)

    if not source_type_match and not keyword_hits and not claim_hits:
        return EvidenceRelevanceScore(
            grade=0,
            note=f"{evidence.title}: 来源类型和期望判断均未命中。",
        )

    grade = 1
    reasons = []
    if source_type_match:
        reasons.append("来源类型匹配")
    if keyword_hits:
        reasons.append(f"命中关键词 {len(keyword_hits)} 个")
    if claim_hits:
        reasons.append(f"命中判断点 {len(claim_hits)} 个")

    if source_type_match and (len(keyword_hits) >= 2 or claim_hits):
        grade = 2

    if source_type_match and (
        len(claim_hits) >= 2
        or len(keyword_hits) >= 3
        or (claim_hits and len(keyword_hits) >= 2)
    ):
        grade = 3

    return EvidenceRelevanceScore(
        grade=grade,
        note=f"{evidence.title}: {', '.join(reasons) or '弱相关'}，等级 {grade}。",
    )


def calculate_retrieval_metrics(
    evaluation_case: RagEvaluationCase,
    graded_evidence: list[GradedEvidence],
    *,
    top_k: int,
) -> RetrievalMetricScores:
    grades = [item.grade for item in graded_evidence[:top_k]]
    relevant_count = sum(1 for grade in grades if grade > 0)
    expected_items = expected_match_items(evaluation_case)
    covered_count = count_covered_expected_items(expected_items, graded_evidence)
    expected_count = len(expected_items)

    return RetrievalMetricScores(
        hit_rate=1.0 if relevant_count else 0.0,
        recall=calculate_recall(covered_count, expected_count, bool(relevant_count)),
        precision=calculate_precision(grades, top_k),
        mrr=calculate_mrr(grades),
        ndcg=calculate_ndcg(grades, ideal_count=max(expected_count, relevant_count)),
        relevant_count=relevant_count,
        expected_count=expected_count,
    )


def calculate_recall(
    covered_count: int,
    expected_count: int,
    has_relevant_evidence: bool,
) -> float:
    if expected_count <= 0:
        return 1.0 if has_relevant_evidence else 0.0
    return round(min(covered_count / expected_count, 1.0), 6)


def calculate_precision(grades: list[int], top_k: int) -> float:
    if top_k <= 0:
        return 0.0
    relevant_count = sum(1 for grade in grades[:top_k] if grade > 0)
    return round(relevant_count / top_k, 6)


def calculate_mrr(grades: list[int]) -> float:
    for index, grade in enumerate(grades, start=1):
        if grade > 0:
            return round(1.0 / index, 6)
    return 0.0


def calculate_ndcg(grades: list[int], *, ideal_count: int) -> float:
    if not grades:
        return 0.0

    dcg = discounted_cumulative_gain(grades)
    ideal_grades = sorted(grades, reverse=True)

    if ideal_count > len(ideal_grades):
        ideal_grades.extend([3 for _ in range(ideal_count - len(ideal_grades))])

    ideal_grades = ideal_grades[: len(grades)]
    idcg = discounted_cumulative_gain(ideal_grades)

    if idcg == 0:
        return 0.0

    return round(dcg / idcg, 6)


def discounted_cumulative_gain(grades: list[int]) -> float:
    return sum(
        ((2**grade) - 1) / math.log2(index + 1)
        for index, grade in enumerate(grades, start=1)
    )


def expected_match_items(evaluation_case: RagEvaluationCase) -> list[str]:
    return [
        *list(evaluation_case.expected_keywords),
        *list(evaluation_case.expected_claims),
    ]


def count_expected_items(evaluation_case: RagEvaluationCase) -> int:
    return len(expected_match_items(evaluation_case))


def count_covered_expected_items(
    expected_items: list[str],
    graded_evidence: list[GradedEvidence],
) -> int:
    if not expected_items:
        return 0

    evidence_text = normalize_for_match(
        " ".join(
            " ".join(
                [
                    item.evidence.title,
                    item.evidence.summary,
                    item.evidence.linked_claim,
                    item.evidence.chunk_text,
                ]
            )
            for item in graded_evidence
            if item.grade > 0
        )
    )
    return len(matched_items(expected_items, evidence_text))


def matched_items(items: list[str], text: str) -> list[str]:
    matched = []
    for item in items:
        normalized = normalize_for_match(item)
        if normalized and normalized in text:
            matched.append(item)
    return matched


def evidence_to_safe_dict(item: GradedEvidence) -> dict[str, Any]:
    evidence = item.evidence
    return {
        "chunk_uuid": str(evidence.chunk_uuid),
        "research_source_uuid": str(evidence.research_source_uuid),
        "source_type": evidence.source_type,
        "support_level": evidence.support_level,
        "title": clip_text(evidence.title, 300),
        "url": evidence.url,
        "summary": clip_text(evidence.summary, MAX_STORED_TEXT_LENGTH),
        "linked_claim": clip_text(evidence.linked_claim, MAX_STORED_TEXT_LENGTH),
        "retriever_score": round(float(evidence.relevance_score), 6),
        "relevance_grade": item.grade,
        "grading_note": item.note,
    }


def evaluation_run_to_read(
    evaluation_run: RagEvaluationRun,
    *,
    research_task_uuid: Optional[UUID],
) -> RagEvaluationRunRead:
    return RagEvaluationRunRead(
        uuid=evaluation_run.uuid,
        research_task_uuid=research_task_uuid,
        name=evaluation_run.name,
        status=evaluation_run.status,
        run_id=evaluation_run.run_id,
        trace_id=evaluation_run.trace_id,
        trace_url=evaluation_run.trace_url,
        config=evaluation_run.config,
        summary_metrics=evaluation_run.summary_metrics,
        case_total=evaluation_run.case_total,
        case_completed_count=evaluation_run.case_completed_count,
        case_failed_count=evaluation_run.case_failed_count,
        case_skipped_count=evaluation_run.case_skipped_count,
        average_hit_rate=evaluation_run.average_hit_rate,
        average_recall=evaluation_run.average_recall,
        average_precision=evaluation_run.average_precision,
        average_mrr=evaluation_run.average_mrr,
        average_ndcg=evaluation_run.average_ndcg,
        error_summary=evaluation_run.error_summary,
        started_at=evaluation_run.started_at,
        completed_at=evaluation_run.completed_at,
        created_at=evaluation_run.created_at,
        updated_at=evaluation_run.updated_at,
        deleted_at=evaluation_run.deleted_at,
    )


def evaluation_result_to_read(
    evaluation_result: RagEvaluationResult,
    *,
    evaluation_case_uuid: UUID,
) -> RagEvaluationResultRead:
    return RagEvaluationResultRead(
        uuid=evaluation_result.uuid,
        evaluation_case_uuid=evaluation_case_uuid,
        status=evaluation_result.status,
        category=evaluation_result.category,
        question=evaluation_result.question,
        case_snapshot=evaluation_result.case_snapshot,
        retrieval_query=evaluation_result.retrieval_query,
        top_k=evaluation_result.top_k,
        retrieval_status=evaluation_result.retrieval_status,
        retrieved_evidence=evaluation_result.retrieved_evidence,
        relevant_count=evaluation_result.relevant_count,
        expected_count=evaluation_result.expected_count,
        hit_rate=evaluation_result.hit_rate,
        recall=evaluation_result.recall,
        precision=evaluation_result.precision,
        mrr=evaluation_result.mrr,
        ndcg=evaluation_result.ndcg,
        scoring_notes=evaluation_result.scoring_notes,
        error_summary=evaluation_result.error_summary,
        started_at=evaluation_result.started_at,
        completed_at=evaluation_result.completed_at,
        created_at=evaluation_result.created_at,
        updated_at=evaluation_result.updated_at,
        deleted_at=evaluation_result.deleted_at,
    )


def export_run_results(
    db: Session,
    task: ResearchTask,
    evaluation_run: RagEvaluationRun,
) -> dict[str, Any]:
    results = repository.list_active_results_by_run_id(db, evaluation_run.id)
    return {
        "run": evaluation_run_to_read(
            evaluation_run,
            research_task_uuid=task.uuid,
        ).model_dump(mode="json"),
        "results": [
            evaluation_result_to_read(
                result,
                evaluation_case_uuid=UUID(str(result.case_snapshot["uuid"])),
            ).model_dump(mode="json")
            for result in results
        ],
    }


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def safe_error_summary(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    normalized = normalize_space(str(value))
    if not normalized:
        return None

    if "Traceback" in normalized or normalized.startswith('File "'):
        return "RAG 检索评测失败，请查看应用日志。"

    first_line = normalized.splitlines()[0].strip()
    if not first_line:
        return None

    redacted = sanitize_sensitive_text(first_line)
    return redacted[:300]


def sanitize_sensitive_text(value: str) -> str:
    sanitized = value
    replacements = [
        ("sk-", "sk-***"),
        ("api_key=", "api_key=***"),
        ("api-key=", "api-key=***"),
        ("apikey=", "apikey=***"),
        ("authorization:", "authorization: ***"),
        ("bearer ", "bearer ***"),
    ]

    lowered = sanitized.lower()
    for needle, replacement in replacements:
        index = lowered.find(needle)
        if index >= 0:
            suffix_start = index + len(needle)
            suffix_end = suffix_start
            while suffix_end < len(sanitized) and sanitized[suffix_end] not in " ,;":
                suffix_end += 1
            sanitized = (
                sanitized[:index]
                + replacement
                + sanitized[suffix_end:]
            )
            lowered = sanitized.lower()

    return sanitized


def normalize_for_match(value: str) -> str:
    return normalize_space(value).lower()


def normalize_space(value: str) -> str:
    return " ".join(str(value).split())


def clip_text(value: str, limit: int) -> str:
    normalized = normalize_space(value)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."


def dump_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
