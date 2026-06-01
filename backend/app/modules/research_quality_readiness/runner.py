from __future__ import annotations

import argparse
from uuid import UUID

from app.db.session import SessionLocal
from app.modules.research_quality_readiness import service
from app.modules.research_tasks import service as research_task_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an internal research quality readiness check.",
    )
    parser.add_argument(
        "--task-uuid",
        required=True,
        help="Public UUID of a completed research task.",
    )
    parser.add_argument(
        "--skip-rag-evaluation",
        action="store_true",
        help="Skip running RAG retrieval evaluation during readiness check.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    task_uuid = UUID(args.task_uuid)

    with SessionLocal() as db:
        task = research_task_service.get_research_task(db, task_uuid)
        if task is None:
            raise SystemExit(f"未找到研究任务：{task_uuid}")

        try:
            readiness_run = service.create_readiness_run(
                db,
                task,
                run_rag_evaluation=not args.skip_rag_evaluation,
            )
        except service.ReadinessUnavailableError as exc:
            raise SystemExit(str(exc)) from exc
        print(
            service.dump_json(
                service.readiness_run_to_read(
                    readiness_run,
                    task=task,
                ).model_dump(mode="json")
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
