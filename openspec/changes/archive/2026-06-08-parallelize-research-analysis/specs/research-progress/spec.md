## ADDED Requirements

### Requirement: 进度页展示并行研究分析阶段

系统 SHALL 在研究任务进度页展示并行研究分析阶段，让用户理解需求洞察、货源候选和竞品参考可以同时运行，并在三个分支完成、跳过或安全失败后进入研究发现汇总和后续评估阶段。

#### Scenario: 并行分析运行中展示多个分支

- **WHEN** 用户打开状态为 `running` 且当前阶段为 `analyze_research` 的研究任务进度页
- **THEN** 系统展示正在并行分析需求洞察、货源候选和竞品参考的中文说明
- **AND** 阶段时间线展示 `generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references` 的独立运行中、已完成或失败状态
- **AND** 当前阶段文案不暗示只有一个线性分析节点正在执行
- **AND** 文案表达为初步分析、候选方向或待验证参考

#### Scenario: 并行分支部分失败但任务继续

- **WHEN** 用户打开一条并行研究分析中任一分支失败但其他分支仍完成或运行中的研究任务进度页
- **THEN** 系统仍展示任务为运行中或可继续完成的状态
- **AND** 失败分支展示中文可理解的安全摘要
- **AND** 未失败分支展示自身状态
- **AND** 系统不将单个并行分析分支失败误判为基础商机生成失败

#### Scenario: 汇总阶段展示分支结果已收敛

- **WHEN** 用户打开当前阶段为 `synthesize_research_findings` 的研究任务进度页
- **THEN** 系统展示正在汇总需求、货源和竞品研究发现的中文说明
- **AND** 阶段时间线展示三个专业分析分支的最终状态
- **AND** 系统展示后续将继续估算验证预算、复核风险和生成行动计划
- **AND** 用户侧信息不暴露内部自增 ID、完整 prompt、完整网页正文或原始异常堆栈

#### Scenario: 完成任务展示并行分支历史

- **WHEN** 用户打开已完成研究任务的进度页
- **THEN** 系统展示当前 run 已记录的并行专业分析分支历史
- **AND** 每个分支展示完成时间、耗时或安全失败摘要
- **AND** 系统展示 `synthesize_research_findings` 汇总阶段已完成或失败状态
- **AND** 系统保留进入商机推荐和基础报告的入口

#### Scenario: 运行中自动刷新并行阶段

- **WHEN** 进度页读取到任务状态为 `running` 且处于 `analyze_research` 或 `synthesize_research_findings`
- **THEN** 前端定期重新读取任务进度
- **AND** 刷新结果更新各并行分支的开始时间、完成时间、失败摘要和耗时
- **AND** 任务进入 `completed` 或 `failed` 后前端停止运行中轮询
