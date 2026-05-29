## Why

MarketPilot 现在已经可以创建持久化研究任务，但任务还不会执行研究，也不会产出真实商机结果。本 change 将用户提交的任务推进为第一条端到端 P0 研究闭环：运行轻量 Agent/LLM 流程，持久化 3-5 个结构化商机，并让排行榜、详情页和基础报告视图可以读取这些结果。

## What Changes

- 为已有研究任务新增用户可触发的研究运行。
- 扩展研究任务生命周期，使任务可以从 `created` 进入 `queued`、`running`、`completed` 或 `failed`。
- 使用 LangGraph 实现最小单图研究 Agent：归一化输入、调用已配置的 OpenAI-compatible LLM 生成结构化商机、校验结果并持久化。
- 本 change 不做外部前置调研；LLM 只基于用户输入、表单条件、产品默认场景和模型已有知识生成“基础推荐”或“待验证商机草案”。
- 为测试和缺少 LLM 凭证的本地环境提供确定性 fallback 生成能力。
- 持久化生成的商机推荐，字段覆盖 P0 排行榜、详情页和基础报告视图所需信息。
- 新增读取某条任务商机列表和单个商机详情的 API。
- 来源收集、前置搜索、RAG、竞品深挖、详细利润模型、完整最终报告生成和 LangSmith 运行可观测性不纳入本 change。

## Capabilities

### New Capabilities

- `opportunity-research`: 为已有研究任务运行轻量商机研究流程，并记录成功或失败状态。
- `opportunity-results`: 保存并暴露生成的商机推荐，供排行榜、详情页和基础报告视图读取。

### Modified Capabilities

- `research-tasks`: 研究任务新增可执行生命周期状态，并可关联完成或失败的研究运行，同时保留现有创建、读取和列表契约。

## Impact

- 影响后端模块：`backend/app/modules/research_tasks`、`backend/app/modules/opportunities`、`backend/app/agents`、`backend/app/workers` 和 `backend/app/api/v1`；`backend/app/agents/graph.py` 应从占位改为真实 LangGraph 单图工作流。
- 影响前端模块：研究任务操作、商机排行榜/详情页，以及当前仍读取静态 demo 数据的报告入口。
- 影响数据存储：新增商机结果持久化，并扩展研究任务状态和阶段语义。
- 影响集成：通过现有 DeepSeek-compatible 配置使用 OpenAI-compatible LLM provider；后台执行可使用 Celery，并提供本地/测试确定性 fallback。
- 影响产品文案：结果页和报告页应表达为基础推荐、待验证商机或验证草案，不应暗示已经完成公开市场调研、来源引用或竞品核验。
- 新增测试应覆盖任务状态迁移、成功生成结果、校验失败、确定性 fallback，以及前端读取真实商机结果。
