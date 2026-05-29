## ADDED Requirements

### Requirement: 研究任务可以进入执行生命周期

系统 SHALL 支持研究任务在创建后进入基础商机研究执行生命周期，同时保持创建任务不自动执行 Agent 的既有行为。

#### Scenario: 任务创建后仍不自动执行

- **WHEN** 用户成功创建研究任务
- **THEN** 任务状态仍为 `created`
- **AND** 当前阶段仍为 `intake`
- **AND** 系统不因创建动作自动调用 LLM
- **AND** 系统不因创建动作自动生成商机结果

#### Scenario: 任务启动后状态更新

- **WHEN** 用户启动研究任务运行
- **THEN** 任务状态可以从 `created` 进入 `queued`
- **AND** 后台执行开始后任务状态可以进入 `running`
- **AND** 执行成功后任务状态可以进入 `completed`
- **AND** 执行失败后任务状态可以进入 `failed`

#### Scenario: 任务读取返回执行状态

- **WHEN** 用户读取任务列表或单个任务
- **THEN** 系统返回任务当前状态
- **AND** 系统返回任务当前阶段
- **AND** 系统返回可为空的运行 ID、trace ID 和失败原因

### Requirement: 已完成研究任务关联商机结果

系统 SHALL 让完成基础商机研究的任务可以被用于查找对应商机推荐结果。

#### Scenario: 完成任务可以进入商机结果

- **WHEN** 一条研究任务状态为 `completed`
- **THEN** 系统能通过该任务 UUID 找到该任务的商机结果列表
- **AND** 前端任务列表可以提供查看商机推荐的入口

#### Scenario: 失败任务保留重试入口信息

- **WHEN** 一条研究任务状态为 `failed`
- **THEN** 系统保留失败原因
- **AND** 前端任务列表或任务详情可以提供重新运行入口
