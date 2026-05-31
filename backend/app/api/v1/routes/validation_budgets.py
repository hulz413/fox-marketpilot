from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.opportunities import service as opportunities_service
from app.modules.research_tasks import service as research_tasks_service
from app.modules.validation_budgets import service as validation_budgets_service
from app.modules.validation_budgets.schemas import OpportunityValidationBudgetRead

router = APIRouter()


@router.get(
    "/research-tasks/{task_uuid}/validation-budgets",
    response_model=list[OpportunityValidationBudgetRead],
)
def list_research_task_validation_budgets(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityValidationBudgetRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    opportunities = opportunities_service.list_task_opportunities(db, task)
    opportunity_uuid_by_id = {
        opportunity.id: opportunity.uuid for opportunity in opportunities
    }

    return [
        validation_budgets_service.validation_budget_to_read(
            budget,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity_uuid_by_id[budget.opportunity_id],
        )
        for budget in validation_budgets_service.list_task_validation_budgets(db, task)
    ]


@router.get(
    "/opportunities/{opportunity_uuid}/validation-budgets",
    response_model=list[OpportunityValidationBudgetRead],
)
def list_opportunity_validation_budgets(
    opportunity_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityValidationBudgetRead]:
    opportunity = opportunities_service.get_opportunity(db, opportunity_uuid)

    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    task = research_tasks_service.get_research_task_by_id(
        db,
        opportunity.research_task_id,
    )

    if task is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return [
        validation_budgets_service.validation_budget_to_read(
            budget,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity.uuid,
        )
        for budget in validation_budgets_service.list_opportunity_validation_budgets(
            db,
            opportunity,
        )
    ]
