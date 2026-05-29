## Purpose

定义 MarketPilot 基础商机研究运行的启动、执行、LLM 结构化生成、实现边界和基础可观测契约。

## Requirements

### Requirement: 用户可以启动基础商机研究运行

系统 SHALL 允许用户对一条已创建且未软删除的研究任务启动一次基础商机研究运行。

#### Scenario: 启动存在的研究任务

- **WHEN** 用户请求启动一条存在且未软删除的研究任务
- **THEN** 系统为该任务生成运行 ID
- **AND** 系统将任务状态更新为 `queued`
- **AND** 系统将当前阶段更新为 `queued`
- **AND** 系统清空上一轮失败原因
- **AND** 系统投递或触发后台研究运行

#### Scenario: 拒绝不存在的研究任务

- **WHEN** 用户请求启动一个不存在或已软删除的研究任务
- **THEN** 系统返回未找到错误
- **AND** 系统不创建研究运行
- **AND** 系统不生成商机结果

#### Scenario: 避免重复启动运行中的任务

- **WHEN** 用户请求启动一条状态为 `queued` 或 `running` 的研究任务
- **THEN** 系统返回该任务当前运行状态
- **AND** 系统不重复投递新的研究运行

### Requirement: 系统执行 LangGraph 轻量商机研究 Agent

系统 SHALL 使用 LangGraph 单图 Agent 执行基础商机研究，归一化用户输入、生成结构化商机、校验结果并持久化结果。

#### Scenario: 成功执行研究运行

- **WHEN** 后台研究运行开始处理任务
- **THEN** 系统将任务状态更新为 `running`
- **AND** 系统将当前阶段更新为 `generate_opportunities`
- **AND** 系统通过 LangGraph 图执行研究节点
- **AND** 系统基于任务的自然语言需求和关键研究条件生成 3-5 个商机结果
- **AND** 每个商机结果满足 `opportunity-results` 能力定义的必填字段
- **AND** 系统持久化商机结果
- **AND** 系统将任务状态更新为 `completed`
- **AND** 系统将当前阶段更新为 `completed`

#### Scenario: 研究运行失败

- **WHEN** Agent 执行、LLM 调用、结果解析或结果校验失败且无法恢复
- **THEN** 系统将任务状态更新为 `failed`
- **AND** 系统将当前阶段更新为 `failed`
- **AND** 系统保存中文可理解的失败原因
- **AND** 系统不暴露敏感凭证、原始异常堆栈或内部自增 ID 给前端用户

### Requirement: Agent 使用结构化 LLM 交互

系统 SHALL 通过配置的 OpenAI-compatible LLM provider 生成基础商机推荐，并对模型输出做结构化校验。

#### Scenario: LLM 返回有效结构化结果

- **WHEN** 配置了可用 LLM provider 且模型返回有效结构化结果
- **THEN** 系统接受 3-5 个商机
- **AND** 系统按推荐排序保存这些商机
- **AND** 系统不要求本阶段提供来源链接、竞品证据或 RAG 引用

#### Scenario: LLM 返回无效结构化结果

- **WHEN** 模型返回的结果无法解析、少于 3 个商机、多于 5 个商机或缺少必填字段
- **THEN** 系统 SHALL 至少执行一次可控重试或进入失败处理
- **AND** 最终仍无有效结果时任务状态为 `failed`
- **AND** 失败原因说明结果生成失败

#### Scenario: 本地或测试环境缺少 LLM 凭证

- **WHEN** 系统运行在 local 或 test 环境且未配置 LLM API key
- **THEN** 系统使用确定性 fallback 生成 3 个中文商机结果
- **AND** fallback 结果仍满足商机结果 schema
- **AND** 自动化测试不依赖外部 LLM 服务

### Requirement: 基础研究运行不做外部前置调研

系统 SHALL 在本阶段直接基于任务输入和默认产品场景生成基础商机推荐，不执行外部搜索、网页抓取、RAG 检索或来源收集。

#### Scenario: 生成商机时不调用外部调研工具

- **WHEN** 系统执行基础商机研究运行
- **THEN** 系统不调用 Tavily、Playwright、网页正文提取、向量检索或 RAG 流程
- **AND** 系统不创建研究来源记录
- **AND** 系统不要求商机结果包含来源链接或引用依据

#### Scenario: 结果不宣称来源支撑

- **WHEN** 系统返回基础商机结果
- **THEN** 系统将结果表达为基础推荐、待验证商机或验证草案
- **AND** 系统不宣称该结果已经完成公开市场调研
- **AND** 系统不宣称该结果已经完成竞品、供给或来源核验

### Requirement: 研究运行记录基础可观测信息

系统 SHALL 为每次基础研究运行记录足以排障的基础状态和日志信息。

#### Scenario: 记录运行开始与完成

- **WHEN** 研究运行开始、完成或失败
- **THEN** 系统记录包含任务 UUID、运行 ID、阶段和结果状态的应用日志
- **AND** 任务记录保留运行 ID
- **AND** 任务记录保留可为空的 trace ID 字段供后续 LangSmith tracing 使用

#### Scenario: 失败信息可用于前端展示

- **WHEN** 研究运行失败
- **THEN** 任务记录包含可展示的失败原因
- **AND** 前端能够通过读取任务详情或列表获得失败摘要
