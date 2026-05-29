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

## 基础商机研究运行

`run-opportunity-research` 使用 LangGraph 单图工作流生成基础商机推荐。`ENVIRONMENT=local`
或 `ENVIRONMENT=test` 且未配置 `LLM_API_KEY` 时，后端会使用确定性 fallback 生成
3 个中文待验证商机，方便本地开发和自动化测试。

生产环境应配置真实 OpenAI-compatible LLM 凭证；缺少 `LLM_API_KEY` 时不应静默使用
fallback。当前基础研究运行不做外部前置调研，不调用 Tavily、Playwright、RAG、向量检索
或来源收集模块。
