## MODIFIED Requirements

### Requirement: Agent 节点和 LLM 调用可以观测

系统 SHALL 在基础商机研究运行中记录主要 Agent 节点、LLM 调用、来源收集、需求洞察、货源候选、竞品参考、验证预算估算、风险复核、行动计划和结果持久化阶段的可观测信息。

#### Scenario: 成功运行记录节点链路

- **WHEN** 基础商机研究运行成功完成
- **THEN** 系统记录 `normalize_intake`、`generate_opportunities`、`validate_results`、`persist_results`、`collect_research_sources`、`generate_demand_insights`、`generate_supply_candidates`、`generate_competitor_references`、`estimate_validation_budgets`、`review_opportunity_risks` 和 `create_action_plans` 阶段的开始、完成和耗时
- **AND** LangSmith tracing 启用时这些阶段可在同一条研究运行 trace 下关联查看
- **AND** 应用日志包含任务 UUID、运行 ID、trace ID、阶段和耗时字段

#### Scenario: LLM 调用记录可排障信息

- **WHEN** 系统调用 OpenAI-compatible LLM provider 生成基础商机推荐、摘要来源判断、需求洞察、货源候选、竞品参考、验证预算估算、风险复核或行动计划
- **THEN** LangSmith tracing 启用时该 LLM 调用可在研究运行 trace 中查看
- **AND** trace metadata 包含 provider、model、任务 UUID 和运行 ID
- **AND** 系统不把 API key 或其他敏感凭证写入 trace metadata 或用户可见失败信息

#### Scenario: 来源收集调用记录可排障信息

- **WHEN** 系统调用公开搜索或网页正文提取能力收集来源线索
- **THEN** 系统记录来源收集阶段的任务 UUID、运行 ID、查询数量、保存来源数量和结果状态
- **AND** LangSmith tracing 启用时来源收集阶段可在同一条研究运行 trace 下关联查看
- **AND** 系统不把外部搜索 API key、完整敏感错误或内部自增 ID 写入用户可见信息

#### Scenario: 货源候选生成记录可排障信息

- **WHEN** 系统生成货源候选
- **THEN** 系统记录货源候选阶段的任务 UUID、运行 ID、保存候选数量、来源关联数量和结果状态
- **AND** LangSmith tracing 启用时货源候选阶段可在同一条研究运行 trace 下关联查看
- **AND** 系统不把 LLM API key、原始异常堆栈、供应商平台敏感请求信息或内部自增 ID 写入用户可见信息

#### Scenario: 竞品参考生成记录可排障信息

- **WHEN** 系统生成竞品参考
- **THEN** 系统记录竞品参考阶段的任务 UUID、运行 ID、保存参考数量、来源关联数量和结果状态
- **AND** LangSmith tracing 启用时竞品参考阶段可在同一条研究运行 trace 下关联查看
- **AND** 系统不把 LLM API key、原始异常堆栈、平台敏感请求信息或内部自增 ID 写入用户可见信息

#### Scenario: 验证预算估算记录可排障信息

- **WHEN** 系统生成验证预算估算
- **THEN** 系统记录验证预算估算阶段的任务 UUID、运行 ID、保存预算估算数量和结果状态
- **AND** LangSmith tracing 启用时验证预算估算阶段可在同一条研究运行 trace 下关联查看
- **AND** 系统不把 LLM API key、原始异常堆栈、精确财务承诺或内部自增 ID 写入用户可见信息

#### Scenario: 风险复核记录可排障信息

- **WHEN** 系统生成风险复核
- **THEN** 系统记录风险复核阶段的任务 UUID、运行 ID、保存风险复核数量和结果状态
- **AND** LangSmith tracing 启用时风险复核阶段可在同一条研究运行 trace 下关联查看
- **AND** 系统不把 LLM API key、原始异常堆栈、正式合规结论、供应链尽调结论或内部自增 ID 写入用户可见信息

#### Scenario: 行动计划生成记录可排障信息

- **WHEN** 系统生成行动计划
- **THEN** 系统记录行动计划阶段的任务 UUID、运行 ID、保存行动计划数量和结果状态
- **AND** LangSmith tracing 启用时行动计划阶段可在同一条研究运行 trace 下关联查看
- **AND** 系统不把 LLM API key、原始异常堆栈、自动联系供应商结果、自动发布内容结果或内部自增 ID 写入用户可见信息

### Requirement: Agent 阶段历史和耗时需要持久化

系统 SHALL 将每次基础商机研究运行的完整阶段历史和耗时保存为可读取的持久化记录，为后续研究进度页提供数据基础。

#### Scenario: 成功运行保存完整阶段历史

- **WHEN** 基础商机研究运行成功完成
- **THEN** 系统保存该运行每个主要阶段的事件记录
- **AND** 每条事件记录关联任务 UUID 或任务公开标识、运行 ID 和可空 trace ID
- **AND** 每条事件记录包含阶段名称、阶段状态、开始时间、完成时间和耗时
- **AND** 阶段历史包含来源收集阶段的完成、跳过或部分成功信息
- **AND** 阶段历史包含需求洞察、货源候选、竞品参考、验证预算估算、风险复核和行动计划阶段的完成、跳过或失败信息
- **AND** 系统不暴露内部自增 ID

#### Scenario: 失败运行保存失败阶段历史

- **WHEN** 基础商机研究运行在某个核心阶段失败
- **THEN** 系统保存失败阶段的事件记录
- **AND** 失败阶段记录包含失败状态、失败时间、耗时和错误摘要
- **AND** 已完成阶段的事件记录仍保留
- **AND** 用户可见错误摘要不包含敏感凭证、原始堆栈或内部自增 ID

#### Scenario: 来源收集失败保留阶段历史

- **WHEN** 来源收集阶段失败、跳过或部分成功但基础商机结果已经保存
- **THEN** 系统保存来源收集阶段的事件记录或阶段 metadata
- **AND** 该记录可用于解释来源列表为空或不完整
- **AND** 研究任务可以继续保持已完成结果入口

#### Scenario: 货源候选失败保留阶段历史

- **WHEN** 货源候选阶段失败、跳过或部分成功但基础商机结果已经保存
- **THEN** 系统保存货源候选阶段的事件记录或阶段 metadata
- **AND** 该记录可用于解释货源候选列表为空或不完整
- **AND** 研究任务可以继续保持已完成结果入口

#### Scenario: 竞品参考失败保留阶段历史

- **WHEN** 竞品参考阶段失败、跳过或部分成功但基础商机结果已经保存
- **THEN** 系统保存竞品参考阶段的事件记录或阶段 metadata
- **AND** 该记录可用于解释竞品参考列表为空或不完整
- **AND** 研究任务可以继续保持已完成结果入口

#### Scenario: 验证预算估算失败保留阶段历史

- **WHEN** 验证预算估算阶段失败、跳过或部分成功但基础商机结果已经保存
- **THEN** 系统保存验证预算估算阶段的事件记录或阶段 metadata
- **AND** 该记录可用于解释验证预算估算为空或不完整
- **AND** 研究任务可以继续保持已完成结果入口

#### Scenario: 风险复核失败保留阶段历史

- **WHEN** 风险复核阶段失败、跳过或部分成功但基础商机结果已经保存
- **THEN** 系统保存风险复核阶段的事件记录或阶段 metadata
- **AND** 该记录可用于解释风险复核为空或不完整
- **AND** 研究任务可以继续保持已完成结果入口

#### Scenario: 行动计划失败保留阶段历史

- **WHEN** 行动计划阶段失败、跳过或部分成功但基础商机结果已经保存
- **THEN** 系统保存行动计划阶段的事件记录或阶段 metadata
- **AND** 该记录可用于解释行动计划为空或不完整
- **AND** 研究任务可以继续保持已完成结果入口

#### Scenario: 重新运行保留不同运行的阶段历史

- **WHEN** 用户重新运行一条已完成或已失败的研究任务
- **THEN** 系统为新运行保存新的阶段事件记录
- **AND** 旧运行的阶段事件不会被新运行覆盖
- **AND** 后续可以通过运行 ID 区分不同运行的阶段历史
