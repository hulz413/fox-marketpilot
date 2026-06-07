## 背景

MarketPilot 当前已经完成基础商机推荐、需求洞察、货源候选、竞品参考、验证预算、风险复核、行动计划、RAG 检索评测和 research readiness。现有 readiness 的生成内容检查主要是 deterministic smoke check：字段是否存在、数量是否足够、文案是否保持谨慎边界。

下一步需要回答更细的问题：生成结果是否真的遵守用户输入限制，商机推荐和后续分析是否语义一致，风险与行动建议是否足够具体，以及内容是否避免把“待验证建议”说成“已核验结论”。本 change 只建立内部生成质量评测能力，不改变生成链路。

## 目标 / 非目标

**目标：**

- 建立可版本化、可复跑的中文生成质量评测集。
- 支持对一条已完成研究任务运行生成质量评测，并保存 evaluation run 和 case result。
- 用 rubric 检查约束遵守、字段完整性、商机数量、风险具体性、行动可执行性、跨模块一致性和谨慎边界。
- 输出 `passed`、`warning`、`failed` 等内部状态、中文摘要、case 级原因和聚合指标。
- 让 readiness 可以读取最近一次生成质量评测摘要，并将其作为内部演示就绪检查项。
- 在 LangSmith 可用时记录评测 metadata；不可用时本地 runner 仍可运行。

**非目标：**

- 不修改基础商机生成 prompt、Agent 编排、商机排序算法或 RAG 检索策略。
- 不做生成前外部调研、全局知识库、多 Agent 协作或 groundedness 评测。
- 不把生成质量评测展示给公开分享页读者或普通用户。
- 不把评测状态作为商机是否真实成立、市场是否已验证或利润是否保证的证明。
- 不建设复杂评测看板、线上质量门禁或跨任务排行榜。

## 技术决策

1. 新增独立 `generation_quality_evaluation` 后端模块。

   生成质量评测是内部质量工具，和生产生成路径、RAG 检索评测、readiness 都有关联，但职责不同。独立模块包含 schemas、models、repository、service、runner、fixture 和测试，可以读取研究任务与商机增强分析，但不反向影响研究主流程。

   备选方案：直接扩展 `research_quality_readiness`。这个方案初期代码少，但会让 readiness 同时承担评测集、case 结果、评分和汇总职责，后续难以单独复跑或调试。

2. 评测集以仓库 fixture 为源头，数据库保存运行快照。

   首版内置中文 case 覆盖典型输入限制和演示场景，例如预算上限、渠道、排除品类、目标人群、供给来源偏好、毛利预期和禁止过度声称。运行时保存 case 快照，保证历史 evaluation run 不会因为 fixture 修改而失去可解释性。

   数据库新增表遵循项目通用字段规范：每张表包含内部自增 `id`、公开 `uuid`、`created_at`、`updated_at` 和 `deleted_at`。对外响应和跨模块关联使用公开 UUID，不暴露内部自增 ID。默认查询只读取 `deleted_at` 为空的 case、run 和 result。

3. 评测采用 deterministic rubric 为主，可预留 LLM judge。

   首版优先实现可复现的规则评分和结构化 rubric：检查任务输入约束是否被商机结果违反，增强分析是否缺失，风险是否具体，行动计划是否可执行，文案是否出现禁止表达。对于语义更强的判断，case 结果保存 `rubric_scores`、`reasons` 和可空 `judge_metadata`，未来可接入 LLM judge，但本切片不要求新增外部模型依赖。

   备选方案：首版直接使用 LLM judge。这个方案语义覆盖更强，但测试稳定性、成本和提示词边界更复杂，不适合作为第一版内部质量能力的唯一依据。

4. 保存 run、case result 和聚合指标。

   核心记录包括：

   - `generation_evaluation_cases`：case 名称、类别、输入约束、期望判断点、rubric、启用状态和版本信息。
   - `generation_evaluation_runs`：评测运行状态、关联任务 UUID、研究 run ID、整体状态、case 计数、指标摘要、中文摘要、安全错误摘要和可空 trace 信息。
   - `generation_evaluation_results`：单个 case 的快照、目标商机或任务范围、rubric 分数、状态、原因、受影响商机公开 UUID 和安全错误摘要。

   聚合指标不需要追求复杂统计，首版保存 case 总数、通过数、warning 数、失败数、跳过数、整体状态和每个 rubric 维度的通过率即可。

5. readiness 只消费摘要，不拥有评测逻辑。

   readiness runner 可以读取最近一次未软删除的 generation evaluation run；如果不存在，可以按配置触发一次评测，或将生成质量检查标为未检查/需复查。readiness 保存生成质量评测运行公开 UUID、整体状态、摘要和关键原因，不返回 case 全量明细。

6. 评测入口保持内部化。

   首版提供内部命令或 runner，用于选择已完成任务运行评测，并提供只读内部 API 或服务方法供 readiness 使用。用户进度页、商机详情、基础报告和公开分享页不展示评测分数。

## 迁移计划

1. 新增 Alembic migration，创建 generation evaluation case、run 和 result 表。
2. 增加默认中文评测集 fixture，并提供加载或按需导入逻辑。
3. 实现评测服务和 runner，支持对已完成研究任务运行评测。
4. 实现 rubric 评分和安全错误摘要，覆盖约束遵守、结构完整、风险/行动质量、一致性和谨慎边界。
5. 将生成质量评测摘要接入 readiness runner，保存为内部检查项。
6. 增加自动化测试，覆盖 fixture、运行成功、case 部分失败、敏感信息过滤、readiness 汇总和未完成任务拒绝。
7. 回滚时停止调用评测 runner；新增表不影响研究任务、商机结果、分享或 readiness 既有读取。

## 风险 / 取舍

- [Risk] 规则评分不能完全理解中文语义。→ Mitigation: 首版强调可复现和可解释，保存 case 级原因，后续可在同一结构上接 LLM judge。
- [Risk] 评测结果被误解为商机真实成立。→ Mitigation: 评测只作为内部质量检查，不进入公开分享页或用户结果页，文案始终表达为生成质量复查。
- [Risk] 评测集过小导致通过率虚高。→ Mitigation: 首版覆盖多个约束类型和输出模块，后续按失败案例增量扩充 fixture。
- [Risk] readiness 触发评测增加演示前耗时。→ Mitigation: readiness 优先读取最近 run；是否自动触发评测由实现配置或内部命令决定。
- [Risk] 评测失败影响主流程。→ Mitigation: generation evaluation 不修改研究任务状态，不删除商机或增强分析，失败只记录内部摘要。
- [Risk] 结果明细包含敏感或过长内容。→ Mitigation: 响应只返回公开 UUID、聚合指标、短摘要和安全原因，不返回完整 prompt、完整正文、API key、原始异常堆栈或内部 ID。

## 开放问题

- 首版默认 fixture 数量建议从 8-12 个中文 case 开始，覆盖预算、渠道、排除品类、风险和行动计划。
- 是否在本切片提供前端内部页面暂不强制；如果 runner、API 和 readiness 摘要足够验收，可以把 UI 延后。
- 是否启用 LLM judge 先作为可选配置保留，不作为首版验收前提。
