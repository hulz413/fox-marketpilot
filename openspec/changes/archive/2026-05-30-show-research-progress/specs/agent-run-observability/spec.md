## ADDED Requirements

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
