## 1. 阶段契约与上下文准备

- [x] 1.1 在研究任务阶段枚举、阶段文案和相关前端映射中新增 `analyze_research` 与 `synthesize_research_findings`。
- [x] 1.2 梳理 `ResearchGraphState`，增加可归并的并行分析分支结果字段，并避免并行分支依赖共享 ORM 对象作为输出。
- [x] 1.3 调整需求洞察、货源候选和竞品参考的上下文构建，移除当前 run 内 sibling output 的硬依赖，改为主要依赖任务、基础商机、来源和 RAG 证据。

## 2. LangGraph 并行编排

- [x] 2.1 实现并行分析分支 runner，使每个分支使用独立 DB session 重新加载任务并独立提交业务结果与阶段事件。
- [x] 2.2 增加 `synthesize_research_findings` 节点，汇总三个专业分析分支的状态、保存数量、来源关联数量、检索统计和安全失败摘要。
- [x] 2.3 调整 `build_research_graph()` 边关系：`index_rag_evidence` fan-out 到需求、货源和竞品分支，再 fan-in 到 `synthesize_research_findings`。
- [x] 2.4 确保 `estimate_validation_budgets`、`review_opportunity_risks` 和 `create_action_plans` 只在汇总阶段之后执行。
- [x] 2.5 保持 local/test 环境 deterministic fallback，不让自动化测试依赖外部 LLM、搜索或网络服务。

## 3. 可观测性与进度展示

- [x] 3.1 为并行分支阶段事件写入 `research_analysis` 分支组 metadata，并记录分支状态、耗时、保存数量和安全失败摘要。
- [x] 3.2 确保 LangSmith tracing 启用时并行分支和 `synthesize_research_findings` 可关联到同一 run trace。
- [x] 3.3 调整研究进度读取与前端时间线，让 `analyze_research` 阶段展示需求、货源和竞品多个分支的运行中、完成或失败状态。
- [x] 3.4 更新进度页谨慎中文文案，避免把候选、参考和初步分析表达成已核验结论。

## 4. 测试与验证

- [x] 4.1 增加后端 graph 测试，验证来源和 RAG 之后会启动三个专业分析分支，并在汇总后继续预算、风险和行动计划。
- [x] 4.2 增加并行分支失败隔离测试，验证任一增强分析分支失败不会覆盖基础商机结果，也不会阻止其他分支完成。
- [x] 4.3 增加阶段事件测试，验证并行分支和汇总阶段记录 run ID、trace ID、状态、耗时和安全 metadata。
- [x] 4.4 增加或更新前端进度 UI 契约测试，覆盖 `analyze_research`、分支部分失败和 `synthesize_research_findings` 展示。
- [x] 4.5 运行后端测试、后端 lint、前端测试或 lint，并记录无法运行的验证项和原因。
