from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


import app.modules.research_tasks.models  # noqa: E402,F401
import app.modules.opportunities.models  # noqa: E402,F401
