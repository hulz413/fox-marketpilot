## 1. 数据模型与配置

- [x] 1.1 增加 embedding provider 配置项和 `.env.example` 示例，覆盖 base URL、API key、model、dimension 和启用状态。
- [x] 1.2 增加 OpenAI-compatible embedding client，并提供 local/test 确定性 embedding fallback。
- [x] 1.3 新增 `rag_evidence_chunks` 模型、schema、repository 和 Alembic migration，包含通用 `id`、`uuid`、`created_at`、`updated_at`、`deleted_at` 字段。
- [x] 1.4 在 Postgres migration 中启用 pgvector extension，并为任务、商机、来源类型、软删除和 embedding 检索建立必要索引。

## 2. RAG 索引与检索

- [x] 2.1 实现 evidence chunk 构建逻辑，从 active `research_sources` 清洗并组合标题、摘要、片段和关联判断。
- [x] 2.2 实现任务级 RAG 索引重建服务，重新运行时软删除旧 chunks 并索引最新来源。
- [x] 2.3 实现 task-scoped retriever，支持按任务、商机、来源类型和 top-k 检索。
- [x] 2.4 实现缺来源、缺 embedding 配置、embedding 失败和检索无结果时的安全降级结果。

## 3. LangGraph 与竞品参考接入

- [x] 3.1 在研究任务阶段枚举、阶段中文文案和进度契约中加入 `index_rag_evidence`。
- [x] 3.2 在 LangGraph 来源收集后插入 RAG 索引节点，并确保失败不阻断后续分析阶段。
- [x] 3.3 将竞品参考生成接入 retriever，优先使用当前任务内 `competitor` / `general` evidence chunks。
- [x] 3.4 保留竞品参考现有来源选择和确定性 fallback，确保 RAG 不可用时研究任务仍可完成。

## 4. 可观测性与安全边界

- [x] 4.1 为 `index_rag_evidence` 记录阶段事件、耗时、索引 chunk 数、跳过原因和安全错误摘要。
- [x] 4.2 在竞品参考阶段记录 retrieval query 数量、过滤范围、top-k、返回 chunk 数、来源链接数量和 fallback 状态。
- [x] 4.3 在 LangSmith tracing 启用时写入 RAG indexing / retrieval metadata，避免记录 API key、完整网页正文、原始堆栈或内部自增 ID。
- [x] 4.4 检查对外 API 和前端展示不暴露 RAG chunk、来源、任务或商机的内部自增 ID。

## 5. 前端进度与展示契约

- [x] 5.1 更新研究进度页阶段时间线，让 `index_rag_evidence` 展示中文谨慎文案。
- [x] 5.2 确认 RAG 索引失败、跳过或部分失败时，进度页仍展示任务可查看结果。
- [x] 5.3 确认竞品参考展示继续使用“公开线索”“初步参考”“待验证”等谨慎表达。

## 6. 测试与验证

- [x] 6.1 增加 RAG chunk 构建、任务重建、软删除、source_type 过滤和商机过滤的后端单元测试。
- [x] 6.2 增加 retriever 排序、空结果、embedding fallback 和检索失败降级测试。
- [x] 6.3 增加 LangGraph 运行测试，验证 `index_rag_evidence` 阶段事件、失败非阻塞和后续阶段继续执行。
- [x] 6.4 增加竞品参考测试，验证有 RAG 召回时关联来源、无召回时回退现有逻辑。
- [x] 6.5 增加前端 UI 契约测试，覆盖 RAG 索引阶段文案和终态展示。
- [x] 6.6 运行 `pytest`、`ruff check .`、前端 lint/UI 契约测试，并记录线上演示所需的 LangSmith trace 验证步骤。
