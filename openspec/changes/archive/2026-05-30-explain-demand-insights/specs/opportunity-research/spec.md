## MODIFIED Requirements

### Requirement: 系统执行 LangGraph 轻量商机研究 Agent

系统 SHALL 使用 LangGraph 单图 Agent 执行基础商机研究，归一化用户输入、生成结构化商机、校验结果、持久化结果，在结果保存后尝试收集公开来源线索，并在来源收集后尝试生成需求洞察。

#### Scenario: 成功执行研究运行

- **WHEN** 后台研究运行开始处理任务
- **THEN** 系统将任务状态更新为 `running`
- **AND** 系统将当前阶段更新为 `generate_opportunities`
- **AND** 系统通过 LangGraph 图执行研究节点
- **AND** 系统基于任务的自然语言需求和关键研究条件生成 3-5 个商机结果
- **AND** 每个商机结果满足 `opportunity-results` 能力定义的必填字段
- **AND** 系统持久化商机结果
- **AND** 系统进入 `collect_research_sources` 阶段并尝试收集公开来源线索
- **AND** 系统进入 `generate_demand_insights` 阶段并尝试为每个商机生成需求洞察
- **AND** 系统将任务状态更新为 `completed`
- **AND** 系统将当前阶段更新为 `completed`

#### Scenario: 核心研究运行失败

- **WHEN** Agent 执行、LLM 调用、结果解析、结果校验或商机结果持久化失败且无法恢复
- **THEN** 系统将任务状态更新为 `failed`
- **AND** 系统将当前阶段更新为 `failed`
- **AND** 系统保存中文可理解的失败原因
- **AND** 系统不暴露敏感凭证、原始异常堆栈或内部自增 ID 给前端用户

#### Scenario: 来源收集失败不覆盖基础结果

- **WHEN** 商机结果已经成功持久化但来源收集失败或被跳过
- **THEN** 系统保留已生成的商机结果
- **AND** 系统仍可以进入需求洞察生成阶段
- **AND** 系统可以将任务状态更新为 `completed`
- **AND** 系统记录来源收集阶段事件或应用日志用于排障
- **AND** 系统不把外部来源收集失败伪装成商机生成失败

#### Scenario: 需求洞察失败不覆盖基础结果

- **WHEN** 商机结果已经成功持久化但需求洞察生成失败
- **THEN** 系统保留已生成的商机结果和已收集来源
- **AND** 系统可以将任务状态更新为 `completed`
- **AND** 系统记录需求洞察阶段事件或应用日志用于排障
- **AND** 系统不把需求洞察失败伪装成商机生成失败
