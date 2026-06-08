## ADDED Requirements

### Requirement: 并行研究分析分支需要可观测

系统 SHALL 在基础商机研究运行中记录并行研究分析分支的阶段事件、trace metadata 和安全日志，使开发者可以区分同一 run 下的需求洞察、货源候选、竞品参考和研究发现汇总状态。

#### Scenario: 并行分支启动时记录阶段事件

- **WHEN** 系统进入 `analyze_research` 阶段并启动专业分析分支
- **THEN** 系统为 `generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references` 分别记录 running 阶段事件
- **AND** 每条阶段事件关联同一任务 UUID、运行 ID 和可空 trace ID
- **AND** 阶段 metadata 标记该事件属于 `research_analysis` 分支组
- **AND** 系统不把内部自增 ID 写入用户可见信息

#### Scenario: 并行分支完成时记录独立结果

- **WHEN** 任一专业分析分支完成
- **THEN** 系统记录该分支的 completed 阶段事件、完成时间和耗时
- **AND** 阶段 metadata 包含该分支的结果状态、保存数量和来源或检索统计
- **AND** 其他仍在运行的专业分析分支不会被标记为完成或失败

#### Scenario: 并行分支失败时保留安全摘要

- **WHEN** 任一专业分析分支失败但基础商机结果已经保存
- **THEN** 系统记录该分支的 failed 阶段事件、失败时间、耗时和中文安全错误摘要
- **AND** 系统不把 LLM API key、外部搜索凭证、完整 prompt、完整网页正文、原始异常堆栈或内部自增 ID 写入用户可见信息
- **AND** 同一并行分支组中的其他分支仍可以继续完成

#### Scenario: 汇总阶段记录分支状态

- **WHEN** `generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references` 均进入可汇总状态
- **THEN** 系统记录 `synthesize_research_findings` 阶段事件
- **AND** 汇总阶段 metadata 包含三个专业分析分支的 completed、failed 或 skipped 状态
- **AND** LangSmith tracing 启用时汇总阶段可在同一条研究运行 trace 下关联查看
- **AND** 应用日志包含任务 UUID、运行 ID、trace ID、阶段、分支状态和耗时字段

#### Scenario: 并行分支不共享不安全运行上下文

- **WHEN** 系统并行执行专业分析分支
- **THEN** 每个分支的阶段事件写入和业务结果保存使用可独立提交的运行上下文
- **AND** 任一分支回滚不会回滚其他已经完成分支的结果或阶段事件
- **AND** 系统仍通过运行 ID 区分重新运行产生的阶段历史
