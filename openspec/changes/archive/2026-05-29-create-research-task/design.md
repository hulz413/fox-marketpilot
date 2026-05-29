## Context

MarketPilot 已完成项目骨架和产品骨架。前端已有 `/research/new`、`/research/tasks` 等页面和中文演示数据，后端目前只提供健康检查接口，`research_tasks` 业务模块仍是占位。用户可以看到“新建研究”入口，但点击创建只会跳转，不会保存真实任务。

本 change 是 P0 业务闭环的第一块地基：先建立可持久化、可读取、可关联后续执行流程的研究任务。它需要同时触达前端表单、FastAPI 路由、数据库模型和迁移，但不进入 Agent 执行、LLM 调用或异步编排。

## Goals / Non-Goals

**Goals:**

- 支持用户从自然语言需求和关键条件创建商机研究任务。
- 将研究任务持久化到 PostgreSQL，并能通过 API 读取任务列表和单个任务。
- 让 `/research/new` 提交真实 API，创建成功后进入真实任务列表或任务入口。
- 让 `/research/tasks` 从后端读取真实任务，展示标题、状态、当前阶段、创建时间和操作入口。
- 为后续 `run-opportunity-research`、`show-research-progress` 和 `observe-agent-runs` 预留状态、阶段、运行 ID、trace ID 和失败原因字段。

**Non-Goals:**

- 不执行 LangGraph、Celery worker 或任何 Agent 节点。
- 不调用 LLM、Tavily、LangSmith、对象存储或外部搜索服务。
- 不生成商机推荐、商机详情或最终报告。
- 不实现 SSE 实时进度、重新运行历史任务或研究历史归档。
- 不引入认证、权限、团队协作或多租户隔离。

## Decisions

### Decision: 以 `research_tasks` 作为第一个真实业务表

新增 `research_tasks` 表，保存内部自增 ID、对外 UUID、标题、自然语言需求、结构化条件、状态、当前阶段、运行关联字段、时间戳和软删除时间。建议字段如下：

- `id`: 默认自增 integer primary key，作为数据库内部主键
- `uuid`: UUID，唯一且非空，创建任务时生成，用于 API 返回、前端路由和后续跨模块关联
- `title`: 任务标题，默认可从自然语言需求截取生成
- `brief`: 用户输入的自然语言需求
- `budget`: 验证预算
- `target_channels`: 目标渠道列表
- `preferred_categories`: 偏好品类列表
- `excluded_categories`: 排除品类列表
- `target_audience`: 目标人群
- `expected_profit`: 期望利润
- `supply_preferences`: 供给来源偏好列表
- `constraints`: 其他限制条件
- `status`: 初始为 `created`
- `current_stage`: 初始为 `intake`
- `run_id`: 后续异步运行 ID，当前为空
- `trace_id`: 后续 LangSmith trace ID，当前为空
- `failure_reason`: 后续失败原因，当前为空
- `created_at` / `updated_at`: 创建和更新时间戳
- `deleted_at`: 软删除时间戳，默认为空

Alternatives considered:

- 只把整份表单存为 JSON：实现更快，但任务列表、筛选和后续进度查询会缺少清晰字段。
- 为每个条件建立独立关联表：结构更规范，但对 MVP 任务创建过重；当前多数条件是轻量筛选文本或列表。

### Decision: 后端按业务模块组织任务模型、schema、service 和 route

在 `backend/app/modules/research_tasks` 下放置 SQLAlchemy model、Pydantic schemas、repository/service 等任务领域代码，在 `backend/app/api/v1/routes` 下注册 `research_tasks` route。读取任务时默认只返回 `deleted_at IS NULL` 的记录。API v1 暴露：

- `POST /api/v1/research-tasks`
- `GET /api/v1/research-tasks`
- `GET /api/v1/research-tasks/{task_uuid}`

Alternatives considered:

- 把 model、schema、service 放到全局目录：短期直接，但会削弱 roadmap 按 research task、opportunity、source、report 演进的边界。
- 只做前端本地状态：能演示创建，但不能支撑后续 Agent、进度和结果关联。

### Decision: 创建任务只落库，不自动启动研究流程

创建成功后任务状态保持 `created`，当前阶段保持 `intake`。本 change 不投递 Celery 任务，也不调用 `build_research_graph()`。后续 `run-opportunity-research` 可在任务创建后或用户触发后接管状态迁移。

Alternatives considered:

- 创建后立即入队一个占位 Celery 任务：会让边界看似更接近完整流程，但会提前引入 worker、失败处理和进度语义。
- 创建后直接同步生成静态推荐：会污染 `run-opportunity-research` 的职责，也会让推荐结果来源不清晰。

### Decision: 前端用现有技术栈接入真实任务 API

新建研究页转为客户端表单，使用已有 React Hook Form、Zod、TanStack Query 和 API URL helper。任务列表页从 API 获取任务数据，并保留空状态和中文示例入口。展示文案保持中文，API 字段和 TypeScript 类型保持英文。

Alternatives considered:

- 使用 Server Actions：能减少显式 API client 代码，但当前后端已选择 FastAPI 作为业务 API，前后端分离契约更重要。
- 继续使用静态 mock 数据：不会推进真实闭环，也无法验证后端模型和 API。

## Risks / Trade-offs

- [Risk] 任务字段在后续 Agent 设计中需要调整 -> Mitigation: 只固定 P0 输入和状态锚点，扩展分析数据留给 opportunities、sources 和 reports 模块。
- [Risk] 初始状态命名与后续执行状态不匹配 -> Mitigation: 当前只使用 `created` + `intake`，后续 change 可明确新增 `queued`、`running`、`completed`、`failed` 等状态迁移。
- [Risk] 前端表单一次性暴露过多字段影响可用性 -> Mitigation: 自然语言需求作为主输入，结构化字段作为辅助条件，页面保持已有企业后台风格。
- [Risk] 本地开发没有 PostgreSQL 时任务接口不可用 -> Mitigation: 沿用现有 infra PostgreSQL 约定，并在测试中使用可控数据库会话或 test client 依赖覆盖。

## Migration Plan

1. 新增 `research_tasks` SQLAlchemy model，并确保 Alembic metadata 能发现它。
2. 新增 Alembic migration 创建 `research_tasks` 表、`uuid` 唯一约束、`deleted_at` 字段和必要索引。
3. 新增 Pydantic request/response schemas、repository/service 和 FastAPI routes。
4. 新增后端测试覆盖创建、列表、详情和基础校验。
5. 更新前端新建研究页和任务列表页接入 API。
6. 新增前端类型、API client 和表单校验，保留空状态与示例入口。

Rollback 时可以移除新增 routes 和前端 API 接入，并回滚 `research_tasks` migration。当前没有生产数据迁移负担。

## Open Questions

- 后续 `run-opportunity-research` 是在任务创建成功后自动入队，还是由任务页显式点击“开始研究”触发？
- 任务列表是否需要分页和搜索？本 change 可先按创建时间倒序返回有限数量，等任务量真实增长后再扩展。
