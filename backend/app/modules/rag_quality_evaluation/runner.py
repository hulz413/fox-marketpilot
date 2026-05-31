from __future__ import annotations

import argparse
from uuid import UUID

from app.db.session import SessionLocal
from app.modules.rag_quality_evaluation import service
from app.modules.research_tasks import service as research_task_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an internal RAG retrieval quality evaluation.",
    )
    parser.add_argument(
        "--task-uuid",
        required=True,
        help="Public UUID of a completed research task.",
    )
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        help="Evaluation case category to include. Can be repeated.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Override top-k for all evaluation cases.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Optional evaluation run name.",
    )
    parser.add_argument(
        "--skip-load-defaults",
        action="store_true",
        help="Do not upsert default fixture cases before running.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    task_uuid = UUID(args.task_uuid)

    with SessionLocal() as db:
        task = research_task_service.get_research_task(db, task_uuid)
        if task is None:
            raise SystemExit(f"未找到研究任务：{task_uuid}")

        if task.status != "completed":
            raise SystemExit(f"研究任务尚未完成，当前状态：{task.status}")

        evaluation_run = service.run_retrieval_evaluation(
            db,
            task,
            name=args.name,
            categories=args.categories,
            top_k=args.top_k,
            load_defaults=not args.skip_load_defaults,
        )
        print(service.dump_json(service.export_run_results(db, task, evaluation_run)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
