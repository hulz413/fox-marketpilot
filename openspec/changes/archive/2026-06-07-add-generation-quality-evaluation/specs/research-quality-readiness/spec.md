## MODIFIED Requirements

### Requirement: 系统检查生成内容展示质量

系统 SHALL 在质量就绪检查中对用户可见研究结果和增强分析执行确定性 smoke check，并纳入最近一次生成质量评测摘要。

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

#### Scenario: 纳入生成质量评测摘要

- **WHEN** readiness runner 检查一条已完成研究任务且存在最近 generation evaluation run
- **THEN** 系统读取该 evaluation run 的公开 UUID、整体状态、case 计数、rubric 维度摘要、中文摘要和 stale 状态
- **AND** readiness run 保存生成质量评测检查项摘要和 evaluation run 公开 UUID
- **AND** 如果 generation evaluation run 为 `failed` 或已过期，生成内容展示质量检查至少标记为 warning
- **AND** readiness 响应不返回完整 case 快照、完整 prompt、完整网页正文、原始异常堆栈或内部自增 ID

#### Scenario: 缺少生成质量评测时保留 smoke check

- **WHEN** readiness runner 检查一条已完成研究任务但不存在 generation evaluation run
- **THEN** 系统继续执行确定性生成内容 smoke check
- **AND** 生成质量评测检查项标记为未检查、warning 或等价内部状态
- **AND** 系统可以提示团队运行生成质量评测
- **AND** readiness 检查不因为缺少 generation evaluation run 而修改研究任务状态或删除已有结果
