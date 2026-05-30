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

系统 SHALL 在基础商机研究运行中记录主要 Agent 节点、LLM 调用、来源收集、需求洞察、货源候选、竞品参考和结果持久化阶段的可观测信息。

#### Scenario: 成功运行记录节点链路

- **WHEN** 基础商机研究运行成功完成
- **THEN** 系统记录 `normalize_intake`、`generate_opportunities`、`validate_results`、`persist_results`、`collect_research_sources`、`generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references` 阶段的开始、完成和耗时
- **AND** LangSmith tracing 启用时这些阶段可在同一条研究运行 trace 下关联查看
- **AND** 应用日志包含任务 UUID、运行 ID、trace ID、阶段和耗时字段

#### Scenario: LLM 调用记录可排障信息

- **WHEN** 系统调用 OpenAI-compatible LLM provider 生成基础商机推荐、摘要来源判断、需求洞察、货源候选或竞品参考
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

### Requirement: Agent 阶段历史和耗时需要持久化

系统 SHALL 将每次基础商机研究运行的完整阶段历史和耗时保存为可读取的持久化记录，为后续研究进度页提供数据基础。

#### Scenario: 成功运行保存完整阶段历史

- **WHEN** 基础商机研究运行成功完成
- **THEN** 系统保存该运行每个主要阶段的事件记录
- **AND** 每条事件记录关联任务 UUID 或任务公开标识、运行 ID 和可空 trace ID
- **AND** 每条事件记录包含阶段名称、阶段状态、开始时间、完成时间和耗时
- **AND** 阶段历史包含来源收集阶段的完成、跳过或部分成功信息
- **AND** 阶段历史包含需求洞察、货源候选和竞品参考阶段的完成、跳过或失败信息
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
