## Purpose

定义 MarketPilot Agent 研究运行的 trace、日志关联、阶段历史、耗时和失败定位能力，帮助开发者从任务记录、应用日志和 LangSmith trace 定位同一次运行。

## Requirements

### Requirement: Agent 研究运行可以追踪

系统 SHALL 为每次基础商机研究运行提供可关联的 Agent run observability 记录，使开发者能从任务记录、应用日志和 LangSmith trace 定位同一次运行。

#### Scenario: LangSmith tracing 启用时记录 trace

- **WHEN** 后台执行一条基础商机研究运行且 LangSmith tracing 已通过环境变量启用
- **THEN** 系统创建一条可在 LangSmith 项目中查看的研究运行 trace
- **AND** trace 包含任务 UUID、运行 ID、当前环境和研究边界 metadata
- **AND** 任务记录保存该运行可关联的 trace ID

#### Scenario: LangSmith tracing 未启用时保持主流程可用

- **WHEN** 后台执行一条基础商机研究运行且未配置 LangSmith tracing
- **THEN** 系统仍执行基础商机研究并生成或失败处理结果
- **AND** 系统不因为缺少 LangSmith API key 而让研究任务失败
- **AND** 任务记录的 trace ID 可以为空

### Requirement: Agent 节点和 LLM 调用可以观测

系统 SHALL 在基础商机研究运行中记录主要 Agent 节点、LLM 调用、来源收集、RAG 证据索引、需求洞察、货源候选、竞品参考、验证预算估算、风险复核、行动计划和结果持久化阶段的可观测信息。

#### Scenario: 成功运行记录节点链路

- **WHEN** 基础商机研究运行成功完成
- **THEN** 系统记录 `normalize_intake`、`generate_opportunities`、`validate_results`、`persist_results`、`collect_research_sources`、`index_rag_evidence`、`generate_demand_insights`、`generate_supply_candidates`、`generate_competitor_references`、`estimate_validation_budgets`、`review_opportunity_risks` 和 `create_action_plans` 阶段的开始、完成和耗时
- **AND** LangSmith tracing 启用时这些阶段可在同一条研究运行 trace 下关联查看
- **AND** 应用日志包含任务 UUID、运行 ID、trace ID、阶段和耗时字段

#### Scenario: LLM 调用记录可排障信息

- **WHEN** 系统调用 OpenAI-compatible LLM provider 生成基础商机推荐、摘要来源判断、需求洞察、货源候选、竞品参考、验证预算估算、风险复核或行动计划
- **THEN** LangSmith tracing 启用时该 LLM 调用可在研究运行 trace 中查看
- **AND** trace metadata 包含 provider、model、任务 UUID 和运行 ID
- **AND** 系统不把 API key 或其他敏感凭证写入 trace metadata 或用户可见失败信息

### Requirement: 并行研究分析分支需要可观测

系统 SHALL 在基础商机研究运行中记录并行研究分析分支的阶段事件、trace metadata 和安全日志，使开发者可以区分同一 run 下的需求洞察、货源候选、竞品参考和研究发现汇总状态。

#### Scenario: 并行分支启动时记录阶段事件

- **WHEN** 系统进入 `analyze_research` 阶段并启动专业分析分支
- **THEN** 系统为 `generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references` 分别记录 running 阶段事件
- **AND** 每条阶段事件关联同一任务 UUID、运行 ID 和可空 trace ID
- **AND** 阶段 metadata 标记该事件属于 `research_analysis` 分支组
- **AND** 系统不把内部自增 ID 写入用户可见信息

#### Scenario: 并行分支完成时记录独立结果

- **WHEN** 任一专业分析分支完成
- **THEN** 系统记录该分支的 completed 阶段事件、完成时间和耗时
- **AND** 阶段 metadata 包含该分支的结果状态、保存数量和来源或检索统计
- **AND** 其他仍在运行的专业分析分支不会被标记为完成或失败

#### Scenario: 并行分支失败时保留安全摘要

- **WHEN** 任一专业分析分支失败但基础商机结果已经保存
- **THEN** 系统记录该分支的 failed 阶段事件、失败时间、耗时和中文安全错误摘要
- **AND** 系统不把 LLM API key、外部搜索凭证、完整 prompt、完整网页正文、原始异常堆栈或内部自增 ID 写入用户可见信息
- **AND** 同一并行分支组中的其他分支仍可以继续完成

#### Scenario: 汇总阶段记录分支状态

- **WHEN** `generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references` 均进入可汇总状态
- **THEN** 系统记录 `synthesize_research_findings` 阶段事件
- **AND** 汇总阶段 metadata 包含三个专业分析分支的 completed、failed 或 skipped 状态
- **AND** LangSmith tracing 启用时汇总阶段可在同一条研究运行 trace 下关联查看
- **AND** 应用日志包含任务 UUID、运行 ID、trace ID、阶段、分支状态和耗时字段

#### Scenario: 并行分支不共享不安全运行上下文

- **WHEN** 系统并行执行专业分析分支
- **THEN** 每个分支的阶段事件写入和业务结果保存使用可独立提交的运行上下文
- **AND** 任一分支回滚不会回滚其他已经完成分支的结果或阶段事件
- **AND** 系统仍通过运行 ID 区分重新运行产生的阶段历史

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

### Requirement: 来源收集观测信息保持安全

系统 SHALL 在记录来源收集观测信息时避免暴露外部服务凭证、内部实现细节或不适合用户可见的原始错误。

#### Scenario: 来源收集失败摘要安全

- **WHEN** 来源收集阶段发生 Tavily、网页提取、网络或摘要错误
- **THEN** 系统记录中文可理解的安全错误摘要
- **AND** 错误摘要不包含 API key、原始异常堆栈、完整请求头或内部自增 ID
- **AND** 应用日志可以保留足以开发者排障的任务 UUID、运行 ID、阶段名和错误类型

#### Scenario: 来源收集缺少外部凭证

- **WHEN** 来源收集阶段因缺少公开搜索 API key 被跳过或使用 fallback
- **THEN** 系统记录来源收集未使用外部搜索的观测信息
- **AND** 研究任务不会仅因为缺少来源收集凭证而失败
- **AND** 用户可见信息不暴露具体凭证名称或配置细节

### Requirement: Agent trace 可以从任务入口打开

系统 SHALL 在已生成 LangSmith trace 的研究任务上提供可打开对应 trace 的入口，帮助内部演示和排障直接查看运行链路。

#### Scenario: 任务有 trace URL 时展示入口

- **WHEN** 用户在任务列表或任务相关页面查看一条已经关联 LangSmith trace URL 的研究任务
- **THEN** 前端展示打开 LangSmith trace 的外链入口
- **AND** 点击入口后打开对应 LangSmith trace 页面
- **AND** LangSmith 页面可用于查看运行树、节点输入输出、错误、耗时和 token usage 等指标

#### Scenario: 任务没有 trace URL 时不展示入口

- **WHEN** 用户查看一条未启用 tracing 或尚未创建 trace 的研究任务
- **THEN** 前端不展示可点击的 LangSmith trace 入口
- **AND** 任务列表仍正常展示任务状态、当前阶段和可用操作

### Requirement: 失败运行可以定位失败阶段

系统 SHALL 在基础商机研究运行失败时记录可定位失败阶段的观测信息，同时保留用户可理解的失败摘要。

#### Scenario: 节点失败时记录失败阶段

- **WHEN** Agent 节点、LLM 调用、结果解析、结果校验或持久化失败且无法恢复
- **THEN** 系统记录失败阶段、任务 UUID、运行 ID、trace ID 和错误摘要
- **AND** 任务状态更新为 `failed`
- **AND** 任务失败原因是中文可理解摘要
- **AND** 用户可见失败原因不包含敏感凭证、原始堆栈或内部自增 ID

#### Scenario: 可观测系统异常不覆盖业务结果

- **WHEN** LangSmith trace 创建、trace ID 获取或 metadata 写入失败
- **THEN** 系统记录可观测异常日志
- **AND** 系统继续执行基础商机研究主流程
- **AND** 研究任务不会仅因为可观测系统异常而失败

### Requirement: Agent 阶段事件可以作为进度时间线读取

系统 SHALL 允许任务进度页读取当前研究运行的阶段事件，并将其作为用户可见的进度时间线数据。

#### Scenario: 读取当前 run 的阶段事件

- **WHEN** 用户读取一条已有 run ID 的研究任务进度
- **THEN** 系统返回该任务当前 run ID 对应的未软删除阶段事件
- **AND** 阶段事件按开始时间升序排列
- **AND** 每条事件包含事件 UUID、run ID、可空 trace ID、阶段名、阶段状态、开始时间、完成时间、耗时和可空错误摘要
- **AND** 系统不返回阶段事件的内部自增 ID

#### Scenario: 任务没有 run ID

- **WHEN** 用户读取一条尚未启动运行的研究任务进度
- **THEN** 系统返回空阶段事件列表
- **AND** API 响应保持成功
- **AND** 前端可以使用任务状态展示尚未启动说明

#### Scenario: 当前 run 没有阶段事件

- **WHEN** 用户读取一条已有 run ID 但尚未写入阶段事件的研究任务进度
- **THEN** 系统返回空阶段事件列表
- **AND** API 响应保持成功
- **AND** 系统不创建占位阶段事件

#### Scenario: 重新运行后只返回当前 run 事件

- **WHEN** 一条研究任务已经重新运行并生成新的 run ID
- **THEN** 默认进度读取只返回新 run ID 对应的阶段事件
- **AND** 旧 run 的阶段事件继续保留在数据层
- **AND** 旧 run 的阶段事件不覆盖当前进度

### Requirement: 进度事件读取保持用户可见安全

系统 SHALL 在面向进度页返回阶段事件时保持用户可见信息安全，避免暴露内部实现细节或敏感信息。

#### Scenario: 失败阶段返回安全摘要

- **WHEN** 当前 run 存在失败阶段事件
- **THEN** 系统返回可展示的错误摘要
- **AND** 错误摘要不包含敏感凭证、原始异常堆栈或内部自增 ID
- **AND** 任务级失败原因仍作为用户主错误文案

#### Scenario: 软删除阶段事件不返回

- **WHEN** 当前 run 存在已软删除阶段事件
- **THEN** 进度读取默认不返回该事件
- **AND** 阶段时间线只使用 `deleted_at` 为空的事件

#### Scenario: tracing 未启用时仍可读取进度事件

- **WHEN** LangSmith tracing 未启用且研究任务已写入阶段事件
- **THEN** 系统仍返回阶段事件列表
- **AND** trace ID 和 trace URL 可以为空
- **AND** API 响应不暴露 tracing 初始化细节

### Requirement: Agent 运行记录 RAG 索引和检索观测信息

系统 SHALL 在基础商机研究运行中记录 RAG evidence indexing 和 retrieval 的阶段历史、trace metadata 和安全错误摘要。

#### Scenario: RAG 索引阶段可观测

- **WHEN** 后台研究运行执行 `index_rag_evidence` 阶段
- **THEN** 系统保存该阶段事件记录
- **AND** 阶段事件包含任务 UUID、运行 ID、可空 trace ID、阶段状态、开始时间、完成时间、耗时、索引 chunk 数和可空错误摘要
- **AND** LangSmith tracing 启用时，该阶段可在同一条研究运行 trace 下关联查看

#### Scenario: RAG 检索调用可观测

- **WHEN** 竞品参考生成阶段执行 RAG evidence retrieval
- **THEN** 系统记录 retrieval query 数量、过滤范围、top-k、返回 chunk 数、来源链接数量和 fallback 状态
- **AND** LangSmith tracing 启用时，检索调用 metadata 包含任务 UUID、运行 ID、商机 UUID、来源类型过滤和召回数量
- **AND** 系统不把 API key、完整网页正文、原始异常堆栈或内部自增 ID 写入 trace metadata 或用户可见失败信息

#### Scenario: RAG 可观测异常不覆盖业务结果

- **WHEN** RAG 索引或检索的 trace 创建、metadata 写入或观测记录保存失败
- **THEN** 系统记录应用日志用于开发者排障
- **AND** 系统继续执行研究主流程或现有 fallback
- **AND** 研究任务不会仅因为 RAG 可观测系统异常而失败
