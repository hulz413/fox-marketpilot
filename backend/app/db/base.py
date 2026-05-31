from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


import app.modules.research_tasks.models  # noqa: E402,F401
import app.modules.opportunities.models  # noqa: E402,F401
import app.modules.agent_runs.models  # noqa: E402,F401
import app.modules.sources.models  # noqa: E402,F401
import app.modules.demand_insights.models  # noqa: E402,F401
import app.modules.supply_candidates.models  # noqa: E402,F401
import app.modules.competitor_references.models  # noqa: E402,F401
import app.modules.validation_budgets.models  # noqa: E402,F401
import app.modules.opportunity_risks.models  # noqa: E402,F401
import app.modules.action_plans.models  # noqa: E402,F401
import app.modules.rag_retrieval.models  # noqa: E402,F401
import app.modules.rag_quality_evaluation.models  # noqa: E402,F401
