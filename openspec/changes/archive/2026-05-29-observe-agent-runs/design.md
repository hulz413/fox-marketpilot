## Context

`run-opportunity-research` 已经让研究任务通过 Celery 和 LangGraph 单图工作流生成基础商机结果。当前任务模型已经预留 `run_id`、`trace_id` 和 `failure_reason`，但 `trace_id` 仍为空，LangSmith 环境配置函数尚未接入运行路径，LangGraph 节点和 OpenAI-compatible LLM 调用也没有统一的 trace metadata。

LangSmith Python tracing 的推荐启用路径是 `LANGSMITH_TRACING=true`、`LANGSMITH_API_KEY` 和 `LANGSMITH_PROJECT`。LangGraph 应用可以在 tracing context 中自动串联节点；自定义函数可以使用 `traceable`，OpenAI SDK client 可以使用 `wrap_openai`，并可通过当前 run tree 读取 `trace_id`。本 change 只把这些能力接到现有基础研究运行，不扩展研究深度。

数据库层面需要新增轻量的 `agent_run_events` 表，用于保存每次研究运行的阶段历史、耗时和失败摘要。该表遵循项目数据库通用字段规范：包含内部自增 `id`、公开 `uuid`、`created_at`、`updated_at` 和 `deleted_at`；通过 `research_task_id` 关联内部任务记录，通过 `run_id`、`trace_id`、`stage`、`status`、`started_at`、`completed_at`、`duration_ms`、`error_summary` 和可选 metadata 保存运行事件。对外暴露时使用公开 UUID、任务 UUID、run ID 和 trace ID，不暴露内部自增 ID。软删除读取行为不变：默认只读取 `deleted_at` 为空的任务、商机和运行事件。

## Goals / Non-Goals

**Goals:**

- 每次基础商机研究运行都有稳定的 `run_id`，并在 LangSmith tracing 启用时回写可用的 `trace_id`。
- LangSmith trace 能把一次研究运行、LangGraph 节点、LLM 调用和关键 metadata 串在一起。
- 系统能将运行开始、阶段开始、阶段完成、完成结果、失败阶段和耗时落库，并同步写入结构化应用日志。
- 已生成 trace 的任务能在前端任务入口直接打开对应 LangSmith trace 页面，供内部演示和排障查看运行树、错误、耗时和 token 等指标。
- 无 LangSmith 环境变量时，系统仍能执行研究、生成结果和通过自动化测试；此时 `trace_id` 可以为空。
- 失败时保留中文可展示失败摘要，并在日志或 trace 中定位失败阶段。

**Non-Goals:**

- 不新增用户侧完整进度页，不实现 SSE 实时流式进度。
- 不新增外部搜索、来源收集、RAG、竞品分析、多 Agent 协作或评测集。
- 不新增日志查询 UI；完整阶段历史和耗时先作为后端数据能力落库，用户侧展示留给 `show-research-progress`。
- 不要求测试环境访问真实 LangSmith 服务或真实 LLM 服务。

## Decisions

### Decision 1: 使用任务字段和运行事件表共同作为观测锚点

继续使用 `research_tasks.run_id`、`trace_id` 和 `failure_reason` 保存任务当前运行摘要，同时新增 `agent_run_events` 表保存完整阶段历史和耗时。`run_id` 在启动运行时生成；`trace_id` 在 traced root run 可用后尽早回写；失败时 `failure_reason` 保持中文、简短、可展示。每个阶段事件通过任务内部 ID、run ID 和 trace ID 关联到同一次运行。

备选方案是只依赖 LangSmith 和结构化日志。该方案实现更轻，但后续 `show-research-progress` 无法稳定读取完整阶段历史和耗时，因此不采用。

### Decision 2: 在研究运行入口建立 root trace

在 `execute_research_run` 或其邻近封装中建立 root run，例如 `opportunity_research`，并附加 `task_uuid`、`run_id`、`environment`、`research_boundary` 等 metadata。LangSmith tracing 启用时，通过当前 run tree 获取 `trace_id` 并保存到任务；未启用或不可用时不阻断主流程。

备选方案是在每个 LangGraph 节点单独创建 trace。这样会导致一次研究运行被拆成多条 trace，不利于演示和排障，因此不采用。

### Decision 3: 节点级观测与任务阶段保持一致但不过度产品化

LangGraph 节点按现有工作流记录阶段事件：`normalize_intake`、`generate_opportunities`、`validate_results`、`persist_results`。每个阶段至少记录开始时间、完成或失败时间、耗时、状态和错误摘要。运行中可以将 `current_stage` 更新为更细阶段，以便任务列表和后续进度页读取；前端只需补齐阶段 label，不创建新的进度页。

备选方案是继续只使用 `generate_opportunities` 一个阶段。这样改动更小，但无法满足“主要 Agent 节点可观测”和“失败阶段可定位”的目标。

### Decision 4: LLM 调用使用 LangSmith wrapper 或 traceable 边界

对现有 OpenAI-compatible client 使用 LangSmith 的 OpenAI wrapper，或在 `LLMOpportunityGenerator.generate` 外层使用 `traceable(run_type="llm")`，并附加 `llm_provider`、`llm_model`、`task_uuid` 和 `run_id` metadata。DeepSeek 仍通过现有 OpenAI-compatible 配置访问。

备选方案是手写 LangSmith RunTree 包裹每次 LLM 调用。它控制力更强，但样板代码更多，不适合当前轻量单图工作流。

### Decision 5: 可观测失败不覆盖业务失败

LangSmith 初始化、trace id 获取或 metadata 写入失败时只记录 warning，不让研究任务失败。只有 Agent 执行、LLM 调用、结构化解析、结果校验或持久化失败才会把任务置为 `failed`。

备选方案是 tracing 失败即任务失败。该方案会让观测系统影响核心演示闭环，风险不成比例。

### Decision 6: LangSmith 入口放在任务行和未来进度页

本 change 先在现有 `/research/tasks` 任务列表的操作区提供可选外链入口：任务已有 trace URL 时展示“LangSmith”或外链图标，点击后在新标签打开对应 trace。后续 `show-research-progress` 可以在任务进度页的运行信息区复用同一字段，作为更自然的排障入口。

备选方案是新增全局“可观测性”页面。它会把用户从业务任务上下文中拿走，而且需要额外聚合 run、log 和 metrics，本阶段收益不如任务级入口直接。

### Decision 7: LangSmith project 不写死，按环境配置

代码不固定写死 `marketpilot`，而是继续通过 `LANGSMITH_PROJECT` 路由 trace。推荐命名按环境区分：开发和演示环境使用 `marketpilot-dev`，生产环境使用 `marketpilot-prod`。实现上必须保持 env 可配置。

本地开发时配置在 `backend/.env`：

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_PROJECT=marketpilot-dev
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=<workspace-id-if-required>
```

线上生产环境需要在 Railway Web Service 和 Worker Service 中配置相同的 LangSmith 环境变量：

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<production-langsmith-api-key>
LANGSMITH_PROJECT=marketpilot-prod
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=<workspace-id-if-required>
```

默认 hosted LangSmith 使用 `https://api.smith.langchain.com`；APAC、EU 区域或自托管实例需要配置对应 endpoint。使用 Service Key 或 org-scoped key 时，通常还需要配置 `LANGSMITH_WORKSPACE_ID`，否则 LangSmith SDK 可能无法判断 trace 写入哪个 workspace 并返回 403。API 和 worker 必须使用同一个 `LANGSMITH_PROJECT`、`LANGSMITH_ENDPOINT` 和必要的 workspace ID，否则任务记录中的 trace 关联与 worker 实际产出的 LangSmith trace 可能分散到不同 project、endpoint 或 workspace。

备选方案是所有环境固定使用 `marketpilot`。该方案设置简单，但本地调试、演示和生产 trace 会混在一起，不利于后续排障、评测和权限管理。

## Risks / Trade-offs

- [Risk] LangSmith 包装 OpenAI-compatible DeepSeek client 时 token usage 或成本字段可能不完整。  
  Mitigation: 仍记录输入、输出、模型名、耗时和错误；成本统计不作为本 change 验收条件。

- [Risk] 新增运行事件表会扩大本 change 的迁移和测试范围。  
  Mitigation: 表结构保持轻量，只保存阶段历史、耗时、错误摘要和必要 metadata；不在本 change 中实现完整进度页。

- [Risk] trace 中可能包含用户输入和模型输出。  
  Mitigation: 只在用户显式配置 LangSmith env 后启用 tracing；metadata 不包含凭证；失败摘要不暴露堆栈和密钥。

- [Risk] 前端 LangSmith 外链只有拥有对应 LangSmith workspace 权限的人才能打开。  
  Mitigation: 入口定位为内部演示和排障能力；无权限用户会进入 LangSmith 登录或无权限页面，不在产品内暴露 API key。

- [Risk] Celery worker 和 API 进程环境变量不一致会导致 API 记录与 worker 产出的 trace 分散到不同 project，或本地 API 可见配置但 worker 不产出 trace。  
  Mitigation: 本地统一写入 `backend/.env`；线上 Railway Web Service 和 Worker Service 使用相同的 `LANGSMITH_TRACING`、`LANGSMITH_API_KEY` 和 `LANGSMITH_PROJECT`。

## Migration Plan

1. 新增 `agent_run_events` Alembic migration，遵循内部自增 ID、公开 UUID、时间戳和软删除字段规范。
2. 复用现有 `research_tasks.trace_id` 字段保存当前运行 trace 摘要。
3. 将 LangSmith 环境配置接入 FastAPI 和 Celery worker 启动路径，保证 API 与 worker 使用同一套 settings。
4. 在研究运行入口建立 root trace 并回写 `trace_id`；在 LangGraph 节点和 LLM 调用处补 metadata、结构化日志和运行事件落库。
5. 更新前后端阶段枚举、中文 label 和可选 trace URL 字段，保证更细阶段和 LangSmith 外链不会让任务列表显示异常。
6. 增加自动化测试，覆盖 tracing disabled、trace id 回写、阶段事件落库、失败阶段日志和重新运行刷新 trace id。
7. 部署时先保持 `LANGSMITH_TRACING=false`，确认功能无回归后再由运维或开发者写入 LangSmith env 开启真实 trace；开发和演示环境使用 `marketpilot-dev`，生产环境使用 `marketpilot-prod`。

Rollback 策略：关闭 `LANGSMITH_TRACING` 即可停用真实 trace；代码仍保留基础日志和任务状态，不影响研究任务执行。

## Open Questions

暂无。已确认后续 `show-research-progress` 需要完整阶段历史和耗时落库；LangSmith project 不在代码中写死，推荐通过 `LANGSMITH_PROJECT` 按环境配置。
