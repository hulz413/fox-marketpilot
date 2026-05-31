## ADDED Requirements

### Requirement: 系统建立任务内 RAG 证据索引

系统 SHALL 从当前研究任务已保存的未软删除研究来源派生 RAG evidence chunks，并将这些 chunks 作为可重建的任务内检索索引。

#### Scenario: 从研究来源生成证据 chunk

- **WHEN** 一条研究任务完成来源收集且存在未软删除研究来源
- **THEN** 系统基于来源标题、摘要、片段和关联判断生成 evidence chunk 文本
- **AND** 每个 chunk 关联研究任务、可选商机和原始研究来源
- **AND** 每个 chunk 保存来源类型、支撑强度、URL、发布方、内容 hash 和 chunk 序号
- **AND** 系统不把最终报告、行动计划、竞品参考或其他模型生成结论写入 RAG 语料

#### Scenario: 没有可索引来源时跳过索引

- **WHEN** 一条研究任务没有未软删除研究来源
- **THEN** 系统不创建 RAG evidence chunks
- **AND** 系统记录索引阶段为 skipped 或等价状态
- **AND** 研究任务后续分析阶段仍可继续执行

#### Scenario: 重新运行重建任务索引

- **WHEN** 一条已完成研究任务被重新运行并产生新的来源集合
- **THEN** 系统将该任务上一轮 RAG evidence chunks 从默认检索中排除
- **AND** 系统为最新未软删除来源重建 evidence chunks
- **AND** 后续检索默认只返回最新未软删除 chunks

### Requirement: 系统为证据 chunk 生成 embedding

系统 SHALL 为可索引的 RAG evidence chunks 生成 embedding，并保存 embedding 模型、维度和状态信息，支持后续语义检索。

#### Scenario: embedding provider 可用时保存向量

- **WHEN** RAG 索引阶段需要处理 evidence chunks 且 embedding provider 已配置可用
- **THEN** 系统为每个 chunk 生成 embedding
- **AND** 系统保存 embedding、embedding model 和 embedding dimension
- **AND** 系统保存 chunk 创建时间、更新时间和可为空的删除时间
- **AND** 系统不在 metadata 中保存 API key 或其他敏感凭证

#### Scenario: 本地或测试环境使用确定性 embedding

- **WHEN** 系统运行在 local 或 test 环境且未配置真实 embedding provider
- **THEN** 系统可以使用确定性 embedding fallback 建立可重复的测试索引
- **AND** fallback embedding 支持稳定排序和过滤测试
- **AND** 自动化测试不依赖外部 embedding 服务

#### Scenario: embedding provider 不可用时非阻塞降级

- **WHEN** embedding provider 缺失、调用失败或返回无效结果
- **THEN** 系统记录安全错误摘要或跳过原因
- **AND** 系统不因为 RAG 索引失败而让研究任务进入 `failed`
- **AND** 后续分析节点可以回退到现有来源选择或确定性 fallback

### Requirement: 系统执行任务内证据检索

系统 SHALL 提供 task-scoped retriever，默认只在当前研究任务的未软删除 RAG evidence chunks 中检索相关证据。

#### Scenario: 按当前任务检索证据

- **WHEN** 下游分析节点请求 RAG evidence retrieval
- **THEN** 系统使用当前研究任务作为强制过滤条件
- **AND** 系统不返回其他研究任务的 chunks
- **AND** 系统返回按相似度或确定性相关性排序的 top-k chunks

#### Scenario: 按商机和来源类型收窄检索

- **WHEN** 检索请求包含商机和来源类型过滤条件
- **THEN** 系统优先返回同一研究任务、同一商机和匹配来源类型的 chunks
- **AND** 来源类型过滤可覆盖 `demand`、`supply`、`competitor`、`risk` 或 `general`
- **AND** 系统可以在同商机结果不足时返回同任务内的通用来源 chunks

#### Scenario: 检索无结果

- **WHEN** 当前任务没有可用 chunks 或检索没有命中结果
- **THEN** 系统返回空检索结果
- **AND** 调用方可以继续使用现有来源选择或 fallback 生成
- **AND** 系统不把检索无结果展示为研究任务失败

### Requirement: RAG 检索结果保留来源引用边界

系统 SHALL 让 RAG 检索结果可以追溯到原始公开来源，同时避免把证据片段包装成已核验结论。

#### Scenario: 检索结果包含来源引用信息

- **WHEN** retriever 返回 evidence chunks
- **THEN** 每个结果包含 chunk UUID、研究来源 UUID、可选商机 UUID、标题、URL、来源类型、支撑强度、相关性分数和 chunk 文本
- **AND** 系统不返回 chunk、来源、任务或商机的内部自增 ID
- **AND** 结果中的来源信息可用于后续报告或详情页展示公开线索

#### Scenario: 检索结果保持谨慎表达

- **WHEN** RAG evidence chunk 被用于生成竞品、需求、风险或其他分析结论
- **THEN** 生成内容使用“公开线索”“初步参考”“可能”“待验证”或等价谨慎表达
- **AND** 生成内容不宣称来源已经证明市场成立、售价已确认、竞品已全面核验或供应能力已确认

### Requirement: RAG 索引和检索可观测且非阻塞

系统 SHALL 为 RAG indexing 和 retrieval 记录足以排障的可观测信息，并确保 RAG 失败不破坏已有研究结果闭环。

#### Scenario: 记录 RAG 索引阶段

- **WHEN** 后台研究运行执行 RAG evidence indexing
- **THEN** 系统记录 `index_rag_evidence` 阶段事件
- **AND** 阶段事件包含任务 UUID、运行 ID、阶段状态、耗时、索引 chunk 数、跳过原因或安全错误摘要
- **AND** LangSmith tracing 启用时，该阶段与同一研究运行 trace 关联

#### Scenario: 记录 RAG 检索调用

- **WHEN** 下游分析节点执行 RAG evidence retrieval
- **THEN** 系统记录 retrieval query、过滤范围、top-k、返回 chunk 数和 fallback 状态
- **AND** LangSmith tracing 启用时，检索调用可在同一研究运行 trace 下查看
- **AND** trace metadata 不包含 API key、原始异常堆栈、完整网页正文或内部自增 ID

#### Scenario: RAG 失败不破坏研究闭环

- **WHEN** RAG 索引、embedding 或检索发生错误
- **THEN** 基础商机、来源、需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划流程仍可继续执行
- **AND** 系统记录安全错误摘要和应用日志
- **AND** 用户可见信息不暴露敏感凭证、原始堆栈或内部自增 ID
