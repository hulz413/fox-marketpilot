## ADDED Requirements

### Requirement: 系统提供内部质量面板页面

系统 SHALL 提供一个面向团队的内部质量面板，用于集中查看已完成研究任务的质量状态和复查入口。

#### Scenario: 打开内部质量面板

- **WHEN** 团队打开内部质量面板路由
- **THEN** 页面展示中文内部质量复查界面
- **AND** 页面提供选择或浏览研究任务的入口
- **AND** 页面说明质量结果是内部复查信号，不代表商机、需求、供给、利润或市场机会已经被证明

#### Scenario: 演示用户菜单提供内部入口

- **WHEN** 团队打开产品页右上角的演示用户菜单
- **THEN** 系统展示内部质量复查入口
- **AND** 团队可以从该入口进入 `/internal/quality`

#### Scenario: 内部面板不进入一级导航和用户侧内容页

- **WHEN** 用户查看产品一级导航、研究进度页、商机详情页、报告页或公开分享页
- **THEN** 系统不展示内部质量面板入口
- **AND** 系统不在这些用户侧页面展示 RAG 检索评测分数、生成质量评测结果、readiness 检查项或内部错误摘要

#### Scenario: 内部路由不声称提供权限隔离

- **WHEN** 团队查看内部质量面板
- **THEN** 页面不得把内部路由描述为登录、角色权限或访问控制能力
- **AND** 如果需要公网访问保护，应由部署层或后续认证 change 处理

### Requirement: 面板支持选择已完成研究任务

系统 SHALL 允许团队在内部质量面板中查找并选择已完成研究任务，用于查看或触发质量复查。

#### Scenario: 展示可复查研究任务

- **WHEN** 内部质量面板加载研究任务列表
- **THEN** 系统展示未软删除研究任务的公开 UUID、标题、状态、当前阶段、创建时间和更新时间
- **AND** 已完成任务可以进入质量详情
- **AND** 页面不展示研究任务内部自增 ID

#### Scenario: 处理没有已完成任务

- **WHEN** 系统没有可复查的已完成研究任务
- **THEN** 面板展示中文空状态
- **AND** 空状态提示团队先完成一次研究任务后再运行质量复查
- **AND** 页面不展示静态 demo 质量结果作为替代

#### Scenario: 未完成任务不可运行质量复查

- **WHEN** 团队选择状态不是 `completed` 的研究任务
- **THEN** 面板可以展示任务状态摘要
- **AND** 面板不得提供会把该任务标记为可演示的操作
- **AND** 如果团队触发质量运行，系统返回中文可理解的拒绝原因且不修改研究任务状态

### Requirement: 面板展示最近研究质量就绪检查

系统 SHALL 在内部质量面板中展示所选研究任务的最近 readiness run 摘要。

#### Scenario: 展示最近 readiness 摘要

- **WHEN** 团队选择一条已完成研究任务且存在最近 readiness run
- **THEN** 面板展示 readiness run 公开 UUID、整体状态、运行状态、中文摘要、过期状态、开始时间和完成时间
- **AND** 面板展示检查项状态、严重程度、摘要、可操作原因和建议动作
- **AND** 面板展示聚合指标但不展示 RAG chunk 原文、完整网页正文、内部自增 ID 或原始异常堆栈

#### Scenario: 缺少 readiness run

- **WHEN** 团队选择一条已完成研究任务但不存在 readiness run
- **THEN** 面板展示未检查状态
- **AND** 面板提供运行研究质量就绪检查的操作
- **AND** 未检查状态不得被展示为 `ready`、`warning` 或 `failed` 结论

#### Scenario: readiness 过期

- **WHEN** 最近 readiness run 的研究 run ID 与当前研究任务 run ID 不一致
- **THEN** 面板展示已过期状态
- **AND** 面板提示团队重新运行研究质量就绪检查
- **AND** 已过期 readiness run 不作为当前任务的可演示结论

### Requirement: 面板支持触发研究质量就绪检查

系统 SHALL 允许团队从内部质量面板对已完成研究任务触发 readiness run。

#### Scenario: 成功触发 readiness run

- **WHEN** 团队在内部质量面板对已完成研究任务点击运行质量就绪检查
- **THEN** 系统创建新的 readiness run
- **AND** 面板展示运行中状态，完成后刷新最近 readiness 摘要
- **AND** readiness 运行不修改研究任务状态、商机结果、来源、RAG chunks、增强分析、评测结果或分享记录

#### Scenario: readiness run 失败

- **WHEN** readiness run 创建或执行失败
- **THEN** 面板展示中文安全错误摘要
- **AND** 页面保留已有质量结果和研究结果入口
- **AND** 系统不得把失败的 readiness run 展示为可演示结论

### Requirement: 面板支持触发和读取生成质量评测

系统 SHALL 允许团队从内部质量面板触发生成质量评测，并读取所选任务的最近 generation evaluation run 摘要。

#### Scenario: 成功触发生成质量评测

- **WHEN** 团队在内部质量面板对已完成研究任务点击运行生成质量评测
- **THEN** 系统创建新的 generation evaluation run
- **AND** 系统复用现有生成质量评测 service 和默认启用 case
- **AND** 面板展示运行完成后的整体状态、case 计数、rubric 维度摘要、中文摘要和安全错误摘要
- **AND** 系统不在响应中暴露完整 prompt、完整用户输入、完整网页正文、完整 case 快照、内部自增 ID 或原始异常堆栈

#### Scenario: 读取最近生成质量评测

- **WHEN** 团队选择一条已完成研究任务
- **THEN** 面板读取最近未软删除的 generation evaluation run
- **AND** 如果不存在 evaluation run，面板展示未评测状态并提供运行入口
- **AND** 如果最近 evaluation run 已过期，面板提示团队重新运行生成质量评测

#### Scenario: 生成质量评测失败不阻断主流程

- **WHEN** generation evaluation run 创建、评分或读取失败
- **THEN** 面板展示中文安全错误摘要
- **AND** 系统不修改研究任务状态、当前阶段、商机结果、增强分析、readiness run、RAG 评测结果或分享记录
- **AND** 用户侧研究进度、商机详情、报告和分享流程不受影响

### Requirement: 面板展示 RAG 质量摘要

系统 SHALL 在内部质量面板中展示 readiness run 汇总的 RAG 索引健康和 RAG 检索评测摘要。

#### Scenario: 展示 RAG 索引健康和检索指标

- **WHEN** 最近 readiness run 包含 RAG 索引健康或 RAG 检索评测检查项
- **THEN** 面板展示来源数、chunk 数、embedding 状态、评测运行公开 UUID、case 计数和 P0 检索指标摘要
- **AND** 面板展示 skipped、warning 或 failed 的中文原因
- **AND** 面板不展示完整 evidence chunk、完整网页正文、内部自增 ID 或 API key

#### Scenario: 缺少 RAG 摘要

- **WHEN** 最近 readiness run 不包含 RAG 检索评测摘要
- **THEN** 面板展示中文未检查或无可用 RAG 摘要状态
- **AND** 面板提示团队运行 readiness run 以刷新 RAG 质量摘要
- **AND** 缺少 RAG 摘要不得阻止团队查看生成质量评测摘要

### Requirement: 内部质量 API 保持安全和可观测

系统 SHALL 为内部质量面板使用的 API 提供安全输出、可理解错误和内部观测信息。

#### Scenario: API 输出不泄露敏感信息

- **WHEN** 内部质量面板读取 readiness run、generation evaluation run 或相关任务摘要
- **THEN** API 响应只包含公开 UUID、状态、聚合指标、中文摘要、可操作原因和安全错误摘要
- **AND** API 响应不包含内部自增 ID、API key、完整请求头、完整 prompt、完整网页正文、RAG chunk 原文、原始异常堆栈或内部配置

#### Scenario: 质量运行保留内部观测

- **WHEN** 团队从内部质量面板触发 readiness run 或 generation evaluation run
- **THEN** 系统记录研究任务公开 UUID、质量运行公开 UUID、研究 run ID、运行状态、耗时和安全错误摘要
- **AND** 如果 LangSmith tracing 已启用，系统可以复用现有 readiness 或 generation evaluation tracing metadata
- **AND** trace 或日志 metadata 不包含 API key、完整 prompt、完整网页正文、RAG chunk 原文、原始异常堆栈或内部自增 ID
