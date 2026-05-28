# MarketPilot Backend

这是 MarketPilot 的 FastAPI 后端和 Agent runtime，部署时使用 `backend/` 作为 Railway Web Service 和 Worker Service root directory。

## 常用命令

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
celery -A app.workers.celery_app worker --loglevel=info
pytest
ruff check .
```
