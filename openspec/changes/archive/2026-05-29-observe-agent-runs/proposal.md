## 为什么

当前 P0 已经跑通“创建任务 -> 启动基础研究 -> 生成商机结果 -> 查看列表/详情/报告”的最短闭环，但 Agent 执行链路仍主要依赖应用日志和任务状态字段，演示和排障时很难证明每个研究节点、LLM 调用和失败阶段具体发生了什么。

本 change 用最小可验证范围补齐 Agent 运行可观测性：每次研究运行都能关联 LangSmith trace、任务记录和基础错误日志，为后续更细的研究进度页提供可信数据基础。

## 变更内容

- 为基础商机研究运行引入 Agent run observability 能力，覆盖 trace id、run id、task uuid、阶段、耗时、错误摘要和运行结果。
- 将 LangGraph 研究节点和 LLM 调用接入 LangSmith tracing；无 LangSmith 环境变量时仍能正常运行和通过测试。
- 在研究任务记录中回写可追踪的 `trace_id`，让任务列表、任务详情和日志可以关联到同一次 Agent trace。
- 将每次运行的阶段历史和耗时持久化，为后续 `show-research-progress` 提供完整数据基础。
- 在任务相关页面提供 LangSmith 外链入口；有 trace 的任务可以直接打开对应 LangSmith trace 页面查看运行树、错误、耗时和 token 等指标。
- 增强运行日志，使运行开始、阶段变化、完成和失败都包含足够排障的上下文。
- 不新增面向用户的完整进度页；更细的用户侧进度展示留给 `show-research-progress`。
- 不引入外部搜索、来源收集、RAG、竞品分析或多 Agent 协作。

## 能力

### 新增能力

- `agent-run-observability`: 定义 Agent 研究运行的 tracing、日志关联、阶段耗时和失败定位能力。

### 修改能力

- `research-tasks`: 研究任务在执行后需要能返回与当前运行关联的 trace ID 和失败摘要。
- `opportunity-research`: 基础商机研究运行需要在 LangGraph 节点和 LLM 调用层面产生可观测事件，并在失败时定位失败阶段。

## 影响

- 后端 Agent 运行时：`backend/app/agents/graph.py`
- 后端研究任务生命周期：`backend/app/modules/research_tasks/*`
- Agent 运行事件存储：新增用于阶段历史和耗时的持久化模型与 Alembic migration
- LangSmith 集成：`backend/app/integrations/langsmith.py`
- 后台 worker 执行路径：`backend/app/workers/research.py`
- 前端任务入口：`frontend/src/features/research/research-task-list.tsx`
- API 响应契约：现有研究任务响应继续暴露 `run_id`、`trace_id` 和 `failure_reason`，并可增加可空 LangSmith trace URL
- 配置：继续通过现有 LangSmith 环境变量启用 tracing：`LANGSMITH_TRACING`、`LANGSMITH_API_KEY`、`LANGSMITH_PROJECT`
- 测试：后端单元/集成测试应覆盖 tracing 未启用行为、trace metadata 持久化、失败阶段归因和日志上下文，并且不依赖真实 LangSmith 凭证
