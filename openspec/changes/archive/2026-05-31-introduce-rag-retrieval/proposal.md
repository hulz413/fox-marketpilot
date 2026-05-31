## 为什么

当前 MarketPilot 已能收集公开来源并在需求、货源、竞品、风险等节点中展示或引用来源摘要，但下游分析仍主要按来源类型粗粒度取用材料，缺少按具体问题语义召回证据的能力。为了在不建设全局知识库的前提下提升结论可追溯性，本 change 引入任务内 RAG 检索，把当前研究任务已筛选的来源转成可检索证据，并先接入竞品参考生成。

## 变更内容

- 从当前研究任务的 `research_sources` 派生 RAG evidence chunks，保存可重建的文本片段、来源关联、检索 metadata 和 embedding。
- 新增 task-scoped retriever，默认只在当前 `research_task_id` 内检索，可按商机和来源类型收窄范围。
- 在来源收集完成后为当前任务建立或刷新 RAG 证据索引，并记录索引数量、跳过原因和失败状态。
- 先将 RAG 检索接入竞品参考生成：竞品节点基于商机问题召回相关证据，生成竞品/价格/差异化参考时保留可追溯来源。
- 在缺少来源、缺少 embedding 配置、索引失败或检索失败时，保留现有来源选择与确定性 fallback，不破坏完整研究闭环。
- 在 LangSmith trace、阶段事件和应用日志中记录 RAG indexing / retrieval 的基础可观测信息。
- 本 change 不建设跨任务全局知识库，不把最终报告或模型生成结论反灌进 RAG，不接入基础商机生成，不做正式 RAG 质量评测。

## 能力

### 新增能力

- `rag-retrieval`: 定义任务内 RAG 证据索引、embedding 存储、检索、来源引用、失败降级和可观测性契约。

### 修改能力

- `opportunity-research`: 研究运行在来源收集后建立 RAG 证据索引，并在竞品参考阶段使用任务内检索；失败时不破坏基础结果。
- `competitor-references`: 竞品参考生成优先使用任务内 RAG 检索召回的相关证据，并保留现有来源选择 fallback。
- `research-progress`: 进度页可以识别 RAG 证据索引阶段及其完成、跳过或失败状态。
- `agent-run-observability`: Agent 阶段历史和 trace 需要覆盖 RAG 索引与检索信息，便于排查召回为空、索引失败或配置缺失。

## 影响

- Backend: 新增 RAG evidence chunk 领域模型、schema、repository、service、retriever 和 Alembic migration。
- Database: 新增可重建的 RAG 索引表，关联 `research_tasks`、可选 `opportunities` 和 `research_sources`，并使用 pgvector 存储 embedding。
- Agent runtime: 在现有 LangGraph 单图中增加 RAG 证据索引阶段；竞品参考节点接入检索结果。
- Integrations: 新增 OpenAI-compatible embedding client；本地和测试环境使用确定性 embedding fallback，自动化测试不依赖外部 embedding 服务。
- Observability: 记录索引 chunk 数、embedding 状态、retrieval query、召回数量、来源 UUID、score 和安全错误摘要。
- Tests: 覆盖索引生成、任务内过滤、商机/来源类型过滤、检索 fallback、竞品参考接入、阶段事件和 trace metadata。
- Out of scope: 全局跨任务知识库、正式 RAG 评测、网页全文长期归档、基础商机生成前置 RAG、多 Agent 协作、向用户暴露内部自增 ID。
