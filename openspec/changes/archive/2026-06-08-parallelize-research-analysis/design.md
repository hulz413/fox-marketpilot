## 背景

MarketPilot 当前通过 `backend/app/agents/graph.py` 中的 LangGraph 单图执行研究运行。现有节点顺序是线性的：保存基础商机后收集公开来源、建立任务内 RAG 证据索引，再依次生成需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划。

这个顺序稳定、易观察，但红框中的研究分析阶段已经形成三个相对独立的专业分析视角：需求、货源和竞品。它们都主要依赖当前任务、基础商机、公开来源和任务内 RAG 证据；后续验证预算、风险复核和行动计划才更适合等待这些增强结果统一落库后继续执行。

本 change 不改变数据库主数据模型，不新增外部服务，不改变公开结果 API 的读取边界；重点是调整 LangGraph 执行拓扑、阶段事件和进度展示契约。

## 目标 / 非目标

**目标：**

- 将 `generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references` 调整为来源与 RAG 完成后的并行专业分析分支。
- 增加 `synthesize_research_findings` 汇总节点，等待三个分支完成、跳过或安全失败后再进入验证预算估算。
- 让每个并行分支独立记录开始、完成、失败、耗时和安全 metadata。
- 让研究进度页可以表达多个专业分析阶段同时运行。
- 保持 local/test 环境 deterministic fallback 和不依赖外部 LLM、搜索或网络服务的测试边界。
- 保持增强分析失败不覆盖基础商机结果，也不阻断其他可继续执行的增强分析。

**非目标：**

- 不引入 CrewAI、AutoGen、LangGraph supervisor prebuilt 或其他新 multi-agent 框架。
- 不新增“专业 Agent”配置后台、角色管理、开放域对话或动态规划能力。
- 不在基础商机生成之前做外部搜索、RAG 或竞品深挖。
- 不新增数据库表作为必选范围；既有表继续遵循 `id`、`created_at`、`updated_at`、`deleted_at` 通用字段规范，软删除读取仍默认只返回 `deleted_at IS NULL` 数据。
- 不修改报告、详情页或分享页的公开数据结构，除非为了展示进度文案做轻量前端适配。

## 技术决策

### 决策：使用 LangGraph fan-out/fan-in，而不是新 multi-agent 框架

研究图调整为：

```text
normalize_intake
  -> generate_opportunities
  -> validate_results
  -> persist_results
  -> collect_research_sources
  -> index_rag_evidence
  -> generate_demand_insights
     generate_supply_candidates
     generate_competitor_references
  -> synthesize_research_findings
  -> estimate_validation_budgets
  -> review_opportunity_risks
  -> create_action_plans
```

`index_rag_evidence` 同时连到三个专业分析分支，三个分支都连到 `synthesize_research_findings`。LangGraph 会在 fan-in 节点前等待上游分支返回。并行分支不通过共享 state 传递领域对象，仍以数据库持久化结果作为后续阶段读取来源。

备选方案：

- 使用新的 multi-agent 框架：产品叙事更强，但会引入新依赖和新的调度语义，超出当前 MVP 稳定性边界。
- 使用 Celery group/chord：适合跨 worker 并行，但会把一次研究运行拆成多个异步任务，当前 run ID、trace 和进度页协调成本更高。
- 保持串行仅改文案：风险最低，但不能解决等待时间和专业分支表达问题。

### 决策：并行分支使用独立 DB session 和可归并 state

当前 graph state 里包含 `db: Session` 和 `task: ResearchTask`。并行分支不能共享同一个 SQLAlchemy session 或同一个 ORM task 实例，否则容易出现提交顺序、对象状态和 `current_stage` 写入竞争。

并行分支节点应改为用任务 UUID、run ID 和 trace ID 重新加载任务，并在分支内部使用独立 DB session 执行业务 service、阶段事件和提交。分支返回轻量 branch result，例如：

```text
analysis_branch_results += [
  {
    "stage": "generate_demand_insights",
    "status": "completed",
    "metadata": {...}
  }
]
```

LangGraph state 中用于汇总并发结果的字段需要使用 reducer，例如 list append/concat，避免并行节点更新同一 key 时互相覆盖。领域结果仍由各模块自己的 repository 写入既有表，汇总节点只读取安全 metadata 和数据库中可读取的增强结果。

备选方案：

- 继续共享原始 `db` 和 `task`：代码改动少，但并行执行时可靠性差。
- 分支只返回 LLM 结果，由汇总节点统一落库：事务边界更集中，但会让每个模块现有 `replace_task_*` service 重用变差，也会让失败隔离更复杂。

### 决策：并行分析期间使用粗粒度 `current_stage`

`ResearchTask.current_stage` 是单值枚举，不能准确表达三个分支同时运行。为避免并行分支互相覆盖任务当前阶段，任务进入 fan-out 后应设置为粗粒度阶段 `analyze_research`，分支细节由 `agent_run_events` 表达。

每个专业分析分支仍记录自己的阶段事件：`generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references`。当 `synthesize_research_findings` 开始时，任务当前阶段更新为该汇总阶段；后续再进入验证预算、风险复核和行动计划。

备选方案：

- 将 `current_stage` 改为数组：表达更精确，但会影响 API schema、前端状态判断和历史数据兼容。
- 让最后启动的分支覆盖 `current_stage`：实现简单，但用户看到的当前阶段会随机且误导。

### 决策：解除并行分支之间的硬依赖

当前 `supply_candidates` 会读取需求洞察摘要，`competitor_references` 会读取需求洞察和货源候选摘要。并行后这类 sibling output 不能作为必需输入。三个分支应主要基于任务、基础商机、公开来源和任务内 RAG 证据构建上下文；如果历史数据或重新运行残留数据可读，也必须避免把旧 run 的 sibling output 当作当前并行分支的必需条件。

后续 `estimate_validation_budgets`、`review_opportunity_risks` 和 `create_action_plans` 在 `synthesize_research_findings` 之后执行，可以继续读取需求、货源和竞品三个分支的最新落库结果。

备选方案：

- 保留需求 -> 货源 -> 竞品依赖：输出上下文更完整，但无法并行。
- 只并行需求和货源，竞品等待二者：折中可行，但 fan-out 价值较弱，且竞品本身已经能基于 RAG competitor/general 证据独立生成初步参考。

### 决策：汇总节点不新增主数据表

`synthesize_research_findings` 的职责是收敛三个专业分支的状态、记录阶段事件 metadata，并为后续串行阶段提供“可以继续”的边界。它不要求新增 `research_findings` 表；后续预算、风险和行动计划继续读取现有增强分析表。

汇总阶段 metadata 应包含每个分支的状态、保存数量、来源关联数量、检索统计和安全失败摘要。用户可见进度页只展示中文概括，不暴露内部自增 ID、完整 prompt、完整网页正文、API key 或原始异常堆栈。

备选方案：

- 新增汇总表：长期可用于报告级 research summary，但本 change 的目标是执行拓扑和可观测性，不需要先增加存储模型。
- 只依赖三个分支事件、不新增汇总节点：可以减少一个阶段，但后续串行阶段缺少清晰 fan-in 边界，也不利于进度页表达“研究发现已汇总”。

## 迁移计划

1. 扩展研究阶段枚举和前端阶段文案，加入 `analyze_research` 与 `synthesize_research_findings`。
2. 调整 LangGraph state，增加可归并的 `analysis_branch_results` 字段，并改造并行分支 wrapper 使用独立 DB session。
3. 调整 `build_research_graph()` 边关系，从 `index_rag_evidence` fan-out 到三个专业分析分支，再 fan-in 到 `synthesize_research_findings`。
4. 调整需求、货源和竞品上下文构建，移除当前 run 内 sibling output 的硬依赖。
5. 更新进度 API/前端时间线展示，让 `analyze_research` 期间可展示多个 running branch。
6. 补齐后端 graph、阶段事件、失败隔离和前端阶段展示测试。

回滚时可恢复原线性边关系，并保留新增阶段枚举不影响历史数据读取；已写入的阶段事件按 run ID 保留，不需要数据迁移。

## 风险 / 取舍

- [Risk] 并行分支共享 DB session 导致事务或 ORM 状态异常 -> Mitigation: 分支内部使用独立 session，按任务 UUID 和 run ID 重新加载任务。
- [Risk] `current_stage` 单值无法表达多个运行中阶段 -> Mitigation: 使用 `analyze_research` 作为粗粒度当前阶段，细粒度状态由阶段事件展示。
- [Risk] 移除 sibling output 输入后，货源和竞品生成质量短期下降 -> Mitigation: 三个分支共享任务、商机、来源和 RAG 证据；预算、风险、行动计划仍在汇总后读取完整增强结果。
- [Risk] 多个 LLM 分支同时调用提高瞬时并发和失败概率 -> Mitigation: 保持每个分支独立 fallback、可控重试和安全失败；生产环境可通过 Celery worker 并发和 provider 限流配置控制。
- [Risk] LangSmith trace 中并行节点顺序不再线性 -> Mitigation: metadata 中记录 `analysis_group=research_analysis`、`branch_stage` 和 run ID，进度页按 started/completed 时间展示。

## 开放问题

- 是否需要在后续独立 change 中把 `synthesize_research_findings` 扩展为可阅读的报告级“研究发现摘要”表？本 change 暂不做。
- 生产环境是否需要为并行 LLM 分支增加显式并发上限或 provider rate limit 配置？本 change 先沿用现有 provider 配置和失败隔离。
