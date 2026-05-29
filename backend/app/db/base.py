from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


import app.modules.research_tasks.models  # noqa: E402,F401
