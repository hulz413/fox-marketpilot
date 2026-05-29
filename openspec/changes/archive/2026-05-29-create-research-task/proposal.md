## Why

当前产品骨架已经提供“新建研究”和“研究任务”入口，但用户提交需求后还不会创建真实业务对象，后续研究执行、进度观测、商机结果和报告都缺少统一锚点。

本 change 将研究任务创建作为 P0 闭环的第一步，让用户可以从自然语言或关键条件提交商机研究需求，并在任务列表中看到真实创建的任务。

## What Changes

- 新增研究任务创建能力，支持用户提交自然语言需求和关键研究条件。
- 新增研究任务读取能力，让任务列表展示真实任务而不是静态演示数据。
- 前端新建研究页面改为提交真实任务，并在创建成功后进入任务列表或对应任务入口。
- 为后续研究执行、进度展示和 Agent trace 预留任务状态、阶段和运行关联字段。
- 不在本 change 中执行 Agent、调用 LLM、收集来源、生成商机推荐或生成最终报告。

## Capabilities

### New Capabilities

- `research-tasks`: 创建、读取和展示商机研究任务，保存用户输入的研究目标与限制条件，并为后续研究执行提供状态锚点。

### Modified Capabilities

- 无。

## Impact

- Affected frontend: `frontend/src/app/research/new/page.tsx`、`frontend/src/app/research/tasks/page.tsx`、研究任务 API client 和相关 feature 代码。
- Affected backend: FastAPI v1 routes、`research_tasks` domain module、SQLAlchemy model、Pydantic schemas、repository/service layer、Alembic migration 和后端测试。
- Affected data: PostgreSQL 将保存研究任务记录，包括内部自增 `id`、公开 `uuid`、标准时间戳、`deleted_at` 和用户提交的研究条件。
- Affected systems: 本 change 不需要外部 LLM、Tavily、LangSmith、Celery 或 LangGraph runtime。
