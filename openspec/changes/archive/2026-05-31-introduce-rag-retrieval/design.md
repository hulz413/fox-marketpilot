## 背景

现有研究流程已经能在基础商机保存后收集公开来源，并让需求、货源、竞品、风险等节点读取来源列表。这个模型适合展示来源透明度，但下游分析节点目前主要按 `source_type` 和商机关联取前几条来源，无法围绕具体问题做语义召回。

本 change 把 RAG 限定为任务内证据检索：只索引当前研究任务已经保存的 `research_sources`，默认只在当前任务内召回，并先接入竞品参考生成。它不是全局商机知识库，也不是对互联网内容做长期归档。

## 目标 / 非目标

**目标：**

- 从当前任务的研究来源派生可检索的 evidence chunks。
- 使用 embedding 和 pgvector 支持任务内语义检索。
- 为竞品参考节点提供按商机和问题召回的证据输入。
- 保留缺来源、缺 embedding 配置、索引失败和检索失败时的非阻塞 fallback。
- 在阶段事件、应用日志和 LangSmith trace 中记录索引与检索的关键 metadata。

**非目标：**

- 不建设跨任务全局知识库。
- 不把最终报告、行动计划、竞品参考等模型生成结论写回 RAG 语料。
- 不改变基础商机生成阶段的边界；生成基础商机前仍不执行外部搜索或 RAG。
- 不做正式 RAG 质量评测；评测留给后续 `evaluate-rag-quality`。
- 不长期保存大量网页全文；第一版只使用已清洗的来源摘要、片段和关联判断。

## 技术决策

### 1. RAG 语料从 `research_sources` 派生

每条 active `research_sources` 可以生成 1 个 evidence chunk。chunk 文本由 `title`、`summary`、`snippet` 和 `linked_claim` 清洗后组合，metadata 保留 `source_type`、`support_level`、`url`、`publisher`、原始来源 UUID、任务 UUID 和可选商机 UUID。

选择这个方案是因为当前来源已经过查询、数量限制和谨慎摘要处理，适合做第一版证据检索。备选方案是直接索引网页全文，但它会带来噪音、重复、成本和版权边界问题，不适合作为这个切片的第一步。

### 2. 新增可重建的 RAG 索引表

新增 `rag_evidence_chunks` 表，作为 `research_sources` 的派生缓存。表遵循项目数据库通用字段规范：包含内部自增 `id`、公开 `uuid`、`created_at`、`updated_at` 和可为空 `deleted_at`；对外或跨模块只使用 UUID，不暴露内部自增 ID。

核心字段包括：

- `research_task_id`
- `opportunity_id`
- `research_source_id`
- `source_type`
- `chunk_index`
- `chunk_text`
- `content_hash`
- `embedding`
- `embedding_model`
- `embedding_dimension`
- `token_count`
- `raw_metadata`

默认读取和检索只使用 `deleted_at` 为空的 chunk。重新运行研究任务或重新收集来源后，系统软删除旧 chunk 并为最新来源重建索引。

### 3. pgvector 是线上检索存储，测试使用确定性 fallback

本地依赖服务和线上 Postgres 使用 pgvector；迁移需要确保 `vector` extension 可用，并为 embedding 建立合适的向量索引或普通过滤索引。由于现有自动化测试大量使用 SQLite in-memory，测试环境不依赖真实 pgvector 相似度查询，而使用确定性 embedding 与 Python 内存相似度 fallback 验证过滤、排序和降级行为。

备选方案是只用 JSON 存 embedding 并在应用层计算相似度，但这会偏离技术栈中 pgvector 的目标，也不适合线上数据规模。折中方式是保持服务接口一致，数据库相关实现按环境选择可用路径。

### 4. embedding provider 独立于 chat LLM 配置

新增 embedding 配置，例如 provider、base URL、API key、model 和 dimension。生产环境未配置 embedding 时，RAG 索引阶段标记为 skipped，竞品参考节点回退到现有来源选择逻辑；local/test 可使用确定性 embedding fallback，保证测试可重复。

这样可以避免把 chat LLM provider 和 embedding provider 强绑定。部分 OpenAI-compatible chat provider 不一定提供 embedding API，独立配置能降低部署风险。

### 5. 检索默认 task-scoped

retriever 输入包含 `research_task_id`、可选 `opportunity_id`、可选 `source_types`、query 和 `top_k`。系统 MUST 默认限制在当前任务内检索；如果传入商机，则优先检索同商机 chunk，并可在结果不足时按规则回退到同任务通用来源。

这个边界直接回应库增长和证据污染风险：RAG 索引可以随任务增长，但一次生成不会跨任务召回旧材料，也不会把其他研究任务的来源混入当前报告。

### 6. 先接入竞品参考生成

竞品参考最依赖公开证据，且现有来源类型已经包含 `competitor` 和 `general`。第一版在 `generate_competitor_references` 阶段为每个商机构造竞品检索 query，优先召回 `competitor` / `general` evidence chunks，再把召回证据注入现有竞品参考生成输入。

如果没有可用检索结果，节点继续使用当前来源选择和 fallback 逻辑。这样可以验证 RAG 的价值，同时不扩大到需求、货源、风险和行动计划等所有节点。

### 7. 可观测性记录索引与检索，但不暴露敏感信息

新增或复用阶段事件记录 `index_rag_evidence` 的开始、完成、跳过或失败。竞品参考阶段的 metadata 增加 retrieval query 数量、召回 chunk 数、来源链接数量和 fallback 原因。LangSmith tracing 启用时，索引和检索子步骤写入同一研究 run trace，metadata 不包含 API key、原始异常堆栈、完整网页正文或内部自增 ID。

## 迁移计划

1. 增加后端配置项和 embedding client，local/test 默认走确定性 fallback。
2. 增加 `rag_evidence_chunks` 模型和 migration；Postgres migration 创建 pgvector extension 并新增索引。
3. 增加 RAG indexing service：从 active `research_sources` 重建当前任务 chunk。
4. 增加 retriever service：支持 task / opportunity / source_type 过滤和 top-k 召回。
5. 在 LangGraph 来源收集后插入 `index_rag_evidence` 阶段，失败不阻断后续节点。
6. 在竞品参考生成中优先使用 retriever 结果，并保留现有 fallback。
7. 补齐 API 层或内部 schema 所需的公开 UUID 输出，避免暴露内部 ID。
8. 增加单元测试、集成测试和前端进度文案契约测试。

回滚时可以禁用 embedding 配置或 RAG feature flag，让索引阶段跳过并回到现有来源选择路径；`rag_evidence_chunks` 作为派生缓存，可以软删除或重建，不影响核心商机、来源和竞品参考业务数据。

## 风险 / 取舍

- 向量索引增长过快 → 每个任务沿用来源数量上限，并对 chunk 数设置上限；chunk 是派生缓存，可软删除、归档或重建。
- embedding provider 不可用 → 索引阶段标记 skipped 或 failed，竞品参考继续使用现有来源选择 fallback。
- 召回证据不相关 → 检索限制在当前任务和来源类型内，并在生成输入中保留谨慎表达要求。
- SQLite 测试与 pgvector 行为不完全一致 → 单元测试覆盖服务契约和 fallback，Postgres/pgvector 相关迁移和相似度查询通过独立集成验证。
- RAG 被误解为已完成市场核验 → UI 和生成文案继续使用“公开线索”“初步参考”“待验证”等表达，不宣称竞品、售价或市场规模已确认。

## 开放问题

- 第一版 embedding model 和 dimension 采用哪个生产配置，需要结合实际 provider 可用性决定。
- 是否需要 feature flag 控制 RAG 检索接入竞品参考，还是仅通过 embedding 配置缺失来跳过。
- 后续 `evaluate-rag-quality` 是否使用同一批 task-scoped chunks 作为固定评测语料，还是另建 LangSmith Dataset 快照。
