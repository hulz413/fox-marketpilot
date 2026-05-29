## ADDED Requirements

### Requirement: 基础研究运行产生 Agent 可观测事件

系统 SHALL 在基础商机研究运行中为 LangGraph 节点和 LLM 调用产生可观测事件，以支持演示、调试和失败定位。

#### Scenario: 执行 LangGraph 节点时记录阶段事件

- **WHEN** 后台研究运行执行 LangGraph 工作流
- **THEN** 系统记录每个主要节点的阶段名称、开始时间、完成时间或失败时间
- **AND** 系统记录每个阶段的耗时
- **AND** 系统将阶段事件与任务 UUID 和运行 ID 关联

#### Scenario: 运行中任务展示当前细分阶段

- **WHEN** 后台研究运行正在执行某个主要 LangGraph 节点
- **THEN** 系统可以将研究任务当前阶段更新为对应细分阶段
- **AND** 前端任务列表读取任务时可以得到可识别的阶段值

### Requirement: 基础研究运行接入 LangSmith tracing

系统 SHALL 在 LangSmith tracing 启用时，将基础商机研究运行、主要节点和 LLM 调用记录到同一条可追踪链路。

#### Scenario: trace 关联研究运行

- **WHEN** 基础商机研究运行开始且 LangSmith tracing 已启用
- **THEN** 系统创建或进入一条研究运行 trace
- **AND** 该 trace 关联任务 UUID、运行 ID、环境和项目名称
- **AND** 系统将 trace ID 写回研究任务记录

#### Scenario: trace 关联 LLM 生成

- **WHEN** 基础商机研究运行调用 LLM 生成商机推荐
- **THEN** LangSmith tracing 启用时系统记录该 LLM 调用
- **AND** 该调用与同一研究运行 trace 关联
- **AND** 该调用可用于查看输入、输出、耗时、模型名和错误信息

### Requirement: 基础研究失败记录可定位错误

系统 SHALL 在基础商机研究失败时记录失败阶段和错误摘要，并保持用户侧失败信息可理解。

#### Scenario: 生成阶段失败

- **WHEN** 商机生成阶段因 LLM 调用、JSON 解析或结构化校验失败而无法恢复
- **THEN** 系统将任务状态更新为 `failed`
- **AND** 系统记录失败阶段为商机生成相关阶段
- **AND** 系统保存中文可理解失败原因
- **AND** 系统不暴露敏感凭证、原始堆栈或内部自增 ID

#### Scenario: 持久化阶段失败

- **WHEN** 商机结果持久化失败
- **THEN** 系统将任务状态更新为 `failed`
- **AND** 系统记录失败阶段为结果持久化相关阶段
- **AND** 系统不返回部分成功的商机结果作为本次完成结果
