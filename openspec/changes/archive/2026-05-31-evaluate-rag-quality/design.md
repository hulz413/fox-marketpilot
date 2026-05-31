## 背景

MarketPilot 当前已经完成任务内 RAG：研究来源会被整理成 evidence chunks，竞品参考生成会优先使用当前任务内检索证据，并在进度页和 LangSmith trace 中暴露基础排障信息。第一轮评测要先回答一个更窄的问题：retriever 是否能在当前任务内把相关证据找出来、找全，并把更相关的证据排在前面。

本 change 只补齐检索阶段的评测闭环。索引阶段健康指标、生成答案质量、引用支撑度和 groundedness 后续再作为独立增强考虑。

## 目标 / 非目标

**目标：**

- 建立可版本化、可复跑的中文商机研究 RAG 检索评测集。
- 支持一次基础检索评测运行，覆盖 retrieval query、top-k 召回证据和证据相关性等级。
- 保存 P0 检索指标：`hit_rate@k`、`recall@k`、`precision@k`、`mrr@k` 和 `ndcg@k`。
- 评测运行可关联研究任务、run ID、可空 trace ID 和 trace URL。
- LangSmith tracing 可用时写入检索评测 metadata；不可用时本地测试仍能复跑。

**非目标：**

- 不评估索引阶段健康指标，例如 source index coverage、embedding success rate 或 metadata completeness。
- 不评估生成答案质量、answer relevancy、citation support 或 groundedness。
- 不建设跨任务全局知识库。
- 不把基础商机生成改成 RAG 前置调研。
- 不把评测结果展示给最终用户，或作为商机是否成立的证明。
- 不在本切片实现复杂评测看板、排行榜或 CI 强制质量门禁。

## 技术决策

### 决策 1：新增独立 `rag_quality_evaluation` 后端模块

评测能力放在独立模块中，包含 schemas、models、repository、service、runner 和测试。这样可以复用现有 `rag_retrieval`、`sources`、`opportunities` 和 `integrations.langsmith`，同时避免把检索生产路径和内部评测路径耦合在一起。

替代方案是直接扩展 `rag_retrieval` 模块。这个方案初期代码更少，但评测集、评测运行和指标汇总会让核心 retriever 模块承担太多内部质量工具职责。

### 决策 2：评测集以仓库内版本化 fixture 为源头，数据库保存运行快照

仓库内保留一份中文 MVP 检索评测集，覆盖需求、货源、竞品和风险问题。运行评测时，系统可以把 fixture 导入数据库或直接构造运行快照，并把每次运行使用的 case 内容写入结果记录，保证后续复查时不受 fixture 修改影响。

数据库新增表遵循通用字段规范：每张表包含内部自增 `id`、公开 `uuid`、`created_at`、`updated_at` 和 `deleted_at`。对外读取或跨模块展示使用 `uuid`，不暴露内部自增 ID。默认查询只读取 `deleted_at` 为空的 case、run 和 result。

### 决策 3：评测 case 支持二元相关和分级相关

每个评测 case 至少包含问题、类别、期望来源类型、期望关键词或判断点、`top_k` 和评分规则。为了支持 `ndcg@k`，评测结果需要为每条召回 evidence 保存相关性等级：

- `0`：不相关
- `1`：弱相关
- `2`：相关
- `3`：强相关或关键证据

`hit_rate@k`、`recall@k`、`precision@k` 和 `mrr@k` 可以把等级大于 0 的 evidence 视为相关；`ndcg@k` 使用 0-3 等级计算整体排序质量。第一版相关性判定可以先使用规则评分器：来源类型、关键词、linked claim、summary 和 chunk text 命中情况；后续再接 LLM judge 或人工标注。

### 决策 4：保存评测运行和逐 case 检索结果

新增三类核心记录：

- `rag_evaluation_cases`：评测问题、类别、期望来源类型、期望关键词或判断点、默认 `top_k`、启用状态和评分说明。
- `rag_evaluation_runs`：评测运行名称、状态、关联任务 UUID / run ID / trace 信息、配置、汇总指标和安全错误摘要。
- `rag_evaluation_results`：单个 case 的 retrieval query、top-k、召回来源摘要、相关性等级、P0 指标、评分说明、状态和错误摘要。

结果中的来源引用只保存公开来源 UUID、标题、URL、来源类型、支撑强度、相关性分数和必要片段摘要，不保存完整网页正文、API key、原始异常堆栈或内部自增 ID。

### 决策 5：评测入口使用内部脚本或命令，不接入用户前台

本切片提供后端内部运行入口，例如脚本或模块命令：选择一个已完成研究任务或测试 fixture 任务，运行检索评测并打印/保存结果。可选提供只读内部 API 供后续调试页面使用，但不作为用户可见产品能力。

替代方案是在前端进度页直接展示评测结果。这样演示直观，但容易让用户误解为商机结论评分，也会扩大本切片 UI 范围。

## 迁移计划

1. 新增评测相关 Alembic migration，创建 case、run、result 表，并保留软删除字段。
2. 增加默认中文检索评测集 fixture 和导入/加载逻辑。
3. 实现评测 runner，先在本地或测试环境用现有 deterministic RAG fallback 完成一次检索评测。
4. 接入 LangSmith trace metadata，记录 retrieval query、top-k、召回数量、相关性等级和 P0 指标。
5. 用自动化测试验证 fixture 加载、检索评测运行、指标计算、失败降级和敏感信息过滤。
6. 回滚时可停止调用评测 runner；新增表不影响现有研究任务读取和执行。

## 风险 / 取舍

- 评测集过小导致分数虚高 → 初版覆盖多个业务判断类型，并在结果中保留 case 级评分说明，后续可增量扩充。
- 规则评分无法完全判断语义相关性 → 第一版强调可重复和可解释，同时保留相关性等级字段，后续可替换为人工标注或 LLM judge。
- `ndcg@k` 依赖分级相关性 → 初版使用 0-3 等级评分规则，并在 case 结果里保存判定原因。
- LangSmith 配置缺失或不可用 → 本地 fixture、数据库结果和 deterministic scorer 仍可运行，外部观测失败不影响评测本身。
- 评测结果被误认为用户结论 → 入口和文案限定为内部检索质量观察，不进入商机报告和详情页。
- 真实 embedding provider 让测试结果不稳定 → 自动化测试显式隔离外部 embedding/trace 配置，必要时注入 deterministic clients。

## 开放问题

- 首版评测集规模建议从 8-10 个中文 case 开始，后续根据 RAG 改动再扩容。
- 首版是否需要只读 API 可以在实现时按工作量决定；若脚本输出和数据库记录已满足验收，可把 UI/API 延后。
