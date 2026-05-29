## 1. 后端数据模型

- [x] 1.1 在 `backend/app/modules/research_tasks` 下新增 `ResearchTask` SQLAlchemy model，包含默认自增 `id`、唯一 UUID `uuid`、提交条件、状态、阶段、运行关联、失败原因、`created_at`、`updated_at` 和可空 `deleted_at`。
- [x] 1.2 确保 Alembic metadata 会导入研究任务 model，使迁移可以发现该表。
- [x] 1.3 为 `research_tasks` 表创建 Alembic migration，包含 UUID 唯一约束、可空 `deleted_at`，以及 created-at/status/deleted-at 相关索引。
- [x] 1.4 新增 Pydantic schemas，覆盖创建请求、列表响应、详情响应、状态值和校验错误。

## 2. 后端 API

- [x] 2.1 如果当前还没有 API 数据库 session dependency，则补充该依赖。
- [x] 2.2 实现研究任务 repository/service 方法，支持创建任务、按创建时间倒序列出未删除任务、按 UUID 读取未删除任务。
- [x] 2.3 新增 FastAPI routes：`POST /api/v1/research-tasks`、`GET /api/v1/research-tasks` 和 `GET /api/v1/research-tasks/{task_uuid}`。
- [x] 2.4 在 v1 API router 中注册研究任务 router。
- [x] 2.5 确保创建任务时设置 `status=created`、`current_stage=intake`，并且不调用 Celery、LangGraph、LLM、Tavily 或 LangSmith。
- [x] 2.6 新增后端测试，覆盖创建成功、缺少 brief 校验、未删除任务倒序列表、按 UUID 读取、软删除过滤和未找到行为。

## 3. 前端接入

- [x] 3.1 新增前端研究任务类型和 API client helper，覆盖创建、列表读取和详情读取。
- [x] 3.2 使用现有 React Hook Form 和 Zod 技术栈，把新建研究页面改成真实表单。
- [x] 3.3 将新建研究表单数据提交到创建任务 API，并在成功后跳转到任务列表或新任务入口。
- [x] 3.4 将研究任务列表的静态行替换为 API 加载的任务，同时保留加载、空状态和错误状态。
- [x] 3.5 保持面向用户的中文校验文案和状态文案与产品骨架一致。

## 4. 验证

- [x] 4.1 运行后端测试和 lint 检查，覆盖新增任务 API 和 model。
- [x] 4.2 运行前端 typecheck、lint 和 build 检查。
- [x] 4.3 启动本地应用，验证用户可以提交示例研究需求，并在任务列表看到创建出的任务。
- [x] 4.4 验证任务创建不会触发 Agent 执行、Celery job、LLM 调用、Tavily 调用或 LangSmith trace。
- [x] 4.5 验证任务响应包含公开 `uuid`、可空 `deleted_at`，以及供后续可观测性切片使用的可空 `run_id`、`trace_id` 和 `failure_reason` 字段。
