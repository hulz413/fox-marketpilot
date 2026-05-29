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

## Agent 运行可观测性

基础研究运行会保存 `agent_run_events` 阶段历史和耗时。LangSmith tracing 默认关闭；本地需要真实 trace 时，在 `backend/.env` 配置：

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_PROJECT=marketpilot-dev
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
# Service Key 或 org-scoped key 需要指定目标 workspace。
LANGSMITH_WORKSPACE_ID=<your-workspace-id>
```

生产环境在 Railway Web Service 和 Worker Service 中使用同一组 LangSmith 变量，并设置：

```bash
LANGSMITH_PROJECT=marketpilot-prod
```

默认 hosted LangSmith 可以使用 `https://api.smith.langchain.com`；APAC、EU 区域或自托管实例需要把 `LANGSMITH_ENDPOINT` 改成对应端点。使用 Service Key 或 org-scoped key 时，通常还需要配置 `LANGSMITH_WORKSPACE_ID`，否则 SDK 可能无法判断 trace 写入哪个 workspace 并返回 403。API 与 Celery worker 必须使用同一个 `LANGSMITH_PROJECT`、`LANGSMITH_ENDPOINT` 和必要的 workspace ID，否则任务里的 trace 入口可能和 worker 产出的 trace 分散到不同 project、endpoint 或 workspace。关闭 tracing 时保留 `LANGSMITH_TRACING=false` 即可；阶段事件落库和基础任务状态不依赖 LangSmith 凭证。
