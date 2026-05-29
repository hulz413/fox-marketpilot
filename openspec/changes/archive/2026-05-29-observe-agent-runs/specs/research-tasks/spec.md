## ADDED Requirements

### Requirement: 研究任务可以关联 Agent trace

系统 SHALL 让研究任务记录能够关联最近一次基础商机研究运行的 run ID、trace ID 和失败摘要。

#### Scenario: 读取已追踪运行的任务

- **WHEN** 用户读取一条已经启动基础商机研究运行的任务
- **THEN** 系统返回该任务当前运行 ID
- **AND** 如果该运行已成功创建 LangSmith trace，系统返回对应 trace ID
- **AND** 如果系统能构造对应 LangSmith trace 页面地址，系统返回可空 trace URL
- **AND** 系统不返回内部自增 ID

#### Scenario: 重新运行刷新运行关联

- **WHEN** 用户重新运行一条已完成或已失败的研究任务
- **THEN** 系统为新运行生成新的运行 ID
- **AND** 系统清空上一轮失败原因
- **AND** 系统将 trace ID 更新为新运行的 trace ID，或在新运行尚未创建 trace 时保持为空

#### Scenario: tracing 未启用时任务仍可读取

- **WHEN** 用户读取一条在 LangSmith tracing 未启用环境中运行的任务
- **THEN** 系统仍返回任务状态、当前阶段、运行 ID 和失败原因
- **AND** trace ID 可以为空
- **AND** trace URL 可以为空
- **AND** API 响应保持成功且不暴露 tracing 初始化细节

### Requirement: 失败任务保留可展示失败摘要

系统 SHALL 在研究任务失败时保留中文可展示失败摘要，并让开发者能通过运行关联字段继续排障。

#### Scenario: 读取失败任务

- **WHEN** 用户读取一条失败的研究任务
- **THEN** 系统返回状态 `failed`
- **AND** 系统返回中文可理解的失败原因
- **AND** 系统返回当前运行 ID
- **AND** 如果失败运行创建过 trace，系统返回 trace ID
- **AND** 失败原因不包含敏感凭证、原始异常堆栈或内部自增 ID
