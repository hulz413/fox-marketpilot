## ADDED Requirements

### Requirement: 系统创建研究质量就绪检查运行

系统 SHALL 支持团队对已完成研究任务运行内部质量就绪检查，并保存可读取的 readiness run。

#### Scenario: 对已完成任务运行就绪检查

- **WHEN** 团队对一条状态为 `completed` 且未软删除的研究任务触发质量就绪检查
- **THEN** 系统创建一条 readiness run
- **AND** readiness run 关联研究任务公开 UUID 和检查时的研究 run ID
- **AND** 系统保存检查运行状态、整体就绪状态、中文摘要、检查项明细、汇总指标、开始时间和完成时间
- **AND** 系统不在响应中暴露研究任务、商机、来源、RAG chunk、评测运行或 readiness run 的内部自增 ID

#### Scenario: 拒绝未完成任务标记为可演示

- **WHEN** 团队对状态不是 `completed` 的研究任务触发质量就绪检查
- **THEN** 系统不返回 `ready` 结论
- **AND** 系统返回中文可理解的错误或保存 `failed` readiness run
- **AND** 系统不修改研究任务状态、当前阶段或已有研究结果

#### Scenario: 读取最近一次就绪检查

- **WHEN** 前端或内部工具读取一条研究任务的最近 readiness run
- **THEN** 系统默认只返回 `deleted_at` 为空的最近记录
- **AND** 响应包含 readiness run 公开 UUID、任务公开 UUID、研究 run ID、整体状态、检查项摘要、汇总指标和安全错误摘要
- **AND** 如果不存在 readiness run，系统返回未检查状态或空结果，不把任务误判为 failed

#### Scenario: 任务重新运行后标记检查结果过期

- **WHEN** 研究任务当前 run ID 与最近 readiness run 保存的研究 run ID 不一致
- **THEN** 系统将该 readiness run 标记为 stale 或在响应中提供等价过期标识
- **AND** 前端可以提示团队重新运行质量就绪检查
- **AND** 过期 readiness run 不作为当前任务的可演示结论

### Requirement: 系统检查研究阶段完整性

系统 SHALL 在质量就绪检查中验证当前研究 run 的关键阶段是否完整，并输出可操作的阶段检查结果。

#### Scenario: 关键阶段全部可确认

- **WHEN** readiness runner 检查一条已完成研究任务的当前 run
- **THEN** 系统读取当前 run 的阶段事件
- **AND** 系统检查基础推荐、结果保存、来源收集、RAG 证据索引、需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划阶段
- **AND** 每个阶段检查项包含阶段状态、耗时或完成时间、缺失原因或失败摘要
- **AND** 关键阶段全部完成或可接受降级时，阶段完整性检查为 pass 或 warning

#### Scenario: 基础商机结果缺失

- **WHEN** 研究任务状态为 `completed` 但不存在 active 商机结果
- **THEN** 阶段完整性检查标记为 failed
- **AND** 整体就绪状态不得为 `ready`
- **AND** 系统提供中文原因，说明基础商机结果缺失

#### Scenario: 增强阶段部分缺失

- **WHEN** 基础商机结果存在，但需求洞察、货源候选、竞品参考、验证预算、风险复核或行动计划存在缺失、跳过或失败
- **THEN** 阶段完整性检查至少标记为 warning
- **AND** 检查项列出缺失或失败的增强阶段
- **AND** 系统仍保留已生成的商机结果和其他增强分析

### Requirement: 系统检查 RAG 索引和检索健康

系统 SHALL 在质量就绪检查中汇总当前任务的来源、RAG chunks、embedding 状态和 RAG 检索评测摘要。

#### Scenario: RAG 索引健康检查通过

- **WHEN** 当前任务存在 active 研究来源和 active RAG evidence chunks
- **THEN** 系统统计 active 来源数、active chunk 数、已生成 embedding 的 chunk 数、embedding model 和 embedding dimension
- **AND** 系统确认检索默认限制在当前任务范围内
- **AND** RAG 索引健康检查包含索引状态、fallback 状态和安全摘要

#### Scenario: 来源存在但 RAG chunk 缺失

- **WHEN** 当前任务存在 active 研究来源但不存在 active RAG evidence chunks
- **THEN** RAG 索引健康检查标记为 warning 或 failed
- **AND** 系统提供中文原因，说明证据索引缺失或被跳过
- **AND** 系统不删除已有研究来源或商机结果

#### Scenario: embedding 不可用时降级

- **WHEN** RAG evidence chunks 因 embedding provider 缺失、调用失败或配置无效而降级
- **THEN** 系统在 RAG 索引健康检查中记录 fallback 或 skipped 原因
- **AND** readiness run 保留安全错误摘要
- **AND** 研究任务主流程不因 readiness 检查失败而进入 failed

#### Scenario: 纳入 RAG 检索评测摘要

- **WHEN** 当前任务存在可用 RAG chunks 且团队运行 readiness 检查
- **THEN** 系统运行或读取同任务的 RAG 检索质量评测摘要
- **AND** readiness run 保存评测运行公开 UUID、状态、case 总数、完成数、失败数、跳过数和 P0 检索指标摘要
- **AND** 系统不在 readiness 响应中返回完整 chunk 文本、完整网页正文或内部自增 ID

#### Scenario: RAG 检索评测失败不阻断主流程

- **WHEN** RAG 检索评测在 readiness 检查中失败、部分失败或没有可用 case
- **THEN** readiness run 将 RAG 检索评测检查标记为 warning 或 failed
- **AND** 系统保存中文安全错误摘要
- **AND** 系统不修改研究任务状态、不删除 RAG chunks、不删除已有评测结果

### Requirement: 系统检查生成内容展示质量

系统 SHALL 在质量就绪检查中对用户可见研究结果和增强分析执行确定性 smoke check。

#### Scenario: 生成内容结构完整

- **WHEN** readiness runner 检查已完成研究任务的生成内容
- **THEN** 系统检查每个 active 商机是否具备名称、产品方向、目标人群、推荐理由、渠道、价格带、粗略利润、风险等级和下一步摘要
- **AND** 系统检查每个 active 商机是否具备需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划记录或明确缺失原因
- **AND** 生成内容检查项保存缺失字段、缺失记录和受影响商机的公开 UUID

#### Scenario: 生成内容为空或数量不足

- **WHEN** 商机结果少于 MVP 需要的 3 个 active 商机，或关键增强分析为空
- **THEN** 生成内容检查标记为 warning 或 failed
- **AND** 整体就绪状态不得为 `ready`
- **AND** 系统提供中文可操作原因

#### Scenario: 用户可见文案保持谨慎边界

- **WHEN** 系统检查需求洞察、货源候选、竞品参考、验证预算、风险复核、行动计划、报告摘要或分享快照中的用户可见文本
- **THEN** 系统验证关键结论保持初步参考、候选方向、待验证、需要确认或等价谨慎表达
- **AND** 如果文案误称已经完成公开市场核验、供应商确认、库存确认、利润保证、自动联系供应商、自动发布内容或真实验证，系统将检查标记为 warning 或 failed
- **AND** readiness 结果说明该问题是内部质量复查提示，不作为用户侧商机结论

### Requirement: 前端展示内部演示就绪状态

系统 SHALL 在前端应用内展示研究质量就绪状态，帮助团队准备演示，同时避免把内部评测暴露给公开报告读者。

#### Scenario: 任务进度页展示演示就绪检查

- **WHEN** 用户打开一条已完成研究任务的进度页
- **THEN** 前端展示「演示就绪检查」面板或等价内部检查区域
- **AND** 面板展示最近 readiness run 的整体状态、检查时间、检查项摘要和可操作原因
- **AND** 如果尚未检查，面板提供运行检查入口
- **AND** 如果检查结果过期，面板提示重新运行检查

#### Scenario: 任务进度页运行就绪检查

- **WHEN** 用户在任务进度页点击运行质量就绪检查
- **THEN** 前端调用内部 readiness API
- **AND** 检查完成后刷新并展示最新 readiness run
- **AND** 检查失败时展示中文安全错误摘要，不影响商机推荐、报告和来源入口

#### Scenario: 研究历史列表展示轻量状态

- **WHEN** 用户打开研究历史列表
- **THEN** 前端可以为已完成任务展示 readiness badge
- **AND** badge 状态包含未检查、可演示、需复查、检查失败或已过期中的一种等价表达
- **AND** 历史列表不展示 RAG chunk 文本、完整评测明细、trace metadata 或内部自增 ID

#### Scenario: 公开分享页不展示内部质量检查

- **WHEN** 外部读者打开公开报告分享页
- **THEN** 页面不读取或展示 readiness run
- **AND** 页面不展示 RAG 检索评测分数、内部检查项、trace URL、阶段调试信息或安全错误摘要
- **AND** 公开分享页继续只展示只读报告快照和谨慎边界说明

### Requirement: 研究质量就绪检查保持可观测和安全边界

系统 SHALL 为 readiness 检查提供足够的内部观测信息，并保证检查不会破坏用户研究主流程或泄露敏感信息。

#### Scenario: readiness 检查接入 trace 和日志

- **WHEN** 系统运行 readiness 检查
- **THEN** 系统记录 readiness run UUID、研究任务 UUID、研究 run ID、检查项状态、耗时和安全错误摘要
- **AND** 如果 LangSmith tracing 已启用，系统可以记录 readiness trace 或 metadata
- **AND** trace metadata 不包含 API key、完整网页正文、chunk 原文、原始异常堆栈或内部自增 ID

#### Scenario: readiness 检查失败不影响研究闭环

- **WHEN** readiness 检查运行失败、部分失败或未配置
- **THEN** 用户创建研究任务、启动研究、查看进度、查看商机详情、查看报告、生成分享和撤销分享的流程不受影响
- **AND** 系统不因为 readiness 检查失败而修改研究任务状态
- **AND** 系统不因为 readiness 检查失败而删除已有商机、来源、RAG chunks、增强分析、RAG 评测结果或分享记录

#### Scenario: readiness 输出保持安全

- **WHEN** 前端或内部工具读取 readiness run
- **THEN** 响应只包含公开 UUID、安全摘要、聚合指标、检查项状态和可操作原因
- **AND** 响应不包含内部自增 ID、API key、完整请求头、完整网页正文、chunk 原文、原始异常堆栈或内部配置
- **AND** readiness 状态不得被描述为需求、供给、竞品、风险、利润或市场机会已经被证明
