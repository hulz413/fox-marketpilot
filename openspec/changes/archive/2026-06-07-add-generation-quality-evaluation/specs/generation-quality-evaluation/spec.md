## ADDED Requirements

### Requirement: 系统维护中文生成质量评测集

系统 SHALL 提供面向中文商机研究场景的生成质量评测集，用于复跑已完成研究结果的约束遵守和语义质量检查。

#### Scenario: 评测集覆盖典型输入约束

- **WHEN** 团队加载默认生成质量评测集
- **THEN** 系统提供多个中文评测 case
- **AND** case 覆盖预算上限、目标渠道、偏好品类、排除品类、目标人群、期望利润、供给来源偏好和谨慎边界
- **AND** 每个 case 包含名称、类别、输入约束、期望判断点、rubric、启用状态和评分说明
- **AND** 每个 case 使用公开 UUID 作为稳定标识

#### Scenario: 只使用启用的评测 case

- **WHEN** 系统准备一次生成质量评测运行
- **THEN** 系统默认只选择启用且未软删除的评测 case
- **AND** 系统不读取 `deleted_at` 非空的评测 case
- **AND** 系统允许按类别筛选评测 case

#### Scenario: 评测集内容可版本化和复查

- **WHEN** 评测 case 来自仓库内默认 fixture 或数据库记录
- **THEN** 系统保留 case 的输入约束、期望判断点、rubric 和评分说明
- **AND** 系统在评测结果中保存本次运行使用的 case 快照或等价内容
- **AND** 后续 fixture 修改不会改变历史评测结果的可解释性

### Requirement: 系统运行生成质量评测

系统 SHALL 支持对一条已完成研究任务运行内部生成质量评测，并保存 evaluation run 和逐 case 结果。

#### Scenario: 成功运行一次生成质量评测

- **WHEN** 团队对一条状态为 `completed` 且未软删除的研究任务触发生成质量评测
- **THEN** 系统创建一条 generation evaluation run
- **AND** run 关联研究任务公开 UUID 和当前研究 run ID
- **AND** 系统读取该任务 active 商机结果、需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划
- **AND** 系统为每个启用 case 保存一条 evaluation result
- **AND** 系统不在响应中暴露研究任务、商机、增强分析、评测 case、评测 run 或 result 的内部自增 ID

#### Scenario: 拒绝未完成任务评测

- **WHEN** 团队对状态不是 `completed` 的研究任务触发生成质量评测
- **THEN** 系统不返回 `passed` 结论
- **AND** 系统返回中文可理解的错误或保存 `failed` evaluation run
- **AND** 系统不修改研究任务状态、当前阶段、已有商机结果或增强分析

#### Scenario: 单个 case 失败不终止整次评测

- **WHEN** 某个评测 case 的评分或数据读取失败
- **THEN** 系统将该 case result 标记为 `failed`
- **AND** 系统保存中文安全错误摘要
- **AND** 系统继续执行后续评测 case
- **AND** 整次 evaluation run 可以以 `completed`、`partial` 或 `failed` 状态结束

#### Scenario: 读取最近一次生成质量评测

- **WHEN** 内部工具或 readiness runner 读取一条研究任务的最近 generation evaluation run
- **THEN** 系统默认只返回 `deleted_at` 为空的最近记录
- **AND** 响应包含 evaluation run 公开 UUID、任务公开 UUID、研究 run ID、整体状态、case 计数、指标摘要、中文摘要和安全错误摘要
- **AND** 如果不存在 evaluation run，系统返回未评测状态或空结果，不把任务误判为 failed

### Requirement: 系统评估生成结果的业务约束和语义质量

系统 SHALL 使用固定 rubric 检查已完成研究结果是否满足任务输入约束、结构完整、语义一致、风险具体、行动可执行并保持谨慎边界。

#### Scenario: 检查任务输入约束遵守

- **WHEN** evaluation runner 检查一条已完成研究任务
- **THEN** 系统检查商机结果是否违反预算上限、目标渠道、排除品类、目标人群、期望利润或供给来源偏好
- **AND** 违反约束的 case result 至少标记为 `warning`
- **AND** case result 保存受影响商机的公开 UUID 和中文原因

#### Scenario: 检查结果数量和字段完整性

- **WHEN** evaluation runner 检查 active 商机结果
- **THEN** 系统确认商机数量满足 MVP 需要的 3 到 5 个
- **AND** 系统检查每个商机具备名称、产品方向、目标人群、推荐理由、适合渠道、价格带、粗略利润空间、风险等级、推荐优先级和下一步建议摘要
- **AND** 缺失字段或数量不足时，case result 标记为 `warning` 或 `failed`

#### Scenario: 检查增强分析一致性

- **WHEN** evaluation runner 检查增强分析
- **THEN** 系统检查需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划是否与对应商机主题一致
- **AND** 系统检查增强分析是否引用错误商机、明显偏离目标人群或与排除条件冲突
- **AND** 不一致结果保存对应模块、商机公开 UUID 和中文原因

#### Scenario: 检查风险和行动建议质量

- **WHEN** evaluation runner 检查风险复核和行动计划
- **THEN** 系统验证风险说明具体到质量、履约、售后、竞争、合规或平台规则等可理解维度
- **AND** 系统验证行动计划包含可执行验证动作、询盘话术或上架前检查项
- **AND** 空泛风险或不可执行行动建议至少标记为 `warning`

#### Scenario: 检查用户可见文案谨慎边界

- **WHEN** evaluation runner 检查商机结果、报告摘要、增强分析或分享快照中的用户可见文本
- **THEN** 系统验证关键结论保持初步参考、候选方向、待验证、需要确认或等价谨慎表达
- **AND** 如果文案误称已经完成公开市场核验、供应商确认、库存确认、利润保证、自动联系供应商、自动发布内容或真实验证，系统将 case result 标记为 `warning` 或 `failed`
- **AND** 评测结果说明该问题是内部生成质量复查提示，不作为用户侧商机结论

### Requirement: 系统汇总生成质量评测指标

系统 SHALL 为每个 evaluation run 汇总 case 状态、rubric 维度结果和整体生成质量状态。

#### Scenario: 计算整体评测状态

- **WHEN** 一次生成质量评测运行结束
- **THEN** 系统计算 case 总数、通过数、warning 数、失败数和跳过数
- **AND** 系统基于 case result 汇总整体状态为 `passed`、`warning` 或 `failed`
- **AND** 只要存在 failed case，整体状态不得为 `passed`
- **AND** 系统保存中文摘要和主要复查原因

#### Scenario: 汇总 rubric 维度

- **WHEN** 系统保存 evaluation run 指标摘要
- **THEN** 指标摘要包含约束遵守、结构完整、增强一致性、风险质量、行动质量和谨慎边界等维度
- **AND** 每个维度包含通过数、warning 数、失败数或等价通过率
- **AND** 指标摘要不包含完整 prompt、完整用户输入、完整网页正文或内部自增 ID

#### Scenario: 任务重新运行后标记评测结果过期

- **WHEN** 研究任务当前 run ID 与最近 generation evaluation run 保存的研究 run ID 不一致
- **THEN** 系统将该 evaluation run 标记为 stale 或在响应中提供等价过期标识
- **AND** 过期 evaluation run 不作为当前任务的生成质量结论
- **AND** 内部工具或 readiness runner 可以提示团队重新运行生成质量评测

### Requirement: 生成质量评测接入内部观测

系统 SHALL 为生成质量评测提供内部日志和可选 LangSmith tracing metadata，便于团队排查评测失败或质量问题。

#### Scenario: LangSmith tracing 启用时记录评测 metadata

- **WHEN** LangSmith tracing 已启用且团队运行生成质量评测
- **THEN** 系统为 evaluation run 创建或进入可追踪 trace
- **AND** trace metadata 包含 evaluation run UUID、研究任务 UUID、可空研究 run ID、case 数量、整体状态和 rubric 维度摘要
- **AND** 每个 case 的 trace metadata 包含 case UUID、类别、状态、主要原因和受影响商机公开 UUID
- **AND** trace metadata 不包含 API key、完整 prompt、完整网页正文、原始异常堆栈或内部自增 ID

#### Scenario: LangSmith 未配置时评测仍可运行

- **WHEN** LangSmith tracing 未配置
- **THEN** 系统仍可加载评测集并运行生成质量评测
- **AND** 系统仍保存本地 evaluation run 和 result
- **AND** 系统不因为缺少 LangSmith API key 而让评测运行失败

### Requirement: 生成质量评测保持内部安全边界

系统 SHALL 将生成质量评测作为内部质量观察能力，避免影响用户研究主流程或泄露敏感信息。

#### Scenario: 评测不阻断用户研究主流程

- **WHEN** 生成质量评测运行失败、部分失败或未配置
- **THEN** 用户创建研究任务、启动研究、查看进度、查看商机详情、查看报告、生成分享和撤销分享的流程不受影响
- **AND** 系统不因为评测失败而修改研究任务状态
- **AND** 系统不因为评测失败而删除已有商机、来源、RAG chunks、增强分析、RAG 评测结果、readiness run 或分享记录

#### Scenario: 评测结果不作为用户可见商机结论

- **WHEN** 用户查看商机详情、基础报告、来源透明度信息或公开分享页
- **THEN** 系统不把内部生成质量评测状态展示为商机可信度、市场成立度或推荐排序依据
- **AND** 系统不把生成质量评测结果描述为需求、供给、竞品、利润、风险或市场机会已经被证明
- **AND** 用户可见内容继续使用待验证和初步参考表达

#### Scenario: 评测输出保持安全

- **WHEN** 内部工具、readiness runner 或 API 读取 generation evaluation run
- **THEN** 响应只包含公开 UUID、安全摘要、聚合指标、case 状态和可操作原因
- **AND** 响应不包含内部自增 ID、API key、完整请求头、完整 prompt、完整网页正文、原始异常堆栈或内部配置
- **AND** 应用日志可以保留任务 UUID、evaluation run UUID、case UUID、错误类型和阶段名用于开发者排障
